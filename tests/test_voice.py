import base64
import io
import urllib.error

import pytest

from reelforge.schema import Line
from reelforge.voice import VoiceError, synthesize_line

LINE = Line("l01", "LEAD", "[sighs] Hi yo", "deadpan", 0.5, "calm")


def _resp(text="[sighs] Hi yo"):
    chars = list(text)
    st = [i * 0.1 for i in range(len(chars))]
    return {
        "audio_base64": base64.b64encode(b"ID3fakeaudio").decode(),
        "alignment": {"characters": chars, "character_start_times_seconds": st,
                      "character_end_times_seconds": [s + 0.1 for s in st]},
    }


def _http_error(code: int):
    return urllib.error.HTTPError("https://x", code, "err", {}, io.BytesIO(b"{}"))


def test_writes_audio_alignment_and_caches(tmp_path):
    calls = []

    def post(url, headers, body):
        calls.append((url, headers, body))
        return _resp()

    v = synthesize_line(LINE, "VOICE", tmp_path, "KEY", post=post)
    assert v.audio_path.read_bytes() == b"ID3fakeaudio"
    assert "".join(c.ch for c in v.chars) == "Hi yo"
    url, headers, body = calls[0]
    assert "/VOICE/with-timestamps" in url and "output_format=mp3_44100_128" in url
    assert headers["xi-api-key"] == "KEY"
    assert body == {"text": "[sighs] Hi yo", "model_id": "eleven_v4"}
    synthesize_line(LINE, "VOICE", tmp_path, "KEY", post=post)
    assert len(calls) == 1  # second call served from cache


def test_text_change_busts_cache(tmp_path):
    calls = []
    post = lambda u, h, b: calls.append(1) or _resp(b["text"])  # noqa: E731
    synthesize_line(LINE, "V", tmp_path, "K", post=post)
    synthesize_line(Line("l01", "LEAD", "[sighs] Hey", "deadpan", 0.5, "calm"), "V", tmp_path, "K", post=post)
    assert len(calls) == 2


def test_retries_on_429(tmp_path):
    errors = [_http_error(429)]

    def post(u, h, b):
        if errors:
            raise errors.pop()
        return _resp()

    v = synthesize_line(LINE, "V", tmp_path, "K", post=post, sleep=lambda s: None)
    assert v.audio_path.exists()


def test_auth_error_raises_without_retry(tmp_path):
    calls = []

    def post(u, h, b):
        calls.append(1)
        raise _http_error(401)

    with pytest.raises(VoiceError, match="401"):
        synthesize_line(LINE, "V", tmp_path, "K", post=post, sleep=lambda s: None)
    assert len(calls) == 1


def test_falls_back_to_v3_when_v4_rejected(tmp_path, monkeypatch):
    monkeypatch.delenv("ELEVENLABS_MODEL", raising=False)
    models = []

    def post(u, h, b):
        models.append(b["model_id"])
        if b["model_id"] == "eleven_v4":
            raise _http_error(400)
        return _resp()

    v = synthesize_line(LINE, "V", tmp_path, "K", post=post, sleep=lambda s: None)
    assert models == ["eleven_v4", "eleven_v3"] and v.audio_path.exists()


def test_error_message_includes_elevenlabs_detail(tmp_path):
    def post(u, h, b):
        raise urllib.error.HTTPError("https://x", 401, "err", {},
                                     io.BytesIO(b'{"detail": {"message": "Invalid API key"}}'))

    with pytest.raises(VoiceError, match="Invalid API key"):
        synthesize_line(LINE, "V", tmp_path, "K", post=post, sleep=lambda s: None)


def test_directed_delivery_tags_settings_and_cache_keys(tmp_path):
    from reelforge.schema import Line
    from reelforge.voice import delivery_key, directed_text, take_path, voice_settings
    happy = Line("l1", "A", "We shipped it!", "happy", 0.5, "calm")
    assert directed_text(happy) == "[cheerfully] We shipped it!"
    assert directed_text(Line("l1", "A", "We shipped it!", "happy", 0.9, "calm")) == "[excited] We shipped it!"
    assert directed_text(Line("l1", "A", "Okay.", "neutral", 0.2, "calm")) == "[quietly] Okay."
    assert directed_text(Line("l1", "A", "[whispers] hi", "happy", 0.9, "calm")) == "[whispers] hi"  # writer's tag wins
    assert voice_settings(happy)["stability"] == 0.5 and voice_settings(Line("l", "A", "x", "sad", 0.8, "calm"))["stability"] == 0.0
    plain, directed = take_path(happy, "v", tmp_path, "eleven_v4"), take_path(happy, "v", tmp_path, "eleven_v4", direct=True)
    assert plain != directed and delivery_key(happy) == "happy:0.50"
    sad = Line("l1", "A", "We shipped it!", "sad", 0.5, "calm")
    assert take_path(sad, "v", tmp_path, "eleven_v4", direct=True) != directed  # a new emotion is a new take
    assert take_path(sad, "v", tmp_path, "eleven_v4") == plain  # undirected keys never change


def test_directed_synthesis_sends_tags_and_settings(tmp_path):
    import base64
    from reelforge.schema import Line
    from reelforge.voice import synthesize_line
    sent = []
    def post(url, headers, body):
        sent.append(body)
        return {"audio_base64": base64.b64encode(b"ID3").decode(), "alignment": {
            "characters": list("hi"), "character_start_times_seconds": [0.0, 0.1], "character_end_times_seconds": [0.1, 0.2]}}
    synthesize_line(Line("l1", "A", "hi", "surprised", 0.9, "calm"), "v", tmp_path, "k", post=post, model="eleven_v4", direct=True)
    assert sent[0]["text"] == "[shocked] hi" and sent[0]["voice_settings"]["stability"] == 0.0
