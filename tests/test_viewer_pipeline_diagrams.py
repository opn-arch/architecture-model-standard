"""Tests for behavior sequence and flow diagram generation (Task 3.1 & 3.2)."""

import xml.etree.ElementTree as ET

import pytest

from architecture_model.core.types import (
    ArchitectureModel, Entities, Relationship, ModelMeta,
    Behavior, Component, Step, Status, BehaviorPattern,
)
from architecture_model.core.visualize import (
    generate_behavior_sequence_diagram,
    generate_behavior_flow_diagram,
    build_entity_properties,
    _render_mermaid_svg,
    generate_html_viewer,
)


def _make_model(behaviors=None, components=None, relationships=None):
    """Helper to build a minimal model."""
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="2.0"),
        entities=Entities(
            behaviors=behaviors or [],
            components=components or [],
        ),
        relationships=relationships or [],
    )


# ── Sequence Diagram Tests ──────────────────────────────────────────

class TestGenerateBehaviorSequenceDiagram:
    def test_basic_structured_steps(self):
        """Sequence diagram with structured_steps shows participants and arrows."""
        comp_a = Component(id="COMP-A", name="Auth Service", status=Status.ACTIVE)
        comp_b = Component(id="COMP-B", name="Database", status=Status.ACTIVE)
        beh = Behavior(
            id="BEH-1", name="Login Flow", status=Status.ACTIVE,
            structured_steps=[
                Step(order=1, action="Validate credentials", component_ref="COMP-A"),
                Step(order=2, action="Query user record", component_ref="COMP-B"),
                Step(order=3, action="Return token", component_ref="COMP-A"),
            ],
        )
        model = _make_model(behaviors=[beh], components=[comp_a, comp_b])
        result = generate_behavior_sequence_diagram(model, "BEH-1")

        assert "sequenceDiagram" in result
        assert "Auth Service" in result
        assert "Database" in result
        assert "Validate credentials" in result
        assert "Query user record" in result
        assert "Return token" in result

    def test_self_arrow_for_same_component(self):
        """Consecutive steps on same component produce self-arrows."""
        comp = Component(id="COMP-A", name="Processor", status=Status.ACTIVE)
        beh = Behavior(
            id="BEH-1", name="Process", status=Status.ACTIVE,
            structured_steps=[
                Step(order=1, action="Step one", component_ref="COMP-A"),
                Step(order=2, action="Step two", component_ref="COMP-A"),
            ],
        )
        model = _make_model(behaviors=[beh], components=[comp])
        result = generate_behavior_sequence_diagram(model, "BEH-1")

        assert "sequenceDiagram" in result
        assert "Processor->>Processor" in result

    def test_missing_component_ref_uses_system(self):
        """Steps with empty component_ref use 'System' as participant."""
        beh = Behavior(
            id="BEH-1", name="Boot", status=Status.ACTIVE,
            structured_steps=[
                Step(order=1, action="Initialize", component_ref=""),
                Step(order=2, action="Ready", component_ref=""),
            ],
        )
        model = _make_model(behaviors=[beh])
        result = generate_behavior_sequence_diagram(model, "BEH-1")

        assert "System" in result

    def test_trigger_shown_as_note(self):
        """Behavior trigger appears as a Note."""
        comp = Component(id="COMP-A", name="API", status=Status.ACTIVE)
        beh = Behavior(
            id="BEH-1", name="Request", status=Status.ACTIVE,
            trigger="HTTP POST /login",
            structured_steps=[
                Step(order=1, action="Handle request", component_ref="COMP-A"),
            ],
        )
        model = _make_model(behaviors=[beh], components=[comp])
        result = generate_behavior_sequence_diagram(model, "BEH-1")

        assert "Note" in result
        assert "HTTP POST /login" in result

    def test_actor_step_adds_actor_participant(self):
        """Steps with actor='user' add an Actor participant."""
        comp = Component(id="COMP-A", name="UI", status=Status.ACTIVE)
        beh = Behavior(
            id="BEH-1", name="Submit", status=Status.ACTIVE,
            structured_steps=[
                Step(order=1, action="Click submit", component_ref="COMP-A", actor="user"),
                Step(order=2, action="Process form", component_ref="COMP-A"),
            ],
        )
        model = _make_model(behaviors=[beh], components=[comp])
        result = generate_behavior_sequence_diagram(model, "BEH-1")

        assert "Actor" in result

    def test_no_structured_steps_returns_empty(self):
        """Behavior with no structured_steps returns empty string."""
        beh = Behavior(id="BEH-1", name="Empty", status=Status.ACTIVE)
        model = _make_model(behaviors=[beh])
        result = generate_behavior_sequence_diagram(model, "BEH-1")
        assert result == ""

    def test_nonexistent_behavior_returns_empty(self):
        model = _make_model()
        result = generate_behavior_sequence_diagram(model, "BEH-NOPE")
        assert result == ""


