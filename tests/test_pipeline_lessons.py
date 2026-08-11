"""Tests for pipeline lessons generator."""

from architecture_model.pipeline.lessons import LessonEntry, generate_lessons
from architecture_model.pipeline.protocol import Diagnostic, LLMCallRecord, Uncertainty


class TestFromDiagnostics:
    def test_aggregation(self):
        diags = [
            Diagnostic(severity="warning", code="LOW_COVERAGE", message="File coverage below threshold"),
            Diagnostic(severity="warning", code="LOW_COVERAGE", message="File coverage below threshold"),
            Diagnostic(severity="warning", code="LOW_COVERAGE", message="File coverage below threshold"),
            Diagnostic(severity="error", code="MISSING_REL", message="Missing relationship"),
        ]
        lessons = LessonEntry.from_diagnostics("allocate", diags)
        assert len(lessons) == 2
        low_cov = [l for l in lessons if "3 instances" in l.summary][0]
        assert low_cov.count == 3
        assert low_cov.severity == "warning"
        missing = [l for l in lessons if "Missing" in l.summary][0]
        assert missing.count == 1

    def test_single_diagnostic(self):
        diags = [Diagnostic(severity="info", code="X", message="Something")]
        lessons = LessonEntry.from_diagnostics("observe", diags)
        assert len(lessons) == 1
        assert lessons[0].summary == "Something"
        assert "instances" not in lessons[0].summary


class TestFromUncertainties:
    def test_aggregation(self):
        uncs = [
            Uncertainty(category="naming", description="unclear name A"),
            Uncertainty(category="naming", description="unclear name B"),
            Uncertainty(category="scope", description="ambiguous scope"),
        ]
        lessons = LessonEntry.from_uncertainties("infer", uncs)
        assert len(lessons) == 2
        naming = [l for l in lessons if l.count == 2][0]
        assert "2 instances" in naming.summary
        scope = [l for l in lessons if l.count == 1][0]
        assert scope.summary == "ambiguous scope"


class TestFromLLMCalls:
    def test_enrichment_pattern(self):
        calls = [
            LLMCallRecord(stage="infer", purpose="capability_naming", items_produced=5),
            LLMCallRecord(stage="infer", purpose="capability_naming", items_produced=3),
        ]
        lessons = LessonEntry.from_llm_calls("infer", calls)
        enrichment = [l for l in lessons if "enrichment" in l.summary][0]
        assert "8 items" in enrichment.summary

    def test_cache_savings(self):
        calls = [
            LLMCallRecord(stage="infer", purpose="x", cached=True, total_tokens=1000),
            LLMCallRecord(stage="infer", purpose="x", cached=True, total_tokens=500),
        ]
        lessons = LessonEntry.from_llm_calls("infer", calls)
        cache_lesson = [l for l in lessons if "cache" in l.summary][0]
        assert "1,500 tokens" in cache_lesson.summary
        assert "2 cache hits" in cache_lesson.summary

    def test_no_calls(self):
        assert LessonEntry.from_llm_calls("infer", []) == []


class TestGenerateLessons:
    def test_grouped_by_stage(self):
        entries = [
            LessonEntry(stage="infer", summary="Lesson A"),
            LessonEntry(stage="infer", summary="Lesson B"),
            LessonEntry(stage="specify", summary="Lesson C"),
        ]
        md = generate_lessons(entries, "MySystem")
        assert "# Lessons: MySystem" in md
        assert "## Stage: infer" in md
        assert "## Stage: specify" in md
        assert "- Lesson A" in md
        assert "- Lesson C" in md

    def test_empty(self):
        md = generate_lessons([], "Empty")
        assert "No lessons to report" in md
