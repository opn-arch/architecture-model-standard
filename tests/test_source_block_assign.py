"""Tests for deterministic tie-breaking in auto_assign_source_blocks."""

from architecture_model.core.source_block_assign import auto_assign_source_blocks
from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
    Strength,
)


def _make_model(components, relationships):
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.3", project="test"),
        entities=Entities(components=components),
        relationships=relationships,
    )


def test_deterministic_tiebreak_alphabetical():
    """Two components with identical degree should be assigned deterministically by ID."""
    # Both COMP-B and COMP-A connect to COMP-C (degree 1 each)
    comps = [
        Component(id="COMP-B", name="B", status=Status.ACTIVE),
        Component(id="COMP-A", name="A", status=Status.ACTIVE),
        Component(id="COMP-C", name="C", status=Status.ACTIVE),
    ]
    rels = [
        Relationship(type=RelationType.DEPENDS_ON, from_id="COMP-B", to_id="COMP-C"),
        Relationship(type=RelationType.DEPENDS_ON, from_id="COMP-A", to_id="COMP-C"),
    ]

    # Run multiple times with different input orders
    results = []
    for _ in range(5):
        model = _make_model(comps, rels)
        assigned = auto_assign_source_blocks(model)
        fb_map = {c.id: c.source_block for c in assigned.entities.components}
        results.append(fb_map)

    # All runs should produce identical assignments
    for r in results[1:]:
        assert r == results[0], f"Non-deterministic: {r} != {results[0]}"


def test_tiebreak_reversed_input_order():
    """Same graph, reversed component order → same source_block assignment."""
    rels = [
        Relationship(type=RelationType.DEPENDS_ON, from_id="COMP-B", to_id="COMP-C"),
        Relationship(type=RelationType.DEPENDS_ON, from_id="COMP-A", to_id="COMP-C"),
    ]

    comps_order1 = [
        Component(id="COMP-B", name="B", status=Status.ACTIVE),
        Component(id="COMP-A", name="A", status=Status.ACTIVE),
        Component(id="COMP-C", name="C", status=Status.ACTIVE),
    ]
    comps_order2 = [
        Component(id="COMP-A", name="A", status=Status.ACTIVE),
        Component(id="COMP-C", name="C", status=Status.ACTIVE),
        Component(id="COMP-B", name="B", status=Status.ACTIVE),
    ]

    m1 = auto_assign_source_blocks(_make_model(comps_order1, rels))
    m2 = auto_assign_source_blocks(_make_model(comps_order2, rels))

    fb1 = {c.id: c.source_block for c in m1.entities.components}
    fb2 = {c.id: c.source_block for c in m2.entities.components}
    assert fb1 == fb2, f"Different orders gave different results: {fb1} vs {fb2}"
