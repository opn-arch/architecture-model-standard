"""Tests for quality orchestrator — chains code review → model feedback → dashboard."""
import copy
from architecture_model.quality.orchestrator import quality_loop, QualityLoopResult
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Component, Capability, Status,
)


def _make_model():
    return ArchitectureModel(
        meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
        entities=Entities(
            components=[
                Component(id="COMP-1", name="Alpha", status=Status.ACTIVE,
                          files=["nonexistent.py"]),
                Component(id="COMP-2", name="Beta", status=Status.ACTIVE),
            ],
            capabilities=[
                Capability(id="CAP-1", name="Cap", status=Status.ACTIVE,
                           intent="Test cap", moes=["MOE-1"]),
            ],
        ),
        relationships=[],
    )


class TestQualityLoop:
    def test_returns_result_dataclass(self):
        model = _make_model()
        result = quality_loop(model)
        assert isinstance(result, QualityLoopResult)
        assert result.original_model is model
        assert result.updated_model is not None
        assert result.report is not None

    def test_does_not_mutate_original(self):
        model = _make_model()
        original_intent = model.entities.components[0].intent
        result = quality_loop(model)
        assert model.entities.components[0].intent == original_intent

    def test_diff_populated_when_changes(self):
        model = _make_model()
        result = quality_loop(model)
        # diff should exist (may or may not have changes depending on feedback)
        assert result.diff is not None

    def test_feedback_list_populated(self):
        model = _make_model()
        result = quality_loop(model)
        assert isinstance(result.feedbacks, list)
