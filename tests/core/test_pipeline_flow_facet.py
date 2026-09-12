"""Tests for the Pipeline Flow behavior facet (C15).

The Pipeline Flow facet renders a 1-hop composite view for each pipeline
anchor behavior: root + direct sub-behaviors + implementing components.
Deep drill-down remains available via node clicks on the rendered viewer.
"""

from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Relationship,
    Actor, Capability, Behavior, Component, ActorType,
)
from architecture_model.core.visualize import (
    _pipeline_flow_facet_lines,
    _sid,
)


def _model_with_pipeline() -> ArchitectureModel:
    return ArchitectureModel(
        meta=ModelMeta(project="Test", schema_version="2.1"),
        entities=Entities(
            actors=[Actor(id="ACT-1", name="Dev", status="ACTIVE", type=ActorType.HUMAN)],
            capabilities=[Capability(id="CAP-1", name="Cap", status="ACTIVE")],
            behaviors=[
                Behavior(id="BEH-P1", name="EXTRACT", status="ACTIVE"),
                Behavior(id="BEH-P1.1", name="Observe", status="ACTIVE"),
                Behavior(id="BEH-P1.2", name="Infer", status="ACTIVE"),
                Behavior(id="BEH-99", name="Unrelated", status="ACTIVE"),
            ],
            interfaces=[], constraints=[], layers=[],
            components=[
                Component(id="COMP-1", name="Pipeline", status="ACTIVE"),
                Component(id="COMP-2", name="Manifest", status="ACTIVE"),
                Component(id="COMP-3", name="Unrelated", status="ACTIVE"),
            ],
        ),
        relationships=[
            Relationship(from_id="BEH-P1", to_id="BEH-P1.1", type="contains"),
            Relationship(from_id="BEH-P1", to_id="BEH-P1.2", type="contains"),
            Relationship(from_id="COMP-1", to_id="BEH-P1", type="traces-to"),
            Relationship(from_id="COMP-2", to_id="BEH-P1.1", type="traces-to"),
        ],
    )


def _entity_map(model):
    m: dict = {}
    for b in model.entities.behaviors:
        m[b.id] = ("behavior", b.name)
    for c in model.entities.components:
        m[c.id] = ("component", c.name)
    return m


def test_pipeline_flow_facet_includes_root_and_subs():
    model = _model_with_pipeline()
    out = _pipeline_flow_facet_lines(model, "BEH-P1", "EXTRACT", _entity_map(model))
    assert out is not None
    assert "graph LR" in out
    # Root and both sub-behaviors present
    assert _sid("BEH-P1") in out
    assert _sid("BEH-P1.1") in out
    assert _sid("BEH-P1.2") in out
    # Unrelated behavior not present
    assert _sid("BEH-99") not in out


def test_pipeline_flow_facet_includes_implementing_components():
    model = _model_with_pipeline()
    out = _pipeline_flow_facet_lines(model, "BEH-P1", "EXTRACT", _entity_map(model))
    assert out is not None
    # Implementing components at root and sub level
    assert _sid("COMP-1") in out
    assert _sid("COMP-2") in out
    # Unrelated component not present
    assert _sid("COMP-3") not in out


def test_pipeline_flow_facet_none_when_empty():
    """A behavior with no subs and no implementations returns None."""
    model = _model_with_pipeline()
    out = _pipeline_flow_facet_lines(model, "BEH-99", "Unrelated", _entity_map(model))
    assert out is None
