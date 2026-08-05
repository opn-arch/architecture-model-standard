"""Tests for system design document generator."""

import pytest
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Component, Relationship, RelationType, Behavior,
)
from architecture_model.docs.system_design import generate_system_design


def _make_model(components=None, relationships=None, behaviors=None, layers=None):
    return ArchitectureModel(
        meta=ModelMeta(project="test-project", schema_version="1.3"),
        entities=Entities(
            components=components or [],
            behaviors=behaviors or [],
            layers=layers or [],
        ),
        relationships=relationships or [],
    )


class TestSystemDesign:
    def test_with_components(self):
        """Model with components → generates inventory table."""
        comp1 = Component(id="COMP-1", name="Core", status="ACTIVE", files=["a.py", "b.py"])
        comp2 = Component(id="COMP-2", name="API", status="ACTIVE", files=["c.py"])
        model = _make_model(components=[comp1, comp2])

        result = generate_system_design(model)

        assert "# System Design: test-project" in result
        assert "## Component Inventory" in result
        assert "| COMP-1 | Core | ACTIVE | 2 |" in result
        assert "| COMP-2 | API | ACTIVE | 1 |" in result

    def test_with_relationships_and_mermaid(self):
        """Model with depends-on → generates Mermaid diagram."""
        comp1 = Component(id="COMP-1", name="Core", status="ACTIVE")
        comp2 = Component(id="COMP-2", name="API", status="ACTIVE")
        rels = [Relationship(from_id="COMP-1", to_id="COMP-2", type=RelationType.DEPENDS_ON)]
        model = _make_model(components=[comp1, comp2], relationships=rels)

        result = generate_system_design(model)

        assert "## Relationship Summary" in result
        assert "depends-on" in result
        assert "```mermaid" in result
        assert "COMP-1[Core] --> COMP-2[API]" in result

    def test_empty_model(self):
        """Empty model → still valid markdown."""
        model = _make_model()

        result = generate_system_design(model)

        assert "# System Design: test-project" in result
        assert "## Architecture Overview" in result
        assert "No components found." in result
