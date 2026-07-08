"""Tests for the artifact selector module."""

import pytest

from architecture_model.artifacts.selector import (
    ARTIFACT_REGISTRY,
    ArtifactSpec,
    SUBSYSTEM_ARTIFACTS,
    SubsystemInfo,
    get_artifact_spec,
    select_artifacts,
    select_subsystem_artifacts,
    should_decompose,
)
from architecture_model.core.types import (
    ArchitectureModel,
    Behavior,
    BehaviorPattern,
    Capability,
    Component,
    Constraint,
    ConstraintType,
    Entities,
    Interface,
    InterfaceType,
    Layer,
    ModelMeta,
    Priority as EntityPriority,
    Relationship,
    RelationType,
    Status,
    Strength,
)


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


def _make_model(**kwargs) -> ArchitectureModel:
    """Create a minimal model with specified entity lists."""
    entities = Entities(
        components=kwargs.get("components", []),
        interfaces=kwargs.get("interfaces", []),
        capabilities=kwargs.get("capabilities", []),
        behaviors=kwargs.get("behaviors", []),
        constraints=kwargs.get("constraints", []),
        layers=kwargs.get("layers", []),
    )
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.4", project="test-project"),
        entities=entities,
        relationships=kwargs.get("relationships", []),
    )


def _make_component(id: str) -> Component:
    return Component(id=id, name=f"Component {id}", status=Status.ACTIVE)


def _make_interface(id: str) -> Interface:
    return Interface(
        id=id, name=f"Interface {id}", status=Status.ACTIVE, type=InterfaceType.REST
    )


def _make_capability(id: str) -> Capability:
    return Capability(id=id, name=f"Capability {id}", status=Status.ACTIVE)


def _make_behavior(id: str) -> Behavior:
    return Behavior(id=id, name=f"Behavior {id}", status=Status.ACTIVE)


def _make_constraint(id: str) -> Constraint:
    return Constraint(id=id, name=f"Constraint {id}", status=Status.ACTIVE)


def _make_layer(id: str) -> Layer:
    return Layer(id=id, name=f"Layer {id}", status=Status.ACTIVE)


