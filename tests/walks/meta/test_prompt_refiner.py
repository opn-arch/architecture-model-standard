"""Tests for :mod:`architecture_model.walks.meta.prompt_refiner` (Part 15)."""
from __future__ import annotations

from pathlib import Path

import yaml

from architecture_model.feedback.llm_calls import append
from architecture_model.pipeline.protocol import LLMCallRecord
from architecture_model.walks.meta.prompt_refiner import (
    HIGH_COST_MULTIPLE,
    PromptTemplateCard,
    RefinerReport,
    refine_prompts,
)


def _mk(**overrides) -> LLMCallRecord:
    base = dict(
        stage="observe",
        purpose="test",
        timestamp="2026-01-01T00:00:00+00:00",
        prompt_template="fill_promise",
        total_tokens=100,
        model="mock",
        output_used=True,
    )
    base.update(overrides)
    return LLMCallRecord(**base)


def _write_endpoints(root: Path, templates: list[tuple[str, str]]) -> None:
    """Write ``endpoints.yaml`` with (id, prompt_template) pairs."""
    payload = {
        "endpoints": [
            {"id": eid, "prompt_template": tmpl}
            for eid, tmpl in templates
        ]
    }
    dst = root / ".architecture" / "llm" / "endpoints.yaml"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(yaml.safe_dump(payload))


def test_no_journal_no_endpoints_returns_empty(tmp_path):
    report = refine_prompts(tmp_path)
    assert isinstance(report, RefinerReport)
    assert report.cards == ()
    assert report.counts == {}


def test_stable_verdict(tmp_path):
    for _ in range(5):
        append(tmp_path, _mk(prompt_template="fill_promise", total_tokens=100))
    report = refine_prompts(tmp_path)
    assert len(report.cards) == 1
    c = report.cards[0]
    assert c.template_id == "fill_promise"
    assert c.verdict == "stable"
    assert c.details["sample_size"] == 5


def test_high_failure_verdict(tmp_path):
    # 5 calls, 3 failures (60% >= 30%)
    for i in range(5):
        append(
            tmp_path,
            _mk(prompt_template="fill_promise", output_used=(i >= 3)),
        )
    report = refine_prompts(tmp_path)
    assert len(report.cards) == 1
    assert report.cards[0].verdict == "high-failure"
    assert report.cards[0].details["failure_rate"] >= 0.30


def test_high_failure_needs_min_calls(tmp_path):
    # Only 2 calls even at 100% failure → stable (below sample threshold).
    for _ in range(2):
        append(tmp_path, _mk(prompt_template="rare", output_used=False))
    report = refine_prompts(tmp_path)
    assert report.cards[0].verdict == "stable"


def test_high_cost_verdict(tmp_path):
    # Baseline: 6 cheap calls at 100 tokens.
    for _ in range(6):
        append(tmp_path, _mk(prompt_template="cheap", total_tokens=100))
    # Expensive: 3 calls at 500 tokens each (median 500 vs overall 100 → 5x).
    for _ in range(3):
        append(tmp_path, _mk(prompt_template="expensive", total_tokens=500))
    report = refine_prompts(tmp_path)
    by_id = {c.template_id: c for c in report.cards}
    assert by_id["cheap"].verdict == "stable"
    assert by_id["expensive"].verdict == "high-cost"
    assert by_id["expensive"].details["median_tokens"] >= (
        HIGH_COST_MULTIPLE * 100
    )


def test_unused_verdict(tmp_path):
    _write_endpoints(
        tmp_path,
        [("architecture-model-standard:src/x.py:12", "declared_but_absent")],
    )
    report = refine_prompts(tmp_path)
    assert len(report.cards) == 1
    c = report.cards[0]
    assert c.template_id == "declared_but_absent"
    assert c.verdict == "unused"
    assert c.details["sample_size"] == 0
    assert (
        c.details["endpoint_id"]
        == "architecture-model-standard:src/x.py:12"
    )


def test_declared_and_present_gets_endpoint_id(tmp_path):
    _write_endpoints(tmp_path, [("ep-1", "fill_promise")])
    for _ in range(3):
        append(tmp_path, _mk(prompt_template="fill_promise"))
    report = refine_prompts(tmp_path)
    c = report.cards[0]
    assert c.template_id == "fill_promise"
    assert c.verdict == "stable"
    assert c.details["endpoint_id"] == "ep-1"


def test_counts_aggregate(tmp_path):
    # stable + high-failure + unused declared.
    for _ in range(4):
        append(tmp_path, _mk(prompt_template="ok", output_used=True))
    for i in range(5):
        append(
            tmp_path,
            _mk(prompt_template="broken", output_used=(i == 0)),
        )
    _write_endpoints(tmp_path, [("ep-x", "missing_template")])
    report = refine_prompts(tmp_path)
    assert report.counts.get("stable") == 1
    assert report.counts.get("high-failure") == 1
    assert report.counts.get("unused") == 1


def test_docstring_realizes_marker():
    """Meta-coverage walk discovers this via the RST marker."""
    import architecture_model.walks.meta.prompt_refiner as mod

    assert "Realizes ``CAP-WK.prompt-refinement``" in (mod.__doc__ or "")
