"""Append-only ``.architecture/test_results.jsonl`` writer (Phase 2 Task 17).

Records one JSONL line per test suite invocation. Consumers (drift
analyzer, learning loop) key on ``suite`` and ``timestamp`` to build
per-suite pass-rate trends.

Same atomicity / determinism conventions as :mod:`gates` and :mod:`drift`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_JOURNAL_RELPATH = ".architecture/test_results.jsonl"


def _now_iso() -> str:
    pinned = os.environ.get("AMS_DETERMINISTIC_NOW")
    if pinned:
        return pinned
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class TestFailure:
    """A single test failure inside a batch.

    Attributes
    ----------
    nodeid:
        Test identifier (pytest ``nodeid`` or JUnit ``classname.name``).
    message:
        First line of the failure message (typically the assertion).
    """

    # Prevent pytest from collecting this dataclass as a test class
    # (class name starts with ``Test``).
    __test__ = False

    nodeid: str
    message: str

    def to_dict(self) -> dict:
        return {"nodeid": self.nodeid, "message": self.message}


@dataclass(frozen=True)
class TestResultBatch:
    """A single test-suite invocation summary.

    Attributes
    ----------
    suite:
        Suite name (e.g. ``"ams-unit"``, ``"oca-e2e"``). Keys per-suite
        trending.
    total, passed, failed, skipped:
        Test-count roll-up. Consumers may derive ``errored`` as
        ``total - passed - failed - skipped`` if desired; explicit
        ``errored`` is deferred.
    duration_s:
        Wall-clock seconds for the suite.
    failures:
        Optional tuple of :class:`TestFailure`. Absent / empty when the
        suite passed.
    timestamp:
        ISO-8601 UTC. If empty, :func:`append` stamps ``_now_iso()``.
    """

    # Prevent pytest from collecting this dataclass as a test class.
    __test__ = False

    suite: str
    total: int
    passed: int
    failed: int
    skipped: int
    duration_s: float
    failures: tuple[TestFailure, ...] = ()
    timestamp: str = ""

    def to_json_line(self) -> str:
        payload: dict = {
            "timestamp": self.timestamp or _now_iso(),
            "suite": self.suite,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "duration_s": self.duration_s,
            "failures": [f.to_dict() for f in self.failures],
        }
        return json.dumps(payload, ensure_ascii=False) + "\n"


def append(repo_path: Path, batch: TestResultBatch) -> None:
    """Atomically append ``batch`` to ``<repo>/.architecture/test_results.jsonl``."""
    target = repo_path / _JOURNAL_RELPATH
    target.parent.mkdir(parents=True, exist_ok=True)
    line = batch.to_json_line().encode("utf-8")
    fd = os.open(target, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
    try:
        os.write(fd, line)
        os.fsync(fd)
    finally:
        os.close(fd)


__all__ = ["TestResultBatch", "TestFailure", "append"]
