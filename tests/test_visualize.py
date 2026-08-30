"""Tests for Mermaid diagram generation."""

import pytest

from architecture_model.core.types import (
    Actor,
    ActorType,
    ArchitectureModel,
    Behavior,
    Capability,
    Component,
    ComponentKind,
    Entities,
    Interface,
    InterfaceType,
    Layer,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
)
from architecture_model.core.visualize import (
    generate_all_diagrams,
    generate_behaviors_diagram,
    generate_components_diagram,
    generate_context_diagram,
    generate_dependencies_diagram,
)


def _make_model():
    """Minimal model with actors, components, interfaces."""
    return ArchitectureModel(
        meta=ModelMeta(project="test-system", schema_version="2.0"),
        entities=Entities(
            actors=[
                Actor(id="ACT-1", name="User", status=Status.ACTIVE, type=ActorType.HUMAN),
                Actor(
                    id="ACT-2", name="External API", status=Status.ACTIVE, type=ActorType.SYSTEM
                ),
            ],
            capabilities=[
                Capability(
                    id="CAP-1", name="Data Processing", status=Status.ACTIVE, source_block="S1"
                ),
            ],
            components=[
                Component(
                    id="COMP-1",
                    name="Processor",
                    status=Status.ACTIVE,
                    kind=ComponentKind.SERVICE,
                    source_block="S1",
                ),
                Component(
                    id="COMP-2",
                    name="Gateway",
                    status=Status.ACTIVE,
                    kind=ComponentKind.SERVICE,
                    source_block="S1",
                ),
            ],
            behaviors=[
                Behavior(id="BEH-1", name="Process Data", status=Status.ACTIVE),
                Behavior(id="BEH-2", name="Validate Input", status=Status.ACTIVE),
            ],
            interfaces=[
                Interface(id="IFC-1", name="REST API", status=Status.ACTIVE, type=InterfaceType.REST),
            ],
            constraints=[],
            layers=[
                Layer(id="L-svc", name="Services", status=Status.ACTIVE),
            ],
        ),
        relationships=[
            Relationship(from_id="ACT-1", to_id="IFC-1", type=RelationType.CONSUMES),
            Relationship(from_id="COMP-2", to_id="IFC-1", type=RelationType.EXPOSES),
            Relationship(from_id="COMP-1", to_id="CAP-1", type=RelationType.REALIZES),
            Relationship(from_id="COMP-1", to_id="COMP-2", type=RelationType.DEPENDS_ON),
            Relationship(from_id="L-svc", to_id="COMP-1", type=RelationType.CONTAINS),
            Relationship(from_id="L-svc", to_id="COMP-2", type=RelationType.CONTAINS),
            Relationship(from_id="BEH-1", to_id="BEH-2", type=RelationType.TRIGGERS),
            Relationship(from_id="COMP-1", to_id="BEH-1", type=RelationType.TRACES_TO),
        ],
    )


class TestContextDiagram:
    def test_structure(self):
        diagram = generate_context_diagram(_make_model())
        assert diagram.startswith("flowchart TB")
        assert "User" in diagram
        assert "External API" in diagram
        assert "consumes" in diagram

    def test_system_boundary(self):
        diagram = generate_context_diagram(_make_model())
        assert "subgraph system" in diagram
        assert "REST API" in diagram

    def test_person_actor_shape(self):
        diagram = generate_context_diagram(_make_model())
        # Human actors now use standardized stadium shape
        assert "ACT_1([" in diagram

    def test_no_interfaces_fallback(self):
        model = _make_model()
        model.entities.interfaces = []
        diagram = generate_context_diagram(model)
        assert "sys_core" in diagram


class TestComponentsDiagram:
    def test_structure(self):
        diagram = generate_components_diagram(_make_model())
        assert diagram.startswith("flowchart TB")
        assert "Processor" in diagram
        assert "Gateway" in diagram

    def test_layer_grouping(self):
        diagram = generate_components_diagram(_make_model())
        assert "subgraph L_svc" in diagram
        assert "Services" in diagram

    def test_realizes_edges(self):
        diagram = generate_components_diagram(_make_model())
        assert "realizes" in diagram
        assert "COMP_1" in diagram
        assert "CAP_1" in diagram


class TestBehaviorsDiagram:
    def test_structure(self):
        diagram = generate_behaviors_diagram(_make_model())
        assert diagram.startswith("flowchart LR")
        assert "Process Data" in diagram
        assert "Validate Input" in diagram

    def test_triggers_edge(self):
        diagram = generate_behaviors_diagram(_make_model())
        assert "triggers" in diagram

    def test_traces_to(self):
        diagram = generate_behaviors_diagram(_make_model())
        assert "traces-to" in diagram
        assert "Processor" in diagram


class TestDependenciesDiagram:
    def test_structure(self):
        diagram = generate_dependencies_diagram(_make_model())
        assert diagram.startswith("flowchart LR")
        assert "Processor" in diagram
        assert "Gateway" in diagram

    def test_depends_on_edge(self):
        diagram = generate_dependencies_diagram(_make_model())
        assert "depends-on" in diagram

    def test_source_block_grouping(self):
        diagram = generate_dependencies_diagram(_make_model())
        assert "Data Processing" in diagram  # S1 capability name as label


class TestGenerateAll:
    def test_writes_all_files(self, tmp_path):
        model = _make_model()
        paths = generate_all_diagrams(model, tmp_path)
        assert (tmp_path / "context.mmd").exists()
        assert (tmp_path / "components.mmd").exists()
        assert (tmp_path / "behaviors.mmd").exists()
        assert (tmp_path / "dependencies.mmd").exists()
        assert len(paths) == 4

    def test_creates_output_dir(self, tmp_path):
        model = _make_model()
        out = tmp_path / "nested" / "dir"
        generate_all_diagrams(model, out)
        assert out.exists()
        assert (out / "context.mmd").exists()
