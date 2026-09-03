"""Tests for lifecycle.atomic_store."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from architecture_model.lifecycle import atomic_store


def _list_tmp(dirpath: Path) -> list[Path]:
    return [p for p in dirpath.iterdir() if ".tmp-" in p.name or ".staging-" in p.name]


def test_write_atomic_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "hello.txt"
    atomic_store.write_atomic(target, b"hello")
    assert target.read_bytes() == b"hello"


def test_write_atomic_leaves_no_tmp(tmp_path: Path) -> None:
    target = tmp_path / "a.bin"
    atomic_store.write_atomic(target, b"x")
    assert _list_tmp(tmp_path) == []


def test_write_atomic_crash_before_replace_preserves_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "orig.txt"
    target.write_bytes(b"ORIGINAL")

    def boom(*args: object, **kwargs: object) -> None:
        raise OSError("simulated crash")

    monkeypatch.setattr(atomic_store.os, "replace", boom)
    with pytest.raises(OSError):
        atomic_store.write_atomic(target, b"NEW")
    assert target.read_bytes() == b"ORIGINAL"
    assert _list_tmp(tmp_path) == []


def test_write_atomic_new_file_crash_leaves_no_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "new.txt"

    def boom(*args: object, **kwargs: object) -> None:
        raise OSError("simulated crash")

    monkeypatch.setattr(atomic_store.os, "replace", boom)
    with pytest.raises(OSError):
        atomic_store.write_atomic(target, b"NEW")
    assert not target.exists()
    assert _list_tmp(tmp_path) == []


def test_write_tree_atomic_publishes_multiple_files(tmp_path: Path) -> None:
    root = tmp_path / "pkg"
    files = {
        Path("a.txt"): b"A",
        Path("sub/b.txt"): b"B",
        Path("sub/deep/c.txt"): b"C",
    }
    atomic_store.write_tree_atomic(root, files)
    assert (root / "a.txt").read_bytes() == b"A"
    assert (root / "sub/b.txt").read_bytes() == b"B"
    assert (root / "sub/deep/c.txt").read_bytes() == b"C"
    # No staging leftover
    siblings = [p for p in tmp_path.iterdir() if ".staging-" in p.name]
    assert siblings == []


def test_write_tree_atomic_all_or_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "pkg"
    files = {Path("a.txt"): b"A", Path("b.txt"): b"B"}

    calls = {"n": 0}
    real_replace = os.replace

    def flaky(src: object, dst: object) -> None:
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("boom")
        real_replace(src, dst)  # type: ignore[arg-type]

    monkeypatch.setattr(atomic_store.os, "replace", flaky)
    with pytest.raises(OSError):
        atomic_store.write_tree_atomic(root, files)
    assert not root.exists()
    siblings = [p for p in tmp_path.iterdir() if ".staging-" in p.name]
    assert siblings == []


def test_write_tree_atomic_refuses_existing_root(tmp_path: Path) -> None:
    root = tmp_path / "pkg"
    root.mkdir()
    with pytest.raises(FileExistsError):
        atomic_store.write_tree_atomic(root, {Path("a.txt"): b"A"})


def test_switch_current_atomic(tmp_path: Path) -> None:
    target = tmp_path / "v1"
    target.mkdir()
    pointer = tmp_path / "current"
    atomic_store.switch_current(pointer, target)
    assert pointer.is_symlink()
    resolved = (pointer.parent / os.readlink(pointer)).resolve()
    assert resolved == target.resolve()


def test_switch_current_swaps_existing(tmp_path: Path) -> None:
    v1 = tmp_path / "v1"
    v1.mkdir()
    v2 = tmp_path / "v2"
    v2.mkdir()
    pointer = tmp_path / "current"
    atomic_store.switch_current(pointer, v1)
    atomic_store.switch_current(pointer, v2)
    resolved = (pointer.parent / os.readlink(pointer)).resolve()
    assert resolved == v2.resolve()


def test_switch_current_missing_target_raises(tmp_path: Path) -> None:
    pointer = tmp_path / "current"
    with pytest.raises(FileNotFoundError):
        atomic_store.switch_current(pointer, tmp_path / "does-not-exist")