def _make_relationship(from_id: str, to_id: str) -> Relationship:
    return Relationship(
        type=RelationType.DEPENDS_ON, from_id=from_id, to_id=to_id
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSelectArtifactsMinimalModel:
    """Model with only components → selects component-dependent priority-1 artifacts."""

    def test_select_artifacts_minimal_model(self):
        model = _make_model(
            components=[_make_component("C1"), _make_component("C2"), _make_component("C3")]
        )
        result = select_artifacts(model)

        selected_ids = [a.id for a in result]
        assert "system-overview" in selected_ids
        assert "component-catalog" in selected_ids
        # Should NOT include artifacts that need interfaces, capabilities, etc.
        assert "api-reference" not in selected_ids
        assert "capability-map" not in selected_ids
        assert "behavior-flows" not in selected_ids


class TestSelectArtifactsRichModel:
    """Model with all entity types → selects all 12 artifacts when manifest provided."""

    def test_select_artifacts_rich_model(self):
        model = _make_model(
            components=[_make_component("C1")],
            interfaces=[_make_interface("I1")],
            capabilities=[_make_capability("CAP1")],
            behaviors=[_make_behavior("B1")],
            constraints=[_make_constraint("CON1")],
            layers=[_make_layer("L1")],
            relationships=[_make_relationship("C1", "C2")],
        )
        manifest = {
            "test_files": ["tests/test_foo.py"],
            "metrics": {"loc": 1000, "complexity": 5},
        }

        result = select_artifacts(model, manifest=manifest)

        selected_ids = [a.id for a in result]
        assert len(selected_ids) == 12
        # Spot check all categories present
        assert "system-overview" in selected_ids
        assert "api-reference" in selected_ids
        assert "test-strategy" in selected_ids
        assert "metrics-dashboard" in selected_ids
        assert "integration-guide" in selected_ids


class TestSelectArtifactsNoInterfaces:
    """Model without interfaces → excludes interface-dependent artifacts."""

    def test_select_artifacts_no_interfaces(self):
        model = _make_model(
            components=[_make_component("C1")],
            capabilities=[_make_capability("CAP1")],
            layers=[_make_layer("L1")],
            relationships=[_make_relationship("C1", "C2")],
        )
        result = select_artifacts(model)

        selected_ids = [a.id for a in result]
        assert "api-reference" not in selected_ids
        assert "integration-guide" not in selected_ids


class TestSelectArtifactsNoManifest:
    """No manifest → excludes test-strategy and metrics-dashboard."""

    def test_select_artifacts_no_manifest(self):
        model = _make_model(
            components=[_make_component("C1")],
            interfaces=[_make_interface("I1")],
            capabilities=[_make_capability("CAP1")],
            behaviors=[_make_behavior("B1")],
            constraints=[_make_constraint("CON1")],
            layers=[_make_layer("L1")],
            relationships=[_make_relationship("C1", "C2")],
        )
        result = select_artifacts(model, manifest=None)

        selected_ids = [a.id for a in result]
        assert "test-strategy" not in selected_ids
        assert "metrics-dashboard" not in selected_ids
        # But everything else that doesn't need manifest should be included
        assert "system-overview" in selected_ids
        assert "api-reference" in selected_ids


class TestSelectArtifactsSortedByPriority:
    """Results sorted by priority (1 first), then alphabetically by id."""

    def test_select_artifacts_sorted_by_priority(self):
        model = _make_model(
            components=[_make_component("C1")],
            interfaces=[_make_interface("I1")],
            capabilities=[_make_capability("CAP1")],
            behaviors=[_make_behavior("B1")],
            constraints=[_make_constraint("CON1")],
            layers=[_make_layer("L1")],
            relationships=[_make_relationship("C1", "C2")],
        )
        result = select_artifacts(model)

        # Check ordering: all priority-1 before priority-2 before priority-3
        priorities = [a.priority for a in result]
        assert priorities == sorted(priorities)

        # Within same priority, check alphabetical by id
        for priority_group in [1, 2, 3]:
            group_ids = [a.id for a in result if a.priority == priority_group]
            assert group_ids == sorted(group_ids)


class TestGetArtifactSpec:
    """Lookup artifact spec by ID."""

    def test_get_artifact_spec_found(self):
        spec = get_artifact_spec("api-reference")
        assert spec is not None
        assert spec.id == "api-reference"
        assert spec.name == "API Reference"
        assert spec.category == "design"
        assert spec.priority == 1

    def test_get_artifact_spec_not_found(self):
        spec = get_artifact_spec("nonexistent-artifact")
        assert spec is None


class TestDependencyGraphNeedsRelationships:
    """Components but no relationships → no dependency-graph."""

    def test_dependency_graph_needs_relationships(self):
        model = _make_model(
            components=[_make_component("C1"), _make_component("C2")],
            # No relationships
        )
        result = select_artifacts(model)

        selected_ids = [a.id for a in result]
        assert "dependency-graph" not in selected_ids

    def test_dependency_graph_with_relationships(self):
        model = _make_model(
            components=[_make_component("C1"), _make_component("C2")],
            relationships=[_make_relationship("C1", "C2")],
        )
        result = select_artifacts(model)

        selected_ids = [a.id for a in result]
        assert "dependency-graph" in selected_ids


# ---------------------------------------------------------------------------
# Subsystem Decomposition Tests
# ---------------------------------------------------------------------------


class TestShouldDecompose:
    """Tests for the should_decompose heuristic."""

    def test_should_decompose_small_system(self):
        """Model with 3 components → False."""
        model = _make_model(
            components=[_make_component(f"C{i}") for i in range(3)]
        )
        assert should_decompose(model) is False

    def test_should_decompose_many_components(self):
        """Model with 25 components → True."""
        model = _make_model(
            components=[_make_component(f"C{i}") for i in range(25)]
        )
        assert should_decompose(model) is True

    def test_should_decompose_many_fblocks(self):
        """6 components with 6 different f_block values → True."""
        components = []
        for i in range(6):
            c = _make_component(f"C{i}")
            c.f_block = f"F{i}"
            components.append(c)
        model = _make_model(components=components)
        assert should_decompose(model) is True

    def test_should_decompose_many_files(self):
        """Model + manifest with 60 files → True."""
        model = _make_model(components=[_make_component("C1")])
        manifest = {
            "metrics": {"total_files": 60},
        }
        assert should_decompose(model, manifest) is True


class TestSubsystemInfo:
    """Tests for SubsystemInfo dataclass."""

    def test_subsystem_info_creation(self):
        """Can create SubsystemInfo with expected fields."""
        info = SubsystemInfo(
            id="F1",
            name="Core Engine",
            components=["C1", "C2", "C3"],
            file_count=12,
            test_count=5,
        )
        assert info.id == "F1"
        assert info.name == "Core Engine"
        assert info.components == ["C1", "C2", "C3"]
        assert info.file_count == 12
        assert info.test_count == 5

    def test_subsystem_info_defaults(self):
        """file_count and test_count default to 0."""
        info = SubsystemInfo(id="cli", name="CLI", components=["C10"])
        assert info.file_count == 0
        assert info.test_count == 0


class TestSelectSubsystemArtifacts:
    """Tests for select_subsystem_artifacts."""

    def test_select_subsystem_artifacts_basic(self):
        """Subsystem with components → gets component-catalog."""
        model = _make_model(
            components=[_make_component("C1"), _make_component("C2")]
        )
        subsystem = SubsystemInfo(
            id="F1", name="Core", components=["C1", "C2"]
        )
        result = select_subsystem_artifacts(subsystem, model)
        selected_ids = [a.id for a in result]
        assert "component-catalog" in selected_ids

    def test_select_subsystem_artifacts_with_interfaces(self):
        """Subsystem with matching interfaces → gets api-reference."""
        iface = _make_interface("I1")
        iface.provider = "C1"
        model = _make_model(
            components=[_make_component("C1")],
            interfaces=[iface],
        )
        subsystem = SubsystemInfo(
            id="F1", name="Core", components=["C1"]
        )
        result = select_subsystem_artifacts(subsystem, model)
        selected_ids = [a.id for a in result]
        assert "api-reference" in selected_ids

    def test_select_subsystem_artifacts_excludes_system_level(self):
        """Subsystem NEVER gets system-overview, layer-architecture, deployment-view."""
        model = _make_model(
            components=[_make_component("C1")],
            interfaces=[_make_interface("I1")],
            capabilities=[_make_capability("CAP1")],
            behaviors=[_make_behavior("B1")],
            constraints=[_make_constraint("CON1")],
            layers=[_make_layer("L1")],
            relationships=[_make_relationship("C1", "C2")],
        )
        manifest = {
            "test_files": ["tests/test_foo.py"],
            "metrics": {"loc": 1000},
        }
        subsystem = SubsystemInfo(
            id="F1", name="Core", components=["C1"], test_count=5
        )
        result = select_subsystem_artifacts(subsystem, model, manifest)
        selected_ids = [a.id for a in result]
        assert "system-overview" not in selected_ids
        assert "layer-architecture" not in selected_ids
        assert "deployment-view" not in selected_ids

    def test_select_subsystem_artifacts_empty_subsystem(self):
        """Subsystem with 0 components → empty list."""
        model = _make_model(
            components=[_make_component("C1")],
            interfaces=[_make_interface("I1")],
        )
        subsystem = SubsystemInfo(
            id="F1", name="Empty", components=[]
        )
        result = select_subsystem_artifacts(subsystem, model)
        assert result == []
