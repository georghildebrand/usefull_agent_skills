"""Find secret-looking values in text and replace them with placeholders."""

import math
import re
from collections import Counter
from dataclasses import dataclass

PLACEHOLDER_RE = re.compile(r"<SECRET_\d+>")

_KEY_NAMES = r"token|secret|password|passwd|pwd|api[_-]?key|apikey|key|auth|credential|private"
# `key = v`, `key: v`, `KEY=v`, `"key": "v"`. Group "val" is the value only.
_KEY_VALUE_RE = re.compile(
    rf"""(?ix)
    [\w.-]*(?:{_KEY_NAMES})[\w.-]*      # key name containing a secret word
    ["']?[ \t]*[:=][ \t]*["']?          # separator, optional quotes
    (?P<val>[^\s"',;]+)                 # the value
    """
)
_PREFIX_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|gho_|github_pat_|sk-ant-|sk-|AKIA|ASIA|dapi|xox[abpr]-|glpat-)"
    r"[A-Za-z0-9_\-]{12,}"
)
_PEM_RE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL
)
_JWT_RE = re.compile(r"eyJ[\w-]+\.[\w-]+\.[\w-]+")
_URL_CRED_RE = re.compile(r"://[^\s:/@]+:(?P<val>[^\s@/]+)@")
# "=" is allowed only as trailing base64 padding, so `name=value` splits at the "=".
_ENTROPY_RUN_RE = re.compile(r"[A-Za-z0-9+/_\-]{20,}={0,2}")

_MIN_ENTROPY = 3.5
_MAX_DIGIT_SHARE = 0.6  # mostly-digit runs are ids, not secrets


@dataclass
class MaskResult:
    masked: str
    mapping: dict[str, str]  # placeholder -> real value


def _entropy(s: str) -> float:
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in Counter(s).values())


def _is_high_entropy(run: str) -> bool:
    digits = sum(ch.isdigit() for ch in run)
    letters = sum(ch.isalpha() for ch in run)
    return (
        letters > 0
        and digits > 0
        and digits / len(run) <= _MAX_DIGIT_SHARE
        and _entropy(run) >= _MIN_ENTROPY
    )


def find_secret_spans(text: str) -> list[tuple[int, int, str]]:
    """Return merged (start, end, category) spans of secret values, sorted by start."""
    spans: list[tuple[int, int, str]] = []
    for m in _KEY_VALUE_RE.finditer(text):
        spans.append((m.start("val"), m.end("val"), "key-value"))
    for m in _PREFIX_RE.finditer(text):
        spans.append((m.start(), m.end(), "prefix"))
    for m in _PEM_RE.finditer(text):
        spans.append((m.start(), m.end(), "pem"))
    for m in _JWT_RE.finditer(text):
        spans.append((m.start(), m.end(), "jwt"))
    for m in _URL_CRED_RE.finditer(text):
        spans.append((m.start("val"), m.end("val"), "url-credential"))
    for m in _ENTROPY_RUN_RE.finditer(text):
        if _is_high_entropy(m.group()):
            spans.append((m.start(), m.end(), "entropy"))

    merged: list[tuple[int, int, str]] = []
    for start, end, cat in sorted(spans):
        if merged and start < merged[-1][1]:
            prev_start, prev_end, prev_cat = merged[-1]
            merged[-1] = (prev_start, max(prev_end, end), prev_cat)
        else:
            merged.append((start, end, cat))
    return merged


def mask_secrets(text: str) -> MaskResult:
    """Replace each secret value with `<SECRET_n>`, numbered by first occurrence."""
    value_to_placeholder: dict[str, str] = {}
    parts: list[str] = []
    pos = 0
    for start, end, _cat in find_secret_spans(text):
        value = text[start:end]
        placeholder = value_to_placeholder.setdefault(
            value, f"<SECRET_{len(value_to_placeholder) + 1}>"
        )
        parts.append(text[pos:start])
        parts.append(placeholder)
        pos = end
    parts.append(text[pos:])
    mapping = {p: v for v, p in value_to_placeholder.items()}
    return MaskResult(masked="".join(parts), mapping=mapping)
