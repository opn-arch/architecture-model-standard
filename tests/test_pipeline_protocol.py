"""Tests for pipeline protocol types."""

from pathlib import Path

import pytest

from architecture_model.pipeline.protocol import (
    Claim,
    Diagnostic,
    Evidence,
    PipelineContext,
    QualityMetrics,
    SOURCE_WEIGHTS,
    StageResult,
    Uncertainty,
)


class TestEvidence:
    def test_valid_creation(self):
        e = Evidence(source="ast", confidence=0.9, raw="found class Foo")
        assert e.source == "ast"
        assert e.confidence == 0.9
        assert e.raw == "found class Foo"
        assert e.location == ""

    def test_with_location(self):
        e = Evidence(source="ast", confidence=1.0, raw="x", location="foo.py:10")
        assert e.location == "foo.py:10"

    def test_confidence_too_high(self):
        with pytest.raises(ValueError):
            Evidence(source="ast", confidence=1.1, raw="x")

    def test_confidence_too_low(self):
        with pytest.raises(ValueError):
            Evidence(source="ast", confidence=-0.1, raw="x")

    def test_confidence_boundary_zero(self):
        e = Evidence(source="ast", confidence=0.0, raw="x")
        assert e.confidence == 0.0

    def test_confidence_boundary_one(self):
        e = Evidence(source="ast", confidence=1.0, raw="x")
        assert e.confidence == 1.0


class TestClaim:
    def test_confidence_empty_evidence(self):
        c = Claim(value="hello", evidence=[])
        assert c.confidence == 0.0

    def test_confidence_single_ast(self):
        e = Evidence(source="ast", confidence=0.8, raw="x")
        c = Claim(value="x", evidence=[e])
        # 0.8 * 1.0 / 1 = 0.8
        assert c.confidence == pytest.approx(0.8)

    def test_confidence_weighted(self):
        e1 = Evidence(source="ast", confidence=1.0, raw="x")
        e2 = Evidence(source="llm_analysis", confidence=0.5, raw="y")
        c = Claim(value="z", evidence=[e1, e2])
        # (1.0*1.0 + 0.5*0.6) / 2 = 1.3/2 = 0.65
        assert c.confidence == pytest.approx(0.65)

    def test_confidence_capped_at_one(self):
        # Even with high values, should cap at 1.0
        e = Evidence(source="ast", confidence=1.0, raw="x")
        c = Claim(value="x", evidence=[e])
        assert c.confidence <= 1.0

    def test_uncertain_flag(self):
        c = Claim(value="maybe", uncertain=True)
        assert c.uncertain is True


class TestUncertainty:
    def test_creation(self):
        u = Uncertainty(
            category="naming",
            description="Can't determine component name",
            context={"file": "foo.py"},
        )
        assert u.category == "naming"
        assert u.suggested_fallback == "llm_analysis"
        assert u.priority == "enriching"

    def test_custom_fallback(self):
        u = Uncertainty(
            category="x", description="y", suggested_fallback="ask_user", priority="blocking"
        )
        assert u.suggested_fallback == "ask_user"
        assert u.priority == "blocking"


class TestQualityMetrics:
    def test_passes_all_above(self):
        qm = QualityMetrics(
            score=85.0,
            sub_scores={"coverage": 0.9, "accuracy": 0.8},
            thresholds={"coverage": 0.7, "accuracy": 0.7},
        )
        assert qm.passes is True

    def test_fails_one_below(self):
        qm = QualityMetrics(
            score=50.0,
            sub_scores={"coverage": 0.5, "accuracy": 0.8},
            thresholds={"coverage": 0.7, "accuracy": 0.7},
        )
        assert qm.passes is False

    def test_passes_empty_thresholds(self):
        qm = QualityMetrics(score=100.0)
        assert qm.passes is True

    def test_passes_exact_threshold(self):
        qm = QualityMetrics(
            score=70.0,
            sub_scores={"x": 0.7},
            thresholds={"x": 0.7},
        )
        assert qm.passes is True


class TestStageResult:
    def test_creation(self):
        qm = QualityMetrics(score=90.0)
        sr = StageResult(
            output={"components": []},
            quality=qm,
            diagnostics=[Diagnostic(severity="info", code="I001", message="ok", context={})],
            uncertainties=[],
            input_hash="abc123",
            duration_ms=150,
            version="2.0",
        )
        assert sr.output == {"components": []}
        assert sr.quality.score == 90.0
        assert len(sr.diagnostics) == 1
        assert sr.input_hash == "abc123"
        assert sr.duration_ms == 150
        assert sr.version == "2.0"


class TestPipelineContext:
    def test_has_and_get(self):
        qm = QualityMetrics(score=80.0)
        sr = StageResult(output="data", quality=qm)
        ctx = PipelineContext(
            repo_path=Path("/tmp/repo"),
            output_dir=Path("/tmp/out"),
            cache={"scan": sr},
        )
        assert ctx.has("scan") is True
        assert ctx.has("missing") is False
        assert ctx.get("scan") is sr
        assert ctx.get("missing") is None

    def test_domain_default(self):
        ctx = PipelineContext(repo_path=Path("/tmp"), output_dir=Path("/tmp"))
        assert ctx.domain == "software"

    def test_domain_custom(self):
        ctx = PipelineContext(repo_path=Path("/tmp"), output_dir=Path("/tmp"), domain="electrical")
        assert ctx.domain == "electrical"


class TestSourceWeights:
    def test_ast_weight(self):
        assert SOURCE_WEIGHTS["ast"] == 1.0

    def test_llm_analysis_weight(self):
        assert SOURCE_WEIGHTS["llm_analysis"] == 0.6

    def test_search_result_lowest(self):
        assert SOURCE_WEIGHTS["search_result"] == 0.5
