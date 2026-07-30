"""Test confidence aggregation."""
from architecture_model.core.confidence import (
    compute_model_confidence,
    aggregate_block_confidence,
    model_confidence_summary,
)
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Component, Behavior, Status,
)


def test_aggregate_block_confidence():
    model = ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="1.3"),
        entities=Entities(components=[
            Component(id="C1", name="A", status=Status.ACTIVE, f_block="F1", contract="X", files=["a.py"]),
            Component(id="C2", name="B", status=Status.ACTIVE, f_block="F1"),
            Component(id="C3", name="C", status=Status.ACTIVE, f_block="F2", contract="Y", pattern="adapter", files=["c.py"]),
        ]),
        relationships=[],
    )
    compute_model_confidence(model)
    blocks = aggregate_block_confidence(model)
    assert "F1" in blocks
    assert "F2" in blocks
    assert blocks["F1"]["avg_confidence"] < blocks["F2"]["avg_confidence"]
    assert blocks["F1"]["entity_count"] == 2
    assert blocks["F2"]["entity_count"] == 1


def test_model_confidence_summary():
    model = ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="1.3"),
        entities=Entities(components=[
            Component(id="C1", name="A", status=Status.ACTIVE, contract="X", files=["a.py"]),
            Component(id="C2", name="B", status=Status.ACTIVE),
        ]),
        relationships=[],
    )
    compute_model_confidence(model)
    summary = model_confidence_summary(model)
    assert "overall" in summary
    assert "high_confidence" in summary
    assert "low_confidence" in summary
    assert "gaps" in summary
    assert summary["total_entities"] == 2
