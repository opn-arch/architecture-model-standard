"""Tests for unified quality dashboard."""
from architecture_model.quality.dashboard import quality_report, QualityReport
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Component, Capability,
    Status, FunctionSignature, TestContract,
)


class TestQualityReport:
    def test_returns_report_dataclass(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(
                components=[Component(id="COMP-1", name="Test", status=Status.ACTIVE,
                                      intent="Does testing",
                                      signatures=[FunctionSignature(name="test_fn", params=["a"])])],
                capabilities=[Capability(id="CAP-1", name="Cap", status=Status.ACTIVE,
                                         intent="Test cap", moes=["MOE-1"])],
            ),
            relationships=[],
        )
        report = quality_report(model)
        assert isinstance(report, QualityReport)
        assert 0 <= report.overall_score <= 100
        assert report.validation_score >= 0
        assert isinstance(report.semantic_completeness, dict)
        assert "intent_coverage" in report.semantic_completeness

    def test_semantic_completeness_counts(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(
                components=[
                    Component(id="COMP-1", name="A", status=Status.ACTIVE, intent="has intent"),
                    Component(id="COMP-2", name="B", status=Status.ACTIVE),  # no intent
                ],
                capabilities=[
                    Capability(id="CAP-1", name="C", status=Status.ACTIVE, moes=["m1"]),
                    Capability(id="CAP-2", name="D", status=Status.ACTIVE),  # no moes
                ],
            ),
            relationships=[],
        )
        report = quality_report(model)
        # intent counts both comps (2) and caps (2) = 4 total, 1 comp has intent
        assert report.semantic_completeness["intent_coverage"] == "1/4"
        assert report.semantic_completeness["moe_coverage"] == "1/2"

    def test_overall_grade(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(), relationships=[],
        )
        report = quality_report(model)
        assert report.grade in ("A", "B", "C", "D", "F")

    def test_to_markdown(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(), relationships=[],
        )
        report = quality_report(model)
        md = report.to_markdown()
        assert "# Quality Report" in md
        assert report.grade in md


    def test_dashboard_with_pipeline_results(self):
        from architecture_model.pipeline.protocol import StageResult, QualityMetrics as PQM
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(), relationships=[],
        )
        pipeline_results = {
            "observe": StageResult(output=None, quality=PQM(score=90)),
            "allocate": StageResult(output=None, quality=PQM(score=85)),
        }
        report = quality_report(model, pipeline_results=pipeline_results)
        assert report.pipeline_quality is not None
        assert report.pipeline_quality["observe"] == 90
        assert report.pipeline_quality["allocate"] == 85

    def test_dashboard_without_pipeline_results(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(), relationships=[],
        )
        report = quality_report(model)
        assert report.pipeline_quality is None
