import os
import pathlib

import pytest

from local_llm_guard.files import FileRefused, LoadedFile, check_budget, load_files


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
    small = LoadedFile(tmp_path / "small.txt", "a" * 30, 10)
    check_budget([small], "summarize", 16384)
    big = LoadedFile(tmp_path / "big.txt", "a" * 60000, 20000)
    with pytest.raises(FileRefused, match=r"big\.txt.*20000.*16384.*raise it with local_config"):
        check_budget([big], "summarize", 16384)
