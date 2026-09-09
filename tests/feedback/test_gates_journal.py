"""Tests for :mod:`architecture_model.feedback.gates` (Phase 2 Task 15)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from architecture_model.feedback.gates import GateEvent, append


def _read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_append_creates_journal_and_dir(tmp_path):
    ev = GateEvent(gate_id="g1", outcome="pass", timestamp="2026-01-01T00:00:00+00:00")
    append(tmp_path, ev)
    journal = tmp_path / ".architecture" / "gates.jsonl"
    assert journal.exists()
    rows = _read_lines(journal)
    assert rows == [
        {"timestamp": "2026-01-01T00:00:00+00:00", "gate_id": "g1",
         "outcome": "pass", "findings": []}
    ]


def test_append_two_events_preserves_order(tmp_path):
    a = GateEvent(gate_id="g1", outcome="pass", timestamp="t0")
    b = GateEvent(gate_id="g2", outcome="fail", timestamp="t1",
                  findings=("missing", "orphan"))
    append(tmp_path, a)
    append(tmp_path, b)
    rows = _read_lines(tmp_path / ".architecture" / "gates.jsonl")
    assert len(rows) == 2
    assert rows[0]["gate_id"] == "g1"
    assert rows[1]["gate_id"] == "g2"
    assert rows[1]["findings"] == ["missing", "orphan"]


def test_never_truncates_on_reappend(tmp_path):
    """Third append must not clobber earlier lines."""
    for i in range(3):
        append(tmp_path, GateEvent(gate_id=f"g{i}", outcome="pass", timestamp=f"t{i}"))
    rows = _read_lines(tmp_path / ".architecture" / "gates.jsonl")
    assert [r["gate_id"] for r in rows] == ["g0", "g1", "g2"]


def test_model_revision_omitted_when_none(tmp_path):
    append(tmp_path, GateEvent(gate_id="g1", outcome="pass", timestamp="t0"))
    rows = _read_lines(tmp_path / ".architecture" / "gates.jsonl")
    assert "model_revision" not in rows[0]


def test_model_revision_serialized_when_set(tmp_path):
    append(
        tmp_path,
        GateEvent(
            gate_id="g1",
            outcome="pass",
            timestamp="t0",
            model_revision="0000042",
        ),
    )
    rows = _read_lines(tmp_path / ".architecture" / "gates.jsonl")
    assert rows[0]["model_revision"] == "0000042"


def test_deterministic_now_pin(tmp_path, monkeypatch):
    monkeypatch.setenv("AMS_DETERMINISTIC_NOW", "2026-06-06T12:34:56+00:00")
    ev = GateEvent(gate_id="g1", outcome="pass")  # no explicit timestamp
    append(tmp_path, ev)
    rows = _read_lines(tmp_path / ".architecture" / "gates.jsonl")
    assert rows[0]["timestamp"] == "2026-06-06T12:34:56+00:00"


def test_findings_order_preserved(tmp_path):
    ev = GateEvent(
        gate_id="g1", outcome="warn", timestamp="t0",
        findings=("z-item", "a-item", "m-item"),
    )
    append(tmp_path, ev)
    rows = _read_lines(tmp_path / ".architecture" / "gates.jsonl")
    assert rows[0]["findings"] == ["z-item", "a-item", "m-item"]


def test_gate_event_frozen():
    ev = GateEvent(gate_id="g1", outcome="pass")
    with pytest.raises((AttributeError, Exception)):
        ev.gate_id = "changed"  # type: ignore[misc]


def test_append_survives_preexisting_architecture_dir(tmp_path):
    (tmp_path / ".architecture").mkdir()
    (tmp_path / ".architecture" / "other.txt").write_text("keep me")
    append(tmp_path, GateEvent(gate_id="g1", outcome="pass", timestamp="t0"))
    assert (tmp_path / ".architecture" / "other.txt").read_text() == "keep me"
    rows = _read_lines(tmp_path / ".architecture" / "gates.jsonl")
    assert len(rows) == 1


def test_outcomes_all_three_valid(tmp_path):
    for oc in ("pass", "fail", "warn"):
        append(tmp_path, GateEvent(gate_id=f"g-{oc}", outcome=oc, timestamp=f"t-{oc}"))
    rows = _read_lines(tmp_path / ".architecture" / "gates.jsonl")
    assert {r["outcome"] for r in rows} == {"pass", "fail", "warn"}


def test_unicode_findings_survive_roundtrip(tmp_path):
    ev = GateEvent(
        gate_id="g1", outcome="warn", timestamp="t0",
        findings=("π-issue", "→ dangling ref"),
    )
    append(tmp_path, ev)
    rows = _read_lines(tmp_path / ".architecture" / "gates.jsonl")
    assert rows[0]["findings"] == ["π-issue", "→ dangling ref"]
