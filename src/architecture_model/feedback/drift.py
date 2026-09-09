"""Append-only ``.architecture/drift.jsonl`` writer (Phase 2 Task 16).

Records a full drift snapshot per model revision as a single JSONL line.
A snapshot bundles all currently-flagged drift issues (orphans, missing
implementations, unrealized capabilities, broken references) so consumers
can reconstruct historical drift state per revision without cross-line
correlation.

Atomicity and determinism follow the same conventions as
:mod:`architecture_model.feedback.gates` — ``O_APPEND`` + ``fsync``,
``AMS_DETERMINISTIC_NOW`` honored for the snapshot timestamp when
omitted at construction time.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

_JOURNAL_RELPATH = ".architecture/drift.jsonl"

DriftKind = Literal[
    "orphan",
    "missing_impl",
    "unrealized_capability",
    "broken_ref",
]


def _now_iso() -> str:
    pinned = os.environ.get("AMS_DETERMINISTIC_NOW")
    if pinned:
        return pinned
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class DriftFlag:
    """A single drift flag against a model entity.

    Attributes
    ----------
    entity_id:
        Model entity id (e.g. ``"COMP-3"``, ``"CAP-F1"``).
    kind:
        One of ``"orphan"``, ``"missing_impl"``, ``"unrealized_capability"``,
        ``"broken_ref"``.
    detail:
        Human-readable diagnostic. Machine consumers should key on
        ``kind`` + ``entity_id``; ``detail`` is for developers.
    """

    entity_id: str
    kind: DriftKind
    detail: str

    def to_dict(self) -> dict:
        return {"entity_id": self.entity_id, "kind": self.kind, "detail": self.detail}


@dataclass(frozen=True)
class DriftSnapshot:
    """A revision-scoped batch of drift flags.

    Attributes
    ----------
    model_revision:
        7-digit generation id or content digest the flags were computed
        against. REQUIRED — drift without a revision is meaningless.
    flags:
        Tuple of :class:`DriftFlag`. Order preserved. An empty tuple is
        valid (records a "clean" snapshot).
    timestamp:
        ISO-8601 UTC. If empty, :func:`append` stamps ``_now_iso()``.
    """

    model_revision: str
    flags: tuple[DriftFlag, ...] = ()
    timestamp: str = ""

    def to_json_line(self) -> str:
        payload: dict = {
            "timestamp": self.timestamp or _now_iso(),
            "model_revision": self.model_revision,
            "flags": [f.to_dict() for f in self.flags],
        }
        return json.dumps(payload, ensure_ascii=False) + "\n"


def append(repo_path: Path, snapshot: DriftSnapshot) -> None:
    """Atomically append ``snapshot`` to ``<repo>/.architecture/drift.jsonl``.

    Creates ``.architecture/`` on demand. Never truncates. Safe for
    concurrent writers on POSIX (``O_APPEND`` semantics).
    """
    target = repo_path / _JOURNAL_RELPATH
    target.parent.mkdir(parents=True, exist_ok=True)
    line = snapshot.to_json_line().encode("utf-8")
    fd = os.open(target, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
    try:
        os.write(fd, line)
        os.fsync(fd)
    finally:
        os.close(fd)


__all__ = ["DriftFlag", "DriftSnapshot", "DriftKind", "append"]
