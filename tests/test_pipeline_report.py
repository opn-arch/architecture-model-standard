"""Tests for pipeline report generator."""

from architecture_model.pipeline.protocol import (
    Diagnostic,
    LLMCallRecord,
    QualityMetrics,
    StageResult,
    Uncertainty,
)
from architecture_model.pipeline.report import (
    StageReport,
    _extract_findings,
    generate_pipeline_report,
)
from architecture_model.pipeline.emit_types import EmitResult


def _make_result(score=90.0, duration_ms=100, output=None, diagnostics=None, uncertainties=None):
    return StageResult(
        output=output,
        quality=QualityMetrics(score=score),
        duration_ms=duration_ms,
        diagnostics=diagnostics or [],
        uncertainties=uncertainties or [],
    )


def _make_call(**kwargs):
    defaults = dict(stage="infer", purpose="capability_naming", duration_ms=2300)
    defaults.update(kwargs)
    return LLMCallRecord(**defaults)


class TestStageReportMarkdown:
    def test_without_llm_calls(self):
        sr = StageReport(
            stage_name="observe",
            duration_ms=150,
            score=95.0,
            deterministic_findings=["Discovered 10 modules"],
        )
        md = sr.to_markdown()
        assert "## Stage: observe" in md
        assert "**Score:** 95.0" in md
        assert "Discovered 10 modules" in md
        assert "*(none)*" in md  # LLM calls section

    def test_with_llm_calls(self):
        call = _make_call(
            model="claude-sonnet-4-20250514",
            files_sent=["src/core/parser.py"],
            slices_sent=["COMP-1"],
            prompt_tokens=1200,
            context_tokens=800,
            completion_tokens=350,
            total_tokens=1550,
            items_produced=5,
            confidence=0.91,
        )
        sr = StageReport(
            stage_name="infer",
            duration_ms=3500,
            score=88.0,
            llm_calls=[call],
        )
        md = sr.to_markdown()
        assert "### LLM Calls (1)" in md
        assert "claude-sonnet-4-20250514" in md
        assert "`src/core/parser.py`" in md
        assert "COMP-1" in md
        assert "1,200 prompt" in md
        assert "5 items produced" in md

    def test_diagnostics_rendered(self):
        sr = StageReport(
            stage_name="validate",
            duration_ms=50,
            score=70.0,
            diagnostics=[Diagnostic(severity="warning", code="W1", message="low coverage")],
        )
        md = sr.to_markdown()
        assert "⚠️ W1: low coverage" in md

    def test_uncertainties_rendered(self):
        sr = StageReport(
            stage_name="infer",
            duration_ms=100,
            score=80.0,
            uncertainties=[Uncertainty(category="naming", description="unclear name")],
        )
        md = sr.to_markdown()
        assert "### Uncertainties" in md
        assert "naming: unclear name" in md


class TestGeneratePipelineReport:
    def test_distinguishes_extraction_and_final_model_scores(self):
        results = {
            "validate": _make_result(score=95),
            "emit": StageResult(
                output=EmitResult(
                    extraction_score=95,
                    final_model_score=87,
                    final_model_path="/repo/.architecture-model.yaml",
                    promoted=True,
                ),
                quality=QualityMetrics(score=87),
            ),
        }

        report = generate_pipeline_report(results)

        assert "**Extraction Score:** 95" in report
        assert "**Final Model Score:** 87" in report
        assert "**Final Model:** `/repo/.architecture-model.yaml`" in report
        assert "**Promoted:** yes" in report
    def test_deterministic_run(self):
        results = {"observe": _make_result(95.0, 150)}
        report = generate_pipeline_report(results, "TestSystem")
        assert "# Pipeline Report: TestSystem" in report
        assert "deterministic pipeline run" in report
        assert "**Stages:** 1" in report

    def test_with_llm_calls(self):
        results = {
            "observe": _make_result(95.0, 150),
            "infer": _make_result(88.0, 3500),
        }
        calls = [
            _make_call(
                model="claude-sonnet-4-20250514",
                prompt_tokens=1200,
                completion_tokens=350,
                total_tokens=1550,
                files_sent=["src/parser.py"],
            ),
            _make_call(
                stage="infer",
                purpose="uncertainty_resolution",
                model="claude-sonnet-4-20250514",
                prompt_tokens=500,
                completion_tokens=200,
                total_tokens=700,
                cached=True,
            ),
        ]
        report = generate_pipeline_report(results, "MySystem", calls)
        assert "## LLM Summary" in report
        assert "Total Calls | 2" in report
        assert "2,250" in report  # total tokens
        assert "Cache Hits | 1/2" in report
        assert "## Stage Scores" in report
        assert "| infer | 88.0 | 3500ms | 2 |" in report
        assert "| observe | 95.0 | 150ms | 0 |" in report

    def test_aggregate_tokens(self):
        calls = [
            _make_call(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            _make_call(prompt_tokens=200, completion_tokens=100, total_tokens=300),
        ]
        report = generate_pipeline_report(
            {"infer": _make_result()}, llm_calls=calls
        )
        assert "450" in report  # total tokens
        assert "prompt: 300" in report


class TestExtractFindings:
    def test_observe_stage(self):
        from architecture_model.pipeline.observe_types import (
            ImportEdge,
            Inventory,
            ModuleRecord,
        )
        from pathlib import Path

        inv = Inventory(
            modules=[ModuleRecord(path=Path("a.py")), ModuleRecord(path=Path("b.py"))],
            edges=[ImportEdge(source=Path("a.py"), target=Path("b.py"))],
        )
        result = _make_result(output=inv)
        findings = _extract_findings("observe", result)
        assert any("2 modules" in f for f in findings)
        assert any("1 import edges" in f for f in findings)

    def test_unknown_stage(self):
        result = _make_result(output="something")
        findings = _extract_findings("nonexistent", result)
        assert findings == []

    def test_none_output(self):
        result = _make_result(output=None)
        findings = _extract_findings("observe", result)
        assert findings == []

    def test_allocate_full_coverage_is_reported_as_100_percent(self):
        from architecture_model.pipeline.allocate_types import AllocationResult

        findings = _extract_findings(
            "allocate", _make_result(output=AllocationResult(file_coverage=100.0))
        )

        assert "File coverage: 100%" in findings
        assert not any("10000%" in finding for finding in findings)
