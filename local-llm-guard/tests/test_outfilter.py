import base64

import pytest

from local_llm_guard.outfilter import LeakError, filter_output

NONE = lambda t: []
S = "fakeTok3n" + "Value9xyzABC"
IBAN = "DE89" + "3704" + "0044" + "0532" + "0130" + "00"
PHONE = "+49 170 " + "1234567"


@pytest.mark.parametrize(
    "leak",
    [S, " ".join(S), S[::-1], base64.b64encode(S.encode()).decode(), S.encode().hex()],
)
def test_known_value_in_any_encoding_raises(leak):
    with pytest.raises(LeakError):
        filter_output(f"the value is {leak}", [S], NONE)


def test_leak_error_message_has_no_content():
    with pytest.raises(LeakError) as exc:
        filter_output(f"the value is {S}", [S], NONE)
    assert S not in str(exc.value)


def test_placeholders_pass():
    assert filter_output("token is <SECRET_1>", [S], NONE) == "token is <SECRET_1>"


def test_placeholder_after_key_passes():
    assert filter_output("token: <SECRET_2>", [S], NONE) == "token: <SECRET_2>"


def test_pii_masked_numbers_kept():
    text = "Mail a" + "@b.example, call " + PHONE + ", IBAN " + IBAN + ", revenue 1.2M, 4500 units"
    out = filter_output(text, [], NONE)
    assert "<EMAIL>" in out and "<PHONE>" in out and "<IBAN>" in out
    assert "1.2M" in out and "4500 units" in out
    assert PHONE not in out and IBAN not in out


def test_short_known_value_not_checked_encoded():
    assert filter_output("code abc", ["abc"], NONE) == "code abc"


def test_names_masked_from_finder():
    out = filter_output("Owner is Erika Mustermann.", [], lambda t: ["Erika Mustermann"])
    assert out == "Owner is <NAME>."


def test_new_secret_in_output_masked():
    assert "ghp_" + "a1" * 18 not in filter_output("x ghp_" + "a1" * 18, [], NONE)


def test_new_secret_becomes_unnumbered_placeholder():
    out = filter_output("x ghp_" + "a1" * 18 + " and <SECRET_1>", [], NONE)
    assert out == "x <SECRET> and <SECRET_1>"


def test_name_finder_failure_fails_closed():
    def boom(t):
        raise RuntimeError("x")

    with pytest.raises(LeakError) as exc:
        filter_output("hello", [], boom)
    assert str(exc.value) == "name check failed"


U = "geheimWört" + "chen42"


@pytest.mark.parametrize("leak", [base64.b64encode(U.encode()).decode(), U.encode().hex()])
def test_non_ascii_known_value_encoded_raises(leak):
    with pytest.raises(LeakError):
        filter_output(f"value {leak}", [U], NONE)


def test_base64_split_across_newline_raises():
    enc = base64.b64encode(S.encode()).decode()
    with pytest.raises(LeakError):
        filter_output(enc[:10] + "\n" + enc[10:], [S], NONE)


def test_names_masked_case_insensitive():
    out = filter_output("hi erika mustermann.", [], lambda t: ["Erika Mustermann"])
    assert out == "hi <NAME>."


def test_business_numbers_unchanged():
    text = "date 2026-11-10, total 1,299.00, 4500 units"
    assert filter_output(text, [], NONE) == text


V = "Xq7" + "!pw#" + "9z"


@pytest.mark.parametrize(
    "text",
    [
        "The database pass" + "word is {v}.",
        "DB_PA" + "SS={v}",
        "Das Pass" + "wort ist {v}",
        "pw: {v}",
        "machine h login u pass" + "word {v}",
        "mysql -u root -p{v}",
    ],
)
def test_new_unmasked_secret_shapes_masked_in_output(text):
    out = filter_output(text.format(v=V), [], NONE)
    assert V not in out and "<SECRET>" in out


def test_prose_placeholder_kept():
    out = filter_output("The pass" + "word is <SECRET_1>.", [], NONE)
    assert out == "The pass" + "word is <SECRET_1>."
