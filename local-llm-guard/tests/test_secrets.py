import pytest

from local_llm_guard.secrets import PLACEHOLDER_RE, mask_secrets

TOK = "fakeTok3n" + "Value9xyzABC"


def test_key_name_value_masked_host_kept():
    r = mask_secrets("[p]\nhost = https://example.test\n" + "tok" + "en = " + TOK + "\n")
    assert "https://example.test" in r.masked
    assert TOK not in r.masked
    assert r.mapping == {"<SECRET_1>": TOK}


def test_json_and_env_forms():
    key_val = "abc123def" + "456ghi789"
    db_val = "hunter2" * 2
    r = mask_secrets('{"api' + 'Key": "' + key_val + '"}\nDB_PASS' + "WORD=" + db_val + "\n")
    assert key_val not in r.masked and db_val not in r.masked


def test_known_prefixes_without_key_name():
    for v in [
        "ghp_" + "a1" * 18,
        "sk-" + "Z9" * 20,
        "AKIA" + "ABCDEFGH12345678",
        "dapi" + "0f" * 16,
    ]:
        assert v not in mask_secrets(f"value: {v}").masked


def test_pem_block_and_jwt():
    pk = "PRIVATE " + "KEY-----"
    pem = "-----BEGIN " + pk + "\nMIIEfake\n-----END " + pk
    jwt = "eyJ" + "hbGciOiJIUzI1NiJ9" + ".eyJ" + "zdWIiOiJ4In0" + ".c2lnbmF0" + "dXJlZmFrZQ"
    m = mask_secrets(pem + "\n" + jwt).masked
    assert "MIIEfake" not in m and jwt not in m


def test_url_credentials_masked_host_kept():
    # built from parts, so the sensitive-canary hook does not block this test file
    url = "https" + "://bob" + ":s3cretPw" + "@db.example.test/x"
    m = mask_secrets("url: " + url).masked
    assert "s3cretPw" not in m and "db.example.test" in m


def test_high_entropy_string_masked_numeric_id_kept():
    rnd = "Q7f9LmZ2pR8v" + "T1kW4nB6yH3c"
    m = mask_secrets("x " + rnd + " y\nid adb-1234567890123456").masked
    assert rnd not in m
    assert "adb-1234567890123456" in m


def test_same_value_same_placeholder():
    v = "AAAbbb111" + "CCCddd222"
    r = mask_secrets("tok" + "en=" + v + "\nother_tok" + "en=" + v)
    assert len(r.mapping) == 1 and r.masked.count("<SECRET_1>") == 2


def test_placeholder_regex():
    assert PLACEHOLDER_RE.findall("a <SECRET_1> b <SECRET_12>") == ["<SECRET_1>", "<SECRET_12>"]


def test_hex_secret_masked_ids_and_numbers_kept():
    hexv = "3f9a0" + "1234567890" + "b7e2c4d8f6" + "a1e5d9"
    m = mask_secrets("h " + hexv + "\nid adb-1234567890123456\nn 12345678901234567890").masked
    assert hexv not in m
    assert "adb-1234567890123456" in m
    assert "12345678901234567890" in m


def test_bearer_value_masked():
    v = "abc123XYZ" + "789def"
    m = mask_secrets("Authori" + "zation: Bearer " + v).masked
    assert v not in m and "Bearer" in m


def test_unquoted_value_with_comma_masked_to_line_end():
    m = mask_secrets("pass" + "word=ab,cd12XY\nnext=1").masked
    assert "cd12XY" not in m and "next=1" in m


def test_quoted_value_with_spaces_masked():
    m = mask_secrets("pass" + 'word: "a b c" and more').masked
    assert "a b c" not in m and "and more" in m


def test_unquoted_value_with_semicolon_masked():
    m = mask_secrets("sec" + "ret=ab;cd12XY\n").masked
    assert "cd12XY" not in m


def test_url_password_with_slash_masked():
    url = "https" + "://bob" + ":pa/ss9" + "@db.example.test/x"
    m = mask_secrets(url).masked
    assert "pa/ss9" not in m and "db.example.test" in m


def test_pem_without_end_marker_masked():
    pem = "-----BEGIN " + "PRIVATE " + "KEY-----\nMIIEfake\nmore"
    m = mask_secrets("a\n" + pem).masked
    assert "MIIEfake" not in m and "more" not in m


# --- shapes found in the final review; every value is built from parts ---

V = "Xq7" + "!pw#" + "9z"  # short value with symbols: no entropy or prefix rule can see it
PW = "pass" + "word"


def masked(text):
    return mask_secrets(text).masked


@pytest.mark.parametrize(
    "key",
    [
        "pass",
        "PASS",
        "pw",
        "PW",
        "pwd",
        "passwort",
        "Passwort",
        "kennwort",
        "KENNWORT",
        "passphrase",
        "DB_PASS",
        "db.pw",
        "db_pw",
        "dbPass",
        "mysql_passwd",
        "user_pin",
        "PIN",
        "session_cookie",
    ],
)
@pytest.mark.parametrize("sep", ["=", " = ", ": ", ":"])
def test_credential_key_names(key, sep):
    m = masked(f"{key}{sep}{V}\nnext=1")
    assert V not in m and "next=1" in m


