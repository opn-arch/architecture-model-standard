"""Tests for capability inference from behaviors."""
import pytest
from architecture_model.orchestration.capability_inference import infer_capabilities
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Behavior, Capability, Relationship,
    RelationType
)


class TestInferCapabilities:
    def test_groups_by_url_prefix(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[
                Behavior(id="BEH-1", name="Create user", status="ACTIVE", trigger="POST /users"),
                Behavior(id="BEH-2", name="Get user", status="ACTIVE", trigger="GET /users/{id}"),
                Behavior(id="BEH-3", name="List orders", status="ACTIVE", trigger="GET /orders"),
                Behavior(id="BEH-4", name="Create order", status="ACTIVE", trigger="POST /orders"),
            ]),
            relationships=[]
        )
        result = infer_capabilities(model)
        assert len(result.entities.capabilities) >= 2
        cap_names = {c.name.lower() for c in result.entities.capabilities}
        assert any("user" in n for n in cap_names)
        assert any("order" in n for n in cap_names)

    def test_groups_by_actor(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[
                Behavior(id="BEH-1", name="Login", status="ACTIVE", actor="end_user", trigger="POST /auth/login"),
                Behavior(id="BEH-2", name="Signup", status="ACTIVE", actor="end_user", trigger="POST /auth/signup"),
                Behavior(id="BEH-3", name="Run migration", status="ACTIVE", actor="admin", trigger=""),
            ]),
            relationships=[]
        )
        result = infer_capabilities(model)
        # /auth prefix captures first two, actor:admin captures third
        assert len(result.entities.capabilities) >= 2

    def test_creates_realizes_relationships(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[
                Behavior(id="BEH-1", name="Create user", status="ACTIVE", trigger="POST /users"),
                Behavior(id="BEH-2", name="Get user", status="ACTIVE", trigger="GET /users/{id}"),
            ]),
            relationships=[]
        )
        result = infer_capabilities(model)
        realizes = [r for r in result.relationships if r.type == RelationType.REALIZES]
        assert len(realizes) == 2

    def test_preserves_existing_capabilities(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(
                capabilities=[Capability(id="CAP-1", name="Existing", status="ACTIVE")],
                behaviors=[Behavior(id="BEH-1", name="Do thing", status="ACTIVE", trigger="POST /things")]
            ),
            relationships=[]
        )
        result = infer_capabilities(model)
        assert any(c.name == "Existing" for c in result.entities.capabilities)
        assert len(result.entities.capabilities) >= 2

    def test_no_behaviors_returns_unchanged(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[]),
            relationships=[]
        )
        result = infer_capabilities(model)
        assert result == model

    def test_ungrouped_get_internal_ops(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[
                Behavior(id="BEH-1", name="Background task", status="ACTIVE", trigger="internal"),
            ]),
            relationships=[]
        )
        result = infer_capabilities(model)
        assert any("Internal" in c.name for c in result.entities.capabilities)
