from __future__ import annotations

import types

import importlib.util
import os

# Import the extension module directly from its file to avoid importing the
# top-level package (which pulls in optional runtime deps like livekit.rtc).
ext_path = os.path.join(
    os.getcwd(), "livekit-agents", "livekit", "agents", "voice", "extensions", "transcription_filler_filter.py"
)
spec = importlib.util.spec_from_file_location("transcription_filler_filter", ext_path)
ext = importlib.util.module_from_spec(spec)  # type: ignore
assert spec and spec.loader
spec.loader.exec_module(ext)  # type: ignore
FillerFilter = ext.FillerFilter


class FakeSession:
    def __init__(self, agent_state="listening"):
        self.agent_state = agent_state
        self.events = []

    def emit(self, name, *args, **kwargs):
        self.events.append((name, args, kwargs))


class FakeActivity:
    def __init__(self, session: FakeSession):
        self._session = session
        self.forwarded = []

    # original handler that should be called when transcript is forwarded
    def _on_input_audio_transcription_completed(self, ev):
        self.forwarded.append((ev.transcript, ev.is_final, getattr(ev, "item_id", None)))


class Ev:
    def __init__(self, transcript: str, is_final: bool = True, item_id: str | None = None):
        self.transcript = transcript
        self.is_final = is_final
        self.item_id = item_id


def test_ignore_filler_while_agent_speaking():
    session = FakeSession(agent_state="speaking")
    activity = FakeActivity(session)
    f = FillerFilter.from_env()  # uses defaults
    f.attach_to_activity(activity)

    ev = Ev("uh")
    activity._on_input_audio_transcription_completed(ev)

    # filler while speaking -> should be ignored
    assert activity.forwarded == []
    # should emit agent_false_interruption
    assert any(e[0] == "agent_false_interruption" for e in session.events)


def test_forward_filler_when_agent_listening():
    session = FakeSession(agent_state="listening")
    activity = FakeActivity(session)
    f = FillerFilter.from_env()
    f.attach_to_activity(activity)

    ev = Ev("umm")
    activity._on_input_audio_transcription_completed(ev)

    # filler when agent quiet -> forwarded
    assert activity.forwarded == [("umm", True, None)]
    assert not any(e[0] == "agent_false_interruption" for e in session.events)


def test_forward_mixed_filler_and_command():
    session = FakeSession(agent_state="speaking")
    activity = FakeActivity(session)
    f = FillerFilter.from_env()
    f.attach_to_activity(activity)

    ev = Ev("umm stop")
    activity._on_input_audio_transcription_completed(ev)

    # mixed filler+command -> forwarded
    assert activity.forwarded == [("umm stop", True, None)]

