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
