"""Find secret-looking values in text and replace them with placeholders."""

import math
import re
from collections import Counter
from dataclasses import dataclass

PLACEHOLDER_RE = re.compile(r"<SECRET_\d+>")

_KEY_NAMES = r"token|secret|password|passwd|pwd|api[_-]?key|apikey|key|auth|credential|private"
# `key = v`, `key: v`, `KEY=v`, `"key": "v"`. A quoted value runs to the closing quote;
# an unquoted value runs to the end of the line.
_KEY_VALUE_RE = re.compile(
    rf"""(?ix)
    [\w.-]*(?:{_KEY_NAMES})[\w.-]*      # key name containing a secret word
    ["']?[ \t]*[:=][ \t]*               # closing key quote, separator
    (?:(?P<q>["'])(?P<qval>.*?)(?P=q)    # quoted value
      |(?P<uval>[^\n]+))                 # unquoted value
    """
)
_SCHEME_RE = re.compile(r"(?i)(?:Bearer|Basic|Token)\s+")
_PREFIX_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|gho_|github_pat_|sk-ant-|sk-|AKIA|ASIA|dapi|xox[abpr]-|glpat-)"
    r"[A-Za-z0-9_\-]{12,}"
)
# Without an END marker the block runs to the end of the text.
_PEM_RE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----(?:.*?-----END [A-Z ]*PRIVATE KEY-----|.*\Z)", re.DOTALL
)
_JWT_RE = re.compile(r"eyJ[\w-]+\.[\w-]+\.[\w-]+")
_URL_CRED_RE = re.compile(r"://[^\s:/@]+:(?P<val>\S+)(?=@)")
# "=" is allowed only as trailing base64 padding, so `name=value` splits at the "=".
_ENTROPY_RUN_RE = re.compile(r"[A-Za-z0-9+/_\-]{20,}={0,2}")

_MIN_ENTROPY = 3.5
_ID_RE = re.compile(r"[A-Za-z]+-[0-9]+")  # e.g. a workspace id: letters, one hyphen, digits


@dataclass
class MaskResult:
    masked: str
    mapping: dict[str, str]  # placeholder -> real value


def _entropy(s: str) -> float:
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in Counter(s).values())


def _is_high_entropy(run: str) -> bool:
    has_digit = any(ch.isdigit() for ch in run)
    has_letter = any(ch.isalpha() for ch in run)
    if not (has_digit and has_letter) or _ID_RE.fullmatch(run):
        return False
    return _entropy(run) >= _MIN_ENTROPY


def _key_value_span(m: re.Match[str]) -> tuple[int, int] | None:
    if m.group("qval") is not None:
        start, end = m.start("qval"), m.end("qval")
    else:
        start = m.start("uval")
        val = m.group("uval").rstrip().removesuffix(",").rstrip()
        end = start + len(val)
        scheme = _SCHEME_RE.match(val)
        if scheme:
            start += scheme.end()
    return (start, end) if end > start else None


def find_secret_spans(text: str) -> list[tuple[int, int, str]]:
    """Return merged (start, end, category) spans of secret values, sorted by start."""
    spans: list[tuple[int, int, str]] = []
    for m in _KEY_VALUE_RE.finditer(text):
        span = _key_value_span(m)
        if span:
            spans.append((span[0], span[1], "key-value"))
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
