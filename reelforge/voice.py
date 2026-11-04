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


def _cache_key(text: str, voice_id: str, model: str | None = None) -> str:
    # mirrored in editor/server/api.ts (voice status): keep the two in step
    return hashlib.sha1(f"{model_name(model)}|{voice_id}|{text}".encode("utf-8")).hexdigest()[:10]


def take_path(line: Line, voice_id: str, out_dir: Path, model: str | None = None) -> Path:
    """Where the API take for this exact model + voice + text is cached."""
    return Path(out_dir) / f"{line.id}-{_cache_key(line.text, voice_id, model)}.mp3"


def has_take(line: Line, voice_id: str, out_dir: Path, model: str | None = None) -> bool:
    mp3 = take_path(line, voice_id, out_dir, model)
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
                    model: str | None = None) -> VoicedLine:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model = model_name(model)
    mp3 = take_path(line, voice_id, out_dir, model)
    meta = mp3.with_suffix(".json")
    if not (mp3.exists() and meta.exists()):
        url = URL.format(voice_id=voice_id)
        headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
        body = {"text": line.text, "model_id": model}
        resp, attempt = None, 0
        while resp is None:
            try:
                resp = post(url, headers, body)
            except urllib.error.HTTPError as e:
                if e.code in (400, 404, 422) and body["model_id"] != FALLBACK_MODEL:
                    body = {**body, "model_id": FALLBACK_MODEL}  # v4 not available here: same cache slot
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
