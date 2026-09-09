"""Tests for :mod:`architecture_model.feedback.drift` (Phase 2 Task 16)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from architecture_model.feedback.drift import DriftFlag, DriftSnapshot, append


def _read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_append_creates_journal_and_dir(tmp_path):
    snap = DriftSnapshot(
        model_revision="0000001",
        flags=(DriftFlag(entity_id="COMP-1", kind="orphan", detail="no realizer"),),
        timestamp="2026-01-01T00:00:00+00:00",
    )
    append(tmp_path, snap)
    journal = tmp_path / ".architecture" / "drift.jsonl"
    assert journal.exists()
    rows = _read_lines(journal)
    assert rows == [{
        "timestamp": "2026-01-01T00:00:00+00:00",
        "model_revision": "0000001",
        "flags": [{"entity_id": "COMP-1", "kind": "orphan", "detail": "no realizer"}],
    }]


def test_append_two_snapshots_preserves_order(tmp_path):
    a = DriftSnapshot(model_revision="0000001", timestamp="t0")
    b = DriftSnapshot(model_revision="0000002", timestamp="t1",
                      flags=(DriftFlag(entity_id="CAP-F1", kind="unrealized_capability", detail="no impl"),))
    append(tmp_path, a)
    append(tmp_path, b)
    rows = _read_lines(tmp_path / ".architecture" / "drift.jsonl")
    assert [r["model_revision"] for r in rows] == ["0000001", "0000002"]
    assert rows[1]["flags"][0]["kind"] == "unrealized_capability"


def test_never_truncates_on_reappend(tmp_path):
    for i in range(3):
        append(tmp_path, DriftSnapshot(model_revision=f"000000{i}", timestamp=f"t{i}"))
    rows = _read_lines(tmp_path / ".architecture" / "drift.jsonl")
    assert [r["model_revision"] for r in rows] == ["0000000", "0000001", "0000002"]


def test_empty_flags_records_clean_snapshot(tmp_path):
    """An empty flags tuple is a valid 'no drift observed' record."""
    append(tmp_path, DriftSnapshot(model_revision="0000001", timestamp="t0"))
    rows = _read_lines(tmp_path / ".architecture" / "drift.jsonl")
    assert rows[0]["flags"] == []


def test_flag_order_preserved(tmp_path):
    flags = (
        DriftFlag(entity_id="COMP-1", kind="orphan", detail="a"),
        DriftFlag(entity_id="COMP-2", kind="missing_impl", detail="b"),
        DriftFlag(entity_id="COMP-3", kind="broken_ref", detail="c"),
    )
    append(tmp_path, DriftSnapshot(model_revision="0000001", timestamp="t0", flags=flags))
    rows = _read_lines(tmp_path / ".architecture" / "drift.jsonl")
    assert [f["entity_id"] for f in rows[0]["flags"]] == ["COMP-1", "COMP-2", "COMP-3"]


def test_deterministic_now_pin(tmp_path, monkeypatch):
    monkeypatch.setenv("AMS_DETERMINISTIC_NOW", "2026-06-06T12:34:56+00:00")
    append(tmp_path, DriftSnapshot(model_revision="0000001"))  # no explicit ts
    rows = _read_lines(tmp_path / ".architecture" / "drift.jsonl")
    assert rows[0]["timestamp"] == "2026-06-06T12:34:56+00:00"


def test_snapshot_frozen():
    snap = DriftSnapshot(model_revision="0000001")
    with pytest.raises((AttributeError, Exception)):
        snap.model_revision = "changed"  # type: ignore[misc]


def test_flag_frozen():
    f = DriftFlag(entity_id="COMP-1", kind="orphan", detail="x")
    with pytest.raises((AttributeError, Exception)):
        f.detail = "changed"  # type: ignore[misc]


def test_all_four_kinds(tmp_path):
    flags = tuple(
        DriftFlag(entity_id=f"E-{k}", kind=k, detail=f"d-{k}")
        for k in ("orphan", "missing_impl", "unrealized_capability", "broken_ref")
    )
    append(tmp_path, DriftSnapshot(model_revision="0000001", timestamp="t0", flags=flags))
    rows = _read_lines(tmp_path / ".architecture" / "drift.jsonl")
    assert {f["kind"] for f in rows[0]["flags"]} == {
        "orphan", "missing_impl", "unrealized_capability", "broken_ref"
    }


def test_survives_preexisting_architecture_dir(tmp_path):
    (tmp_path / ".architecture").mkdir()
    (tmp_path / ".architecture" / "gates.jsonl").write_text('{"keep": "me"}\n')
    append(tmp_path, DriftSnapshot(model_revision="0000001", timestamp="t0"))
    # gates.jsonl untouched.
    assert (tmp_path / ".architecture" / "gates.jsonl").read_text() == '{"keep": "me"}\n'
    assert (tmp_path / ".architecture" / "drift.jsonl").exists()
