from __future__ import annotations

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
    def __init__(self, agent_state: str = "listening"):
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


def test_ignore_murmur_while_agent_speaking():
    session = FakeSession(agent_state="speaking")
    activity = FakeActivity(session)
    f = FillerFilter.from_env()  # uses defaults (includes murmurs/noise markers)
    f.attach_to_activity(activity)

    ev = Ev("mm")
    activity._on_input_audio_transcription_completed(ev)

    # murmur while speaking -> should be ignored
    assert activity.forwarded == []
    assert any(e[0] == "agent_false_interruption" for e in session.events)


def test_forward_murmur_when_agent_listening():
    session = FakeSession(agent_state="listening")
    activity = FakeActivity(session)
    f = FillerFilter.from_env()
    f.attach_to_activity(activity)

    ev = Ev("mm")
    activity._on_input_audio_transcription_completed(ev)

    # murmur when agent quiet -> forwarded
    assert activity.forwarded == [("mm", True, None)]
    assert not any(e[0] == "agent_false_interruption" for e in session.events)


def test_ignore_asr_marker_while_agent_speaking():
    session = FakeSession(agent_state="speaking")
    activity = FakeActivity(session)
    f = FillerFilter.from_env()
    f.attach_to_activity(activity)

    ev = Ev("[noise]")
    activity._on_input_audio_transcription_completed(ev)

    assert activity.forwarded == []
    assert any(e[0] == "agent_false_interruption" for e in session.events)


def test_forward_mixed_murmur_and_command():
    session = FakeSession(agent_state="speaking")
    activity = FakeActivity(session)
    f = FillerFilter.from_env()
    f.attach_to_activity(activity)

    ev = Ev("mm stop")
    activity._on_input_audio_transcription_completed(ev)

    # mixed murmur+command -> forwarded
    assert activity.forwarded == [("mm stop", True, None)]
