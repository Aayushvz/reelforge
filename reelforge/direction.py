"""Expression direction for script lines: the owner's notes, and auto-direction for lines without one.

Script format (one line per row):
    Me: [frustrated] Claude, I've been fixing this bug for two hours.
    Claude: [cheerful, proud] Absolutely! I fixed it.
    Claude: [nervous laugh] Interesting... [clears throat] let me investigate.
    Me: [very angry] I've shown you this exact error SIX times. *
The leading [note] (or (note)) is the delivery: sent to ElevenLabs as audio tags and mapped to the face's emotion,
intensity and mood. Brackets later in the line are sound cues performed in place (never captioned). A trailing "*"
marks a punchline, "#beat" forces a wide, and a blank row lengthens the pause before the next line.
Pure standard library.
"""
from __future__ import annotations

import re

# word -> (face emotion, intensity, mood). Emotions/moods are the schema's (EMOTIONS / MOODS).
EXPRESSIONS: dict[str, tuple[str, float, str]] = {
    # happy / warm
    "happy": ("happy", 0.6, "calm"), "cheerful": ("happy", 0.6, "calm"), "excited": ("happy", 0.85, "success"),
    "thrilled": ("happy", 0.9, "success"), "ecstatic": ("happy", 0.95, "success"), "proud": ("happy", 0.7, "success"),
    "delighted": ("happy", 0.75, "success"), "joyful": ("happy", 0.75, "success"), "upbeat": ("happy", 0.6, "calm"),
    "enthusiastic": ("happy", 0.8, "success"), "relieved": ("happy", 0.55, "calm"), "grateful": ("happy", 0.5, "calm"),
    "warm": ("happy", 0.45, "calm"), "friendly": ("happy", 0.45, "calm"), "playful": ("smug", 0.55, "calm"),
    "laughing": ("happy", 0.8, "success"), "laughs": ("happy", 0.7, "calm"), "giggles": ("happy", 0.6, "calm"),
    "chuckles": ("happy", 0.5, "calm"), "triumphant": ("happy", 0.9, "success"), "hopeful": ("happy", 0.45, "calm"),
    "helpful": ("happy", 0.45, "calm"), "bright": ("happy", 0.55, "calm"), "amused": ("smug", 0.5, "calm"),
    "giddy": ("happy", 0.8, "success"), "celebrating": ("happy", 0.9, "success"),
    # sad
    "sad": ("sad", 0.6, "sad"), "defeated": ("sad", 0.65, "sad"), "disappointed": ("sad", 0.55, "sad"),
    "heartbroken": ("sad", 0.9, "sad"), "crying": ("sad", 0.95, "sad"), "tearful": ("sad", 0.8, "sad"),
    "tired": ("sad", 0.4, "calm"), "exhausted": ("sad", 0.6, "calm"), "gloomy": ("sad", 0.5, "sad"),
    "lonely": ("sad", 0.55, "sad"), "hurt": ("sad", 0.6, "sad"), "sulking": ("sad", 0.5, "awkward"),
    "melancholy": ("sad", 0.5, "sad"), "resigned": ("sad", 0.45, "calm"), "sighs": ("sad", 0.4, "calm"),
    "sigh": ("sad", 0.4, "calm"), "deflated": ("sad", 0.55, "sad"), "whining": ("sad", 0.6, "awkward"),
    # worried / scared
    "nervous": ("worried", 0.6, "panic"), "anxious": ("worried", 0.75, "panic"), "worried": ("worried", 0.6, "panic"),
    "scared": ("worried", 0.8, "panic"), "panicking": ("worried", 0.95, "panic"), "panicked": ("worried", 0.95, "panic"),
    "terrified": ("worried", 0.95, "panic"), "stressed": ("worried", 0.75, "panic"), "uneasy": ("worried", 0.5, "awkward"),
    "hesitant": ("worried", 0.4, "awkward"), "unsure": ("confused", 0.45, "awkward"), "desperate": ("worried", 0.9, "panic"),
    "urgent": ("worried", 0.8, "panic"), "frantic": ("worried", 0.95, "panic"), "pleading": ("worried", 0.7, "panic"),
    "begging": ("worried", 0.8, "panic"), "tense": ("worried", 0.65, "panic"), "gulps": ("worried", 0.6, "panic"),
    # surprised
    "surprised": ("surprised", 0.65, "reveal"), "shocked": ("surprised", 0.9, "reveal"),
    "amazed": ("surprised", 0.75, "reveal"), "stunned": ("surprised", 0.85, "reveal"), "gasps": ("surprised", 0.8, "reveal"),
    "gasp": ("surprised", 0.8, "reveal"), "astonished": ("surprised", 0.85, "reveal"), "disbelief": ("surprised", 0.7, "reveal"),
    "impressed": ("surprised", 0.55, "success"), "realising": ("surprised", 0.6, "reveal"),
    "realizing": ("surprised", 0.6, "reveal"), "dramatic": ("surprised", 0.8, "reveal"),
    # smug / teasing
    "smug": ("smug", 0.65, "calm"), "teasing": ("smug", 0.6, "calm"), "cocky": ("smug", 0.75, "calm"),
    "confident": ("smug", 0.55, "success"), "mischievous": ("smug", 0.6, "awkward"), "sly": ("smug", 0.55, "calm"),
    "flirty": ("smug", 0.55, "calm"), "flirtatious": ("smug", 0.6, "calm"), "proudly": ("smug", 0.6, "success"),
    "sarcastic": ("deadpan", 0.6, "awkward"), "mocking": ("smug", 0.7, "awkward"), "sassy": ("smug", 0.7, "calm"),
    "cheeky": ("smug", 0.6, "calm"), "condescending": ("smug", 0.7, "awkward"),
    # deadpan / dry
    "deadpan": ("deadpan", 0.5, "awkward"), "dry": ("deadpan", 0.5, "awkward"), "flat": ("deadpan", 0.45, "awkward"),
    "unimpressed": ("deadpan", 0.6, "awkward"), "bored": ("deadpan", 0.4, "calm"), "monotone": ("deadpan", 0.45, "awkward"),
    "blunt": ("deadpan", 0.55, "awkward"), "matter-of-fact": ("deadpan", 0.45, "calm"), "ironic": ("deadpan", 0.55, "awkward"),
    "unbothered": ("deadpan", 0.4, "calm"), "skeptical": ("deadpan", 0.55, "awkward"), "sceptical": ("deadpan", 0.55, "awkward"),
    # confused
    "confused": ("confused", 0.6, "awkward"), "puzzled": ("confused", 0.55, "awkward"), "curious": ("confused", 0.45, "calm"),
    "baffled": ("confused", 0.75, "awkward"), "bewildered": ("confused", 0.8, "awkward"), "lost": ("confused", 0.6, "awkward"),
    "questioning": ("confused", 0.5, "calm"), "suspicious": ("confused", 0.55, "awkward"),
    # annoyed / angry
    "annoyed": ("annoyed", 0.6, "awkward"), "frustrated": ("annoyed", 0.75, "panic"), "angry": ("annoyed", 0.85, "panic"),
    "furious": ("annoyed", 0.95, "panic"), "irritated": ("annoyed", 0.6, "awkward"), "exasperated": ("annoyed", 0.75, "awkward"),
    "fed up": ("annoyed", 0.75, "awkward"), "shouting": ("annoyed", 0.95, "panic"), "yelling": ("annoyed", 0.95, "panic"),
    "grumpy": ("annoyed", 0.55, "awkward"), "impatient": ("annoyed", 0.65, "awkward"), "snapping": ("annoyed", 0.85, "panic"),
    "outraged": ("annoyed", 0.95, "panic"), "groans": ("annoyed", 0.55, "awkward"), "ranting": ("annoyed", 0.85, "panic"),
    "salty": ("annoyed", 0.55, "awkward"), "stern": ("annoyed", 0.55, "calm"), "complaining": ("annoyed", 0.6, "awkward"),
    # thinking
    "thoughtful": ("thinking", 0.45, "calm"), "thinking": ("thinking", 0.45, "calm"), "pondering": ("thinking", 0.5, "calm"),
    "calm": ("neutral", 0.35, "calm"), "casual": ("neutral", 0.45, "calm"), "explaining": ("thinking", 0.45, "calm"),
    "reflective": ("thinking", 0.45, "calm"), "focused": ("thinking", 0.5, "calm"), "serious": ("neutral", 0.55, "calm"),
    "whispering": ("worried", 0.35, "calm"), "whispers": ("worried", 0.35, "calm"), "soft": ("neutral", 0.3, "calm"),
    "gentle": ("happy", 0.35, "calm"), "reassuring": ("happy", 0.45, "calm"), "sincere": ("neutral", 0.5, "calm"),
    "mumbling": ("embarrassed", 0.4, "awkward"), "muttering": ("annoyed", 0.45, "awkward"),
    # embarrassed
    "embarrassed": ("embarrassed", 0.6, "awkward"), "sheepish": ("embarrassed", 0.5, "awkward"),
    "awkward": ("embarrassed", 0.55, "awkward"), "flustered": ("embarrassed", 0.75, "awkward"),
    "apologetic": ("embarrassed", 0.55, "awkward"), "shy": ("embarrassed", 0.45, "awkward"),
    "guilty": ("embarrassed", 0.6, "awkward"), "caught": ("embarrassed", 0.7, "awkward"),
    "nervous laugh": ("embarrassed", 0.6, "awkward"), "clears throat": ("embarrassed", 0.45, "awkward"),
    # multi-word phrases
    "on the verge of tears": ("sad", 0.9, "sad"), "holding back tears": ("sad", 0.85, "sad"),
    "trying not to laugh": ("smug", 0.6, "awkward"), "long sigh": ("sad", 0.5, "calm"), "deep breath": ("worried", 0.5, "calm"),
    "under breath": ("annoyed", 0.4, "awkward"), "in disbelief": ("surprised", 0.75, "reveal"),
    "matter of fact": ("deadpan", 0.45, "calm"), "over it": ("deadpan", 0.6, "awkward"),
}
STRONGER = ("very", "really", "super", "extremely", "so", "totally", "completely", "incredibly", "absolutely")
SOFTER = ("slightly", "a bit", "a little", "little", "quietly", "softly", "mildly", "kind of", "somewhat", "barely")
SOUND_CUES = ("laughs", "laugh", "sighs", "sigh", "gasps", "gasp", "clears throat", "giggles", "chuckles", "groans",
              "gulps", "pause", "short pause", "long pause", "sniffs", "coughs", "exhales", "inhales", "snorts", "whistles")