# ── Flow Diagram Tests ──────────────────────────────────────────────

class TestGenerateBehaviorFlowDiagram:
    def test_simple_steps_flowchart(self):
        """Behavior with simple string steps produces a graph TD flowchart."""
        beh = Behavior(
            id="BEH-1", name="Deploy", status=Status.ACTIVE,
            steps=["Build image", "Push to registry", "Deploy to cluster"],
        )
        model = _make_model(behaviors=[beh])
        result = generate_behavior_flow_diagram(model, "BEH-1")

        assert "graph TD" in result
        assert "Build image" in result
        assert "Push to registry" in result
        assert "Deploy to cluster" in result

    def test_sequential_edges(self):
        """Flow diagram has edges between consecutive steps."""
        beh = Behavior(
            id="BEH-1", name="Pipeline", status=Status.ACTIVE,
            steps=["A", "B", "C"],
        )
        model = _make_model(behaviors=[beh])
        result = generate_behavior_flow_diagram(model, "BEH-1")

        # Should have edges: step0 --> step1 and step1 --> step2
        assert "-->" in result

    def test_structured_steps_fallback(self):
        """Flow diagram works with structured_steps too."""
        comp = Component(id="COMP-A", name="Svc", status=Status.ACTIVE)
        beh = Behavior(
            id="BEH-1", name="Flow", status=Status.ACTIVE,
            structured_steps=[
                Step(order=1, action="First", component_ref="COMP-A"),
                Step(order=2, action="Second", component_ref="COMP-A"),
            ],
        )
        model = _make_model(behaviors=[beh], components=[comp])
        result = generate_behavior_flow_diagram(model, "BEH-1")

        assert "graph TD" in result
        assert "First" in result
        assert "Second" in result

    def test_no_steps_returns_empty(self):
        beh = Behavior(id="BEH-1", name="Empty", status=Status.ACTIVE)
        model = _make_model(behaviors=[beh])
        result = generate_behavior_flow_diagram(model, "BEH-1")
        assert result == ""

    def test_nonexistent_behavior_returns_empty(self):
        model = _make_model()
        result = generate_behavior_flow_diagram(model, "BEH-NOPE")
        assert result == ""


# ── Viewer Integration Tests (Task 3.2) ─────────────────────────────

class TestBehaviorDiagramInViewer:
    def test_behavior_diagram_in_properties(self):
        """build_entity_properties includes behavior_diagram for behaviors with steps."""
        comp = Component(id="COMP-A", name="Svc", status=Status.ACTIVE)
        beh = Behavior(
            id="BEH-1", name="Pipeline", status=Status.ACTIVE,
            structured_steps=[
                Step(order=1, action="Parse", component_ref="COMP-A"),
                Step(order=2, action="Validate", component_ref="COMP-A"),
            ],
        )
        model = _make_model(behaviors=[beh], components=[comp])
        props = build_entity_properties(model)

        assert "BEH-1" in props
        assert "behavior_diagram" in props["BEH-1"]["properties"]
        assert "sequenceDiagram" in props["BEH-1"]["properties"]["behavior_diagram"]

    def test_simple_steps_get_flow_diagram(self):
        """Behaviors with only simple steps get a flow diagram."""
        beh = Behavior(
            id="BEH-1", name="Deploy", status=Status.ACTIVE,
            steps=["Build", "Test", "Deploy"],
        )
        model = _make_model(behaviors=[beh])
        props = build_entity_properties(model)

        assert "behavior_diagram" in props["BEH-1"]["properties"]
        assert "graph TD" in props["BEH-1"]["properties"]["behavior_diagram"]

    def test_no_steps_no_diagram(self):
        """Behaviors with no steps don't get a behavior_diagram."""
        beh = Behavior(id="BEH-1", name="Empty", status=Status.ACTIVE)
        model = _make_model(behaviors=[beh])
        props = build_entity_properties(model)

        assert "behavior_diagram" not in props["BEH-1"].get("properties", {})


