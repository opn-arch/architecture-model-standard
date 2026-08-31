"""Tests for v3 viewer features: new diagram generators, click injection, property cards."""

import pytest
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Relationship, RelationType,
    Component, Capability, Actor, Behavior, Interface, Constraint, Layer,
    System, Requirement, Status, ActorType, Priority,
)
from architecture_model.core.visualize import (
    generate_icd_diagram,
    generate_requirements_allocation_diagram,
    generate_system_decomposition_diagram,
    inject_click_handlers,
    build_entity_properties,
    generate_html_viewer,
)


def _make_model():
    """Build a model with all entity types for testing."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="2.0", project="test"),
        entities=Entities(
            actors=[Actor(id="ACT-1", name="Developer", status=Status.ACTIVE, type=ActorType.HUMAN)],
            capabilities=[
                Capability(id="CAP-1", name="Parsing", status=Status.ACTIVE, priority=Priority.HIGH),
                Capability(id="CAP-2", name="Validation", status=Status.ACTIVE),
            ],
            components=[
                Component(id="COMP-1", name="Parser", status=Status.ACTIVE),
                Component(id="COMP-2", name="Validator", status=Status.ACTIVE),
                Component(id="COMP-3", name="CLI", status=Status.ACTIVE),
            ],
            behaviors=[Behavior(id="BEH-1", name="Parse File", status=Status.ACTIVE)],
            interfaces=[
                Interface(id="IF-1", name="Parse API", status=Status.ACTIVE),
                Interface(id="IF-2", name="Validate API", status=Status.ACTIVE),
            ],
            constraints=[Constraint(id="CON-1", name="Max 100ms", status=Status.ACTIVE)],
            layers=[Layer(id="LAY-1", name="Core", status=Status.ACTIVE)],
            systems=[
                System(id="SYS-1", name="Core System", status=Status.ACTIVE, component_ids=["COMP-1", "COMP-2"]),
            ],
            requirements=[
                Requirement(id="REQ-1", name="Must parse YAML", status=Status.ACTIVE, priority="must"),
            ],
        ),
        relationships=[
            Relationship(type=RelationType.EXPOSES, from_id="COMP-1", to_id="IF-1"),
            Relationship(type=RelationType.EXPOSES, from_id="COMP-2", to_id="IF-2"),
            Relationship(type=RelationType.CONSUMES, from_id="ACT-1", to_id="IF-1"),
            Relationship(type=RelationType.SATISFIES, from_id="COMP-1", to_id="REQ-1"),
            Relationship(type=RelationType.CONSTRAINED_BY, from_id="COMP-1", to_id="CON-1"),
            Relationship(type=RelationType.DEPENDS_ON, from_id="COMP-2", to_id="COMP-1"),
            Relationship(type=RelationType.REALIZES, from_id="COMP-1", to_id="CAP-1"),
        ],
    )


class TestICDDiagram:
    def test_returns_mermaid(self):
        result = generate_icd_diagram(_make_model())
        assert result.startswith("flowchart LR")

    def test_contains_interfaces(self):
        result = generate_icd_diagram(_make_model())
        assert "Parse API" in result
        assert "Validate API" in result

    def test_contains_consumer_edges(self):
        result = generate_icd_diagram(_make_model())
        assert "consumes" in result

    def test_groups_by_provider(self):
        result = generate_icd_diagram(_make_model())
        # COMP-1 exposes IF-1, so Parser should be a subgraph label
        assert "Parser" in result


class TestRequirementsAllocationDiagram:
    def test_returns_mermaid(self):
        result = generate_requirements_allocation_diagram(_make_model())
        assert result.startswith("flowchart LR")

    def test_contains_requirements(self):
        result = generate_requirements_allocation_diagram(_make_model())
        assert "Must parse YAML" in result

    def test_contains_satisfies_edges(self):
        result = generate_requirements_allocation_diagram(_make_model())
        assert "satisfies" in result

    def test_contains_constrained_by_edges(self):
        result = generate_requirements_allocation_diagram(_make_model())
        assert "constrained-by" in result

    def test_empty_model_shows_placeholder(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.0", project="test"),
            entities=Entities(),
            relationships=[],
        )
        result = generate_requirements_allocation_diagram(model)
        assert "No requirements" in result


class TestSystemDecompositionDiagram:
    def test_returns_mermaid(self):
        result = generate_system_decomposition_diagram(_make_model())
        assert result.startswith("flowchart TB")

    def test_contains_systems(self):
        result = generate_system_decomposition_diagram(_make_model())
        assert "Core System" in result

    def test_contains_components_in_system(self):
        result = generate_system_decomposition_diagram(_make_model())
        assert "Parser" in result
        assert "Validator" in result

    def test_unassigned_components_shown(self):
        result = generate_system_decomposition_diagram(_make_model())
        # COMP-3 (CLI) is not in any system
        assert "CLI" in result


class TestClickInjection:
    def test_injects_click_for_known_ids(self):
        mermaid = "flowchart LR\n    COMP_1[Parser]\n    classDef cls_comp fill:#27AE60"
        result = inject_click_handlers(mermaid, {"COMP-1"})
        assert 'click COMP_1 call showEntity()' in result

    def test_preserves_classdefs(self):
        mermaid = "flowchart LR\n    COMP_1[Parser]\n    classDef cls_comp fill:#27AE60"
        result = inject_click_handlers(mermaid, {"COMP-1"})
        assert "classDef cls_comp" in result

    def test_removes_existing_click_directives(self):
        mermaid = 'flowchart LR\n    COMP_1[Parser]\n    click COMP_1 "old.mmd"'
        result = inject_click_handlers(mermaid, {"COMP-1"})
        assert "old.mmd" not in result
        assert 'click COMP_1 call showEntity()' in result

    def test_ignores_unknown_ids(self):
        mermaid = "flowchart LR\n    COMP_1[Parser]"
        result = inject_click_handlers(mermaid, {"OTHER-1"})
        assert "showEntity" not in result

    def test_handles_empty_diagram(self):
        result = inject_click_handlers("flowchart LR", {"COMP-1"})
        assert "flowchart LR" in result


class TestBuildEntityProperties:
    def test_returns_all_entities(self):
        props = build_entity_properties(_make_model())
        assert "COMP-1" in props
        assert "CAP-1" in props
        assert "ACT-1" in props
        assert "SYS-1" in props
        assert "REQ-1" in props

    def test_component_properties(self):
        props = build_entity_properties(_make_model())
        p = props["COMP-1"]
        assert p["type"] == "component"
        assert p["name"] == "Parser"

    def test_actor_has_type_field(self):
        props = build_entity_properties(_make_model())
        p = props["ACT-1"]
        assert p["properties"]["Actor Type"]

    def test_capability_has_priority(self):
        props = build_entity_properties(_make_model())
        p = props["CAP-1"]
        assert "Priority" in p["properties"]

    def test_requirement_has_priority(self):
        props = build_entity_properties(_make_model())
        p = props["REQ-1"]
        assert p["properties"]["Priority"] == "must"


class TestSystemChildResolution:
    """Test that system decomposition resolves child components when parent ID is missing."""

    def test_resolves_children_when_parent_missing(self):
        """SYS-1 references COMP-1 which doesn't exist, but COMP-1.1 and COMP-1.2 do."""
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.0", project="test"),
            entities=Entities(
                systems=[System(id="SYS-1", name="Core", status=Status.ACTIVE,
                               component_ids=["COMP-1"])],
                components=[
                    Component(id="COMP-1.1", name="Parser", status=Status.ACTIVE),
                    Component(id="COMP-1.2", name="Validator", status=Status.ACTIVE),
                    Component(id="COMP-2", name="CLI", status=Status.ACTIVE),
                ],
            ),
            relationships=[],
        )
        result = generate_system_decomposition_diagram(model)
        # COMP-1 doesn't exist, but its children should be in the system subgraph
        assert "Parser" in result
        assert "Validator" in result
        # COMP-2 is unassigned
        assert "CLI" in result
        assert "Core" in result


class TestHtmlViewerModuleData:
    """Test that viewer includes module data when repo_path is provided."""

    def test_viewer_includes_showModule(self, tmp_path):
        html = generate_html_viewer(_make_model(), tmp_path / "v.html").read_text()
        assert "showModule" in html

    def test_viewer_includes_sid_map(self, tmp_path):
        html = generate_html_viewer(_make_model(), tmp_path / "v.html").read_text()
        assert "sid_map" in html

    def test_viewer_includes_comp_files(self, tmp_path):
        html = generate_html_viewer(_make_model(), tmp_path / "v.html").read_text()
        assert "comp_files" in html

    def test_callback_syntax(self, tmp_path):
        html = generate_html_viewer(_make_model(), tmp_path / "v.html").read_text()
        assert 'callback' in html
