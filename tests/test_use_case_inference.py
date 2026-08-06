"""Tests for composite behavior (use case) inference."""
import pytest
from architecture_model.orchestration.use_case_inference import infer_composite_behaviors
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Behavior, Relationship, RelationType
)


class TestInferCompositeBehaviors:
    def test_chain_becomes_composite(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[
                Behavior(id="BEH-1", name="Receive log", status="ACTIVE", trigger="POST /logs"),
                Behavior(id="BEH-2", name="Parse entities", status="ACTIVE", trigger="internal"),
                Behavior(id="BEH-3", name="Update graph", status="ACTIVE", trigger="internal"),
            ]),
            relationships=[
                Relationship(type="triggers", from_id="BEH-1", to_id="BEH-2"),
                Relationship(type="triggers", from_id="BEH-2", to_id="BEH-3"),
            ]
        )
        result = infer_composite_behaviors(model)
        composites = [b for b in result.entities.behaviors if b.id.startswith("UC-")]
        assert len(composites) == 1
        assert composites[0].trigger == "POST /logs"
        contains = [r for r in result.relationships if r.type == "contains" and r.from_id == "UC-1"]
        assert len(contains) == 3

    def test_parallel_chains_separate_composites(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[
                Behavior(id="BEH-1", name="A", status="ACTIVE", trigger="POST /a"),
                Behavior(id="BEH-2", name="B", status="ACTIVE", trigger="internal"),
                Behavior(id="BEH-3", name="C", status="ACTIVE", trigger="POST /c"),
                Behavior(id="BEH-4", name="D", status="ACTIVE", trigger="internal"),
            ]),
            relationships=[
                Relationship(type="triggers", from_id="BEH-1", to_id="BEH-2"),
                Relationship(type="triggers", from_id="BEH-3", to_id="BEH-4"),
            ]
        )
        result = infer_composite_behaviors(model)
        composites = [b for b in result.entities.behaviors if b.id.startswith("UC-")]
        assert len(composites) == 2

    def test_single_behavior_no_composite(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[
                Behavior(id="BEH-1", name="Solo", status="ACTIVE", trigger="GET /solo"),
            ]),
            relationships=[]
        )
        result = infer_composite_behaviors(model)
        composites = [b for b in result.entities.behaviors if b.id.startswith("UC-")]
        assert len(composites) == 0

    def test_composite_steps_are_behavior_names(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[
                Behavior(id="BEH-1", name="Submit order", status="ACTIVE", trigger="POST /orders"),
                Behavior(id="BEH-2", name="Process payment", status="ACTIVE", trigger="internal"),
            ]),
            relationships=[
                Relationship(type="triggers", from_id="BEH-1", to_id="BEH-2"),
            ]
        )
        result = infer_composite_behaviors(model)
        composites = [b for b in result.entities.behaviors if b.id.startswith("UC-")]
        assert composites[0].steps == ["Submit order", "Process payment"]

    def test_no_triggers_returns_unchanged(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[
                Behavior(id="BEH-1", name="A", status="ACTIVE"),
            ]),
            relationships=[Relationship(type="realizes", from_id="COMP-1", to_id="BEH-1")]
        )
        result = infer_composite_behaviors(model)
        assert result.entities.behaviors == model.entities.behaviors
        assert result.relationships == model.relationships

    def test_enum_type_triggers_detected(self):
        """Trigger relationships using RelationType enum should be detected."""
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[
                Behavior(id="BEH-1", name="Ingest", status="ACTIVE", trigger="POST /data"),
                Behavior(id="BEH-2", name="Transform", status="ACTIVE", trigger="internal"),
            ]),
            relationships=[
                Relationship(type=RelationType.TRIGGERS, from_id="BEH-1", to_id="BEH-2"),
            ]
        )
        result = infer_composite_behaviors(model)
        composites = [b for b in result.entities.behaviors if b.id.startswith("UC-")]
        assert len(composites) == 1
        assert composites[0].steps == ["Ingest", "Transform"]
        contains = [r for r in result.relationships if r.from_id == "UC-1"]
        assert len(contains) == 2
