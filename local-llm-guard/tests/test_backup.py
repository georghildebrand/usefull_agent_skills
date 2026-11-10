import os
import time

from local_llm_guard.backup import backup_file, prune_backups


def test_backup_name_and_modes(tmp_path):
    src = tmp_path / "f.txt"
    src.write_text("hello")
    root = tmp_path / "bk"
    b = backup_file(src, root)
    assert "%" in b.name and "/" not in b.name
    assert b.name.startswith(str(src).replace("/", "%") + ".")
    stamp = b.name.rsplit(".", 1)[1]
    assert len(stamp) == 15 and stamp[8] == "-"
    assert (root.stat().st_mode & 0o777) == 0o700
    assert (b.stat().st_mode & 0o777) == 0o600
    assert b.read_text() == "hello"


def test_prune(tmp_path):
    root = tmp_path / "bk"
    root.mkdir()
    old = root / "old"
    new = root / "new"
    old.write_text("x")
    new.write_text("x")
    t = time.time()
    os.utime(old, (t - 31 * 86400, t - 31 * 86400))
    os.utime(new, (t - 86400, t - 86400))
    assert prune_backups(root=root) == 1
    assert not old.exists() and new.exists()


def test_prune_missing_root(tmp_path):
    assert prune_backups(root=tmp_path / "none") == 0


def test_backup_uses_given_bytes(tmp_path):
    src = tmp_path / "f.txt"
    src.write_bytes(b"changed")
    b = backup_file(src, tmp_path / "bk", data=b"verified")
    assert b.read_bytes() == b"verified"
