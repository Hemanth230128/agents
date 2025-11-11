from _future_ import annotations

import os
import logging
from typing import Any, Iterable, Callable, List, Optional, Dict, Union

# Type aliases for better readability
TranscriptEvent = Dict[str, Any]  # The shape of our transcript events
TranscriptHandler = Callable[[TranscriptEvent], Any]  # Handler signature
AgentActivity = Any  # Type of our activity instances (avoid circular imports)

logger = logging.getLogger(_name_)


class FillerFilter:
    """A runtime extension to filter filler words during agent speech.
    
    Wraps an AgentActivity's realtime transcription handler to ignore filler-only 
    transcripts (like "uh", "umm") when the agent is speaking, while preserving 
    interruption ability for real commands.

    Attributes:
        _ignored_words (List[str]): Words to filter during agent speech
        _orig_handler_map (Dict[AgentActivity, TranscriptHandler]): Original handlers

    Example:
        >>> from livekit.agents.voice.extensions.transcription_filler_filter import FillerFilter
        >>> filter = FillerFilter.from_env()  # load from LIVEKIT_IGNORED_WORDS
        >>> filter.attach_to_activity(activity)
        
        # Or configure explicitly:
        >>> filter = FillerFilter(["uh", "umm", "hmm"])
        >>> filter.attach_to_activity(activity)
    
    The extension is:
    - Non-invasive: patches at runtime without core changes
    - Thread-safe: preserves handler execution context
    - Configurable: via env var or runtime API
    - Language-agnostic: works with any language
    - Defensive: falls back to original handler on errors
    """

    def _init_(self, ignored_words: Optional[Iterable[str]] = None) -> None:
        """Initialize a new filler filter.

        Args:
            ignored_words: Optional list of words to treat as fillers. Each word will
                         be normalized (stripped, lowercased). If None, uses defaults.
        """
        if ignored_words is None:
            ignored_words = []
        self._ignored_words: List[str] = [w.strip().lower() for w in ignored_words if w]
        self._orig_handler_map: Dict[AgentActivity, TranscriptHandler] = {}

    @classmethod
    def from_env(cls, env_var: str = "LIVEKIT_IGNORED_WORDS") -> "FillerFilter":
        """Create a FillerFilter instance configured from environment.

        Args:
            env_var: Name of environment variable containing comma-separated words.
                    Defaults to "LIVEKIT_IGNORED_WORDS".

        Returns:
            A new FillerFilter instance with ignored words from environment or defaults.
        """
        raw = os.environ.get(env_var, "")
        if not raw:
            # Default filler words (English) and background sounds
            raw = (
                # English fillers
                "uh,umm,hmm,err,ah,like,you know,"
                # Background/non-speech sounds
                "mm,mhm,mmm,,,,"  # Murmurs and non-speech markers
                "[noise],[background],[inaudible],"  # Common ASR background markers
                "[laugh],[cough],[breath],"  # Non-speech vocalizations
                "<noise>,<silence>,<background>"  # Alternative ASR markers
            )
        parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
        return cls(parts)

    def set_ignored_words(self, words: Iterable[str]) -> None:
        """Update the set of words to ignore during agent speech.

        Args:
            words: List of words to treat as fillers. Each word will be normalized
                  (stripped, lowercased).
        """
        self._ignored_words = [w.strip().lower() for w in words if w]

    def attach_to_activity(self, activity: AgentActivity) -> None:
        """Attach this filter to an AgentActivity instance.

        This method wraps the activity's _on_input_audio_transcription_completed 
        handler to filter filler-only transcripts during agent speech. The filter
        is thread-safe and preserves async behavior.

        Args:
            activity: The AgentActivity instance to attach to. Must have a
                     _on_input_audio_transcription_completed method and a
                     session with agent_state.

        Raises:
            AttributeError: If activity lacks required method/attributes.
        """
        if activity in self._orig_handler_map:
            return  # already attached

        if not hasattr(activity, "_on_input_audio_transcription_completed"):
            raise AttributeError("activity lacks _on_input_audio_transcription_completed")

        orig = activity._on_input_audio_transcription_completed

        def wrapper(ev):
            try:
                transcript_text = ev.transcript or ""
                if (
                    getattr(activity, "_session", None) is not None
                    and getattr(activity._session, "agent_state", None) == "speaking"
                    and transcript_text.strip()
                    and self._ignored_words
                ):
                    # Tokenize: reuse the project's split_words if available, fall back to simple split
                    try:
                        from ..tokenize.basic import split_words  # type: ignore

                        tokens = [t.lower().strip(".,!?\"'()[]<>") for t in split_words(transcript_text, split_character=True)]  # type: ignore
                    except Exception:
                        tokens = [t.lower().strip(".,!?\"'()[]<>") for t in transcript_text.split()]

                    # Normalize ignored words the same way tokens are normalized so
                    # that markers like "[noise]" match the token "noise".
                    def _norm(s: str) -> str:
                        return s.strip().lower().strip(".,!?\"'()[]<>")

                    ignored_set = {_norm(w) for w in self._ignored_words}
                    if tokens and all(tok in ignored_set for tok in tokens):
                        logger.info("Ignored filler-only interruption while agent speaking: %r", transcript_text)
                        # emit agent_false_interruption for backwards compatibility if session supports it
                        try:
                            if activity._session is not None:
                                activity._session.emit("agent_false_interruption")
                        except Exception:
                            logger.debug("failed to emit agent_false_interruption event", exc_info=True)
                        return
            except Exception:
                # On any unexpected error, fall back to original handler to avoid breaking runtime
                logger.exception("filler filter failed, falling back to original handler")

            return orig(ev)

        # bind wrapper to instance
        setattr(activity, "_on_input_audio_transcription_completed", wrapper)
        self._orig_handler_map[activity] = orig

    def detach_from_activity(self, activity) -> None:
        """Restore the original handler for a previously attached activity."""
        orig = self._orig_handler_map.pop(activity, None)
        if orig is not None:
            setattr(activity, "_on_input_audio_transcription_completed", orig)