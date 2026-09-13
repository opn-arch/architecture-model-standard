"""Tests for the pipeline-completeness validator rule.

Lifts the standalone `architecture-model audit` checks into `validate_model`
so operational pipeline gaps surface as first-class ValidationIssues on every
validation run.
"""
from __future__ import annotations

from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta,
    Behavior, Capability, Component, Relationship,
    Status, RelationType,
)
from architecture_model.core.validator import validate_model


def _meta():
    return ModelMeta(project="test", schema_version="2.1")


def _beh(bid: str, name: str, description: str = "d") -> Behavior:
    return Behavior(id=bid, name=name, status=Status.ACTIVE, description=description)


def _rel(f: str, t: str, kind: RelationType) -> Relationship:
    return Relationship(type=kind, from_id=f, to_id=t)


def _build_ok_pipeline(anchor: str, sub_id: str) -> ArchitectureModel:
    """A minimally-complete pipeline: root + one sub, containment + trace + trigger."""
    comp = Component(id="COMP-X", name="X", status=Status.ACTIVE)
    root = _beh(anchor, f"root of {anchor}", description="Root behavior")
    sub = _beh(sub_id, "sub", description="Sub-behavior")
    rels = [
        _rel(anchor, sub_id, RelationType.CONTAINS),
        _rel(sub_id, "COMP-X", RelationType.TRACES_TO),
        _rel(anchor, sub_id, RelationType.TRIGGERS),
    ]
    return ArchitectureModel(
        meta=_meta(),
        entities=Entities(components=[comp], behaviors=[root, sub]),
        relationships=rels,
    )


def test_pipeline_check_reports_missing_description():
    m = _build_ok_pipeline("BEH-P1", "BEH-P1.1")
    # blank the description on the sub-behavior
    m.entities.behaviors[1].description = ""
    result = validate_model(m)
    codes = [i.code for i in result.issues]
    assert "PIPELINE_MISSING_DESCRIPTION" in codes


def test_pipeline_check_reports_missing_trace():
    m = _build_ok_pipeline("BEH-P1", "BEH-P1.1")
    m.relationships = [r for r in m.relationships if r.type != RelationType.TRACES_TO]
    result = validate_model(m)
    codes = [i.code for i in result.issues]
    assert "PIPELINE_MISSING_TRACE" in codes


def test_pipeline_check_reports_missing_containment():
    m = _build_ok_pipeline("BEH-P1", "BEH-P1.1")
    m.relationships = [r for r in m.relationships if r.type != RelationType.CONTAINS]
    result = validate_model(m)
    codes = [i.code for i in result.issues]
    assert "PIPELINE_MISSING_CONTAINMENT" in codes


def test_pipeline_check_reports_isolated_sub():
    m = _build_ok_pipeline("BEH-P1", "BEH-P1.1")
    m.relationships = [r for r in m.relationships if r.type != RelationType.TRIGGERS]
    result = validate_model(m)
    codes = [i.code for i in result.issues]
    assert "PIPELINE_ISOLATED" in codes


def test_pipeline_check_clean_when_complete():
    m = _build_ok_pipeline("BEH-P1", "BEH-P1.1")
    result = validate_model(m)
    codes = {i.code for i in result.issues}
    assert not any(c and c.startswith("PIPELINE_") for c in codes)


def test_pipeline_check_skipped_when_anchor_absent():
    """Model without any pipeline root should not fire pipeline warnings."""
    m = ArchitectureModel(
        meta=_meta(),
        entities=Entities(components=[Component(id="COMP-A", name="A", status=Status.ACTIVE)]),
        relationships=[],
    )
    result = validate_model(m)
    codes = {i.code for i in result.issues}
    assert not any(c and c.startswith("PIPELINE_") for c in codes)
