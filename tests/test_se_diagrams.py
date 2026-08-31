"""Tests for SE-quality overview diagrams."""
import pytest
from architecture_model.core.parser import load_model
from pathlib import Path
from architecture_model.core.visualize import (
    generate_conops_diagram,
    generate_functional_architecture_diagram,
    generate_logical_architecture_diagram,
    generate_behavior_overview_diagram,
)

@pytest.fixture
def model():
    return load_model(Path(__file__).parent.parent / ".architecture-model.yaml")

class TestConOpsDiagram:
    def test_returns_mermaid(self, model):
        result = generate_conops_diagram(model)
        assert "graph" in result or "flowchart" in result

    def test_contains_actors(self, model):
        result = generate_conops_diagram(model)
        assert "Developer" in result

    def test_contains_capability_groups(self, model):
        result = generate_conops_diagram(model)
        assert "Understand" in result or "Validate" in result

class TestFunctionalArchitectureDiagram:
    def test_returns_mermaid(self, model):
        result = generate_functional_architecture_diagram(model)
        assert "graph" in result or "flowchart" in result

    def test_contains_root_capability(self, model):
        result = generate_functional_architecture_diagram(model)
        assert "CAP_0" in result

    def test_contains_sub_capabilities(self, model):
        result = generate_functional_architecture_diagram(model)
        # Should have L2 sub-caps like CAP_1_1
        assert "CAP_1_1" in result

class TestLogicalArchitectureDiagram:
    def test_returns_mermaid(self, model):
        result = generate_logical_architecture_diagram(model)
        assert "graph" in result or "flowchart" in result

    def test_contains_systems(self, model):
        result = generate_logical_architecture_diagram(model)
        assert "Model Foundation" in result or "SYS_1" in result

    def test_contains_components(self, model):
        result = generate_logical_architecture_diagram(model)
        assert "Core" in result or "COMP" in result

    def test_unassigned_components_shown(self, model):
        result = generate_logical_architecture_diagram(model)
        # COMP-9 (Configuration) and COMP-12 (Utilities) are not in any system
        assert "Other" in result or "Configuration" in result

class TestConOpsSystems:
    def test_conops_contains_systems(self, model):
        result = generate_conops_diagram(model)
        assert "Model Foundation" in result or "SYS_1" in result

    def test_conops_system_to_capability_edges(self, model):
        result = generate_conops_diagram(model)
        # Systems should connect to capabilities via ==>
        assert "==>" in result

class TestBehaviorOverviewDiagram:
    def test_returns_mermaid(self, model):
        result = generate_behavior_overview_diagram(model)
        assert "graph" in result or "flowchart" in result

    def test_contains_behaviors(self, model):
        result = generate_behavior_overview_diagram(model)
        assert "BEH" in result

    def test_contains_sub_behaviors(self, model):
        result = generate_behavior_overview_diagram(model)
        # Should contain stage-level behaviors (children of top-level)
        assert "BEH_P1_1" in result or "Observe" in result
