"""Tests for Decision relationship types and lifecycle-gated validation."""

from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Constraint, Decision, Component, Relationship
)
from architecture_model.core.validator import validate_model


def test_decision_resolves_constraint():
    model = ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(
            constraints=[Constraint(id="CON-1", name="Fast", status="ACTIVE")],
            decisions=[Decision(id="DEC-1", name="Use Redis", status="ACTIVE", decision_status="accepted")],
            components=[Component(id="COMP-1", name="Cache", status="ACTIVE")],
        ),
        relationships=[
            Relationship(type="resolves", from_id="DEC-1", to_id="CON-1"),
            Relationship(type="affects", from_id="DEC-1", to_id="COMP-1"),
        ],
    )
    result = validate_model(model)
    errors = [i for i in result.issues if i.severity.value == "error"]
    assert len(errors) == 0


def test_model_meta_lifecycle_phase():
    meta = ModelMeta(project="test", schema_version="1.3", lifecycle_phase="concept")
    assert meta.lifecycle_phase == "concept"


def test_lifecycle_phase_defaults_to_production():
    meta = ModelMeta(project="test", schema_version="1.3")
    assert meta.lifecycle_phase == "production"


def test_concept_phase_skips_verification_check():
    """In concept phase, UNVERIFIED_CONSTRAINT warnings should not appear."""
    model = ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3", lifecycle_phase="concept"),
        entities=Entities(
            constraints=[Constraint(id="CON-1", name="Fast", status="ACTIVE")],
        ),
        relationships=[]
    )
    result = validate_model(model)
    unverified = [i for i in result.issues if "UNVERIFIED" in (i.code or "")]
    assert len(unverified) == 0


def test_production_phase_runs_verification_check():
    """In production phase, unverified constraints get warning."""
    model = ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3", lifecycle_phase="production"),
        entities=Entities(
            constraints=[Constraint(id="CON-1", name="Fast", status="ACTIVE")],
        ),
        relationships=[]
    )
    result = validate_model(model)
    unverified = [i for i in result.issues if "UNVERIFIED" in (i.code or "")]
    assert len(unverified) == 1