def _clamp(v: float) -> float:
    return round(min(1.0, max(0.0, v)), 2)


def read_note(note: str, text: str = "") -> dict:
    """A delivery note ("very angry", "cheerful, proud", "nervous laugh") -> emotion, intensity, mood, delivery.
    The delivery keeps the owner's words (comma-separated tags); the face gets the first word it recognises."""
    raw = re.sub(r"\s+", " ", note.strip().strip("[]()").strip())
    parts = [p.strip() for p in re.split(r"[,;/]| and ", raw) if p.strip()]
    found, shift = None, 0.0
    for part in parts:
        low = part.lower()
        for w in STRONGER:
            if re.search(rf"\b{w}\b", low):
                shift += 0.2
        for w in SOFTER:
            if re.search(rf"\b{w}\b", low):
                shift -= 0.2
        if found is None:
            found = _lookup(low)
    if found is None:
        found = ("neutral", 0.5, "calm")
    emotion, intensity, mood = found
    intensity += shift + _text_heat(text)
    return {"emotion": emotion, "intensity": _clamp(intensity), "mood": mood, "delivery": ", ".join(parts)[:80]}


def _lookup(phrase: str):
    if phrase in EXPRESSIONS:
        return EXPRESSIONS[phrase]
    for key in sorted((k for k in EXPRESSIONS if " " in k), key=len, reverse=True):  # phrases before single words
        if key in phrase:
            return EXPRESSIONS[key]
    for word in re.findall(r"[a-z][a-z-]*", phrase):
        for cand in (word, word[:-2] if word.endswith("ly") else word, word[:-1] if word.endswith("s") else word,
                     word[:-3] + "y" if word.endswith("ily") else word):  # angrily -> angry
            if cand in EXPRESSIONS:
                return EXPRESSIONS[cand]
    return None


