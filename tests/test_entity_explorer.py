"""Tests for entity explorer faceted diagrams."""
import pytest
from architecture_model.core.parser import load_model
from architecture_model.core.visualize import generate_entity_explorer
from pathlib import Path

@pytest.fixture
def model():
    return load_model(Path(__file__).parent.parent / ".architecture-model.yaml")

class TestComponentExplorer:
    def test_returns_dict(self, model):
        result = generate_entity_explorer(model, "component", "COMP-1")
        assert isinstance(result, dict)

    def test_has_capabilities_facet(self, model):
        result = generate_entity_explorer(model, "component", "COMP-1")
        # COMP-1 (Core) should realize some capabilities
        if "Capabilities" in result:
            assert "realizes" in result["Capabilities"]

    def test_unknown_entity_returns_empty(self, model):
        result = generate_entity_explorer(model, "component", "COMP-999")
        assert result == {}

class TestCapabilityExplorer:
    def test_returns_dict(self, model):
        result = generate_entity_explorer(model, "capability", "CAP-1")
        assert isinstance(result, dict)

    def test_has_functional_breakdown(self, model):
        result = generate_entity_explorer(model, "capability", "CAP-1")
        assert "Functional Breakdown" in result
        assert "CAP_1_1" in result["Functional Breakdown"]

class TestBehaviorExplorer:
    def test_returns_dict(self, model):
        # Find a behavior that exists
        result = generate_entity_explorer(model, "behavior", "BEH-P1")
        assert isinstance(result, dict)

class TestLayerExplorer:
    def test_returns_dict(self, model):
        result = generate_entity_explorer(model, "layer", "LAY-1")
        assert isinstance(result, dict)

    def test_has_components_facet(self, model):
        result = generate_entity_explorer(model, "layer", "LAY-1")
        assert "Components" in result


class TestSystemExplorer:
    def test_returns_dict(self, model):
        result = generate_entity_explorer(model, "system", "SYS-1")
        assert isinstance(result, dict)

    def test_has_component_graph_facet(self, model):
        result = generate_entity_explorer(model, "system", "SYS-1")
        assert "Component Graph" in result

    def test_component_graph_contains_components(self, model):
        result = generate_entity_explorer(model, "system", "SYS-1")
        diagram = result.get("Component Graph", "")
        # SYS-1 should contain at least one component node
        assert "COMP" in diagram

    def test_unknown_system_returns_empty(self, model):
        result = generate_entity_explorer(model, "system", "SYS-999")
        assert result == {}


class TestRequirementExplorer:
    def test_returns_dict(self, model):
        # Find a requirement that exists
        req_ids = [r.id for r in model.entities.requirements]
        if req_ids:
            result = generate_entity_explorer(model, "requirement", req_ids[0])
            assert isinstance(result, dict)

    def test_allocation_map_when_relationships_exist(self):
        """Requirement with satisfies relationship should show Allocation Map."""
        from architecture_model.core.types import (
            ArchitectureModel, ModelMeta, Entities, Relationship, RelationType,
            Component, Requirement, Status,
        )
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.0", project="test"),
            entities=Entities(
                components=[Component(id="COMP-1", name="Parser", status=Status.ACTIVE)],
                requirements=[Requirement(id="REQ-1", name="Must parse", status=Status.ACTIVE)],
            ),
            relationships=[
                Relationship(type=RelationType.SATISFIES, from_id="COMP-1", to_id="REQ-1"),
            ],
        )
        result = generate_entity_explorer(model, "requirement", "REQ-1")
        assert "Allocation Map" in result
        assert "Parser" in result["Allocation Map"]


class TestConstraintExplorer:
    def test_returns_dict(self, model):
        con_ids = [c.id for c in model.entities.constraints]
        if con_ids:
            result = generate_entity_explorer(model, "constraint", con_ids[0])
            assert isinstance(result, dict)

    def test_impact_map_when_relationships_exist(self):
        """Constraint with constrained-by relationship should show Impact Map."""
        from architecture_model.core.types import (
            ArchitectureModel, ModelMeta, Entities, Relationship, RelationType,
            Component, Constraint, Status,
        )
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.0", project="test"),
            entities=Entities(
                components=[Component(id="COMP-1", name="Parser", status=Status.ACTIVE)],
                constraints=[Constraint(id="CON-1", name="Max 100ms", status=Status.ACTIVE)],
            ),
            relationships=[
                Relationship(type=RelationType.CONSTRAINED_BY, from_id="COMP-1", to_id="CON-1"),
            ],
        )
        result = generate_entity_explorer(model, "constraint", "CON-1")
        assert "Impact Map" in result
        assert "Parser" in result["Impact Map"]
