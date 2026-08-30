"""Tests for HTML diagram viewer generation."""
import pytest
from pathlib import Path
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Component, Capability,
    Behavior, Relationship, Status, RelationType,
)
from architecture_model.core.visualize import generate_html_viewer


def _make_model():
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="2.0"),
        entities=Entities(
            components=[
                Component(id="COMP-1", name="Parser", status=Status.ACTIVE),
                Component(id="COMP-2", name="Validator", status=Status.ACTIVE),
            ],
            capabilities=[Capability(id="CAP-F1", name="Parsing", status=Status.ACTIVE)],
            behaviors=[
                Behavior(id="BEH-1", name="Parse File", status=Status.ACTIVE),
                Behavior(id="BEH-1.1", name="Tokenize", status=Status.ACTIVE),
            ],
        ),
        relationships=[
            Relationship(from_id="COMP-1", to_id="CAP-F1", type=RelationType.REALIZES),
            Relationship(from_id="COMP-1", to_id="BEH-1", type=RelationType.TRACES_TO),
            Relationship(from_id="BEH-1", to_id="BEH-1.1", type=RelationType.CONTAINS),
        ],
    )


class TestHtmlViewer:
    def test_generates_html_file(self, tmp_path):
        path = generate_html_viewer(_make_model(), tmp_path / "diagrams.html")
        assert path.exists()
        assert path.suffix == ".html"

    def test_html_contains_mermaid_script(self, tmp_path):
        path = generate_html_viewer(_make_model(), tmp_path / "diagrams.html")
        html = path.read_text()
        assert "mermaid" in html.lower()

    def test_html_contains_diagram_sections(self, tmp_path):
        path = generate_html_viewer(_make_model(), tmp_path / "diagrams.html")
        html = path.read_text()
        assert 'id="diagram-context"' in html
        assert 'id="diagram-components"' in html
        assert 'id="diagram-component-COMP-1"' in html
        assert 'id="diagram-use-case-BEH-1"' in html

    def test_html_has_sidebar_navigation(self, tmp_path):
        path = generate_html_viewer(_make_model(), tmp_path / "diagrams.html")
        html = path.read_text()
        assert "sidebar" in html
        assert "#diagram-context" in html

    def test_click_directives_converted_to_anchors(self, tmp_path):
        path = generate_html_viewer(_make_model(), tmp_path / "diagrams.html")
        html = path.read_text()
        # Should NOT contain .mmd file references
        assert ".mmd" not in html
        # Should contain anchor references
        assert "#diagram-" in html

    def test_html_is_mobile_responsive(self, tmp_path):
        path = generate_html_viewer(_make_model(), tmp_path / "diagrams.html")
        html = path.read_text()
        assert "viewport" in html
        assert "max-width" in html

    def test_custom_title(self, tmp_path):
        path = generate_html_viewer(_make_model(), tmp_path / "diagrams.html", title="My Project")
        html = path.read_text()
        assert "My Project" in html

    def test_mermaid_security_level_loose(self, tmp_path):
        path = generate_html_viewer(_make_model(), tmp_path / "diagrams.html")
        html = path.read_text()
        assert "loose" in html

    def test_contains_all_diagram_types(self, tmp_path):
        path = generate_html_viewer(_make_model(), tmp_path / "diagrams.html")
        html = path.read_text()
        # Standard diagrams
        for name in ["context", "components", "behaviors", "dependencies",
                     "pipeline-flow", "entity-lifecycle", "data-flow",
                     "constraint-map", "traceability", "decomposition"]:
            assert f'id="diagram-{name}"' in html, f"Missing diagram: {name}"

    def test_back_to_top_button(self, tmp_path):
        path = generate_html_viewer(_make_model(), tmp_path / "diagrams.html")
        html = path.read_text()
        assert "back-top" in html or "scrollTo" in html
