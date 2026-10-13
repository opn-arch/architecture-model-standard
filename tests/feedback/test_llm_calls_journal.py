"""Tests for :mod:`architecture_model.feedback.llm_calls` (CAP-DF Part 15)."""
from __future__ import annotations

import json
from pathlib import Path

from architecture_model.feedback.llm_calls import append, read
from architecture_model.pipeline.protocol import LLMCallRecord


def _mk(**overrides) -> LLMCallRecord:
    base = dict(
        stage="observe",
        purpose="test",
        timestamp="2026-01-01T00:00:00+00:00",
        prompt_template="fill_promise",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        model="mock",
        output_used=True,
    )
    base.update(overrides)
    return LLMCallRecord(**base)


def test_append_creates_journal_and_dir(tmp_path):
    ok = append(tmp_path, _mk())
    assert ok is True
    journal = tmp_path / ".architecture" / "llm_calls.jsonl"
    assert journal.exists()
    rows = [json.loads(l) for l in journal.read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    assert rows[0]["stage"] == "observe"
    assert rows[0]["prompt_template"] == "fill_promise"
    assert rows[0]["total_tokens"] == 150


def test_round_trip_read(tmp_path):
    append(tmp_path, _mk(purpose="one"))
    append(tmp_path, _mk(purpose="two"))
    rows = read(tmp_path)
    assert len(rows) == 2
    assert [r["purpose"] for r in rows] == ["one", "two"]


def test_endpoint_and_task_class_overlay(tmp_path):
    append(
        tmp_path,
        _mk(),
        endpoint_id="architecture-model-standard:src/x.py:12",
        task_class="authoring",
    )
    rows = read(tmp_path)
    assert rows[0]["endpoint_id"] == "architecture-model-standard:src/x.py:12"
    assert rows[0]["task_class"] == "authoring"


def test_missing_optional_fields_absent(tmp_path):
    """When endpoint_id/task_class are empty they must not appear in JSON."""
    append(tmp_path, _mk())
    rows = read(tmp_path)
    assert "endpoint_id" not in rows[0]
    assert "task_class" not in rows[0]


def test_read_missing_file_is_empty(tmp_path):
    assert read(tmp_path) == []


def test_append_fail_soft_on_unwritable(tmp_path, monkeypatch):
    """A write error must return False, never raise."""

    def _boom(*a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr("os.open", _boom)
    ok = append(tmp_path, _mk())
    assert ok is False


def test_never_truncates_on_reappend(tmp_path):
    for i in range(5):
        append(tmp_path, _mk(purpose=f"p{i}"))
    rows = read(tmp_path)
    assert [r["purpose"] for r in rows] == [f"p{i}" for i in range(5)]


def test_malformed_line_skipped_on_read(tmp_path):
    append(tmp_path, _mk(purpose="good"))
    journal = tmp_path / ".architecture" / "llm_calls.jsonl"
    with journal.open("a") as f:
        f.write("this is not json\n")
    append(tmp_path, _mk(purpose="also-good"))
    rows = read(tmp_path)
    assert [r["purpose"] for r in rows] == ["good", "also-good"]
