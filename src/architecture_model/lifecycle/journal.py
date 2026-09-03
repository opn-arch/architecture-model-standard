"""Append-only JSONL journal for lifecycle events.

Each entry is a canonical single-line JSON object with fields ``id`` (uuid4
hex), ``ts`` (ISO 8601 UTC), ``event`` (kind string), and ``payload`` (dict).

Concurrency
-----------
Single-writer per process. Multi-process write coordination is out of scope;
use :class:`architecture_model.lifecycle.locks.FileLock` around a
:class:`Journal` if you need it.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterable, Iterator, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

from .serialization import canonical_json

PACKAGE_PUBLISH_BEGIN = "package.publish.begin"
PACKAGE_PUBLISH_COMMIT = "package.publish.commit"
PACKAGE_PUBLISH_ABORT = "package.publish.abort"
STORE_WRITE_BEGIN = "store.write.begin"
STORE_WRITE_COMMIT = "store.write.commit"
INDEX_REBUILD_COMMIT = "index.rebuild.commit"


class JournalEntry(TypedDict):
    id: str
    ts: str
    event: str
    payload: dict[str, Any]


class Journal:
    """Append-only JSONL journal."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, payload: Mapping[str, Any]) -> str:
        """Append one event and return its id."""
        entry_id = uuid.uuid4().hex
        entry: dict[str, Any] = {
            "id": entry_id,
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "event": event,
            "payload": dict(payload),
        }
        line = canonical_json(entry) + b"\n"
        fd = os.open(
            str(self.path),
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o644,
        )
        try:
            written = 0
            while written < len(line):
                written += os.write(fd, line[written:])
            os.fsync(fd)
        finally:
            os.close(fd)
        return entry_id

    def replay(self, *, since: str | None = None) -> Iterable[JournalEntry]:
        """Yield entries in order. If ``since`` is given, skip up to and
        including the entry with that id.
        """
        return self._replay_iter(since)

    def _replay_iter(self, since: str | None) -> Iterator[JournalEntry]:
        if not self.path.exists():
            return
        skipping = since is not None
        with self.path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                obj = json.loads(raw)
                if skipping:
                    if obj.get("id") == since:
                        skipping = False
                    continue
                yield obj  # type: ignore[misc]