class TestOfflineSvgRendering:
    def test_flowchart_renders_nodes_and_paths(self):
        svg = _render_mermaid_svg('graph TD\n    step0["Build"]\n    step1["Deploy"]\n    step0 --> step1')

        assert svg.startswith("<svg")
        assert 'class="diagram-node"' in svg
        assert '<path class="diagram-edge"' in svg
        assert "Build" in svg
        assert "Deploy" in svg

    def test_sequence_renders_participants_and_messages(self):
        svg = _render_mermaid_svg(
            "sequenceDiagram\n"
            "    participant API\n"
            "    participant Database\n"
            "    API->>Database: Query user\n"
        )

        assert svg.startswith("<svg")
        assert 'class="sequence-participant"' in svg
        assert '<path class="sequence-message"' in svg
        assert "Query user" in svg

    def test_viewer_embeds_offline_behavior_svg(self, tmp_path):
        behavior = Behavior(
            id="BEH-1", name="Deploy", status=Status.ACTIVE,
            steps=["Build", "Deploy"],
        )
        model = _make_model(behaviors=[behavior])

        html = generate_html_viewer(model, tmp_path / "viewer.html").read_text()

        from html.parser import HTMLParser
        import json

        class DataParser(HTMLParser):
            data = ""
            active = False
            def handle_starttag(self, tag, attrs):
                self.active = tag == "script" and dict(attrs).get("id") == "viewer-data"
            def handle_data(self, data):
                if self.active:
                    self.data += data
            def handle_endtag(self, tag):
                if tag == "script":
                    self.active = False

        parser = DataParser()
        parser.feed(html)
        properties = json.loads(parser.data)["properties"]["BEH-1"]["properties"]
        assert properties["behavior_svg"].startswith("<svg")
        assert "Diagram source (offline mode)" not in html

    def test_overview_topology_preserves_edge_variants_and_subgraphs(self):
        code = '''flowchart LR
            subgraph Core["Core Layer"]
                A["Receive request"] -->|valid| B("Parse payload")
                A -.-> C{Reject request}
            end
            B ==> D[Persist result]
            C --> D
            class A,B service
        '''

        root = ET.fromstring(_render_mermaid_svg(code))
        nodes = root.findall(".//*[@class='diagram-node']")
        edges = root.findall(".//*[@class='diagram-edge']")

        assert len(nodes) == 4
        assert len(edges) == 4
        assert {node.attrib["data-entity-id"] for node in nodes} == {"A", "B", "C", "D"}
        assert len({node.attrib["transform"].split(",")[0] for node in nodes}) > 1

    def test_behavior_flow_topology_preserves_inline_nodes_and_labels(self):
        code = '''graph TD
            start["Start workflow"] --> choose{"Choose a branch"}
            choose -->|fast path| fast["Fast result"]
            choose --> slow["A deliberately long slow-path label that needs wrapping"]
            fast --> done[Done]
            slow --> done
        '''

        root = ET.fromstring(_render_mermaid_svg(code))

        assert len(root.findall(".//*[@class='diagram-node']")) == 5
        assert len(root.findall(".//*[@class='diagram-edge']")) == 5
        assert root.findall(".//{http://www.w3.org/2000/svg}tspan")
