"""Tests for :mod:`architecture_model.feedback.test_results` (Phase 2 Task 17)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from architecture_model.feedback.test_results import (
    TestFailure,
    TestResultBatch,
    append,
)


def _read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_append_creates_journal_and_dir(tmp_path):
    batch = TestResultBatch(
        suite="ams-unit",
        total=100, passed=99, failed=1, skipped=0,
        duration_s=12.5,
        failures=(TestFailure(nodeid="pkg.test_x::test_y", message="assert 1 == 2"),),
        timestamp="2026-01-01T00:00:00+00:00",
    )
    append(tmp_path, batch)
    journal = tmp_path / ".architecture" / "test_results.jsonl"
    assert journal.exists()
    rows = _read_lines(journal)
    assert rows[0]["suite"] == "ams-unit"
    assert rows[0]["total"] == 100
    assert rows[0]["failures"][0]["nodeid"] == "pkg.test_x::test_y"


def test_two_appends_preserve_order(tmp_path):
    a = TestResultBatch(suite="s1", total=1, passed=1, failed=0, skipped=0,
                        duration_s=0.1, timestamp="t0")
    b = TestResultBatch(suite="s2", total=2, passed=1, failed=1, skipped=0,
                        duration_s=0.2, timestamp="t1")
    append(tmp_path, a)
    append(tmp_path, b)
    rows = _read_lines(tmp_path / ".architecture" / "test_results.jsonl")
    assert [r["suite"] for r in rows] == ["s1", "s2"]


def test_never_truncates_on_reappend(tmp_path):
    for i in range(3):
        append(tmp_path, TestResultBatch(
            suite=f"s{i}", total=1, passed=1, failed=0, skipped=0,
            duration_s=0.1, timestamp=f"t{i}",
        ))
    rows = _read_lines(tmp_path / ".architecture" / "test_results.jsonl")
    assert [r["suite"] for r in rows] == ["s0", "s1", "s2"]


def test_empty_failures_serialized_as_empty_list(tmp_path):
    append(tmp_path, TestResultBatch(
        suite="s1", total=1, passed=1, failed=0, skipped=0,
        duration_s=0.1, timestamp="t0",
    ))
    rows = _read_lines(tmp_path / ".architecture" / "test_results.jsonl")
    assert rows[0]["failures"] == []


def test_failure_order_preserved(tmp_path):
    failures = tuple(TestFailure(nodeid=f"n{i}", message=f"m{i}") for i in range(3))
    append(tmp_path, TestResultBatch(
        suite="s1", total=3, passed=0, failed=3, skipped=0,
        duration_s=0.5, failures=failures, timestamp="t0",
    ))
    rows = _read_lines(tmp_path / ".architecture" / "test_results.jsonl")
    assert [f["nodeid"] for f in rows[0]["failures"]] == ["n0", "n1", "n2"]


def test_deterministic_now_pin(tmp_path, monkeypatch):
    monkeypatch.setenv("AMS_DETERMINISTIC_NOW", "2026-06-06T12:34:56+00:00")
    append(tmp_path, TestResultBatch(
        suite="s1", total=1, passed=1, failed=0, skipped=0, duration_s=0.1,
    ))
    rows = _read_lines(tmp_path / ".architecture" / "test_results.jsonl")
    assert rows[0]["timestamp"] == "2026-06-06T12:34:56+00:00"


def test_batch_frozen():
    b = TestResultBatch(suite="s", total=1, passed=1, failed=0, skipped=0, duration_s=0.1)
    with pytest.raises((AttributeError, Exception)):
        b.suite = "changed"  # type: ignore[misc]


def test_failure_frozen():
    f = TestFailure(nodeid="n", message="m")
    with pytest.raises((AttributeError, Exception)):
        f.message = "changed"  # type: ignore[misc]


def test_survives_preexisting_sibling_journals(tmp_path):
    (tmp_path / ".architecture").mkdir()
    (tmp_path / ".architecture" / "gates.jsonl").write_text('{"keep": "me"}\n')
    append(tmp_path, TestResultBatch(
        suite="s1", total=1, passed=1, failed=0, skipped=0,
        duration_s=0.1, timestamp="t0",
    ))
    assert (tmp_path / ".architecture" / "gates.jsonl").read_text() == '{"keep": "me"}\n'
