import sys
import os

# Ensure the package root (which contains the 'livekit' package) is on sys.path
repo_root = os.getcwd()
pkg_root = os.path.join(repo_root, "livekit-agents")
# Ensure repo root (contains tests/) is on sys.path so tests can be imported as a package
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
# Ensure livekit package root is also available so imports like `import livekit...` work
if pkg_root not in sys.path:
    sys.path.insert(0, pkg_root)

print('sys.path[0]=', sys.path[0])

from tests.test_transcription_filler_filter import (
    test_ignore_filler_while_agent_speaking,
    test_forward_filler_when_agent_listening,
    test_forward_mixed_filler_and_command,
)

failed = False
for fn in (
    test_ignore_filler_while_agent_speaking,
    test_forward_filler_when_agent_listening,
    test_forward_mixed_filler_and_command,
):
    try:
        fn()
        print(f"OK: {fn.__name__}")
    except AssertionError as e:
        print(f"FAIL: {fn.__name__}: {e}")
        failed = True
    except Exception as e:
        print(f"ERROR: {fn.__name__}: {e}")
        failed = True

if failed:
    raise SystemExit(1)

print("ALL TESTS PASSED")
