"""Cross-process file locks with timeout and stale-lock reclaim.

Purpose
-------
Coordinate mutually exclusive access to filesystem-backed resources
(e.g., a package staging area) across processes on the same host.

Invariants
----------
* Uses advisory ``fcntl.flock`` (POSIX). Non-POSIX platforms raise
  :class:`NotImplementedError` on enter.
* On acquire, the lock file contains ``pid\\nhostname\\ntimestamp\\n`` so stale
  locks can be detected.
* Non-reentrant: a second acquire from the same process on the same lock file
  blocks or times out like any other contender.
* Stale locks (mtime older than ``stale_after`` seconds AND holder PID dead)
  are reclaimed with a :class:`StaleLockReclaimed` warning.

Platform scope
--------------
POSIX only in Phase 1. Multi-host coordination (NFS advisory quirks) is out of
scope.
"""

from __future__ import annotations

import os
import random
import socket
import time
import warnings
from pathlib import Path
from types import TracebackType
from typing import Optional

try:
    import fcntl as _fcntl  # noqa: F401

    _HAS_FCNTL = True
except ImportError:  # pragma: no cover - non-POSIX
    _HAS_FCNTL = False


class LockTimeout(Exception):
    """Raised when a lock cannot be acquired within the timeout."""


class StaleLockReclaimed(RuntimeWarning):
    """Warned when a stale lock is reclaimed."""


def _pid_alive(pid: int) -> bool:
    """Return True if ``pid`` responds to signal 0."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Exists but not ours
        return True
    except OSError:
        return False
    return True


class FileLock:
    """Advisory exclusive file lock with timeout and stale reclaim."""

    def __init__(
        self,
        path: Path,
        *,
        timeout: Optional[float] = None,
        stale_after: float = 600.0,
    ) -> None:
        self.path = Path(path)
        self.timeout = timeout
        self.stale_after = stale_after
        self._fd: Optional[int] = None

    def _try_reclaim_stale(self) -> bool:
        """Return True if a stale lock was reclaimed."""
        try:
            st = os.stat(str(self.path))
        except FileNotFoundError:
            return False
        age = time.time() - st.st_mtime
        if age < self.stale_after:
            return False
        # Inspect holder PID
        try:
            content = self.path.read_text()
        except OSError:
            return False
        first = content.splitlines()[0] if content.strip() else ""
        try:
            pid = int(first)
        except ValueError:
            pid = -1
        if _pid_alive(pid):
            return False
        try:
            os.unlink(str(self.path))
        except FileNotFoundError:
            pass
        warnings.warn(
            f"reclaimed stale lock {self.path} (pid={pid}, age={age:.0f}s)",
            StaleLockReclaimed,
            stacklevel=3,
        )
        return True

    def _acquire(self) -> None:
        if not _HAS_FCNTL:
            raise NotImplementedError("FileLock is POSIX-only in Phase 1")
        import fcntl

        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline: Optional[float]
        if self.timeout is None:
            deadline = None
        else:
            deadline = time.monotonic() + max(0.0, self.timeout)

        # Pre-check: reclaim stale lock file even if flock would succeed
        # (advisory locking means an abandoned file can still exist).
        self._try_reclaim_stale()

        while True:
            fd = os.open(
                str(self.path), os.O_RDWR | os.O_CREAT, 0o644
            )
            try:
                if self.timeout is None:
                    fcntl.flock(fd, fcntl.LOCK_EX)
                    acquired = True
                else:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        acquired = True
                    except BlockingIOError:
                        acquired = False
            except BaseException:
                os.close(fd)
                raise

            if acquired:
                self._fd = fd
                # Write holder metadata
                try:
                    os.ftruncate(fd, 0)
                    os.lseek(fd, 0, os.SEEK_SET)
                    meta = (
                        f"{os.getpid()}\n"
                        f"{socket.gethostname()}\n"
                        f"{time.time()}\n"
                    ).encode("utf-8")
                    written = 0
                    while written < len(meta):
                        written += os.write(fd, meta[written:])
                    os.fsync(fd)
                except BaseException:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                    os.close(fd)
                    self._fd = None
                    raise
                return

            # Not acquired
            os.close(fd)
            # Try stale reclaim
            if self._try_reclaim_stale():
                continue
            if deadline is None:
                # timeout is None handled above; unreachable
                continue
            now = time.monotonic()
            if self.timeout == 0 or now >= deadline:
                raise LockTimeout(f"could not acquire {self.path} within timeout")
            sleep_for = min(random.uniform(0.01, 0.05), max(0.0, deadline - now))
            time.sleep(sleep_for)

    def __enter__(self) -> "FileLock":
        self._acquire()
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        if self._fd is None:
            return
        import fcntl

        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            try:
                os.close(self._fd)
            finally:
                self._fd = None
