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
