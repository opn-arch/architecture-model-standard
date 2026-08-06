"""Tests for the forward-authoring requirements parser."""

import pytest
from architecture_model.authoring.parser import parse_requirements_doc
from architecture_model.core.types import RelationType, Status


def test_parse_actors():
    doc = "# Actors\n- Developer: writes code\n- CI System: runs tests"
    model = parse_requirements_doc(doc)
    assert len(model.entities.actors) == 2
    assert model.entities.actors[0].name == "Developer"
    assert model.entities.actors[0].description == "writes code"
    assert model.entities.actors[1].name == "CI System"
    assert model.entities.actors[0].status == Status.ACTIVE


def test_parse_capabilities_with_nesting():
    doc = "# Capabilities\n- CAP-1: Compile\n  - CAP-1.1: ES modules\n  - CAP-1.2: CommonJS"
    model = parse_requirements_doc(doc)
    assert len(model.entities.capabilities) == 3
    contains_rels = [r for r in model.relationships if r.type == RelationType.CONTAINS]
    assert len(contains_rels) == 2
    # Check derives-from relationships too
    derives_rels = [r for r in model.relationships if r.type == RelationType.DERIVES_FROM]
    assert len(derives_rels) == 2


def test_parse_constraints_with_type():
    doc = "# Constraints\n- CON-1: Fast builds (performance)\n- CON-2: No deps (structural)"
    model = parse_requirements_doc(doc)
    assert len(model.entities.constraints) == 2
    from architecture_model.core.types import ConstraintType
    assert model.entities.constraints[0].type == ConstraintType.PERFORMANCE
    assert model.entities.constraints[0].name == "Fast builds"


def test_full_doc_roundtrip():
    doc = "# Actors\n- User: end user\n# Capabilities\n- CAP-1: Login\n# Constraints\n- CON-1: < 100ms (performance)"
    model = parse_requirements_doc(doc)
    assert len(model.entities.actors) == 1
    assert len(model.entities.capabilities) == 1
    assert len(model.entities.constraints) == 1


def test_meta_fields():
    doc = "# Actors\n- Dev: codes"
    model = parse_requirements_doc(doc)
    assert model.meta.project == "authored"
    assert model.meta.schema_version == "1.3"


def test_auto_generate_ids():
    doc = "# Capabilities\n- Build project\n- Run tests"
    model = parse_requirements_doc(doc)
    assert model.entities.capabilities[0].id == "CAP-1"
    assert model.entities.capabilities[1].id == "CAP-2"


def test_empty_doc():
    model = parse_requirements_doc("")
    assert len(model.entities.actors) == 0
    assert len(model.entities.capabilities) == 0
    assert len(model.entities.constraints) == 0
