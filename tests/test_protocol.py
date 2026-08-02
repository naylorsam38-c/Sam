import pytest

from aura.protocol import PresentationRequest, Envelope, Event


def test_intensity_clamped():
    assert PresentationRequest("s", "hi", intensity=5).validate().intensity == 1.0
    assert PresentationRequest("s", "hi", intensity=-2).validate().intensity == 0.0


def test_requires_session_id():
    with pytest.raises(ValueError):
        PresentationRequest("", "hi").validate()


def test_text_length_guard():
    with pytest.raises(ValueError):
        PresentationRequest("s", "x" * 20001).validate()


def test_envelope_roundtrip():
    e = Envelope(type=Event.STATE, session_id="s", data={"state": "IDLE"})
    d = e.json()
    assert d["type"] == Event.STATE and d["session_id"] == "s"
    assert d["data"]["state"] == "IDLE" and "ts" in d
