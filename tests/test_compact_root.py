"""Tests for compact_root_model."""
from __future__ import annotations

import yaml
from dataclasses import dataclass, field

from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    Capability,
    Interface,
    Behavior,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
    ComponentKind,
)
from architecture_model.orchestration.decompose import compact_root_model


def _make_model():
    """Build a minimal model with one detailed component."""
    comp = Component(
        id="COMP-1",
        name="AuthService",
        status=Status.ACTIVE,
        f_block="F1",
        layer="application",
        kind=ComponentKind.SERVICE,
        contract="handles auth",
        pattern="hexagonal",
        description="Auth service",
        tags=["auth"],
        files=["src/auth.py"],
        responsibilities=["authenticate users"],
        signatures=[],
        symbols=[],
        constants=[],
        functions=["login", "logout"],
        test_contracts=[],
        observability=[],
        fields=[],
    )
    comp2 = Component(
        id="COMP-2",
        name="Unrelated",
        status=Status.ACTIVE,
        f_block="F2",
        files=["src/other.py"],
        responsibilities=["do stuff"],
        functions=["run"],
    )
    cap = Capability(id="CAP-1", name="Authentication", status=Status.ACTIVE)
    iface = Interface(id="IF-1", name="REST API", status=Status.ACTIVE)
    beh = Behavior(id="BEH-1", name="Login Flow", status=Status.ACTIVE)

    model = ArchitectureModel(
        meta=ModelMeta(schema_version="2.0", project="test"),
        entities=Entities(
            components=[comp, comp2],
            capabilities=[cap],
            interfaces=[iface],
            behaviors=[beh],
        ),
        relationships=[
            Relationship(from_id="COMP-1", to_id="CAP-1", type=RelationType.REALIZES),
            Relationship(from_id="COMP-1", to_id="IF-1", type=RelationType.EXPOSES),
        ],
    )
    return model


def test_keeps_identity_fields():
    model = _make_model()
    compact_root_model(model, block_ids=["F1"])
    comp = model.entities.components[0]
    assert comp.id == "COMP-1"
    assert comp.name == "AuthService"
    assert comp.f_block == "F1"
    assert comp.contract == "handles auth"
    assert comp.pattern == "hexagonal"
    assert comp.kind == ComponentKind.SERVICE
    assert comp.layer == "application"
    assert comp.description == "Auth service"
    assert comp.tags == ["auth"]
    assert comp.status == Status.ACTIVE


def test_strips_implementation_fields():
    model = _make_model()
    compact_root_model(model, block_ids=["F1"])
    comp = model.entities.components[0]
    assert comp.files == []
    assert comp.responsibilities == []
    assert comp.signatures == []
    assert comp.symbols == []
    assert comp.constants == []
    assert comp.functions == []


def test_non_component_entities_untouched():
    model = _make_model()
    compact_root_model(model, block_ids=["F1"])
    assert len(model.entities.capabilities) == 1
    assert model.entities.capabilities[0].name == "Authentication"
    assert len(model.entities.interfaces) == 1
    assert model.entities.interfaces[0].name == "REST API"
    assert len(model.entities.behaviors) == 1
    assert model.entities.behaviors[0].name == "Login Flow"


def test_relationships_preserved():
    model = _make_model()
    compact_root_model(model, block_ids=["F1"])
    assert len(model.relationships) == 2
    assert model.relationships[0].from_id == "COMP-1"
    assert model.relationships[0].to_id == "CAP-1"


def test_serialized_size_shrinks():
    model = _make_model()
    before = len(yaml.dump({"files": model.entities.components[0].files,
                            "responsibilities": model.entities.components[0].responsibilities,
                            "functions": model.entities.components[0].functions}))
    assert before > 0  # sanity
    compact_root_model(model, block_ids=["F1"])
    comp = model.entities.components[0]
    after = len(yaml.dump({"files": comp.files,
                           "responsibilities": comp.responsibilities,
                           "functions": comp.functions}))
    assert after < before


def test_only_target_blocks_compacted():
    """Components not in block_ids should be left alone."""
    model = _make_model()
    compact_root_model(model, block_ids=["F1"])
    comp2 = model.entities.components[1]
    assert comp2.files == ["src/other.py"]
    assert comp2.responsibilities == ["do stuff"]
    assert comp2.functions == ["run"]
