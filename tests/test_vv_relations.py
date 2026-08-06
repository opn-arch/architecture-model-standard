"""Tests for V&V relationship types (derives-from, verifies) and validator check."""

import pytest

from architecture_model.core.types import (
    ArchitectureModel,
    Constraint,
    ConstraintType,
    Component,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
)
from architecture_model.core.validator import validate_model, Severity


def _make_model(constraints, relationships):
    """Helper to build a minimal model with constraints and relationships."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.3", project="test"),
        entities=Entities(
            constraints=constraints,
            components=[
                Component(id="COMP-1", name="Dummy", status=Status.ACTIVE),
            ],
        ),
        relationships=relationships,
    )


class TestRelationTypeEnum:
    def test_derives_from_exists(self):
        assert RelationType.DERIVES_FROM.value == "derives-from"

    def test_verifies_exists(self):
        assert RelationType.VERIFIES.value == "verifies"

    def test_usable_in_relationship(self):
        r = Relationship(type=RelationType.DERIVES_FROM, from_id="CON-1.1", to_id="CON-1")
        assert r.type == RelationType.DERIVES_FROM

        r2 = Relationship(type=RelationType.VERIFIES, from_id="TEST-1", to_id="CON-1.1")
        assert r2.type == RelationType.VERIFIES


class TestUnverifiedConstraintValidator:
    def test_leaf_constraint_without_verifies_gets_warning(self):
        """Leaf constraints without verifies edge should produce warning."""
        model = _make_model(
            constraints=[
                Constraint(id="CON-1", name="Perf", status=Status.ACTIVE, type=ConstraintType.PERFORMANCE),
            ],
            relationships=[],
        )
        result = validate_model(model)
        codes = [i.code for i in result.issues if i.severity == Severity.WARNING]
        assert "UNVERIFIED_CONSTRAINT" in codes

    def test_leaf_constraint_with_verifies_is_clean(self):
        """Leaf constraints with verifies edge should not produce UNVERIFIED_CONSTRAINT."""
        model = _make_model(
            constraints=[
                Constraint(id="CON-1", name="Perf", status=Status.ACTIVE, type=ConstraintType.PERFORMANCE),
            ],
            relationships=[
                Relationship(type=RelationType.VERIFIES, from_id="TEST-1", to_id="CON-1"),
            ],
        )
        result = validate_model(model)
        codes = [i.code for i in result.issues if i.code == "UNVERIFIED_CONSTRAINT"]
        assert codes == []

    def test_parent_constraint_needs_no_verifies(self):
        """Parent constraints (have children) don't need direct verifies."""
        model = _make_model(
            constraints=[
                Constraint(id="CON-1", name="Parent", status=Status.ACTIVE, type=ConstraintType.PERFORMANCE),
                Constraint(id="CON-1.1", name="Child", status=Status.ACTIVE, type=ConstraintType.PERFORMANCE),
            ],
            relationships=[
                Relationship(type=RelationType.DERIVES_FROM, from_id="CON-1.1", to_id="CON-1"),
                Relationship(type=RelationType.VERIFIES, from_id="TEST-1", to_id="CON-1.1"),
            ],
        )
        result = validate_model(model)
        unverified = [i for i in result.issues if i.code == "UNVERIFIED_CONSTRAINT"]
        assert unverified == []
