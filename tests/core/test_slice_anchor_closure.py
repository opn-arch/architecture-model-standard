"""Track 4 Pass 1 Task 2 — 1-hop closure preserves realizes/contains/depends-on neighbors."""
from architecture_model.core.slice_anchor import apply_one_hop_closure
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Status,
    Capability, Component, Relationship, RelationType,
)


def _cap(id, name):
    return Capability(id=id, name=name, status=Status.ACTIVE)


def _comp(id, name):
    return Component(id=id, name=name, status=Status.ACTIVE)


def _meta():
    return ModelMeta(project="t", schema_version="2.1")


def _model_with_realizes():
    """CAP-1 is in slice. COMP-1 realizes CAP-1 but is NOT in slice. Closure pulls COMP-1 back."""
    full = ArchitectureModel(
        meta=_meta(),
        entities=Entities(
            capabilities=[_cap("CAP-1", "c1")],
            components=[_comp("COMP-1", "k1"), _comp("COMP-2", "k2")],
        ),
        relationships=[
            Relationship(from_id="COMP-1", to_id="CAP-1", type=RelationType.REALIZES),
            Relationship(from_id="COMP-2", to_id="CAP-1", type=RelationType.DEPENDS_ON),
        ],
    )
    sliced = ArchitectureModel(
        meta=_meta(),
        entities=Entities(capabilities=[_cap("CAP-1", "c1")]),
        relationships=[],
    )
    return full, sliced


def test_closure_pulls_realizer_component():
    full, sliced = _model_with_realizes()
    result = apply_one_hop_closure(full, sliced)
    ids = {c.id for c in result.entities.components}
    assert "COMP-1" in ids  # realizes closure
    assert "COMP-2" in ids  # depends-on closure
    rel_pairs = {(r.from_id, r.to_id, r.type.value) for r in result.relationships}
    assert ("COMP-1", "CAP-1", "realizes") in rel_pairs
    assert ("COMP-2", "CAP-1", "depends-on") in rel_pairs


def test_closure_is_one_hop_only_no_transitive():
    """CAP-1 in slice. COMP-1 realizes CAP-1. COMP-1 depends-on COMP-3. COMP-3 must NOT be pulled."""
    full = ArchitectureModel(
        meta=_meta(),
        entities=Entities(
            capabilities=[_cap("CAP-1", "c1")],
            components=[
                _comp("COMP-1", "k1"),
                _comp("COMP-3", "k3"),
            ],
        ),
        relationships=[
            Relationship(from_id="COMP-1", to_id="CAP-1", type=RelationType.REALIZES),
            Relationship(from_id="COMP-1", to_id="COMP-3", type=RelationType.DEPENDS_ON),
        ],
    )
    sliced = ArchitectureModel(
        meta=_meta(),
        entities=Entities(capabilities=[_cap("CAP-1", "c1")]),
        relationships=[],
    )
    result = apply_one_hop_closure(full, sliced)
    ids = {c.id for c in result.entities.components}
    assert "COMP-1" in ids
    assert "COMP-3" not in ids  # would require 2 hops


def test_closure_ignores_non_closure_relation_types():
    """A relationship of type 'exposes' should NOT expand the slice."""
    from architecture_model.core.types import Interface
    full = ArchitectureModel(
        meta=_meta(),
        entities=Entities(
            capabilities=[_cap("CAP-1", "c1")],
            interfaces=[Interface(id="IF-1", name="i1", status=Status.ACTIVE)],
            components=[_comp("COMP-1", "k1")],
        ),
        relationships=[
            Relationship(from_id="COMP-1", to_id="IF-1", type=RelationType.EXPOSES),
            Relationship(from_id="COMP-1", to_id="CAP-1", type=RelationType.REALIZES),
        ],
    )
    sliced = ArchitectureModel(
        meta=_meta(),
        entities=Entities(capabilities=[_cap("CAP-1", "c1")]),
        relationships=[],
    )
    result = apply_one_hop_closure(full, sliced)
    ids = {c.id for c in result.entities.components}
    assert "COMP-1" in ids
    if_ids = {i.id for i in result.entities.interfaces}
    assert "IF-1" not in if_ids
