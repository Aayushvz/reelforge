"""Local alignment for audio generated outside the API (e.g. ElevenLabs web app)."""
from __future__ import annotations

from pathlib import Path

from .alignment import Char


def chars_from_words(words: list[tuple[str, float, float]]) -> list[Char]:
    out: list[Char] = []
    for raw, s, e in words:
        w = raw.strip()
        if not w:
            continue
        if out:
            prev_end = out[-1].end
            out.append(Char(" ", prev_end, max(prev_end, s)))
        step = (e - s) / len(w) if e > s else 0.0
        for k, ch in enumerate(w):
            out.append(Char(ch, s + k * step, s + (k + 1) * step))
    return out


def _transcribe_words(model, audio: Path) -> list[tuple[str, float, float]]:
    # Materialise inside the caller's try: CUDA errors surface only while the generator runs.
    segments, _ = model.transcribe(str(audio), word_timestamps=True, language="en")
    return [(w.word, float(w.start), float(w.end)) for seg in segments for w in seg.words]


def whisper_words(audio: Path, model_size: str = "small") -> list[tuple[str, float, float]]:
    from faster_whisper import WhisperModel  # optional extra: pip install -e ".[align]"

    try:
        model = WhisperModel(model_size, device="auto", compute_type="auto")
        return _transcribe_words(model, audio)
    except RuntimeError:
        # e.g. CUDA runtime DLLs missing (cublas64_12.dll): retry on CPU.
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        return _transcribe_words(model, audio)
