import json
import os
import sys
import urllib.request

try:
    data = json.load(sys.stdin)
    payload = {
        "session": data.get("session_id", ""),
        "goal": data.get("prompt", ""),
    }

    gateway_url = os.environ.get("REFLEXARC_URL", "http://127.0.0.1:8787") + "/v1/session/goal"
    key = os.environ.get("REFLEXARC_KEY", "")

    headers = {"content-type": "application/json"}
    if key:
        headers["authorization"] = f"Bearer {key}"

    req = urllib.request.Request(
        gateway_url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
    )
    urllib.request.urlopen(req, timeout=2).read()
except Exception:
    # Silent fail-safe: must never inject output into Claude context
    pass

sys.exit(0)