def _text_heat(text: str) -> float:
    """!! and SHOUTED words make a line hotter."""
    heat = 0.0
    if "!!" in text or "?!" in text or "!?" in text:
        heat += 0.15
    if any(len(w) >= 3 and w.isupper() for w in re.findall(r"[A-Za-z']+", re.sub(r"\[[^\]]*\]", "", text))):
        heat += 0.15
    return heat


# ---------- auto-direct (lines with no note) ----------
_NEG = re.compile(r"\b(no|not|never|why|still|again|broken|bug|error|fail(ed|ing)?|wrong|crash(ed)?|seriously)\b", re.I)
_POS = re.compile(r"\b(great|awesome|amazing|love|perfect|finally|yes|yay|nice|thanks|thank you|brilliant|won|works|fixed|done|solved|absolutely)\b", re.I)
_SORRY = re.compile(r"\b(sorry|apolog|my bad|oops|whoops)\w*", re.I)
_THINK = re.compile(r"\b(hmm+|let me|maybe|i think|perhaps|actually|well)\b", re.I)
_SURPRISE = re.compile(r"\b(wait|what|whoa|wow|no way|oh)\b", re.I)


def auto_note(text: str, speaker_is_bot: bool, prev_text: str = "", first: bool = False) -> str:
    """A delivery for a line the owner left undirected: punctuation, keywords and the reply pattern."""
    t = re.sub(r"\[[^\]]*\]", "", text).strip()
    words = re.findall(r"[A-Za-z']+", t)
    shouted = any(len(w) >= 3 and w.isupper() for w in words)
    if shouted or "!!" in t:
        return "frustrated, loud" if _NEG.search(t) else "excited"
    if "?!" in t or "!?" in t:
        return "shocked"
    if len(words) <= 4 and len(re.findall(r"[A-Za-z']+", prev_text)) >= 10:
        return "deadpan"
    if _SORRY.search(t):
        return "apologetic"
    if t.endswith("...") or t.startswith("..."):
        return "hesitant"
    if _SURPRISE.search(t[:12]):
        return "surprised"
    if _NEG.search(t):
        return "exasperated" if not speaker_is_bot else "nervous"
    if _POS.search(t):
        return "excited" if "!" in t else "cheerful"
    if _THINK.search(t):
        return "thoughtful"
    if t.endswith("?"):
        return "curious"
    if speaker_is_bot:
        return "upbeat, helpful"
    return "casual, a bit tired" if not first else "casual"


