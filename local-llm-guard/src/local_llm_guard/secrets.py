"""Find secret-looking values in text and replace them with placeholders."""

import math
import re
from collections import Counter
from dataclasses import dataclass

PLACEHOLDER_RE = re.compile(r"<SECRET_\d+>")

# Words that make a key name a credential. Matched in any case and inside compound keys
# (`DB_PASS`, `db.pw`). `pass`, `pin` and `sig` must not go on with a lower-case letter, so
# `mapping` or `signal` do not count, but `dbPass` and `PIN_CODE` do. Over-masking is accepted.
_KEY_NAMES = (
    r"token|secret|passwor[dt]|passwd|passphrase|passcode|kennwort|pass(?-i:(?![a-z]))"
    r"|pwd|pw|pin(?-i:(?![a-z]))|sig(?-i:(?![a-z]))|signature|api[_-]?key|apikey|key|auth"
    r"|credential|private|session|cookie"
)
# A quoted value runs to the matching quote that is not escaped by a backslash.
_QUOTED = r"""(?P<q>["'])(?P<qval>(?:\\.|(?!(?P=q))[^\\\n])*)(?P=q)"""
# `key = v`, `key: v`, `KEY=v`, `"key": "v"`, `password="v"`. An unquoted value runs to the
# end of the line; it may be empty (YAML key with a nested block).
_KEY_VALUE_RE = re.compile(
    rf"""(?ix)
    (?<![\w.-])                        # a key starts at a word start (keeps the scan linear)
    [\w.-]*(?:{_KEY_NAMES})[\w.-]*      # key name containing a secret word
    ["']?[ \t]*[:=][ \t]*               # closing key quote, separator
    (?:{_QUOTED}                         # quoted value
      |(?P<uval>[^\n]*))                 # unquoted value
    """
)
_QUOTED_AT_RE = re.compile(_QUOTED)
_BARE_RE = re.compile(r"\S+")
_BLOCK_INDICATOR_RE = re.compile(r"[|>][1-9]?[+-]?[1-9]?(?:[ \t]+#.*)?")
_YAML_KEY_PREFIX_RE = re.compile(r"[ \t]*(?:-[ \t]+)?[\"']?")
# <password>v</password>, also with attributes or CDATA.
_XML_ELEMENT_RE = re.compile(
    rf"(?is)<(?P<tag>[\w:.-]*(?:{_KEY_NAMES})[\w:.-]*)(?:\s[^<>]*)?>"
    rf"(?P<val>(?:<!\[CDATA\[.*?\]\]>|[^<])*)</(?P=tag)\s*>"
)
# plist: <key>Password</key><string>v</string>
_PLIST_RE = re.compile(
    rf"(?is)<key>[^<]*(?:{_KEY_NAMES})[^<]*</key>\s*<string>(?P<val>[^<]*)</string>"
)
# <add key="DbPassword" value="v" />
_ATTR_PAIR_RE = re.compile(
    rf"""(?is)\b(?:key|name)\s*=\s*["'][^"'\n]*(?:{_KEY_NAMES})[^"'\n]*["']\s+value\s*=\s*"""
)
# .netrc: `machine h login u password v`, or `password v` on its own line.
_NETRC_MACHINE_RE = re.compile(r"(?im)^[ \t]*(?:machine|default)\b[^\n]*")
_NETRC_IN_LINE_RE = re.compile(r"(?i)(?<!\S)(?:password|passwd|account)[ \t]+(?=\S)")
_LINE_START_RE = re.compile(r"(?im)^[ \t]*(?:passwor[dt]|passwd|kennwort)[ \t]+(?=\S)")
_LINE_START_NETRC_RE = re.compile(r"(?im)^[ \t]*account[ \t]+(?=\S)")
# CLI: --password v, --password=v, --api-key v, --token v, --secret v, --pass...
_LONG_FLAG_RE = re.compile(
    r"(?i)(?<![\w-])--[\w-]*(?:pass|token|secret|api-?key|pwd|credential)[\w-]*"
    r"(?:=(?=\S)|[ \t]+(?=[^\s-]))"
)
# -p v / -pv, only on a line with a database-style command.
_DB_COMMAND_RE = re.compile(
    r"(?i)(?<![\w-])(?:mysql\w*|mariadb\w*|psql|pg_\w+|mongo\w*|redis-cli|sqlcmd|sshpass"
    r"|isql|clickhouse-client)(?![\w-])"
)
_SHORT_P_RE = re.compile(r"(?<!\S)-p(?:[ \t]+(?=[^\s-])|(?=\S))")
# Prose: `password is X`, `Passwort ist X`, `the password for bob is X`, `pw: X`.
_PROSE_WORDS = (
    r"passwor[dt]|passwd|passphrase|passcode|kennwort|pwd|pw|pin|token|secret|api[ _-]?key"
    r"|zugangscode|geheimzahl"
)
_PROSE_RE = re.compile(
    rf"(?i)(?<![a-z])(?:{_PROSE_WORDS})[a-z]*(?:[^\n.!?]|\.(?=\S)){{0,40}}?"
    r"(?:(?<![a-z])(?:is|ist|was|war|lautet|are|sind)(?![a-z])|[:=])[ \t]*:?[ \t]*(?=\S)"
)
_SCHEME_RE = re.compile(r"(?i)(?:Bearer|Basic|Token)\s+")
_PREFIX_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|gho_|github_pat_|sk-ant-|sk-|AKIA|ASIA|dapi|xox[abpr]-|glpat-)"
    r"[A-Za-z0-9_\-]{12,}"
)
# Without an END marker the block runs to the end of the text.
_PEM_RE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----"
    r"(?:.*?-----END [A-Z ]*PRIVATE KEY(?: BLOCK)?-----|.*\Z)",
    re.DOTALL,
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


