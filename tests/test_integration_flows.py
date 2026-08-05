"""Tests for integration flow generator."""

import pytest
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Component, Relationship, RelationType,
)
from architecture_model.docs.integration_flows import generate_integration_flows


def _make_model(components=None, relationships=None):
    return ArchitectureModel(
        meta=ModelMeta(project="test-project", schema_version="1.3"),
        entities=Entities(components=components or []),
        relationships=relationships or [],
    )


class TestIntegrationFlows:
    def test_cross_component_deps(self):
        """Model with cross-component deps → sections generated."""
        comp1 = Component(id="COMP-1", name="Core", status="ACTIVE")
        comp2 = Component(id="COMP-2", name="API", status="ACTIVE")
        rels = [
            Relationship(from_id="COMP-1", to_id="COMP-2", type=RelationType.DEPENDS_ON, description="calls API"),
        ]
        model = _make_model(components=[comp1, comp2], relationships=rels)

        result = generate_integration_flows(model)

        assert "# Integration Flows: test-project" in result
        assert "```mermaid" in result
        assert "## Core → API (depends-on)" in result
        assert "calls API" in result
        assert "**Source:** COMP-1 (Core)" in result
        assert "**Target:** COMP-2 (API)" in result

    def test_no_relationships(self):
        """No relationships → minimal output."""
        model = _make_model(components=[Component(id="COMP-1", name="Solo", status="ACTIVE")])

        result = generate_integration_flows(model)

        assert "No cross-component integration flows detected." in result

    def test_multiple_relationship_types(self):
        """Multiple relationship types → each represented."""
        comp1 = Component(id="COMP-1", name="A", status="ACTIVE")
        comp2 = Component(id="COMP-2", name="B", status="ACTIVE")
        rels = [
            Relationship(from_id="COMP-1", to_id="COMP-2", type=RelationType.DEPENDS_ON),
            Relationship(from_id="COMP-2", to_id="COMP-1", type=RelationType.TRIGGERS),
        ]
        model = _make_model(components=[comp1, comp2], relationships=rels)

        result = generate_integration_flows(model)

        assert "depends-on" in result
        assert "triggers" in result
        assert "## A → B" in result
        assert "## B → A" in result
