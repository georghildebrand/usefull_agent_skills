import os
import pathlib

import pytest

from local_llm_guard.files import (
    FileRefused,
    LoadedFile,
    check_budget,
    estimate_tokens,
    load_files,
)


def _no_read(*a, **k):
    raise AssertionError("file was opened")


def test_env_refused_without_reading(tmp_path, monkeypatch):
    for name in (".env", ".env.local"):
        (tmp_path / name).write_text("K=v")
    monkeypatch.setattr(pathlib.Path, "read_bytes", _no_read)
    monkeypatch.setattr(pathlib.Path, "read_text", _no_read)
    monkeypatch.setattr("builtins.open", _no_read)
    for name in (".env", ".env.local"):
        with pytest.raises(FileRefused, match=r"\.env files are never read"):
            load_files([str(tmp_path / name)])


def test_symlink_to_env_refused(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("K=v")
    link = tmp_path / "notes.txt"
    link.symlink_to(tmp_path / ".env")
    monkeypatch.setattr(pathlib.Path, "read_bytes", _no_read)
    with pytest.raises(FileRefused, match=r"\.env files are never read"):
        load_files([str(link)])


def test_too_many_paths():
    with pytest.raises(FileRefused, match="5"):
        load_files([f"/x/{i}" for i in range(6)])


def test_relative_path_refused():
    with pytest.raises(FileRefused, match="absolute"):
        load_files(["rel/path"])


def test_missing_and_directory(tmp_path):
    with pytest.raises(FileRefused, match="not found"):
        load_files([str(tmp_path / "nope.txt")])
    with pytest.raises(FileRefused, match="directory"):
        load_files([str(tmp_path)])


def test_binary_refused(tmp_path):
    blob = tmp_path / "blob.bin"
    blob.write_bytes(b"\x00\x01\xff\xfe\x80")
    with pytest.raises(FileRefused, match="not a text file"):
        load_files([str(blob)])


def test_symlink_resolved(tmp_path):
    real = tmp_path / "real.txt"
    real.write_text("hello")
    link = tmp_path / "link.txt"
    link.symlink_to(real)
    (loaded,) = load_files([str(link)])
    assert loaded.path == real.resolve()
    assert loaded.text == "hello" and loaded.tokens == 2


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores chmod")
def test_permission_denied(tmp_path):
    f = tmp_path / "secret.txt"
    f.write_text("x")
    f.chmod(0)
    try:
        with pytest.raises(FileRefused, match="denied, check the sandbox profile"):
            load_files([str(f)])
    finally:
        f.chmod(0o600)


def test_budget(tmp_path):
    # The budget is checked on the exact prompt text, which holds the file text.
    small = LoadedFile(tmp_path / "small.txt", "a" * 30, 10)
    check_budget([small], "summarize " + small.text, 16384)
    big = LoadedFile(tmp_path / "big.txt", "a" * 60000, 20000)
    with pytest.raises(FileRefused, match=r"big\.txt.*20000.*16384.*raise it with local_config"):
        check_budget([big], "summarize " + big.text, 16384)


def test_estimate_counts_each_digit_as_one_token():
    assert estimate_tokens("1234567890") == 10
    assert estimate_tokens("abcdef") == 2
    assert estimate_tokens("ab cd") == 2  # letters and spaces: 1 per 3
    assert estimate_tokens("12,34\n" * 100) == 500 + 34  # digits and "," count 1 each


def test_estimate_punctuation_and_non_ascii():
    assert estimate_tokens("|-|;:") == 5
    assert estimate_tokens(chr(0x4E00)) == 3  # one UTF-8 byte = at most one token
    assert estimate_tokens(chr(0x1F600)) == 4
    assert estimate_tokens("a1b2c3") == 6  # a word with a digit: every character counts


# Synthetic shapes and the prompt tokens qwen2.5:14b really used for them (measured).
def _shapes():
    import base64
    import hashlib

    return {
        "punct_table": ("".join(f"|-|{i % 7}|;|:|*|\n" for i in range(150)), 1529),
        "cjk": ("".join(chr(0x4E00 + (i * 37) % 2000) for i in range(400)), 623),
        "emoji": ("".join(chr(0x1F600 + i % 70) for i in range(300)), 333),
        "base64": (base64.b64encode(hashlib.sha512(b"x").digest() * 30).decode(), 1910),
        "hex": (hashlib.sha512(b"y").hexdigest() * 30, 3419),
        "prose": ("The quick brown fox jumps over the lazy dog, and then it rests. " * 60, 930),
        "md_table": (
            "".join(f"| row {i} | item name {i} | 12.{i % 100:02d} | ok |\n" for i in range(150)),
            3259,
        ),
    }


@pytest.mark.parametrize("name", list(_shapes()))
def test_estimate_not_below_measured_tokens(name):
    text, real = _shapes()[name]
    assert estimate_tokens(text) >= real


def test_budget_counts_the_prompt_not_the_file_estimate(tmp_path):
    f = LoadedFile(tmp_path / "t.txt", "x", 1)
    with pytest.raises(FileRefused, match="input too large"):
        check_budget([f], "9" * 1100, 2048)


@pytest.mark.parametrize("name", [".EN" + "V", ".En" + "v.local", ".en" + "vrc", "prod.en" + "v"])
def test_env_variants_refused_without_reading(tmp_path, monkeypatch, name):
    (tmp_path / name).write_text("K=v")
    monkeypatch.setattr(pathlib.Path, "read_bytes", _no_read)
    monkeypatch.setattr("builtins.open", _no_read)
    with pytest.raises(FileRefused, match=r"\.env files are never read"):
        load_files([str(tmp_path / name)])


def test_missing_env_path_gets_env_message(tmp_path):
    with pytest.raises(FileRefused, match=r"\.env files are never read"):
        load_files([str(tmp_path / (".en" + "v.local"))])


def test_plain_name_allowed(tmp_path):
    (tmp_path / "notes.txt").write_text("hi")
    assert load_files([str(tmp_path / "notes.txt")])[0].text == "hi"


def test_invalid_utf8_after_ascii_prefix(tmp_path):
    f = tmp_path / "mixed.txt"
    f.write_bytes(b"plain ascii text then " + bytes([0xFF]))
    with pytest.raises(FileRefused, match="not a text file"):
        load_files([str(f)])
