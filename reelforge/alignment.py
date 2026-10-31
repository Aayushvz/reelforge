from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Char:
    ch: str
    start: float
    end: float


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float


def clean_chars(chars: list[str], starts: list[float], ends: list[float]) -> list[Char]:
    """Drop ElevenLabs audio tags like "[sighs]" (they're in the text, not spoken)."""
    out: list[Char] = []
    depth = 0
    for ch, s, e in zip(chars, starts, ends):
        if ch == "[":
            depth += 1
            continue
        if ch == "]":
            depth = max(0, depth - 1)
            continue
        if depth == 0:
            out.append(Char(ch, float(s), float(e)))
    while out and out[0].ch.isspace():
        out.pop(0)
    return out


def words_from_chars(chars: list[Char]) -> list[Word]:
    words: list[Word] = []
    cur: list[Char] = []
    for c in [*chars, Char(" ", 0.0, 0.0)]:
        if c.ch.isspace():
            if cur:
                words.append(Word("".join(x.ch for x in cur), cur[0].start, cur[-1].end))
                cur = []
        else:
            cur.append(c)
    return words
