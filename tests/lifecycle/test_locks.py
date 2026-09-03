"""Tests for lifecycle.locks."""

from __future__ import annotations

import multiprocessing as mp
import os
import time
from pathlib import Path

import pytest

from architecture_model.lifecycle import locks


def _hold_lock(lock_path: str, ready_path: str, release_path: str) -> None:
    from architecture_model.lifecycle.locks import FileLock

    with FileLock(Path(lock_path), timeout=5.0):
        Path(ready_path).write_text("ready")
        # Wait for main to signal release
        deadline = time.time() + 10.0
        while time.time() < deadline and not Path(release_path).exists():
            time.sleep(0.05)


def test_lock_acquire_release(tmp_path: Path) -> None:
    lp = tmp_path / "l.lock"
    with locks.FileLock(lp, timeout=1.0):
        assert lp.exists()
    # Should be releasable and re-acquirable
    with locks.FileLock(lp, timeout=1.0):
        pass


def test_lock_timeout_on_contention(tmp_path: Path) -> None:
    lp = tmp_path / "l.lock"
    ready = tmp_path / "ready"
    release = tmp_path / "release"
    ctx = mp.get_context("spawn")
    proc = ctx.Process(target=_hold_lock, args=(str(lp), str(ready), str(release)))
    proc.start()
    try:
        # Wait for child to acquire
        deadline = time.time() + 5.0
        while time.time() < deadline and not ready.exists():
            time.sleep(0.05)
        assert ready.exists(), "child failed to acquire lock"
        with pytest.raises(locks.LockTimeout):
            with locks.FileLock(lp, timeout=0.5):
                pass
    finally:
        release.write_text("go")
        proc.join(timeout=5.0)
        if proc.is_alive():
            proc.terminate()


def test_lock_records_holder_metadata(tmp_path: Path) -> None:
    lp = tmp_path / "l.lock"
    with locks.FileLock(lp, timeout=1.0):
        text = lp.read_text()
    lines = text.strip().splitlines()
    assert lines[0] == str(os.getpid())
    assert lines[1]  # hostname non-empty
    # ts parseable as float
    float(lines[2])


def test_stale_lock_reclaim(tmp_path: Path) -> None:
    import warnings

    lp = tmp_path / "l.lock"
    # Create stale lock file with dead PID and old mtime
    lp.write_text("9999999\nsome-host\n0\n")
    old = time.time() - 700
    os.utime(lp, (old, old))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with locks.FileLock(lp, timeout=1.0, stale_after=600.0):
            pass
        assert any(
            issubclass(w.category, locks.StaleLockReclaimed) for w in caught
        ), [w.category for w in caught]


def test_lock_reentrance_not_supported(tmp_path: Path) -> None:
    lp = tmp_path / "l.lock"
    with locks.FileLock(lp, timeout=0):
        with pytest.raises(locks.LockTimeout):
            with locks.FileLock(lp, timeout=0):
                pass


def test_lock_non_posix_platform(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(locks, "_HAS_FCNTL", False)
    lp = tmp_path / "l.lock"
    with pytest.raises(NotImplementedError):
        with locks.FileLock(lp, timeout=0):
            pass