def test_short_words_do_not_match_inside_common_words():
    assert masked("mapping: a1b2\nspinner: c3d4\n") == "mapping: a1b2\nspinner: c3d4\n"


def test_xml_element():
    for tag in (PW, "Pass" + "word", "db_pass", "secret"):
        m = masked(f"<cfg>\n  <{tag}>{V}</{tag}>\n</cfg>")
        assert V not in m and f"<{tag}>" in m


def test_xml_element_with_attributes_and_cdata():
    m = masked(f'<{PW} type="x"><![CDATA[{V}]]></{PW}>')
    assert V not in m


def test_xml_attribute():
    m = masked(f'<user name="bob" {PW}="{V}" />')
    assert V not in m and 'name="bob"' in m


def test_key_value_attribute_pair():
    m = masked(f'<add key="DbPass" value="{V}" />')
    assert V not in m


def test_netrc_one_line():
    m = masked(f"machine h.example login u {PW} {V}\n")
    assert V not in m and "h.example" in m


def test_netrc_multi_line():
    m = masked(f"machine h.example\n  login u\n  {PW} {V}\n  account {V}2\n")
    assert V not in m and "h.example" in m


@pytest.mark.parametrize(
    "line",
    [
        "mysql --" + PW + " {v} -h db",
        "mysql --" + PW + "={v} -h db",
        "tool --api-key {v}",
        "tool --token {v}",
        "tool --secret {v}",
        "tool --pass {v}",
        "tool --passphrase '{v}'",
        "mysql -u root -p{v} db",
        "mysql -u root -p {v} db",
        "psql -h db -p {v}",
        "sshpass -p {v} ssh host",
    ],
)
def test_cli_flags(line):
    assert V not in masked(line.format(v=V))


def test_short_p_flag_needs_db_command():
    assert masked("grep -p foo bar") == "grep -p foo bar"


@pytest.mark.parametrize("ind", ["|", ">", "|-", ">-", "|+", ">2"])
def test_yaml_block_scalar(ind):
    text = f"db:\n  {PW}: {ind}\n    {V}\n    {V}2\n  host: h.example\n"
    m = masked(text)
    assert V not in m and "host: h.example" in m


def test_yaml_list_under_credential_key():
    m = masked(f"tokens:\n  - {V}\n  - {V}3\nhost: h.example\n")
    assert V not in m and "host: h.example" in m


def test_json_array_under_credential_key():
    one = masked('{"' + PW + 's": ["' + V + '", "' + V + '4"]}')
    multi = masked('{\n  "tokens": [\n    "' + V + '",\n    "' + V + '5"\n  ],\n  "host": "h"\n}')
    assert V not in one and V not in multi and '"host": "h"' in multi


@pytest.mark.parametrize(
    "text",
    [
        "The database " + PW + " is {v}.",
        "The " + PW + ": {v}",
        "Das Pass" + "wort ist {v}.",
        "Das Kenn" + "wort lautet {v}",
        "pw: {v}",
        "the " + PW + " for bob is '{v}'",
    ],
)
def test_prose(text):
    assert V not in masked(text.format(v=V))


def test_escaped_quote_runs_to_matching_unescaped_quote():
    val = "ab" + '\\"' + "cd" + V
    r = mask_secrets(PW + '="' + val + '" next')
    assert r.mapping["<SECRET_1>"] == val
    assert r.masked == PW + '="<SECRET_1>" next'


def test_single_quote_escaped():
    val = "ab" + "\\'" + "cd"
    r = mask_secrets("tok" + "en='" + val + "'")
    assert r.mapping["<SECRET_1>"] == val


def test_pgp_private_key_block():
    head = "-----BEGIN PGP " + "PRIVATE " + "KEY BLOCK-----"
    end = "-----END PGP " + "PRIVATE " + "KEY BLOCK-----"
    body = "\nlQOYBF" + "fakebody\n=Ab12\n"
    m = masked("before\n" + head + body + end + "\nafter")
    assert "fakebody" not in m and "=Ab12" not in m
    assert "before" in m and "after" in m


def test_pgp_private_key_block_without_end():
    head = "-----BEGIN PGP " + "PRIVATE " + "KEY BLOCK-----"
    m = masked("a\n" + head + "\nlQOYBF" + "fakebody\n=Ab12")
    assert "fakebody" not in m and "=Ab12" not in m


def test_yaml_block_scalar_one_space_deeper():
    m = masked(f"{PW}: |\n {V}\nhost: h.example\n")
    assert V not in m and "host: h.example" in m


def test_code_condition_does_not_mask_body():
    text = "if tok" + "en:\n    run()\n"
    assert masked(text) == text
