"""Tests for rich component spec generator."""

import pytest
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Component, Relationship, RelationType, Behavior,
)
from architecture_model.docs.component_spec import generate_component_spec


def _make_model(components=None, relationships=None, behaviors=None):
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(components=components or [], behaviors=behaviors or []),
        relationships=relationships or [],
    )


class TestRichComponentSpec:
    def test_full_component(self):
        """Component with all fields → output contains all sections."""
        comp = Component(
            id="COMP-1", name="Core", status="ACTIVE",
            description="The core module",
            files=["src/core.py", "src/util.py"],
            responsibilities=["Handle requests", "Manage state"],
            pattern="Repository",
            confidence=0.95,
        )
        beh = Behavior(id="BEH-1", name="ProcessRequest", status="ACTIVE")
        rels = [
            Relationship(from_id="COMP-1", to_id="COMP-2", type=RelationType.DEPENDS_ON, description="uses API"),
            Relationship(from_id="COMP-2", to_id="COMP-1", type=RelationType.DEPENDS_ON, description="callback"),
            Relationship(from_id="COMP-1", to_id="BEH-1", type=RelationType.REALIZES),
        ]
        comp2 = Component(id="COMP-2", name="API", status="ACTIVE")
        model = _make_model(components=[comp, comp2], relationships=rels, behaviors=[beh])

        result = generate_component_spec(comp, model)

        assert "# Component: Core (COMP-1)" in result
        assert "**Status:** ACTIVE" in result
        assert "**Description:** The core module" in result
        assert "## Files" in result
        assert "`src/core.py`" in result
        assert "## Responsibilities" in result
        assert "- Handle requests" in result
        assert "## Relationships" in result
        assert "Dependencies (outgoing)" in result
        assert "Dependents (incoming)" in result
        assert "## Behaviors Realized" in result
        assert "ProcessRequest" in result
        assert "## Patterns" in result
        assert "Repository" in result
        assert "## Confidence" in result
        assert "95%" in result

    def test_minimal_component(self):
        """Minimal component → output still valid markdown with placeholders."""
        comp = Component(id="COMP-1", name="Minimal", status="ACTIVE")
        model = _make_model(components=[comp])

        result = generate_component_spec(comp, model)

        assert "# Component: Minimal (COMP-1)" in result
        assert "**Description:** —" in result
        assert "## Files" in result
        assert "None" in result  # no files
        assert "## Responsibilities" in result
        assert "## Confidence" in result

    def test_component_with_relationships(self):
        """Component with relationships → tables populated."""
        comp1 = Component(id="COMP-1", name="A", status="ACTIVE")
        comp2 = Component(id="COMP-2", name="B", status="ACTIVE")
        rels = [
            Relationship(from_id="COMP-1", to_id="COMP-2", type=RelationType.DEPENDS_ON),
            Relationship(from_id="COMP-2", to_id="COMP-1", type=RelationType.DEPENDS_ON),
        ]
        model = _make_model(components=[comp1, comp2], relationships=rels)

        result = generate_component_spec(comp1, model)

        assert "| Target | Type | Description |" in result
        assert "| Source | Type | Description |" in result
        assert "COMP-2 (B)" in result
        assert "depends-on" in result

    def test_multiple_components(self):
        """Each component gets a complete spec."""
        comp1 = Component(id="COMP-1", name="A", status="ACTIVE", files=["a.py"])
        comp2 = Component(id="COMP-2", name="B", status="ACTIVE", files=["b.py"])
        model = _make_model(components=[comp1, comp2])

        r1 = generate_component_spec(comp1, model)
        r2 = generate_component_spec(comp2, model)

        assert "Component: A (COMP-1)" in r1
        assert "Component: B (COMP-2)" in r2
        assert "`a.py`" in r1
        assert "`b.py`" in r2
