import re
from typing import Literal

RuleHit = Literal["deny", "allowlisted", "none"]

_DENY = [
    re.compile(p)
    for p in (
        r"\brm\s+-[a-zA-Z]*[rR][a-zA-Z]*\s+(/|~|\$HOME)(\s|$)",
        r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",
        r"\bmkfs(\.\w+)?\b",
        r"\bdd\s+if=\S+\s+of=/dev/",
        r"(curl|wget)\b[^|;]*\|\s*(sudo\s+)?(ba|z)?sh\b",
    )
]

_ALLOW = [
    re.compile(p)
    for p in (
        r"^(ls|pwd|whoami|date)(\s+-[A-Za-z]+)*(\s+[\w./~-]+)*$",
        r"^git\s+(status|diff|log)(\s+[\w./~=:-]+)*$",
        r"^(cat|head|tail|wc)\s+[\w./~-]+$",
        r"^(pytest|npm\s+test)(\s+[\w./=:-]+)*$",
    )
]


def classify(text: str) -> RuleHit:
    """Classify command using strict, anchored deterministic regex rules."""
    one_line = text.strip()
    if any(p.search(one_line) for p in _DENY):
        return "deny"
    if "\n" not in one_line and any(p.fullmatch(one_line) for p in _ALLOW):
        return "allowlisted"
    return "none"
