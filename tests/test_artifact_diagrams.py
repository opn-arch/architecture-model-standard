"""Tests for PlantUML diagram generation from architecture models."""

import pytest

from architecture_model.core.types import (
    ArchitectureModel,
    ModelMeta,
    Entities,
    Component,
    Interface,
    Capability,
    Behavior,
    Layer,
    Relationship,
    Actor,
    Constraint,
    Status,
    RelationType,
    ComponentKind,
    ActorType,
    BehaviorPattern,
    Strength,
)
from architecture_model.artifacts.diagrams import (
    generate_component_diagram,
    generate_dependency_diagram,
    generate_sequence_diagram,
    generate_all_diagrams,
    _sanitize_id,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_model(**kwargs) -> ArchitectureModel:
    entities = Entities(
        components=kwargs.get("components", []),
        interfaces=kwargs.get("interfaces", []),
        capabilities=kwargs.get("capabilities", []),
        behaviors=kwargs.get("behaviors", []),
        constraints=kwargs.get("constraints", []),
        layers=kwargs.get("layers", []),
        actors=kwargs.get("actors", []),
    )
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.4", project="test-project"),
        entities=entities,
        relationships=kwargs.get("relationships", []),
    )


def _make_component(id: str, name: str, layer: str = "", technology: str = "", kind: ComponentKind = ComponentKind.MODULE) -> Component:
    return Component(
        id=id,
        name=name,
        status=Status.ACTIVE,
        layer=layer,
        technology=technology,
        kind=kind,
    )


def _make_layer(id: str, name: str, order: int = 0) -> Layer:
    return Layer(id=id, name=name, status=Status.ACTIVE, order=order)


def _make_relationship(from_id: str, to_id: str, type: RelationType) -> Relationship:
    return Relationship(type=type, from_id=from_id, to_id=to_id)


def _make_actor(id: str, name: str, type: ActorType = ActorType.HUMAN) -> Actor:
    return Actor(id=id, name=name, status=Status.ACTIVE, type=type)


def _make_behavior(id: str, name: str, actor: str = "", steps: list[str] | None = None) -> Behavior:
    return Behavior(
        id=id,
        name=name,
        status=Status.ACTIVE,
        actor=actor,
        steps=steps or [],
    )


# ---------------------------------------------------------------------------
# test_sanitize_id
# ---------------------------------------------------------------------------


class TestSanitizeId:
    def test_replaces_hyphens(self):
        assert _sanitize_id("COMP-1") == "COMP_1"

    def test_replaces_dots(self):
        assert _sanitize_id("layer.web") == "layer_web"

    def test_replaces_spaces(self):
        assert _sanitize_id("my component") == "my_component"

    def test_replaces_all_special_chars(self):
        assert _sanitize_id("A-B.C D") == "A_B_C_D"

    def test_no_change_needed(self):
        assert _sanitize_id("simple_id") == "simple_id"


# ---------------------------------------------------------------------------
# test_component_diagram
# ---------------------------------------------------------------------------


