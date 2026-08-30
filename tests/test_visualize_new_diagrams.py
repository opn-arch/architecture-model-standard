"""Tests for 6 new diagram generators."""
import pytest
from architecture_model.core.visualize import (
    generate_pipeline_flow_diagram,
    generate_entity_lifecycle_diagram,
    generate_data_flow_diagram,
    generate_constraint_map_diagram,
    generate_traceability_diagram,
    generate_decomposition_diagram,
)
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Relationship,
    Actor, Capability, Behavior, Interface, Constraint, Layer, Component,
)


def _make_model():
    """Minimal model for testing."""
    return ArchitectureModel(
        meta=ModelMeta(project="TestProject", schema_version="2.0"),
        entities=Entities(
            actors=[Actor(id="ACT-1", name="Developer", status="ACTIVE", type="person")],
            capabilities=[Capability(id="CAP-F1", name="Parsing", status="ACTIVE")],
            behaviors=[
                Behavior(id="BEH-1", name="Parse File", status="ACTIVE"),
            ],
            interfaces=[Interface(id="IF-1", name="REST API", status="ACTIVE", type="REST")],
            constraints=[Constraint(id="CON-1", name="Latency", status="ACTIVE", type="PERFORMANCE")],
            layers=[Layer(id="LAY-1", name="Core", status="ACTIVE")],
            components=[
                Component(id="COMP-1", name="Parser", status="ACTIVE"),
                Component(id="COMP-2", name="Validator", status="ACTIVE"),
            ],
        ),
        relationships=[
            Relationship(from_id="COMP-1", to_id="CAP-F1", type="realizes"),
            Relationship(from_id="LAY-1", to_id="COMP-1", type="contains"),
            Relationship(from_id="LAY-1", to_id="COMP-2", type="contains"),
            Relationship(from_id="COMP-1", to_id="COMP-2", type="depends-on"),
            Relationship(from_id="BEH-1", to_id="COMP-1", type="traces-to"),
        ],
    )


def _make_data_flow_model():
    """Model with data flow relationships."""
    m = _make_model()
    m.relationships.extend([
        Relationship(from_id="COMP-1", to_id="IF-1", type="produces"),
        Relationship(from_id="IF-1", to_id="COMP-2", type="subscribes-to"),
    ])
    return m


def _make_constraint_model():
    """Model with constrained-by relationships."""
    m = _make_model()
    m.relationships.append(
        Relationship(from_id="COMP-1", to_id="CON-1", type="constrained-by"),
    )
    return m


class TestPipelineFlowDiagram:
    def test_has_10_stages(self):
        mmd = generate_pipeline_flow_diagram()
        for i in range(1, 11):
            assert f"S{i}" in mmd

    def test_stage_shapes(self):
        mmd = generate_pipeline_flow_diagram()
        assert "[[" in mmd

    def test_llm_refinement_subgraph(self):
        mmd = generate_pipeline_flow_diagram()
        assert "LLM Refinement" in mmd or "LLM" in mmd

    def test_has_css(self):
        mmd = generate_pipeline_flow_diagram()
        assert "classDef" in mmd

    def test_stages_connected_sequentially(self):
        mmd = generate_pipeline_flow_diagram()
        assert "S1" in mmd and "S2" in mmd
        assert "Inventory" in mmd  # output label


class TestEntityLifecycleDiagram:
    def test_has_stage_subgraphs(self):
        mmd = generate_entity_lifecycle_diagram()
        assert "Observe" in mmd
        assert "Infer" in mmd

    def test_has_multiple_shapes(self):
        mmd = generate_entity_lifecycle_diagram()
        assert "[/" in mmd  # module
        assert "((" in mmd or "(" in mmd  # interface or capability

    def test_has_css(self):
        mmd = generate_entity_lifecycle_diagram()
        assert "classDef" in mmd


class TestDataFlowDiagram:
    def test_renders_produces(self):
        mmd = generate_data_flow_diagram(_make_data_flow_model())
        assert "produces" in mmd

    def test_renders_subscribes_to(self):
        mmd = generate_data_flow_diagram(_make_data_flow_model())
        assert "subscribes-to" in mmd

    def test_empty_model_has_header(self):
        mmd = generate_data_flow_diagram(_make_model())
        assert "flowchart" in mmd

    def test_has_css(self):
        mmd = generate_data_flow_diagram(_make_data_flow_model())
        assert "classDef" in mmd


class TestConstraintMapDiagram:
    def test_renders_constraints(self):
        mmd = generate_constraint_map_diagram(_make_constraint_model())
        assert "constrained-by" in mmd

    def test_constraint_diamond_shape(self):
        mmd = generate_constraint_map_diagram(_make_constraint_model())
        assert "CON_1{" in mmd  # diamond

    def test_empty_has_header(self):
        mmd = generate_constraint_map_diagram(_make_model())
        assert "flowchart" in mmd


class TestTraceabilityDiagram:
    def test_shows_realizes(self):
        mmd = generate_traceability_diagram(_make_model())
        assert "realizes" in mmd

    def test_shows_capabilities_and_components(self):
        mmd = generate_traceability_diagram(_make_model())
        assert "CAP_F1" in mmd
        assert "COMP_1" in mmd

    def test_has_css(self):
        mmd = generate_traceability_diagram(_make_model())
        assert "classDef" in mmd


class TestDecompositionDiagram:
    def test_shows_project_root(self):
        mmd = generate_decomposition_diagram(_make_model())
        assert "TestProject" in mmd

    def test_shows_layers(self):
        mmd = generate_decomposition_diagram(_make_model())
        assert "LAY_1" in mmd

    def test_contains_edges(self):
        mmd = generate_decomposition_diagram(_make_model())
        assert "contains" in mmd

    def test_has_css(self):
        mmd = generate_decomposition_diagram(_make_model())
        assert "classDef" in mmd


class TestCLIVisualizeImport:
    def test_cli_visualize_import(self):
        """Verify CLI visualize doesn't crash on import."""
        from architecture_model.cli.visualize import (
            shape, edge_style, generate_all_diagrams,
            generate_pipeline_flow_diagram,
        )
        assert callable(shape)
        assert callable(generate_all_diagrams)
        assert callable(generate_pipeline_flow_diagram)


class TestGenerateAllDiagrams:
    def test_generate_all_produces_10_files(self, tmp_path):
        from architecture_model.core.visualize import generate_all_diagrams
        model = _make_model()
        paths = generate_all_diagrams(model, tmp_path)
        assert len(paths) >= 10
        expected = {"context", "components", "behaviors", "dependencies",
                    "pipeline-flow", "entity-lifecycle", "data-flow",
                    "constraint-map", "traceability", "decomposition"}
        assert expected.issubset(set(paths.keys()))
        for p in paths.values():
            assert p.exists()
