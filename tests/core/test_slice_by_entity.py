"""Tests for slice_by_entity — root primitive for entity-scoped recursion.

Plan reference: ``docs/plans/2026-09-08-phase-3-recursion-and-entity-views.md``
Task 1. The plan pseudocode uses shorthand attributes (``sub.components``,
``r.from_``, ``sub.all_entities()``); tests here use the real API
(``sub.entities.components``, ``r.from_id`` / ``r.to_id``,
``sub.all_entity_ids``).
"""

from __future__ import annotations

import pytest

from architecture_model.core.slicer import slice_by_entity
from architecture_model.core.types import (
    ArchitectureModel,
    Capability,
    Component,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
)


def _meta() -> ModelMeta:
    return ModelMeta(schema_version="2.1", project="test")


def _comp(cid: str) -> Component:
    return Component(id=cid, name=cid, status=Status.ACTIVE)


def _cap(cid: str) -> Capability:
    return Capability(id=cid, name=cid, status=Status.ACTIVE)


def _rel(rtype: RelationType, src: str, dst: str) -> Relationship:
    return Relationship(type=rtype, from_id=src, to_id=dst)


@pytest.fixture
def model_with_hierarchy() -> ArchitectureModel:
    """COMP-1 contains COMP-1.1 contains COMP-1.1.1 (+ unrelated COMP-2)."""
    return ArchitectureModel(
        meta=_meta(),
        entities=Entities(
            components=[
                _comp("COMP-1"),
                _comp("COMP-1.1"),
                _comp("COMP-1.1.1"),
                _comp("COMP-2"),
            ],
        ),
        relationships=[
            _rel(RelationType.CONTAINS, "COMP-1", "COMP-1.1"),
            _rel(RelationType.CONTAINS, "COMP-1.1", "COMP-1.1.1"),
        ],
    )


@pytest.fixture
def model_with_realizes() -> ArchitectureModel:
    """COMP-3 realizes CAP-F2."""
    return ArchitectureModel(
        meta=_meta(),
        entities=Entities(
            components=[_comp("COMP-3")],
            capabilities=[_cap("CAP-F2"), _cap("CAP-F99")],
        ),
        relationships=[
            _rel(RelationType.REALIZES, "COMP-3", "CAP-F2"),
        ],
    )


@pytest.fixture
def broad_model() -> ArchitectureModel:
    """COMP-3 and COMP-99 both exist but are unrelated."""
    return ArchitectureModel(
        meta=_meta(),
        entities=Entities(
            components=[_comp("COMP-3"), _comp("COMP-99")],
        ),
        relationships=[],
    )


@pytest.fixture
def chained_deps_model() -> ArchitectureModel:
    """COMP-A -depends-on-> COMP-B -depends-on-> COMP-C -depends-on-> COMP-D."""
    return ArchitectureModel(
        meta=_meta(),
        entities=Entities(
            components=[
                _comp("COMP-A"),
                _comp("COMP-B"),
                _comp("COMP-C"),
                _comp("COMP-D"),
            ],
        ),
        relationships=[
            _rel(RelationType.DEPENDS_ON, "COMP-A", "COMP-B"),
            _rel(RelationType.DEPENDS_ON, "COMP-B", "COMP-C"),
            _rel(RelationType.DEPENDS_ON, "COMP-C", "COMP-D"),
        ],
    )


def test_slice_by_entity_includes_entity_and_contains_descendants(model_with_hierarchy):
    sub = slice_by_entity(model_with_hierarchy, "COMP-1")
    ids = {c.id for c in sub.entities.components}
    assert ids == {"COMP-1", "COMP-1.1", "COMP-1.1.1"}


def test_slice_by_entity_includes_realized_capabilities(model_with_realizes):
    sub = slice_by_entity(model_with_realizes, "COMP-3")
    assert "CAP-F2" in {c.id for c in sub.entities.capabilities}
    # Unrelated capability excluded
    assert "CAP-F99" not in {c.id for c in sub.entities.capabilities}


def test_slice_by_entity_excludes_unrelated_entities(broad_model):
    sub = slice_by_entity(broad_model, "COMP-3")
    assert "COMP-99" not in {c.id for c in sub.entities.components}
    assert "COMP-3" in {c.id for c in sub.entities.components}


def test_slice_by_entity_respects_include_hops(chained_deps_model):
    hop1 = slice_by_entity(chained_deps_model, "COMP-A", include_hops=1)
    assert {c.id for c in hop1.entities.components} == {"COMP-A", "COMP-B"}
    hop2 = slice_by_entity(chained_deps_model, "COMP-A", include_hops=2)
    assert {c.id for c in hop2.entities.components} == {"COMP-A", "COMP-B", "COMP-C"}
    hop3 = slice_by_entity(chained_deps_model, "COMP-A", include_hops=3)
    assert {c.id for c in hop3.entities.components} == {
        "COMP-A",
        "COMP-B",
        "COMP-C",
        "COMP-D",
    }


def test_slice_by_entity_relationships_have_both_endpoints_in_sub(model_with_hierarchy):
    sub = slice_by_entity(model_with_hierarchy, "COMP-1")
    ids = sub.all_entity_ids
    for r in sub.relationships:
        assert r.from_id in ids and r.to_id in ids


def test_slice_by_entity_missing_id_raises(broad_model):
    with pytest.raises(KeyError):
        slice_by_entity(broad_model, "COMP-DOES-NOT-EXIST")


def test_slice_by_entity_zero_hops_still_expands_contains(model_with_hierarchy):
    """include_hops=0 should still expand `contains` (unbounded) — hops
    only bounds context relations (realizes/exposes/consumes/depends-on)."""
    sub = slice_by_entity(model_with_hierarchy, "COMP-1", include_hops=0)
    ids = {c.id for c in sub.entities.components}
    assert ids == {"COMP-1", "COMP-1.1", "COMP-1.1.1"}


def test_slice_by_entity_bidirectional_context_hops(model_with_realizes):
    """Hops are bidirectional: starting from CAP-F2, we should reach COMP-3
    via the incoming realizes edge."""
    sub = slice_by_entity(model_with_realizes, "CAP-F2", include_hops=1)
    assert "COMP-3" in {c.id for c in sub.entities.components}
