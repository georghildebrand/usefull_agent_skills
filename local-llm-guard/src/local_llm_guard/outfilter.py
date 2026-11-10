"""Last gate before model text reaches Claude: leak check, then masking."""

import base64
import binascii
import re
from collections.abc import Callable, Iterable

from local_llm_guard.secrets import PLACEHOLDER_RE, find_secret_spans

NameFinder = Callable[[str], list[str]]

_MIN_KNOWN_LEN = 8
_B64_RE = re.compile(r"[A-Za-z0-9+/=]{12,}")
_HEX_RE = re.compile(r"[0-9a-fA-F]{16,}")

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}(?: ?[A-Z0-9]{1,3})?\b")
# Phone: a leading "+" with country code, a bracketed area code, or a leading 0 with separators.
_PHONE_RE = re.compile(
    r"\+\d{1,3}[\s.-]?(?:\(\d{1,4}\)[\s.-]?)?\d{1,4}(?:[\s.-]?\d{2,}){1,4}"
    r"|\(\d{2,5}\)[\s.-]?\d{3,}(?:[\s.-]?\d{2,})*"
    r"|(?<![\w.])0\d{2,4}[\s/.-]\d{3,}(?:[\s.-]\d{2,})*"
)


class LeakError(Exception):
    """Model output holds a known secret, or could not be checked."""


def _decoded_fragments(text: str) -> list[str]:
    out: list[str] = []
    for m in _B64_RE.finditer(text):
        frag = m.group().rstrip("=")
        for skip in range(4):  # the fragment may start inside a base64 quartet
            part = frag[skip:]
            if len(part) % 4 == 1:
                part = part[:-1]  # a single leftover character cannot be decoded
            try:
                raw = base64.b64decode(part + "=" * (-len(part) % 4))
                out += [raw.decode("latin-1"), raw.decode("utf-8", errors="replace")]
            except (binascii.Error, ValueError):
                continue
    for m in _HEX_RE.finditer(text):
        frag = m.group()
        frag = frag[: len(frag) - len(frag) % 2]
        try:
            raw = bytes.fromhex(frag)
            out += [raw.decode("latin-1"), raw.decode("utf-8", errors="replace")]
        except ValueError:
            continue
    return out


def _check_leaks(text: str, secret_values: Iterable[str]) -> None:
    known = [v for v in secret_values if len(v) >= _MIN_KNOWN_LEN]
    if not known:
        return
    stripped = re.sub(r"\s+", "", text)
    variants = [
        text,
        stripped,
        text[::-1],
        stripped[::-1],
        *_decoded_fragments(text),
        *_decoded_fragments(stripped),
    ]
    if any(v in variant for v in known for variant in variants):
        raise LeakError("known secret found in model output")


def _mask_new_secrets(text: str) -> str:
    out: list[str] = []
    pos = 0
    for start, end, _ in find_secret_spans(text):
        if not PLACEHOLDER_RE.sub("", text[start:end]).strip():
            continue  # only existing placeholders
        out.append(text[pos:start])
        out.append("<SECRET>")
        pos = end
    out.append(text[pos:])
    return "".join(out)


def _mask_names(text: str, find_names: NameFinder) -> str:
    try:
        names = sorted({n for n in find_names(text) if n.strip()}, key=len, reverse=True)
        for name in names:
            text = re.sub(rf"(?<!\w){re.escape(name)}(?!\w)", "<NAME>", text, flags=re.IGNORECASE)
    except Exception:  # noqa: BLE001 - fail closed on any finder error
        raise LeakError("name check failed") from None
    return text


def filter_output(text: str, secret_values: Iterable[str], find_names: NameFinder) -> str:
    """Raise LeakError on a known secret; otherwise return text with sensitive data masked."""
    _check_leaks(text, secret_values)
    text = _mask_new_secrets(text)
    text = _EMAIL_RE.sub("<EMAIL>", text)
    text = _IBAN_RE.sub("<IBAN>", text)
    text = _PHONE_RE.sub("<PHONE>", text)
    return _mask_names(text, find_names)
