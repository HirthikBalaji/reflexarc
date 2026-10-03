import json
import os
import sys
import urllib.request

data = json.load(sys.stdin)
payload = {
    "tool": data.get("tool_name"),
    "input": data.get("tool_input", {}),
    "session": data.get("session_id"),
}

gateway_url = os.environ.get("REFLEXARC_URL", "http://127.0.0.1:8787") + "/v1/judge"
key = os.environ.get("REFLEXARC_KEY", "")
timeout = float(os.environ.get("REFLEXARC_TIMEOUT", "8"))

headers = {"content-type": "application/json"}
if key:
    headers["authorization"] = f"Bearer {key}"

req = urllib.request.Request(
    gateway_url,
    data=json.dumps(payload).encode("utf-8"),
    headers=headers,
)

try:
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.loads(r.read().decode("utf-8"))
except Exception as exc:
    # Fail closed on failure/unreachable
    print(f"ReflexArc unreachable ({exc}); failing closed", file=sys.stderr)
    sys.exit(2)

if out.get("enforced") == "none":
    # Shadow mode: pass through with standard permissions
    sys.exit(0)

# Return explicit hook decision: allow | ask | deny
result = {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": out.get("enforced", "ask"),
        "permissionDecisionReason": out.get("reason", "ReflexArc evaluation"),
    }
}
print(json.dumps(result))
sys.exit(0)