class TestComponentDiagram:
    def test_basic(self):
        """Model with 3 components in 2 layers → valid PlantUML with boundaries."""
        layers = [
            _make_layer("web", "Web Layer", order=1),
            _make_layer("data", "Data Layer", order=2),
        ]
        components = [
            _make_component("COMP-1", "Frontend", layer="web", technology="React"),
            _make_component("COMP-2", "API Server", layer="web", technology="FastAPI", kind=ComponentKind.SERVICE),
            _make_component("COMP-3", "Database", layer="data", technology="PostgreSQL", kind=ComponentKind.DATA_STORE),
        ]
        rels = [
            _make_relationship("COMP-1", "COMP-2", RelationType.DEPENDS_ON),
        ]
        model = _make_model(layers=layers, components=components, relationships=rels)
        result = generate_component_diagram(model)

        assert result.startswith("@startuml")
        assert result.endswith("@enduml")
        assert "!include <C4/C4_Component>" in result
        assert "title Component Diagram - test-project" in result
        # Layer boundaries
        assert 'Container_Boundary(web, "Web Layer")' in result
        assert 'Container_Boundary(data, "Data Layer")' in result
        # Components inside boundaries
        assert 'Component(COMP_1, "Frontend", "React", "module")' in result
        assert 'Component(COMP_2, "API Server", "FastAPI", "service")' in result
        assert 'Component(COMP_3, "Database", "PostgreSQL", "data-store")' in result
        # Relationship
        assert 'Rel(COMP_1, COMP_2, "depends-on")' in result

    def test_includes_actors(self):
        """Model with actors → Person/System_Ext elements."""
        actors = [
            _make_actor("ACT-1", "Developer", ActorType.HUMAN),
            _make_actor("ACT-2", "CI System", ActorType.SYSTEM),
            _make_actor("ACT-3", "GitHub API", ActorType.EXTERNAL_SERVICE),
        ]
        components = [_make_component("COMP-1", "App")]
        model = _make_model(actors=actors, components=components)
        result = generate_component_diagram(model)

        assert 'Person(ACT_1, "Developer")' in result
        assert 'System_Ext(ACT_2, "CI System")' in result
        assert 'System_Ext(ACT_3, "GitHub API")' in result

    def test_no_components(self):
        """Empty model → returns minimal valid diagram."""
        model = _make_model()
        result = generate_component_diagram(model)

        assert result.startswith("@startuml")
        assert result.endswith("@enduml")
        assert "title Component Diagram - test-project" in result

    def test_sanitizes_ids(self):
        """Component with 'COMP-1' → uses 'COMP_1' in PlantUML."""
        components = [_make_component("COMP-1", "MyComp")]
        model = _make_model(components=components)
        result = generate_component_diagram(model)

        assert "COMP_1" in result
        # Should not have raw hyphenated ID as a PlantUML identifier
        assert 'Component(COMP-1' not in result

    def test_components_without_layer(self):
        """Components with no layer go outside any boundary."""
        layers = [_make_layer("web", "Web Layer")]
        components = [
            _make_component("COMP-1", "Layered", layer="web"),
            _make_component("COMP-2", "Standalone", layer=""),
        ]
        model = _make_model(layers=layers, components=components)
        result = generate_component_diagram(model)

        # Standalone should appear outside the boundary
        assert 'Container_Boundary(web, "Web Layer")' in result
        assert 'Component(COMP_2, "Standalone"' in result

    def test_filters_relationship_types(self):
        """Only depends-on, exposes, consumes relationships shown."""
        components = [
            _make_component("COMP-1", "A"),
            _make_component("COMP-2", "B"),
        ]
        rels = [
            _make_relationship("COMP-1", "COMP-2", RelationType.DEPENDS_ON),
            _make_relationship("COMP-1", "COMP-2", RelationType.REALIZES),
            _make_relationship("COMP-1", "COMP-2", RelationType.CONTAINS),
        ]
        model = _make_model(components=components, relationships=rels)
        result = generate_component_diagram(model)

        assert 'Rel(COMP_1, COMP_2, "depends-on")' in result
        assert "realizes" not in result
        assert "contains" not in result


# ---------------------------------------------------------------------------
# test_dependency_diagram
# ---------------------------------------------------------------------------


class TestDependencyDiagram:
    def test_basic(self):
        """Model with 3 components and 2 depends-on relationships → correct arrows."""
        components = [
            _make_component("COMP-1", "Frontend"),
            _make_component("COMP-2", "Backend"),
            _make_component("COMP-3", "Database"),
        ]
        rels = [
            _make_relationship("COMP-1", "COMP-2", RelationType.DEPENDS_ON),
            _make_relationship("COMP-2", "COMP-3", RelationType.DEPENDS_ON),
        ]
        model = _make_model(components=components, relationships=rels)
        result = generate_dependency_diagram(model)

        assert result.startswith("@startuml")
        assert result.endswith("@enduml")
        assert "title Dependency Graph - test-project" in result
        assert 'rectangle "Frontend" as COMP_1' in result
        assert 'rectangle "Backend" as COMP_2' in result
        assert 'rectangle "Database" as COMP_3' in result
        assert "COMP_1 --> COMP_2 : depends-on" in result
        assert "COMP_2 --> COMP_3 : depends-on" in result

    def test_no_relationships(self):
        """No relationships → just title, no arrows."""
        components = [
            _make_component("COMP-1", "Lonely"),
        ]
        model = _make_model(components=components)
        result = generate_dependency_diagram(model)

        assert result.startswith("@startuml")
        assert result.endswith("@enduml")
        assert "title Dependency Graph - test-project" in result
        # No rectangles since no component has relationships
        assert "rectangle" not in result
        assert "-->" not in result

    def test_arrow_styles(self):
        """depends-on uses -->, exposes uses ..>, consumes uses <.."""
        components = [
            _make_component("COMP-1", "Service"),
            _make_component("COMP-2", "Client"),
        ]
        interfaces = [
            Interface(id="IF-1", name="API", status=Status.ACTIVE),
        ]
        rels = [
            _make_relationship("COMP-1", "COMP-2", RelationType.DEPENDS_ON),
            _make_relationship("COMP-1", "IF-1", RelationType.EXPOSES),
            _make_relationship("COMP-2", "IF-1", RelationType.CONSUMES),
        ]
        model = _make_model(components=components, interfaces=interfaces, relationships=rels)
        result = generate_dependency_diagram(model)

        assert "COMP_1 --> COMP_2 : depends-on" in result
        assert "COMP_1 ..> IF_1 : exposes" in result
        assert "COMP_2 ..> IF_1 : consumes" in result

    def test_only_includes_connected_entities(self):
        """Only components/interfaces that have at least one relationship are included."""
        components = [
            _make_component("COMP-1", "Connected"),
            _make_component("COMP-2", "Also Connected"),
            _make_component("COMP-3", "Isolated"),
        ]
        rels = [
            _make_relationship("COMP-1", "COMP-2", RelationType.DEPENDS_ON),
        ]
        model = _make_model(components=components, relationships=rels)
        result = generate_dependency_diagram(model)

        assert 'rectangle "Connected" as COMP_1' in result
        assert 'rectangle "Also Connected" as COMP_2' in result
        assert "COMP_3" not in result


