from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .align_local import chars_from_words, whisper_words
from .alignment import Char, clean_chars
from .schema import Line

DEFAULT_MODEL = "eleven_v4"   # newest expressive model; audio tags like [sighs] work
FALLBACK_MODEL = "eleven_v3"  # used when the account or endpoint rejects v4
URL = ("https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"
       "?output_format=mp3_44100_128")
RETRY_CODES = {429, 500, 502, 503, 504}

# Directed delivery (shots-av): the line's emotion becomes an ElevenLabs audio tag that the v3/v4 models perform,
# a stronger one at high intensity and a softer one at low. Tags never reach the captions or the lip sync
# (alignment.clean_chars drops bracketed text). A line that already starts with a tag keeps the writer's own.
DELIVERY = {"neutral": "", "happy": "cheerfully", "sad": "sadly", "worried": "nervously", "surprised": "surprised",
            "smug": "smugly", "deadpan": "deadpan", "confused": "confused", "annoyed": "annoyed",
            "thinking": "thoughtfully", "embarrassed": "sheepishly"}
DELIVERY_STRONG = {"happy": "excited", "sad": "on the verge of tears", "worried": "anxious", "surprised": "shocked",
                   "smug": "teasing", "annoyed": "frustrated", "embarrassed": "flustered", "confused": "bewildered",
                   "thinking": "pondering", "neutral": "", "deadpan": "bone-dry"}


def directed_text(line: Line) -> str:
    text = line.text.strip()
    if text.startswith("["):
        return text
    tags = [(DELIVERY_STRONG if line.intensity >= 0.75 else DELIVERY).get(line.emotion, "")]
    if line.intensity < 0.3:
        tags.append("quietly")
    tags = [t for t in tags if t]
    return f"{' '.join(f'[{t}]' for t in tags)} {text}".strip()


def delivery_key(line: Line) -> str:
    """Part of the cache key, so a new emotion or intensity makes a new take (mirrored in editor/server/api.ts)."""
    return f"{line.emotion}:{line.intensity:.2f}"


def voice_settings(line: Line) -> dict:
    """v3/v4 stability: 0.0 Creative (most emotional range), 0.5 Natural. Intense lines get Creative."""
    return {"stability": 0.0 if line.intensity >= 0.7 else 0.5, "use_speaker_boost": True}


class VoiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class VoicedLine:
    line_id: str
    audio_path: Path
    chars: list[Char]


def _http_post(url: str, headers: dict, body: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def model_name(model: str | None = None) -> str:
    return model or os.environ.get("ELEVENLABS_MODEL") or DEFAULT_MODEL


def _cache_key(text: str, voice_id: str, model: str | None = None, delivery: str = "") -> str:
    # mirrored in editor/server/api.ts (voice status): keep the two in step
    tail = f"|{delivery}" if delivery else ""  # undirected takes keep their old keys (no paid re-generation)
    return hashlib.sha1(f"{model_name(model)}|{voice_id}|{text}{tail}".encode("utf-8")).hexdigest()[:10]


def take_path(line: Line, voice_id: str, out_dir: Path, model: str | None = None, direct: bool = False) -> Path:
    """Where the API take for this exact model + voice + text (+ delivery, when directed) is cached."""
    key = _cache_key(line.text, voice_id, model, delivery_key(line) if direct else "")
    return Path(out_dir) / f"{line.id}-{key}.mp3"


def has_take(line: Line, voice_id: str, out_dir: Path, model: str | None = None, direct: bool = False) -> bool:
    mp3 = take_path(line, voice_id, out_dir, model, direct)
    return mp3.exists() and mp3.with_suffix(".json").exists()


def _detail(e: urllib.error.HTTPError) -> str:
    """ElevenLabs' own error message (never echoes the key), shortened."""
    try:
        d = json.loads(e.read() or b"{}").get("detail")
    except (ValueError, AttributeError, OSError):
        return ""
    msg = d.get("message", "") if isinstance(d, dict) else str(d or "")
    return f": {msg[:200]}" if msg else ""


def synthesize_line(line: Line, voice_id: str, out_dir: Path, api_key: str,
                    post=_http_post, retries: int = 3, sleep=time.sleep,
                    model: str | None = None, direct: bool = False) -> VoicedLine:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model = model_name(model)
    mp3 = take_path(line, voice_id, out_dir, model, direct)
    meta = mp3.with_suffix(".json")
    if not (mp3.exists() and meta.exists()):
        url = URL.format(voice_id=voice_id)
        headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
        body = {"text": directed_text(line) if direct else line.text, "model_id": model}
        if direct:
            body["voice_settings"] = voice_settings(line)
        resp, attempt = None, 0
        while resp is None:
            try:
                resp = post(url, headers, body)
            except urllib.error.HTTPError as e:
                if e.code in (400, 404, 422) and body["model_id"] != FALLBACK_MODEL:
                    body = {**body, "model_id": FALLBACK_MODEL}  # v4 not available here: same cache slot
                    continue
                if e.code in (400, 422) and "voice_settings" in body:  # settings rejected: keep the tags, drop them
                    body = {k: v for k, v in body.items() if k != "voice_settings"}
                    continue
                attempt += 1
                if e.code in RETRY_CODES and attempt < retries:
                    sleep(2 ** (attempt - 1))
                    continue
                raise VoiceError(f"ElevenLabs failed for {line.id}: HTTP {e.code}{_detail(e)}") from e
            except urllib.error.URLError as e:
                attempt += 1
                if attempt < retries:
                    sleep(2 ** (attempt - 1))
                    continue
                raise VoiceError(f"ElevenLabs unreachable for {line.id}: {e.reason}") from e
        mp3.write_bytes(base64.b64decode(resp["audio_base64"]))
        meta.write_text(json.dumps(resp["alignment"]), encoding="utf-8")
    a = json.loads(meta.read_text(encoding="utf-8"))
    chars = clean_chars(a["characters"], a["character_start_times_seconds"],
                        a["character_end_times_seconds"])
    return VoicedLine(line.id, mp3, chars)


def import_line(line: Line, audio_dir: Path, transcribe=None) -> VoicedLine:
    """Use a pre-generated <line.id>.mp3 (e.g. from the ElevenLabs web app); align locally."""
    mp3 = Path(audio_dir) / f"{line.id}.mp3"
    if not mp3.exists():
        raise VoiceError(f"missing imported audio {mp3}")
    meta = mp3.with_suffix(".align.json")
    sha = hashlib.sha1(mp3.read_bytes()).hexdigest()
    cached = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else None
    if isinstance(cached, list):  # legacy cache (no hash): trust it only if newer than the audio
        fresh = meta.stat().st_mtime >= mp3.stat().st_mtime
    else:
        fresh = cached is not None and cached.get("sha1") == sha
    if not fresh:
        words = [tuple(w) for w in (transcribe or whisper_words)(mp3)]
        if not words:
            raise VoiceError(f"no speech found in {mp3}")
        cached = {"sha1": sha, "words": [list(w) for w in words]}
        meta.write_text(json.dumps(cached), encoding="utf-8")
    words = [tuple(w) for w in (cached if isinstance(cached, list) else cached["words"])]
    return VoicedLine(line.id, mp3, chars_from_words(words))
