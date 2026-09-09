"""Supplementary-data loaders for MaterializedSlice (Phase 2 Task 10).

A :class:`~architecture_model.lifecycle.model_slice.SupplementaryRef` on a
slice names an out-of-model data source. This module owns the loaders
that resolve each ``kind`` to a bounded fragment attached to
``MaterializedSlice.supplementary_fragments``.

Phase 2 Task 10 lands ``sil`` end-to-end (reads
``.architecture/sil.sqlite``). The remaining kinds (``gates``, ``drift``,
``test_results``, ``learning``) are wired as stubs that emit
``SLICE.SUPPLEMENTARY_NOT_AVAILABLE`` warnings; their real backing stores
land in Tasks 15-17 (ams-side journals) and the arch-agent learning
store.

All fragments are frozen dataclasses. All loaders are pure and
side-effect-free (read-only SQLite in the sil case).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "SILEvent",
    "SILFragment",
    "GatesFragment",
    "DriftFragment",
    "TestResultsFragment",
    "LearningFragment",
    "load_sil",
    "load_gates",
    "load_drift",
    "load_test_results",
    "load_learning",
]


# ---------------------------------------------------------------------------
# Fragment types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SILEvent:
    """A single row from the ``sil_events`` table."""

    component_id: str
    ts: str
    kind: str
    outcome: str
    duration_ms: float
    ref: str = ""


@dataclass(frozen=True)
class SILFragment:
    """Bounded view over SI&L telemetry.

    ``summary`` is a per-component roll-up ``{component_id: {invocations,
    failures, avg_duration_ms}}`` computed over the filtered events.
    """

    events: tuple[SILEvent, ...] = ()
    summary: dict[str, dict[str, float]] = field(default_factory=dict)


@dataclass(frozen=True)
class GatesFragment:
    """Stub — real backing journal lands in Phase 2 Task 15."""

    events: tuple[dict, ...] = ()


@dataclass(frozen=True)
class DriftFragment:
    """Stub — real backing journal lands in Phase 2 Task 16."""

    events: tuple[dict, ...] = ()


@dataclass(frozen=True)
class TestResultsFragment:
    """Stub — real backing journal lands in Phase 2 Task 17."""

    events: tuple[dict, ...] = ()


@dataclass(frozen=True)
class LearningFragment:
    """Stub — real reader lands when the arch-agent learning store ships."""

    events: tuple[dict, ...] = ()


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _resolve_sil_db(pkg_root: Path, override: str | None) -> Path:
    if override:
        return (pkg_root / override).resolve()
    return pkg_root / ".architecture" / "sil.sqlite"


def load_sil(
    pkg_root: Path,
    *,
    path: str | None = None,
    filter: dict[str, Any] | None = None,
) -> SILFragment | None:
    """Load a bounded SI&L fragment from ``.architecture/sil.sqlite``.

    ``filter`` accepts:

    * ``component_id: str`` — restrict to a single component.
    * ``component_ids: list[str]`` — restrict to a set of components.
    * ``since: str`` — ISO-8601 lower bound on ``ts``.
    * ``until: str`` — ISO-8601 upper bound on ``ts``.
    * ``limit: int`` — cap on number of events returned (default 1000).

    Returns ``None`` when the SQLite file is missing / unreadable or when
    the ``sil_events`` table is absent (SI&L not yet initialized).
    """
    db = _resolve_sil_db(pkg_root, path)
    if not db.is_file():
        return None

    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except sqlite3.DatabaseError:
        return None

    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='sil_events'"
        ).fetchone()
        if row is None:
            return None

        clauses: list[str] = []
        params: list[Any] = []
        f = filter or {}

        cid = f.get("component_id")
        cids = f.get("component_ids")
        if cid and cids:
            raise ValueError(
                "supplementary sil filter: pass component_id OR component_ids, not both"
            )
        if cid:
            clauses.append("component_id = ?")
            params.append(cid)
        elif cids:
            if not isinstance(cids, (list, tuple)) or not cids:
                raise ValueError("component_ids must be a non-empty list")
            placeholders = ",".join("?" for _ in cids)
            clauses.append(f"component_id IN ({placeholders})")
            params.extend(cids)

        since = f.get("since")
        if since:
            clauses.append("ts >= ?")
            params.append(since)

        until = f.get("until")
        if until:
            clauses.append("ts < ?")
            params.append(until)

        limit = int(f.get("limit", 1000))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = (
            "SELECT component_id, ts, kind, outcome, duration_ms, ref "
            f"FROM sil_events {where} "
            "ORDER BY component_id ASC, ts ASC LIMIT ?"
        )
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    events = tuple(
        SILEvent(
            component_id=r["component_id"],
            ts=r["ts"],
            kind=r["kind"] or "",
            outcome=r["outcome"] or "",
            duration_ms=float(r["duration_ms"] or 0.0),
            ref=r["ref"] or "",
        )
        for r in rows
    )

    summary: dict[str, dict[str, float]] = {}
    for ev in events:
        cell = summary.setdefault(
            ev.component_id,
            {"invocations": 0.0, "failures": 0.0, "avg_duration_ms": 0.0},
        )
        cell["invocations"] += 1
        if ev.outcome == "error":
            cell["failures"] += 1
        # Running mean.
        n = cell["invocations"]
        cell["avg_duration_ms"] = (
            cell["avg_duration_ms"] * (n - 1) + ev.duration_ms
        ) / n
    for cell in summary.values():
        cell["avg_duration_ms"] = round(cell["avg_duration_ms"], 4)

    return SILFragment(events=events, summary=summary)


def _stub_load(
    pkg_root: Path,
    *,
    path: str | None,
    filter: dict[str, Any] | None,
    kind: str,
) -> None:
    """Placeholder for kinds whose backing store isn't wired yet."""
    _ = (pkg_root, path, filter, kind)  # intentionally unused
    return None


def load_gates(pkg_root, *, path=None, filter=None):
    return _stub_load(pkg_root, path=path, filter=filter, kind="gates")


def load_drift(pkg_root, *, path=None, filter=None):
    return _stub_load(pkg_root, path=path, filter=filter, kind="drift")


def load_test_results(pkg_root, *, path=None, filter=None):
    return _stub_load(pkg_root, path=path, filter=filter, kind="test_results")


def load_learning(pkg_root, *, path=None, filter=None):
    return _stub_load(pkg_root, path=path, filter=filter, kind="learning")