# ---------- whole scripts ----------
ROW = re.compile(r"^([A-Za-z][\w .'-]{0,24}):\s*(.*)$")
LEAD = re.compile(r"^\s*[\[(]([^\])]{1,80})[\])]\s*(.*)$")
ME = {"me", "you", "i", "hero", "av"}


def direct_line(line: dict, speaker_is_bot: bool, prev_text: str = "", first: bool = False, force: bool = False) -> dict:
    """Fill emotion / intensity / mood / delivery for one line dict. A line with an owner's delivery keeps it (and is
    re-mapped); an empty one is auto-directed (delivery_auto: true). force re-directs auto lines too."""
    out = dict(line)
    note = (out.get("delivery") or "").strip()
    if note and not (force and out.get("delivery_auto")):
        out.update(read_note(note, out.get("text", "")))
        out["delivery_auto"] = bool(out.get("delivery_auto", False))
        return out
    auto = auto_note(out.get("text", ""), speaker_is_bot, prev_text, first)
    out.update(read_note(auto, out.get("text", "")))
    if first:
        out["intensity"] = _clamp(out["intensity"] + 0.1)  # the hook line carries a little extra energy
    out["delivery_auto"] = True
    return out


def parse_script(text: str, hero: str = "me", buddy: str = "claude", hero_names: list[str] | None = None,
                 buddy_is_bot: bool = True) -> list[dict]:
    """The pasted script -> directed line dicts (the editor's PerfLine shape)."""
    me = ME | {n.lower() for n in (hero_names or [])}
    lines: list[dict] = []
    nxt, gap = hero, False
    for row in text.splitlines():
        row = row.strip()
        if not row:
            gap = bool(lines)
            continue
        speaker, body = nxt, row
        m = ROW.match(row)
        if m and not row.lstrip().startswith(("[", "(")):
            speaker = hero if m.group(1).strip().lower() in me else buddy
            body = m.group(2).strip()
        beat = bool(re.search(r"(^|\s)#beat\b", body, re.I))
        body = re.sub(r"(^|\s)#beat\b", " ", body, flags=re.I).strip()
        note = ""
        lm = LEAD.match(body)
        if lm:
            note, body = lm.group(1).strip(), lm.group(2).strip()
        punch = body.endswith("*")
        body = body.rstrip("*").rstrip()
        if not body:
            continue
        if gap and lines:
            lines[-1]["pause_after"] = 0.8
        gap = False
        line = {"id": f"l{len(lines) + 1:02d}", "speaker": speaker, "text": body, "delivery": note,
                "punchline": punch, "beat": beat}
        prev = lines[-1]["text"] if lines else ""
        lines.append(direct_line(line, buddy_is_bot and speaker == buddy, prev, first=not lines))
        nxt = buddy if speaker == hero else hero
    return lines


def direct_lines(lines: list[dict], bot_speakers: set[str], force: bool = False) -> list[dict]:
    """Re-direct an existing script: owner notes re-mapped, empty or auto notes filled."""
    out = []
    for i, l in enumerate(lines):
        prev = lines[i - 1].get("text", "") if i else ""
        out.append(direct_line(l, l.get("speaker") in bot_speakers, prev, first=i == 0, force=force))
    return out


def voice_tags(delivery: str) -> str:
    """The delivery as ElevenLabs audio tags: "cheerful, proud" -> "[cheerful] [proud]"."""
    parts = [p.strip() for p in re.split(r"[,;]", delivery or "") if p.strip()]
    return " ".join(f"[{p}]" for p in parts[:3])