def _token_span(text: str, pos: int, strip_punct: bool) -> tuple[int, int] | None:
    """The value that starts at pos: a quoted string, or a run of non-space characters."""
    m = _QUOTED_AT_RE.match(text, pos)
    if m:
        start, end = m.span("qval")
        return (start, end) if end > start else None
    m = _BARE_RE.match(text, pos)
    if not m:
        return None
    val = m.group()
    if strip_punct:
        val = val.rstrip(".,;:!?)]}\"'")
    return (pos, pos + len(val)) if val else None


def _lines_after(text: str, pos: int):
    """(start, end) of every line after the line that holds pos."""
    i = text.find("\n", pos)
    while i != -1:
        start = i + 1
        end = text.find("\n", start)
        yield start, (len(text) if end == -1 else end)
        i = end


def _content(text: str, start: int, end: int) -> tuple[int, int, int] | None:
    """(indent, content start, content end) of a line, or None for a blank line."""
    line = text[start:end]
    body = line.strip()
    if not body:
        return None
    indent = len(line) - len(line.lstrip(" \t"))
    return indent, start + indent, start + len(line.rstrip())


def _block_spans(text: str, pos: int, key_indent: int, list_items: bool) -> list[tuple[int, int]]:
    """Mask the lines below a key that are indented deeper (and `- ` items, for lists)."""
    out: list[tuple[int, int]] = []
    for start, end in _lines_after(text, pos):
        c = _content(text, start, end)
        if c is None:
            continue
        indent, cs, ce = c
        is_item = text.startswith("- ", cs)
        if indent < key_indent or (indent == key_indent and not (list_items and is_item)):
            break
        if is_item:
            cs += 2
        if ce > cs:
            out.append((cs, ce))
    return out


def _array_spans(text: str, pos: int, rest: tuple[int, int]) -> list[tuple[int, int]]:
    """A JSON array opened on the key line: mask each line up to the closing bracket."""
    out = [rest] if rest[1] > rest[0] else []
    for start, end in _lines_after(text, pos):
        c = _content(text, start, end)
        if c is None:
            continue
        _, cs, ce = c
        if text.startswith("]", cs):
            break
        out.append((cs, ce))
    return out


def _key_value_spans(text: str, m: re.Match[str]) -> list[tuple[int, int]]:
    if m.group("qval") is not None:
        start, end = m.start("qval"), m.end("qval")
        return [(start, end)] if end > start else []
    start = m.start("uval")
    val = m.group("uval").rstrip()
    line_start = text.rfind("\n", 0, m.start()) + 1
    prefix = text[line_start : m.start()]
    key_indent = len(prefix) - len(prefix.lstrip(" \t"))
    if _BLOCK_INDICATOR_RE.fullmatch(val):
        return _block_spans(text, start, key_indent, list_items=False)
    if not val:
        if _YAML_KEY_PREFIX_RE.fullmatch(prefix):
            return _block_spans(text, start, key_indent, list_items=True)
        return []
    if val.startswith("[") and "]" not in val:
        rest = text[start + 1 : start + len(val)]
        offset = len(rest) - len(rest.lstrip())
        return _array_spans(text, start, (start + 1 + offset, start + len(val)))
    val = val.removesuffix(",").rstrip()
    end = start + len(val)
    scheme = _SCHEME_RE.match(val)
    if scheme:
        start += scheme.end()
    return [(start, end)] if end > start else []


def _rule_spans(text: str) -> list[tuple[int, int, str]]:
    """Spans of the key-, flag- and prose-based rules."""
    spans: list[tuple[int, int, str]] = []

    def add(span: tuple[int, int] | None, cat: str) -> None:
        if span and span[1] > span[0]:
            spans.append((span[0], span[1], cat))

    for m in _KEY_VALUE_RE.finditer(text):
        for span in _key_value_spans(text, m):
            add(span, "key-value")
    for rx in (_XML_ELEMENT_RE, _PLIST_RE):
        for m in rx.finditer(text):
            val = m.group("val")
            lead = len(val) - len(val.lstrip())
            add((m.start("val") + lead, m.start("val") + len(val.rstrip())), "xml")
    for m in _ATTR_PAIR_RE.finditer(text):
        add(_token_span(text, m.end(), strip_punct=False), "xml")
    netrc = False
    for line in _NETRC_MACHINE_RE.finditer(text):
        netrc = True
        for m in _NETRC_IN_LINE_RE.finditer(line.group()):
            add(_token_span(text, line.start() + m.end(), strip_punct=False), "netrc")
    for rx in (_LINE_START_RE, _LINE_START_NETRC_RE) if netrc else (_LINE_START_RE,):
        for m in rx.finditer(text):
            add(_token_span(text, m.end(), strip_punct=False), "netrc")
    for m in _LONG_FLAG_RE.finditer(text):
        add(_token_span(text, m.end(), strip_punct=False), "cli-flag")
    for cmd in _DB_COMMAND_RE.finditer(text):
        line_start = text.rfind("\n", 0, cmd.start()) + 1
        line_end = text.find("\n", cmd.start())
        line = text[line_start : len(text) if line_end == -1 else line_end]
        for m in _SHORT_P_RE.finditer(line):
            add(_token_span(text, line_start + m.end(), strip_punct=False), "cli-flag")
    for m in _PROSE_RE.finditer(text):
        add(_token_span(text, m.end(), strip_punct=True), "prose")
    return spans


def find_secret_spans(text: str) -> list[tuple[int, int, str]]:
    """Return merged (start, end, category) spans of secret values, sorted by start."""
    spans = _rule_spans(text)
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
