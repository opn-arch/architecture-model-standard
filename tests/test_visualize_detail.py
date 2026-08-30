"""Tests for per-entity detail diagram generators."""
import pytest
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Component, Capability,
    Interface, Behavior, Relationship, Layer, Status, RelationType,
    InterfaceType,
)
from architecture_model.core.visualize import (
    generate_component_detail_diagram,
    generate_use_case_diagram,
)

def _make_model():
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="2.0"),
        entities=Entities(
            components=[
                Component(id="COMP-1", name="Parser", status=Status.ACTIVE,
                          files=["parser.py", "ast_utils.py"]),
                Component(id="COMP-2", name="Validator", status=Status.ACTIVE),
            ],
            capabilities=[Capability(id="CAP-F1", name="Parsing", status=Status.ACTIVE)],
            interfaces=[Interface(id="IF-1", name="Parse API", status=Status.ACTIVE, type=InterfaceType.INTERNAL)],
            behaviors=[
                Behavior(id="BEH-1", name="Parse File", status=Status.ACTIVE),
                Behavior(id="BEH-1.1", name="Tokenize", status=Status.ACTIVE),
                Behavior(id="BEH-1.2", name="Build AST", status=Status.ACTIVE),
            ],
            layers=[Layer(id="LAY-1", name="Core", status=Status.ACTIVE)],
        ),
        relationships=[
            Relationship(from_id="COMP-1", to_id="CAP-F1", type=RelationType.REALIZES),
            Relationship(from_id="COMP-1", to_id="IF-1", type=RelationType.EXPOSES),
            Relationship(from_id="COMP-1", to_id="BEH-1", type=RelationType.TRACES_TO),
            Relationship(from_id="COMP-1", to_id="COMP-2", type=RelationType.DEPENDS_ON),
            Relationship(from_id="LAY-1", to_id="COMP-1", type=RelationType.CONTAINS),
            Relationship(from_id="BEH-1", to_id="BEH-1.1", type=RelationType.CONTAINS),
            Relationship(from_id="BEH-1", to_id="BEH-1.2", type=RelationType.CONTAINS),
        ],
    )

class TestComponentDetailDiagram:
    def test_returns_flowchart(self):
        assert generate_component_detail_diagram(_make_model(), "COMP-1").startswith("flowchart TB")

    def test_shows_component_node(self):
        assert "Parser" in generate_component_detail_diagram(_make_model(), "COMP-1")

    def test_shows_realized_capabilities(self):
        mmd = generate_component_detail_diagram(_make_model(), "COMP-1")
        assert "CAP_F1" in mmd and "Parsing" in mmd

    def test_shows_exposed_interfaces(self):
        mmd = generate_component_detail_diagram(_make_model(), "COMP-1")
        assert "IF_1" in mmd and "Parse API" in mmd

    def test_shows_traced_behaviors(self):
        assert "BEH_1" in generate_component_detail_diagram(_make_model(), "COMP-1")

    def test_shows_dependencies(self):
        mmd = generate_component_detail_diagram(_make_model(), "COMP-1")
        assert "COMP_2" in mmd and "Validator" in mmd

    def test_shows_source_files(self):
        mmd = generate_component_detail_diagram(_make_model(), "COMP-1")
        assert "parser.py" in mmd and "ast_utils.py" in mmd

    def test_shows_containing_layer(self):
        mmd = generate_component_detail_diagram(_make_model(), "COMP-1")
        assert "LAY_1" in mmd or "Core" in mmd

    def test_unknown_component(self):
        mmd = generate_component_detail_diagram(_make_model(), "COMP-999")
        assert "not found" in mmd.lower()

    def test_has_click_directives(self):
        assert "click" in generate_component_detail_diagram(_make_model(), "COMP-1")

class TestUseCaseDiagram:
    def test_returns_flowchart(self):
        assert generate_use_case_diagram(_make_model(), "BEH-1").startswith("flowchart TB")

    def test_shows_behavior_node(self):
        assert "Parse File" in generate_use_case_diagram(_make_model(), "BEH-1")

    def test_shows_sub_behaviors(self):
        mmd = generate_use_case_diagram(_make_model(), "BEH-1")
        assert "Tokenize" in mmd and "Build AST" in mmd

    def test_shows_implementing_component(self):
        assert "Parser" in generate_use_case_diagram(_make_model(), "BEH-1")

    def test_unknown_behavior(self):
        assert "not found" in generate_use_case_diagram(_make_model(), "BEH-999").lower()

    def test_click_on_sub_behaviors(self):
        assert "click" in generate_use_case_diagram(_make_model(), "BEH-1")
