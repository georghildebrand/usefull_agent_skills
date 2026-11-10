import json

import pytest

from local_llm_guard.edit import (
    CHANGE_SCHEMA,
    Change,
    EditRejected,
    apply_changes,
    parse_changes,
    unified_diff,
)

TOKEN = "ghp_" + "a1" * 18
MAP = {"<SECRET_1>": TOKEN}


def test_valid_change_applied():
    out = apply_changes("a = 1\nb = 2\n", [Change(2, "b = 2", "b = 3")], {})
    assert out == "a = 1\nb = 3\n"


def test_delete_and_multiline():
    out = apply_changes("a\nb\nc\n", [Change(1, "a", ""), Change(3, "c", "c1\nc2")], {})
    assert out == "b\nc1\nc2\n"


def test_wrong_old_rejected():
    with pytest.raises(EditRejected) as e:
        apply_changes("a = 1\n", [Change(1, "a = 9", "a = 2")], {})
    assert "line 1" in str(e.value)
    assert "a = 9" not in str(e.value) and "a = 1" not in str(e.value)


def test_out_of_range_rejected():
    with pytest.raises(EditRejected):
        apply_changes("a\n", [Change(2, "a", "b")], {})
    with pytest.raises(EditRejected):
        apply_changes("a\n", [Change(0, "a", "b")], {})


def test_placeholder_removed_rejected():
    with pytest.raises(EditRejected):
        apply_changes("token = <SECRET_1>\n", [Change(1, "token = <SECRET_1>", "token = x")], MAP)


def test_placeholder_added_rejected():
    with pytest.raises(EditRejected):
        apply_changes("a = 1\n", [Change(1, "a = 1", "a = <SECRET_1>")], MAP)


def test_key_renamed_keeps_real_value():
    masked = "region = x\ntoken = <SECRET_1>\n"
    out = apply_changes(masked, [Change(2, "token = <SECRET_1>", "api_token = <SECRET_1>")], MAP)
    assert out == f"region = x\napi_token = {TOKEN}\n"


def test_crlf_kept():
    out = apply_changes("a\r\nb\r\n", [Change(1, "a", "x\ny")], {})
    assert out == "x\r\ny\r\nb\r\n"


def test_no_final_newline_kept():
    assert apply_changes("a\nb", [Change(2, "b", "c")], {}) == "a\nc"


def test_duplicate_lines_rejected():
    with pytest.raises(EditRejected):
        apply_changes("a\nb\n", [Change(1, "a", "x"), Change(1, "a", "y")], {})


def test_parse_changes():
    raw = json.dumps({"changes": [{"line": 1, "old": "a", "new": "b"}]})
    assert parse_changes(raw) == [Change(1, "a", "b")]


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        "[]",
        '{"changes": "x"}',
        '{"changes": [{"line": "1", "old": "a", "new": "b"}]}',
        '{"changes": [{"line": 1, "old": "a"}]}',
        json.dumps({"changes": [{"line": i + 1, "old": "a", "new": "b"} for i in range(51)]}),
    ],
)
def test_parse_changes_bad(raw):
    with pytest.raises(EditRejected):
        parse_changes(raw)


def test_schema_and_diff():
    assert CHANGE_SCHEMA["properties"]["changes"]["maxItems"] == 50
    d = unified_diff("a\n", "b\n", "/x/f.txt")
    assert "-a" in d and "+b" in d and "/x/f.txt" in d


def test_mixed_endings_rejected():
    with pytest.raises(EditRejected, match="mixes CRLF and LF"):
        apply_changes("a\r\nb\n", [Change(1, "a", "x")], {})
