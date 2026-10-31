import pytest

from reelforge.alignment import clean_chars, words_from_chars


def _align(text: str, step: float = 0.1):
    chars = list(text)
    starts = [i * step for i in range(len(chars))]
    return chars, starts, [s + step for s in starts]


def test_tags_and_leading_space_removed():
    cs = clean_chars(*_align("[sighs] Hi yo"))
    assert "".join(c.ch for c in cs) == "Hi yo"


def test_words_keep_audio_times():
    ws = words_from_chars(clean_chars(*_align("[x] Hi yo")))
    assert [w.text for w in ws] == ["Hi", "yo"]
    assert ws[0].start == pytest.approx(0.4) and ws[0].end == pytest.approx(0.6)
    assert ws[1].start == pytest.approx(0.7) and ws[1].end == pytest.approx(0.9)


def test_nested_or_unclosed_tag_is_ignored_safely():
    cs = clean_chars(*_align("a [b [c] d] e"))
    assert "".join(c.ch for c in cs).split() == ["a", "e"]
