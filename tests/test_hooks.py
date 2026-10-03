import subprocess
import sys
import json
from pathlib import Path

HOOKS_DIR = Path(__file__).parent.parent / "integrations" / "claude_code"


def test_pretool_hook_fails_closed_when_unreachable():
    hook_script = HOOKS_DIR / "pretool_hook.py"
    input_data = json.dumps({"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}, "session_id": "test"})
    # Run hook against unreachable port
    result = subprocess.run(
        [sys.executable, str(hook_script)],
        input=input_data,
        text=True,
        capture_output=True,
        env={"REFLEXARC_URL": "http://127.0.0.1:9999", "REFLEXARC_TIMEOUT": "1"},
    )
    # Must exit with code 2 (fail-closed)
    assert result.returncode == 2
    assert "ReflexArc unreachable" in result.stderr


def test_goal_hook_silent_on_unreachable():
    hook_script = HOOKS_DIR / "goal_hook.py"
    input_data = json.dumps({"prompt": "Delete old files", "session_id": "test"})
    result = subprocess.run(
        [sys.executable, str(hook_script)],
        input=input_data,
        text=True,
        capture_output=True,
        env={"REFLEXARC_URL": "http://127.0.0.1:9999"},
    )
    # Must exit 0 and produce no stdout
    assert result.returncode == 0
    assert result.stdout.strip() == ""
