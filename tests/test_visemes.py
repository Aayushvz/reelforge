from reelforge.alignment import Char
from reelforge.visemes import sample_tracks, viseme_events


def chars(text, step=0.1, t0=0.0):
    return [Char(c, t0 + i * step, t0 + (i + 1) * step) for i, c in enumerate(text)]


def names(ev):
    return [v for _, v in ev]


def test_events_for_mama():
    assert names(viseme_events(chars("mama"))) == ["sil", "MBP", "AA", "MBP", "AA", "sil"]


def test_digraph_th():
    assert names(viseme_events(chars("the"))) == ["sil", "TH", "EE", "sil"]


def test_gap_inserts_silence():
    cs = [Char("a", 0.0, 0.1), Char(" ", 0.1, 1.0), Char("a", 1.0, 1.1)]
    assert names(viseme_events(cs)) == ["sil", "AA", "sil", "sil", "AA", "sil"]


def test_events_sorted():
    ev = viseme_events(chars("hello there friend", step=0.07))
    times = [t for t, _ in ev]
    assert times == sorted(times)


def test_tracks_rest_close_and_open():
    tr = sample_tracks(viseme_events(chars("mama")), 30, 20)
    assert tr["mouthClose"][0] == 0.0
    assert tr["mouthClose"][2] > 0.5   # near first 'm' (t=0.05)
    assert tr["jawOpen"][5] > 0.4      # near first 'a' (t=0.15)
    assert all(0.0 <= v <= 1.0 for vals in tr.values() for v in vals)
