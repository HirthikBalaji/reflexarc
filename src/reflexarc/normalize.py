import json
import re
import unicodedata

_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]|\x1b\[[0-9;]*[A-Za-z]")
_URL = re.compile(r"https?://([A-Za-z0-9.\-]+)")
_PATH = re.compile(r"(?<![\w.])(/[\w.\-/]+|~/[\w.\-/]*|[A-Za-z]:\\[\w.\-\\]*)")


def action_text(tool: str, inp: dict) -> str:
    """Normalize agent action payload to a clean string."""
    if tool == "Bash":
        raw = str(inp.get("command", ""))
    elif tool in ("Write", "Edit"):
        body = inp.get("content") or inp.get("new_string") or ""
        raw = f"{tool} {inp.get('file_path', '')}\n{str(body)[:1500]}"
    else:
        raw = f"{tool} {json.dumps(inp, ensure_ascii=False)[:2000]}"

    raw = unicodedata.normalize("NFKC", raw)  # Defeats lookalike Unicode tricks
    return _CTRL.sub("", raw)


def clip(text: str, head: int = 900, tail: int = 400) -> tuple[str, bool]:
    """Keep the start and end of action text; clip the middle if oversized."""
    if len(text) <= head + tail:
        return text, False
    return text[:head] + "\n...[clipped]...\n" + text[-tail:], True


def targets(text: str) -> set[str]:
    """Extract path and URL targets for scope / novelty checking."""
    return set(_URL.findall(text)) | set(_PATH.findall(text))
