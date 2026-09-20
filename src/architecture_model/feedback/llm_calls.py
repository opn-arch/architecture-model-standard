"""Append-only ``.architecture/llm_calls.jsonl`` writer (CAP-DF Part 15).

Records every LLM invocation as a single JSONL line for consumption by
the ``prompt_refiner`` meta-walk. Mirrors the pattern established by
``feedback/gates.py`` and ``feedback/drift.py``:

* Atomic append via ``O_APPEND | O_CREAT | O_WRONLY`` + ``fsync``.
* Fail-soft — journal write errors NEVER propagate to caller.
* Deterministic ``_now_iso`` (honors ``AMS_DETERMINISTIC_NOW``).

The wire format wraps the existing ``LLMCallRecord`` dataclass fields
plus two optional CAP-DF Part 13/14 additions:

* ``endpoint_id`` — the deterministic id from
  ``.architecture/llm/endpoints.yaml`` (Part 13).
* ``task_class`` — the routing task class (Part 14).

Both are empty strings by default so existing callers that emit bare
``LLMCallRecord`` objects work unchanged.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from architecture_model.pipeline.protocol import LLMCallRecord

_JOURNAL_RELPATH = ".architecture/llm_calls.jsonl"


def _now_iso() -> str:
    """Return current UTC ISO-8601 or the ``AMS_DETERMINISTIC_NOW`` pin."""
    pinned = os.environ.get("AMS_DETERMINISTIC_NOW")
    if pinned:
        return pinned
    return datetime.now(timezone.utc).isoformat()


def _record_to_dict(
    record: LLMCallRecord,
    *,
    endpoint_id: str = "",
    task_class: str = "",
) -> dict[str, Any]:
    payload = asdict(record)
    if not payload.get("timestamp"):
        payload["timestamp"] = _now_iso()
    if endpoint_id:
        payload["endpoint_id"] = endpoint_id
    if task_class:
        payload["task_class"] = task_class
    return payload


def append(
    repo_path: Path,
    record: LLMCallRecord,
    *,
    endpoint_id: str = "",
    task_class: str = "",
) -> bool:
    """Append ``record`` to ``<repo>/.architecture/llm_calls.jsonl``.

    Creates ``.architecture/`` on demand. Never truncates. Safe for
    concurrent writers on POSIX (``O_APPEND`` semantics).

    Returns
    -------
    bool
        ``True`` on successful write, ``False`` if any error occurred
        (directory creation, open, write). Fail-soft: this function
        NEVER raises.
    """
    try:
        target = repo_path / _JOURNAL_RELPATH
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = _record_to_dict(
            record, endpoint_id=endpoint_id, task_class=task_class
        )
        line = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
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
        return True
    except Exception:
        return False


def read(repo_path: Path) -> list[dict[str, Any]]:
    """Read the journal as a list of dicts.

    Missing file → empty list. Malformed lines skipped silently
    (best-effort read; journal never blocks refiner).
    """
    target = repo_path / _JOURNAL_RELPATH
    if not target.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


__all__ = ["append", "read"]
