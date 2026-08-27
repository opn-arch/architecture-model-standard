"""Tests for gap_report — Markdown report generator."""
from __future__ import annotations
import pytest


def test_render_report_has_header():
    from architecture_model.pipeline.gap_report import render_gap_report
    from architecture_model.pipeline.gap_analysis import (
        GapAnalysisResult, StageGap,
    )
    result = GapAnalysisResult(
        repo_path="/tmp/test",
        stage_gaps=[
            StageGap(stage="infer", deterministic={}, llm_alternative={},
                     added=[], removed=[], renamed=[], quality_delta=0.0)
        ],
        naming_chains=[],
        propagation_traces=[],
        summary={"stages_analyzed": 1, "total_gaps": 0},
    )
    md = render_gap_report(result)
    assert "# Gap Analysis Report" in md
    assert "/tmp/test" in md


def test_render_report_includes_naming_chains():
    from architecture_model.pipeline.gap_report import render_gap_report
    from architecture_model.pipeline.gap_analysis import (
        GapAnalysisResult, NamingChain,
    )
    chain = NamingChain(
        source="main.py",
        stages={"infer": "Main", "allocate": "Main"},
        llm_stages={"infer": "Env Loading", "allocate": "DotenvLoader"},
        is_generic=True,
    )
    result = GapAnalysisResult(
        repo_path="/tmp/test", stage_gaps=[], naming_chains=[chain],
        propagation_traces=[], summary={},
    )
    md = render_gap_report(result)
    assert "main.py" in md
    assert "Main" in md
    assert "Env Loading" in md


def test_render_report_includes_propagation():
    from architecture_model.pipeline.gap_report import render_gap_report
    from architecture_model.pipeline.gap_analysis import (
        GapAnalysisResult, PropagationTrace,
    )
    trace = PropagationTrace(
        origin_stage="infer",
        origin_entity="CAP-1 (Main)",
        origin_issue="generic name",
        affected=[{"stage": "allocate", "entity": "COMP-1", "effect": "inherited generic name"}],
    )
    result = GapAnalysisResult(
        repo_path="/tmp/test", stage_gaps=[], naming_chains=[],
        propagation_traces=[trace], summary={},
    )
    md = render_gap_report(result)
    assert "infer" in md
    assert "generic name" in md
    assert "allocate" in md


def test_render_report_includes_renamed_table():
    from architecture_model.pipeline.gap_report import render_gap_report
    from architecture_model.pipeline.gap_analysis import (
        GapAnalysisResult, StageGap,
    )
    gap = StageGap(
        stage="infer", deterministic={}, llm_alternative={},
        added=[], removed=[],
        renamed=[{"det": "Main", "llm": "Environment Loading", "similarity": 0.3}],
        quality_delta=15.0,
    )
    result = GapAnalysisResult(
        repo_path="/tmp/test", stage_gaps=[gap], naming_chains=[],
        propagation_traces=[], summary={"stages_analyzed": 1, "total_gaps": 1},
    )
    md = render_gap_report(result)
    assert "Main" in md
    assert "Environment Loading" in md


def test_render_report_recommendations():
    from architecture_model.pipeline.gap_report import render_gap_report
    from architecture_model.pipeline.gap_analysis import (
        GapAnalysisResult, NamingChain,
    )
    chains = [NamingChain(source="main.py", stages={"infer": "Main"}, llm_stages={"infer": "Env Loading"}, is_generic=True)]
    result = GapAnalysisResult(
        repo_path="/tmp/test", stage_gaps=[], naming_chains=chains,
        propagation_traces=[], summary={},
    )
    md = render_gap_report(result)
    assert "Recommendation" in md or "recommendation" in md
