"""pipeline_v3.substrate.cache — Content-addressed cache.

Stages that pass the same input twice within a run should get identical
outputs. This cache memoizes stage outputs by a content hash of the
input, scoped by stage name and run id.

Not persistent — lives for the duration of a Pipeline run. Persistent
caching (across runs) is a Part 5+ concern and lives elsewhere.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

__all__ = ["ContentCache"]


def _digest(payload: Any) -> str:
    """Return a stable SHA-256 hex digest for any JSON-serializable payload.

    Falls back to ``repr()`` for non-JSON-serializable values. That is
    lossy but deterministic given the same Python interpreter version.
    """
    try:
        blob = json.dumps(payload, sort_keys=True, default=repr).encode("utf-8")
    except TypeError:
        blob = repr(payload).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


@dataclass
class ContentCache:
    """In-run content-addressed cache.

    Key = (stage_name, content_digest). Miss returns ``None``.
    """

    _store: dict[tuple[str, str], Any] = field(default_factory=dict)

    def get(self, stage_name: str, input_payload: Any) -> Any | None:
        key = (stage_name, _digest(input_payload))
        return self._store.get(key)

    def put(self, stage_name: str, input_payload: Any, output: Any) -> None:
        key = (stage_name, _digest(input_payload))
        self._store[key] = output

    def __len__(self) -> int:
        return len(self._store)
