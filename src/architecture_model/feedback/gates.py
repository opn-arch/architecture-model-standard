"""Append-only ``.architecture/gates.jsonl`` writer (Phase 2 Task 15).

Records the outcome of every :func:`architect_gate` invocation as a single
JSONL line. The journal is diagnostic, not authoritative: callers should
NOT fail user-visible operations if :func:`append` raises.

Atomicity
---------
Writes use ``O_APPEND`` with an explicit ``fsync``. On POSIX, ``write()``
to an ``O_APPEND`` file descriptor is atomic for line-sized payloads
(≤ ``PIPE_BUF``, ≥ 4 KiB on Linux/macOS) — concurrent writers cannot
interleave partial lines. The plan called for a "tmp + rename" pattern
but that is inherently incompatible with append semantics ("never
truncates"); ``O_APPEND`` is the standard, portable answer.

Directory creation is idempotent — the ``.architecture/`` directory is
created on demand (``parents=True, exist_ok=True``). Existing sibling
files (``sil.sqlite`` etc.) are never touched.

Determinism
-----------
Timestamps come from :func:`_now_iso` which honors
``AMS_DETERMINISTIC_NOW`` — see the same helper in
``architecture_model.sil.rollup`` for the established convention.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

_JOURNAL_RELPATH = ".architecture/gates.jsonl"

Outcome = Literal["pass", "fail", "warn"]


def _now_iso() -> str:
    """Return current UTC ISO-8601 or the ``AMS_DETERMINISTIC_NOW`` pin."""
    pinned = os.environ.get("AMS_DETERMINISTIC_NOW")
    if pinned:
        return pinned
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class GateEvent:
    """A single gate-invocation outcome record.

    Attributes
    ----------
    timestamp:
        ISO-8601 UTC timestamp. If empty, :func:`append` stamps
        ``_now_iso()`` when serializing.
    gate_id:
        Stable identifier for the gate rule (e.g. ``"schema_valid"``).
    outcome:
        One of ``"pass"``, ``"fail"``, ``"warn"``.
    findings:
        Human-readable finding strings. Order preserved.
    model_revision:
        Optional model revision the gate ran against (7-digit generation
        id or content digest). ``None`` when the gate ran on an
        unpublished model.
    """

    gate_id: str
    outcome: Outcome
    timestamp: str = ""
    findings: tuple[str, ...] = ()
    model_revision: str | None = None

    def to_json_line(self) -> str:
        """Serialize to a single JSONL line (trailing newline included)."""
        payload: dict = {
            "timestamp": self.timestamp or _now_iso(),
            "gate_id": self.gate_id,
            "outcome": self.outcome,
            "findings": list(self.findings),
        }
        if self.model_revision is not None:
            payload["model_revision"] = self.model_revision
        # ensure_ascii=False keeps unicode findings readable; sort_keys
        # NOT enabled — declared key order is more informative in a log.
        return json.dumps(payload, ensure_ascii=False) + "\n"


def append(repo_path: Path, event: GateEvent) -> None:
    """Atomically append ``event`` to ``<repo>/.architecture/gates.jsonl``.

    Creates ``.architecture/`` on demand. Never truncates. Safe for
    concurrent writers on POSIX (``O_APPEND`` semantics).

    Raises
    ------
    OSError
        If the target directory cannot be created or the file cannot be
        opened for append. Callers should catch and log — journal writes
        must not break the caller's control flow.
    """
    target = repo_path / _JOURNAL_RELPATH
    target.parent.mkdir(parents=True, exist_ok=True)
    line = event.to_json_line().encode("utf-8")
    # Open with O_APPEND | O_CREAT | O_WRONLY for atomic append.
    fd = os.open(
        target,
        os.O_APPEND | os.O_CREAT | os.O_WRONLY,
        0o644,
    )
    try:
        os.write(fd, line)
        os.fsync(fd)
    finally:
        os.close(fd)


__all__ = ["GateEvent", "append", "Outcome"]
