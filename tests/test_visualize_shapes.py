"""Tests for standardized diagram shapes, edges, CSS, and updated generators."""
import pytest
from architecture_model.core.visualize import (
    shape, edge_style, css_classes, _sid, _label, _apply_class,
    generate_context_diagram, generate_components_diagram,
    generate_behaviors_diagram, generate_dependencies_diagram,
)
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Relationship,
    Actor, Capability, Behavior, Interface, Constraint, Layer, Component,
    ActorType, InterfaceType, ConstraintType,
)


class TestShape:
    def test_component(self):
        assert shape("component", "COMP-1", "Parser") == "COMP_1[Parser]"

    def test_capability(self):
        assert shape("capability", "CAP-F1", "Validation") == "CAP_F1(Validation)"

    def test_behavior(self):
        result = shape("behavior", "BEH-1", "Parse")
        assert "BEH_1" in result
        assert "{{" in result and "}}" in result

    def test_interface(self):
        assert shape("interface", "IF-1", "REST") == "IF_1((REST))"

    def test_module(self):
        assert shape("module", "M1", "parser.py") == "M1[/parser.py/]"

    def test_actor(self):
        assert shape("actor", "ACT-1", "Dev") == "ACT_1([Dev])"

    def test_constraint(self):
        assert shape("constraint", "CON-1", "Perf") == "CON_1{Perf}"

    def test_layer(self):
        assert shape("layer", "LAY-1", "Core") == "LAY_1[(Core)]"

    def test_stage(self):
        assert shape("stage", "S1", "Observe") == "S1[[Observe]]"

    def test_unknown_falls_back_to_rect(self):
        assert shape("unknown", "X1", "Foo") == "X1[Foo]"

    def test_special_chars_escaped(self):
        result = shape("component", "C-1", "My (Component)")
        assert '"' in result


class TestEdgeStyle:
    def test_realizes(self):
        assert edge_style("realizes") == "==>|realizes|"

    def test_depends_on(self):
        assert edge_style("depends-on") == "-->|depends-on|"

    def test_constrained_by(self):
        assert edge_style("constrained-by") == "-.-x|constrained-by|"

    def test_unknown(self):
        assert edge_style("custom") == "-->|custom|"


class TestCssClasses:
    def test_returns_classDef_lines(self):
        lines = css_classes()
        assert any("classDef" in l for l in lines)
        assert any("cls_comp" in l for l in lines)


class TestApplyClass:
    def test_component(self):
        result = _apply_class("COMP-1", "component")
        assert "class COMP_1 cls_comp" in result

    def test_unknown_returns_empty(self):
        assert _apply_class("X1", "unknown") == ""


def _make_model():
    return ArchitectureModel(
        meta=ModelMeta(project="TestProject", schema_version="2.0"),
        entities=Entities(
            actors=[Actor(id="ACT-1", name="Developer", status="ACTIVE", type=ActorType.HUMAN)],
            capabilities=[Capability(id="CAP-F1", name="Parsing", status="ACTIVE")],
            behaviors=[
                Behavior(id="BEH-1", name="Parse File", status="ACTIVE"),
                Behavior(id="BEH-2", name="Validate", status="ACTIVE"),
            ],
            interfaces=[Interface(id="IF-1", name="REST API", status="ACTIVE", type=InterfaceType.REST)],
            constraints=[Constraint(id="CON-1", name="Latency", status="ACTIVE", type=ConstraintType.PERFORMANCE)],
            layers=[Layer(id="LAY-1", name="Core", status="ACTIVE")],
            components=[
                Component(id="COMP-1", name="Parser", status="ACTIVE"),
                Component(id="COMP-2", name="Validator", status="ACTIVE"),
            ],
        ),
        relationships=[
            Relationship(from_id="ACT-1", to_id="IF-1", type="consumes"),
            Relationship(from_id="COMP-1", to_id="IF-1", type="exposes"),
            Relationship(from_id="COMP-1", to_id="CAP-F1", type="realizes"),
            Relationship(from_id="LAY-1", to_id="COMP-1", type="contains"),
            Relationship(from_id="LAY-1", to_id="COMP-2", type="contains"),
            Relationship(from_id="BEH-1", to_id="BEH-2", type="triggers"),
            Relationship(from_id="COMP-1", to_id="COMP-2", type="depends-on"),
        ],
    )


class TestContextStandard:
    def test_actors_use_stadium(self):
        mmd = generate_context_diagram(_make_model())
        assert "([" in mmd

    def test_interfaces_use_circle(self):
        mmd = generate_context_diagram(_make_model())
        assert "((" in mmd

    def test_has_css(self):
        mmd = generate_context_diagram(_make_model())
        assert "classDef" in mmd

    def test_uses_edge_style(self):
        mmd = generate_context_diagram(_make_model())
        assert "-->|consumes|" in mmd


class TestComponentsStandard:
    def test_capabilities_rounded(self):
        mmd = generate_components_diagram(_make_model())
        assert "CAP_F1(" in mmd

    def test_has_css(self):
        mmd = generate_components_diagram(_make_model())
        assert "classDef" in mmd

    def test_realizes_thick_arrow(self):
        mmd = generate_components_diagram(_make_model())
        assert "==>|realizes|" in mmd


class TestBehaviorsStandard:
    def test_behaviors_use_hexagon(self):
        mmd = generate_behaviors_diagram(_make_model())
        assert "{{" in mmd

    def test_has_css(self):
        mmd = generate_behaviors_diagram(_make_model())
        assert "classDef" in mmd


class TestDependenciesStandard:
    def test_has_css(self):
        mmd = generate_dependencies_diagram(_make_model())
        assert "classDef" in mmd

    def test_depends_on_arrow(self):
        mmd = generate_dependencies_diagram(_make_model())
        assert "-->|depends-on|" in mmd
