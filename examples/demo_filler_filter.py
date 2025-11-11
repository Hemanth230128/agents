#!/usr/bin/env python3
"""Interactive demo of the LiveKit Agents transcription filler filter.

This script lets you type transcripts and see how they would be handled by
the filler filter in different agent states (speaking/listening).

Usage:
    python demo_filler_filter.py

Commands:
    speak    - Set agent state to "speaking"
    listen   - Set agent state to "listening"
    words    - Show current ignored words
    set X Y  - Set ignored words (comma-separated)
    quit     - Exit the demo
    help     - Show this help

Any other input is treated as a transcript to filter.
"""

import os
import sys
from typing import List, Optional

# Add extension module path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
extension_path = os.path.join(repo_root, "livekit-agents", "livekit", "agents",
                            "voice", "extensions", "transcription_filler_filter.py")

# Import FillerFilter directly like the tests do
import importlib.util
spec = importlib.util.spec_from_file_location("transcription_filler_filter", extension_path)
ext = importlib.util.module_from_spec(spec)  # type: ignore
assert spec and spec.loader
spec.loader.exec_module(ext)  # type: ignore
FillerFilter = ext.FillerFilter

if not os.path.exists(extension_path):
    print("Error: Could not find extension module. Please run from repository root.")
    sys.exit(1)


class DemoSession:
    """Minimal session-like object that tracks agent state."""
    def __init__(self, agent_state: str = "listening"):
        self.agent_state = agent_state
        self.events = []

    def emit(self, name: str, *args, **kwargs) -> None:
        """Record emitted events for display."""
        self.events.append((name, args, kwargs))



# Event class that matches what the filter expects
class DemoTranscript:
    def __init__(self, text: str):
        self.transcript = text
        self.is_final = True

    def __str__(self) -> str:
        return self.transcript

class DemoActivity:
    """Minimal activity-like object that can receive transcripts."""
    def __init__(self, session: DemoSession):
        self._session = session
        self.forwarded = []

    def _on_input_audio_transcription_completed(self, ev: DemoTranscript) -> None:
        """Record forwarded transcripts for display.

        The runtime's transcription handler receives an event-like object with a
        `transcript` attribute; store that string for display.
        """
        self.forwarded.append(ev.transcript)


def format_state(state: str) -> str:
    """Format agent state for display with color if available."""
    try:
        import colorama
        colorama.init()
        color = colorama.Fore.GREEN if state == "listening" else colorama.Fore.RED
        return f"{color}{state}{colorama.Style.RESET_ALL}"
    except ImportError:
        return state


def print_status(session: DemoSession, activity: DemoActivity) -> None:
    """Show current state and any pending events/forwards."""
    print(f"\nAgent state: {format_state(session.agent_state)}")
    
    if activity.forwarded:
        print("Forwarded transcripts:")
        for t in activity.forwarded:
            print(f"  - {t}")
        activity.forwarded.clear()
    
    if session.events:
        print("Events emitted:")
        for name, args, kwargs in session.events:
            print(f"  - {name}")
        session.events.clear()


def main() -> None:
    """Run the interactive demo."""
    try:
        import colorama
        colorama.init()
    except ImportError:
        pass

    print(__doc__)
    
    # Create our test objects
    session = DemoSession()
    activity = DemoActivity(session)
    
    # Create and attach the filter
    filt = FillerFilter.from_env()
    
    # Attach our filter (activity handler accepts DemoTranscript objects)
    filt.attach_to_activity(activity)

    while True:
        try:
            text = input("\nEnter transcript (or 'help'/'quit'): ").strip()
            
            if not text:
                continue
            
            if text == "quit":
                break
            
            elif text == "help":
                print(__doc__)
                continue
            
            elif text == "speak":
                session.agent_state = "speaking"
                print_status(session, activity)
                continue
            
            elif text == "listen":
                session.agent_state = "listening"
                print_status(session, activity)
                continue
            
            elif text == "words":
                print("\nCurrently ignored words/sounds:")
                for w in sorted(filt._ignored_words):
                    print(f"  - {w}")
                continue
            
            elif text.startswith("set "):
                words = text[4:].strip().split(",")
                filt.set_ignored_words(words)
                print(f"\nUpdated ignored words to: {sorted(filt._ignored_words)}")
                continue
            
            # Treat as transcript to filter
            activity._on_input_audio_transcription_completed(DemoTranscript(text))
            print_status(session, activity)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

    print("\nDemo finished.")


if __name__ == "__main__":
    main()