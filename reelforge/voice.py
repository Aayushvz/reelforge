from __future__ import annotations

import base64
import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .align_local import chars_from_words, whisper_words
from .alignment import Char, clean_chars
from .schema import Line

MODEL = "eleven_v3"
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


def _cache_key(text: str, voice_id: str) -> str:
    return hashlib.sha1(f"{MODEL}|{voice_id}|{text}".encode("utf-8")).hexdigest()[:10]


def synthesize_line(line: Line, voice_id: str, out_dir: Path, api_key: str,
                    post=_http_post, retries: int = 3, sleep=time.sleep) -> VoicedLine:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    mp3 = out_dir / f"{line.id}-{_cache_key(line.text, voice_id)}.mp3"
    meta = mp3.with_suffix(".json")
    if not (mp3.exists() and meta.exists()):
        url = URL.format(voice_id=voice_id)
        headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
        body = {"text": line.text, "model_id": MODEL}
        resp = None
        for attempt in range(retries):
            try:
                resp = post(url, headers, body)
                break
            except urllib.error.HTTPError as e:
                if e.code in RETRY_CODES and attempt < retries - 1:
                    sleep(2 ** attempt)
                    continue
                raise VoiceError(f"ElevenLabs failed for {line.id}: HTTP {e.code}") from e
            except urllib.error.URLError as e:
                if attempt < retries - 1:
                    sleep(2 ** attempt)
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
    if not meta.exists() or meta.stat().st_mtime < mp3.stat().st_mtime:
        words = (transcribe or whisper_words)(mp3)
        meta.write_text(json.dumps([list(w) for w in words]), encoding="utf-8")
    words = [tuple(w) for w in json.loads(meta.read_text(encoding="utf-8"))]
    return VoicedLine(line.id, mp3, chars_from_words(words))
