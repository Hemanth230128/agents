# LiveKit Agents Voice Extensions

## Transcription Filler Filter

An extension that intelligently filters out filler words/sounds from interrupting the agent while speaking, while still treating them as valid user speech when the agent is quiet.

### Installation

The extension is included with LiveKit Agents. No additional installation required.

### Usage

```python
from livekit.agents.voice.extensions.transcription_filler_filter import FillerFilter

# Create and attach to an AgentActivity instance
filler_filter = FillerFilter.from_env()  # loads from LIVEKIT_IGNORED_WORDS
filler_filter.attach_to_activity(agent_activity)

    # Or configure ignored words at runtime
  filler_filter.set_ignored_words([
    # English filler words
    "uh", "umm", "hmm", "err", "ah", "like", "you know",
  ])
# Later, detach if needed
filler_filter.detach_from_activity(agent_activity)
```

### Configuration

The extension can be configured via:

1. Environment variable (recommended for deployment):
  ```bash
  # Comma-separated list of sounds to ignore while agent is speaking
  LIVEKIT_IGNORED_WORDS="uh,umm,hmm,err,ah,like,you know,mm,mhm,mmm,*,**,***,[noise],[background],[inaudible],[laugh],[cough],[breath],<noise>,<silence>"
  ```

2. Runtime API (good for dynamic updates):
   ```python
   filler_filter.set_ignored_words(["uh", "umm", "hmm"])
   ```

### Default Filtered Sounds

The extension filters two categories of sounds:

1. Filler Words (by language):

- English:
  - uh, um, umm, hmm, err, ah, eh, like, you know
  - Variations: uhh, uhm, erm, hm

-2. Background/Non-speech Sounds:
- Murmurs and minimal responses:
  - mm, mhm, mmm
  - Single sounds: *, **, ***
- Common ASR background markers:
  - [noise], [background], [inaudible]
  - [laugh], [cough], [breath]
  - <noise>, <silence>, <background>

Note: Different ASR providers may transcribe background sounds differently. 
You can customize the list via LIVEKIT_IGNORED_WORDS or set_ignored_words() to match your ASR provider's conventions.

### Events

The extension emits the following events:

- `agent_false_interruption`: Emitted when a filler-only transcript is ignored while the agent is speaking. Useful for monitoring and analytics.

### Interactive Demo

Try out the extension with text-based transcripts:

```bash
# From repository root:
python examples/demo_filler_filter.py

# Available commands:
#   speak    - Set agent state to "speaking"
#   listen   - Set agent state to "listening"
#   words    - Show current ignored words
#   set X Y  - Set ignored words (comma-separated)
#   quit     - Exit
# Any other input is treated as a transcript to filter.
```

### Testing

To run the extension's tests:

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.\.venv\Scripts\Activate.ps1  # Windows PowerShell

# Install test dependencies
pip install pytest

# Run tests
pytest tests/test_transcription_filler_filter.py
```

Or use the lightweight test runner (no pytest required):

```bash
python tests/run_transcription_filler_filter.py
```

### Implementation Notes

- The extension is non-invasive: it wraps the activity's transcription handler without modifying core runtime code.
- Thread-safe and async-aware: preserves the original handler's sync/async behavior.
- Language-agnostic: works with any language's transcription output; just configure the appropriate filler words.
- Case-insensitive matching with punctuation stripping for robustness.