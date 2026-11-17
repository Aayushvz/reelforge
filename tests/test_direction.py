import pytest

from reelforge import direction as D
from reelforge.schema import EMOTIONS, MOODS, Line, parse_performance
from reelforge.voice import delivery_key, directed_text, voice_settings

SCRIPT = """Me: [frustrated] Claude, I've been fixing this bug for two hours.
Claude: [cheerful, proud] Absolutely! I fixed it.
Me: (deadpan) Then why is the screen blank?

Claude: [nervous laugh] Interesting... [clears throat] let me investigate.
Me: [very angry] I've shown you this exact error SIX times. *
Claude: #beat [slightly embarrassed] Oh.
Me: I'm going to bed.
"""


def test_every_word_maps_to_a_real_emotion_and_mood():
    for word, (emo, inten, mood) in D.EXPRESSIONS.items():
        assert emo in EMOTIONS and mood in MOODS and 0 <= inten <= 1, word


def test_parse_script_reads_notes_cues_and_markers():
    ls = D.parse_script(SCRIPT)
    assert [l["speaker"] for l in ls] == ["me", "claude", "me", "claude", "me", "claude", "me"]
    assert ls[0]["delivery"] == "frustrated" and ls[0]["emotion"] == "annoyed" and not ls[0]["delivery_auto"]
    assert ls[1]["delivery"] == "cheerful, proud" and ls[1]["emotion"] == "happy"
    assert ls[2]["delivery"] == "deadpan" and ls[2]["text"] == "Then why is the screen blank?"  # ( ) works too
    assert ls[2]["pause_after"] == 0.8  # the blank row
    assert ls[3]["delivery"] == "nervous laugh" and ls[3]["emotion"] == "embarrassed"
    assert "[clears throat]" in ls[3]["text"]  # an in-line cue stays where it was written
    angry = ls[4]
    assert angry["punchline"] and not angry["text"].endswith("*")
    assert angry["emotion"] == "annoyed" and angry["intensity"] >= 0.95  # "very" + SHOUTED word
    assert ls[5]["beat"] and "#beat" not in ls[5]["text"] and ls[5]["intensity"] < 0.6  # "slightly" softens
    assert ls[6]["delivery_auto"] and ls[6]["delivery"]  # no note: auto-directed, never blank


def test_auto_direct_reads_punctuation_and_keywords():
    assert D.auto_note("WHY is it still broken", False) == "frustrated, loud"
    assert D.auto_note("Wait, what?!", False) == "shocked"
    assert D.auto_note("Sorry about that.", True) == "apologetic"
    assert D.auto_note("Fine.", False, prev_text="I have explained this to you at least twelve times today, okay") == "deadpan"
    assert D.auto_note("It finally works!", True) == "excited"
    assert D.auto_note("Here is your file.", True) == "upbeat, helpful"


def test_unknown_note_keeps_the_owners_words():
    r = D.read_note("like a pirate captain")
    assert r["delivery"] == "like a pirate captain" and r["emotion"] == "neutral"
    assert D.read_note("angrily")["emotion"] == "annoyed"


def test_direct_lines_keeps_owner_notes_and_refills_auto():
    lines = [{"speaker": "me", "text": "Why?!", "delivery": "", "emotion": "neutral", "intensity": 0.5, "mood": "calm"},
             {"speaker": "claude", "text": "Hi", "delivery": "smug", "emotion": "neutral", "intensity": 0.5, "mood": "calm"}]
    out = D.direct_lines(lines, {"claude"})
    assert out[0]["delivery_auto"] and out[0]["delivery"] == "shocked"
    assert out[1]["emotion"] == "smug" and not out[1]["delivery_auto"]


def test_voice_uses_the_note_and_keys_takes_by_it():
    plain = Line("l1", "A", "We did it.", "happy", 0.6, "calm")
    noted = Line("l1", "A", "We did it. [laughs]", "happy", 0.6, "calm", delivery="cheerful, proud")
    assert directed_text(noted) == "[cheerful] [proud] We did it. [laughs]"
    assert delivery_key(plain) == "happy:0.60"  # no note: the old key, no surprise re-generation
    assert delivery_key(noted) == "happy:0.60:cheerful, proud"
    assert voice_settings(noted)["stability"] == 0.3


def test_schema_accepts_delivery_and_rejects_bad_ones():
    base = {"style": "shots-av", "characters": {"me": {"model": "av_hero"}, "claude": {"model": "buddy_claude"}}}
    ok = parse_performance({**base, "lines": [{"speaker": "me", "text": "hi", "delivery": "smug"}]})
    assert ok.lines[0].delivery == "smug"
    with pytest.raises(Exception):
        parse_performance({**base, "lines": [{"speaker": "me", "text": "hi", "delivery": "x" * 81}]})
