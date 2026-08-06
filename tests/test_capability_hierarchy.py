"""Tests for capability hierarchy inference."""
import pytest
from architecture_model.orchestration.capability_inference import (
    infer_capabilities, build_capability_hierarchy
)
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Behavior, Capability, Relationship, RelationType
)


class TestCapabilityHierarchy:
    def test_nested_urls_create_hierarchy(self):
        """Deeper URL paths create parent-child capability relationships."""
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(
                behaviors=[
                    Behavior(id="BEH-1", name="List logs", status="ACTIVE", trigger="GET /logs"),
                    Behavior(id="BEH-2", name="Parse log", status="ACTIVE", trigger="POST /logs/parse"),
                    Behavior(id="BEH-3", name="Search logs", status="ACTIVE", trigger="GET /logs/search"),
                    Behavior(id="BEH-4", name="Get orders", status="ACTIVE", trigger="GET /orders"),
                ],
                capabilities=[
                    Capability(id="CAP-1", name="Log Management", status="ACTIVE"),
                    Capability(id="CAP-2", name="Log Parsing", status="ACTIVE"),
                    Capability(id="CAP-3", name="Log Search", status="ACTIVE"),
                    Capability(id="CAP-4", name="Order Management", status="ACTIVE"),
                ],
            ),
            relationships=[
                Relationship(type=RelationType.REALIZES, from_id="BEH-1", to_id="CAP-1"),
                Relationship(type=RelationType.REALIZES, from_id="BEH-2", to_id="CAP-2"),
                Relationship(type=RelationType.REALIZES, from_id="BEH-3", to_id="CAP-3"),
                Relationship(type=RelationType.REALIZES, from_id="BEH-4", to_id="CAP-4"),
            ]
        )
        result = build_capability_hierarchy(model)
        contains = [r for r in result.relationships if r.type == RelationType.CONTAINS]
        assert len(contains) == 2
        parent_ids = {r.from_id for r in contains}
        child_ids = {r.to_id for r in contains}
        assert "CAP-1" in parent_ids
        assert "CAP-2" in child_ids
        assert "CAP-3" in child_ids

    def test_flat_urls_no_hierarchy(self):
        """All same-depth paths produce no hierarchy."""
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(
                behaviors=[
                    Behavior(id="BEH-1", name="A", status="ACTIVE", trigger="GET /users"),
                    Behavior(id="BEH-2", name="B", status="ACTIVE", trigger="GET /orders"),
                ],
                capabilities=[
                    Capability(id="CAP-1", name="Users", status="ACTIVE"),
                    Capability(id="CAP-2", name="Orders", status="ACTIVE"),
                ],
            ),
            relationships=[
                Relationship(type=RelationType.REALIZES, from_id="BEH-1", to_id="CAP-1"),
                Relationship(type=RelationType.REALIZES, from_id="BEH-2", to_id="CAP-2"),
            ]
        )
        result = build_capability_hierarchy(model)
        contains = [r for r in result.relationships if r.type == RelationType.CONTAINS]
        assert len(contains) == 0

    def test_no_capabilities_returns_unchanged(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(capabilities=[]),
            relationships=[]
        )
        result = build_capability_hierarchy(model)
        assert result == model

    def test_preserves_existing_relationships(self):
        """Existing relationships are not removed."""
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(
                behaviors=[
                    Behavior(id="BEH-1", name="A", status="ACTIVE", trigger="GET /x"),
                ],
                capabilities=[
                    Capability(id="CAP-1", name="X", status="ACTIVE"),
                    Capability(id="CAP-2", name="Y", status="ACTIVE"),
                ],
            ),
            relationships=[
                Relationship(type=RelationType.REALIZES, from_id="BEH-1", to_id="CAP-1"),
                Relationship(type=RelationType.DEPENDS_ON, from_id="COMP-1", to_id="COMP-2"),
            ]
        )
        result = build_capability_hierarchy(model)
        assert len(result.relationships) >= 2