# ---------------------------------------------------------------------------
# test_sequence_diagram
# ---------------------------------------------------------------------------


class TestSequenceDiagram:
    def test_with_steps(self):
        """Behavior with 3 steps → sequence with messages."""
        behavior = _make_behavior(
            "BEH-1", "User Login",
            steps=["User submits credentials", "System validates input", "System returns token"],
        )
        components = [
            _make_component("COMP-1", "AuthService"),
        ]
        model = _make_model(components=components, behaviors=[behavior])
        result = generate_sequence_diagram(behavior, model)

        assert result.startswith("@startuml")
        assert result.endswith("@enduml")
        assert "title User Login" in result
        assert 'participant "System" as System' in result
        assert "User submits credentials" in result
        assert "System validates input" in result
        assert "System returns token" in result

    def test_no_steps(self):
        """Behavior without steps → empty string."""
        behavior = _make_behavior("BEH-1", "Empty Behavior", steps=[])
        model = _make_model(behaviors=[behavior])
        result = generate_sequence_diagram(behavior, model)

        assert result == ""

    def test_includes_actor(self):
        """Behavior with .actor → actor participant shown."""
        actors = [_make_actor("ACT-1", "Developer", ActorType.HUMAN)]
        behavior = _make_behavior(
            "BEH-1", "Code Review",
            actor="ACT-1",
            steps=["Developer opens PR", "System runs checks"],
        )
        model = _make_model(actors=actors, behaviors=[behavior])
        result = generate_sequence_diagram(behavior, model)

        assert 'actor "Developer" as ACT_1' in result
        assert "Developer opens PR" in result
        assert "System runs checks" in result

    def test_without_actor(self):
        """Behavior without .actor → no actor participant, uses System."""
        behavior = _make_behavior(
            "BEH-1", "Background Job",
            steps=["Process queue", "Update state"],
        )
        model = _make_model(behaviors=[behavior])
        result = generate_sequence_diagram(behavior, model)

        assert "actor" not in result.split("\n")[2]  # no actor line
        assert 'participant "System" as System' in result


# ---------------------------------------------------------------------------
# test_generate_all_diagrams
# ---------------------------------------------------------------------------


class TestGenerateAllDiagrams:
    def test_full_model(self):
        """Model with components + relationships + behaviors → returns dict with all diagram types."""
        layers = [_make_layer("web", "Web")]
        components = [
            _make_component("COMP-1", "A", layer="web"),
            _make_component("COMP-2", "B", layer="web"),
        ]
        rels = [_make_relationship("COMP-1", "COMP-2", RelationType.DEPENDS_ON)]
        behaviors = [
            _make_behavior("BEH-1", "Flow", steps=["Step 1", "Step 2"]),
        ]
        model = _make_model(
            layers=layers, components=components,
            relationships=rels, behaviors=behaviors,
        )
        result = generate_all_diagrams(model)

        assert "component-diagram" in result
        assert "dependency-graph" in result
        assert "sequence-BEH-1" in result
        # All values are valid PlantUML
        for name, diagram in result.items():
            assert diagram.startswith("@startuml"), f"{name} missing @startuml"
            assert diagram.endswith("@enduml"), f"{name} missing @enduml"

    def test_empty_model(self):
        """Empty model → empty dict."""
        model = _make_model()
        result = generate_all_diagrams(model)

        assert result == {}

    def test_skips_behaviors_without_steps(self):
        """Behaviors without steps don't generate sequence diagrams."""
        components = [
            _make_component("COMP-1", "A"),
            _make_component("COMP-2", "B"),
        ]
        rels = [_make_relationship("COMP-1", "COMP-2", RelationType.DEPENDS_ON)]
        behaviors = [
            _make_behavior("BEH-1", "Has Steps", steps=["Do something"]),
            _make_behavior("BEH-2", "No Steps", steps=[]),
        ]
        model = _make_model(components=components, relationships=rels, behaviors=behaviors)
        result = generate_all_diagrams(model)

        assert "sequence-BEH-1" in result
        assert "sequence-BEH-2" not in result
