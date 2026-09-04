"""Tests for the legacy ``core.differ`` delegator.

The legacy ``diff_models()`` / ``ModelDiff`` API is preserved for existing
consumers (quality/orchestrator, docs/se/generator, docs/drift, cli/main).
Under the hood it now delegates to :func:`architecture_model.lifecycle.diff.semantic_diff`.

These tests pin two invariants:

* Signature and result shape preserved (``ModelDiff`` with
  ``entity_changes`` / ``relationship_changes``).
* Relationship endpoints use ``from``/``to`` keys wherever the delegator
  emits dict-shaped payloads — never the buggy ``source``/``target``.
* Content matches ``semantic_diff`` for equivalent inputs.
"""

from __future__ import annotations

from architecture_model.core.differ import (
    ChangeType,
    EntityChange,
    ModelDiff,
    RelationshipChange,
    diff_models,
)
from architecture_model.core.types import (
    ArchitectureModel,
    Capability,
    Component,
    Entities,
    ModelMeta,
    RelationType,
    Relationship,
    Status,
)
from architecture_model.lifecycle.diff import semantic_diff


def _model(components=None, capabilities=None, relationships=None) -> ArchitectureModel:
    return ArchitectureModel(
        meta=ModelMeta(schema_version="2.0", project="test"),
        entities=Entities(
            components=list(components or []),
            capabilities=list(capabilities or []),
        ),
        relationships=list(relationships or []),
    )


def _comp(cid: str, name: str = "C") -> Component:
    return Component(id=cid, name=name, source_block="S1", status=Status.ACTIVE)


def _cap(cid: str, name: str = "K") -> Capability:
    return Capability(id=cid, name=name, source_block="S1", status=Status.ACTIVE)


def _rel(f: str, t: str, typ: RelationType = RelationType.REALIZES) -> Relationship:
    return Relationship(from_id=f, to_id=t, type=typ)


# ---------------------------------------------------------------------------
# Legacy API still importable and callable
# ---------------------------------------------------------------------------


def test_diff_models_returns_model_diff_shape() -> None:
    old = _model()
    new = _model(components=[_comp("COMP-1", "One")])
    d = diff_models(old, new)
    assert isinstance(d, ModelDiff)
    assert d.has_changes is True
    assert d.added_count == 1
    assert d.removed_count == 0
    assert isinstance(d.entity_changes[0], EntityChange)
    assert d.entity_changes[0].change_type == ChangeType.ADDED
    assert d.entity_changes[0].entity_id == "COMP-1"
    assert d.entity_changes[0].entity_type == "component"


def test_diff_models_detects_removed_and_modified() -> None:
    old = _model(components=[_comp("COMP-1", "Old"), _comp("COMP-2", "Two")])
    new = _model(components=[_comp("COMP-1", "New")])
    d = diff_models(old, new)
    kinds = {(c.change_type, c.entity_id) for c in d.entity_changes}
    assert (ChangeType.REMOVED, "COMP-2") in kinds
    assert (ChangeType.MODIFIED, "COMP-1") in kinds


# ---------------------------------------------------------------------------
# Relationship endpoints use from/to, not source/target
# ---------------------------------------------------------------------------


def test_relationship_change_uses_from_to_attributes() -> None:
    old = _model(components=[_comp("COMP-1")], capabilities=[_cap("CAP-1")])
    new = _model(
        components=[_comp("COMP-1")],
        capabilities=[_cap("CAP-1")],
        relationships=[_rel("COMP-1", "CAP-1")],
    )
    d = diff_models(old, new)
    assert len(d.relationship_changes) == 1
    rc = d.relationship_changes[0]
    assert isinstance(rc, RelationshipChange)
    # Must expose from_id/to_id — not source/target
    assert rc.from_id == "COMP-1"
    assert rc.to_id == "CAP-1"
    assert not hasattr(rc, "source")
    assert not hasattr(rc, "target")


def test_report_and_summary_use_from_to_arrow() -> None:
    old = _model(components=[_comp("COMP-1")], capabilities=[_cap("CAP-1")])
    new = _model(
        components=[_comp("COMP-1")],
        capabilities=[_cap("CAP-1")],
        relationships=[_rel("COMP-1", "CAP-1")],
    )
    d = diff_models(old, new)
    report = d.format_report()
    assert "COMP-1" in report and "CAP-1" in report
    # Report format should NOT expose buggy source/target labels
    assert "source" not in report.lower().split()
    assert "target:" not in report.lower()


# ---------------------------------------------------------------------------
# Delegator content matches semantic_diff for equivalent inputs
# ---------------------------------------------------------------------------


def test_delegator_matches_semantic_diff_for_relationships() -> None:
    old = _model(
        components=[_comp("COMP-1")],
        capabilities=[_cap("CAP-1"), _cap("CAP-2")],
        relationships=[_rel("COMP-1", "CAP-1")],
    )
    new = _model(
        components=[_comp("COMP-1")],
        capabilities=[_cap("CAP-1"), _cap("CAP-2")],
        relationships=[_rel("COMP-1", "CAP-2")],
    )
    legacy = diff_models(old, new)
    canonical = semantic_diff(old, new)

    added_legacy = {
        (r.from_id, r.to_id, r.rel_type)
        for r in legacy.relationship_changes
        if r.change_type == ChangeType.ADDED
    }
    removed_legacy = {
        (r.from_id, r.to_id, r.rel_type)
        for r in legacy.relationship_changes
        if r.change_type == ChangeType.REMOVED
    }
    added_canon = {(x["from"], x["to"], x["type"]) for x in canonical.relationships.added}
    removed_canon = {(x["from"], x["to"], x["type"]) for x in canonical.relationships.removed}

    assert added_legacy == added_canon
    assert removed_legacy == removed_canon


def test_delegator_matches_semantic_diff_for_entity_add_remove() -> None:
    old = _model(components=[_comp("COMP-1", "One")])
    new = _model(components=[_comp("COMP-2", "Two")])
    legacy = diff_models(old, new)
    canonical = semantic_diff(old, new)

    legacy_added = {c.entity_id for c in legacy.entity_changes if c.change_type == ChangeType.ADDED}
    legacy_removed = {
        c.entity_id for c in legacy.entity_changes if c.change_type == ChangeType.REMOVED
    }
    assert legacy_added == set(canonical.entities["components"].added)
    assert legacy_removed == set(canonical.entities["components"].removed)


def test_no_changes_produces_empty_diff() -> None:
    m = _model(components=[_comp("COMP-1")])
    d = diff_models(m, m)
    assert d.has_changes is False
    assert d.format_report() == "No changes detected between model versions."
