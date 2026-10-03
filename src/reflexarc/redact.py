import re

_PATTERNS = [
    (
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            re.S,
        ),
        "<PRIVATE_KEY>",
    ),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "<AWS_KEY_ID>"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), "<GITHUB_TOKEN>"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"), "<API_KEY>"),
    (
        re.compile(
            r"(?i)\b(bearer|token|password|passwd|secret|api[_-]?key)\b(\s*[=:]\s*)\S+"
        ),
        r"\1\2<REDACTED>",
    ),
]


def redact(text: str) -> str:
    """Redact sensitive credentials and keys, keeping descriptive placeholders."""
    for pat, repl in _PATTERNS:
        text = pat.sub(repl, text)
    return text
