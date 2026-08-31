"""Tests for HTML diagram viewer generation (v2 — SE navigation + entity explorer)."""
import pytest
from pathlib import Path
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Component, Capability,
    Behavior, Relationship, Status, RelationType, Layer, Interface, Actor,
)
from architecture_model.core.visualize import generate_html_viewer


def _make_model():
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="2.0"),
        entities=Entities(
            layers=[Layer(id="L-SVC", name="Services", status=Status.ACTIVE)],
            components=[
                Component(id="COMP-1", name="Parser", status=Status.ACTIVE),
                Component(id="COMP-2", name="Validator", status=Status.ACTIVE),
            ],
            capabilities=[Capability(id="CAP-F1", name="Parsing", status=Status.ACTIVE)],
            behaviors=[
                Behavior(id="BEH-1", name="Parse File", status=Status.ACTIVE),
                Behavior(id="BEH-1.1", name="Tokenize", status=Status.ACTIVE),
            ],
            interfaces=[Interface(id="IF-1", name="CLI Input", status=Status.ACTIVE)],
            actors=[Actor(id="ACT-1", name="Developer", status=Status.ACTIVE)],
        ),
        relationships=[
            Relationship(from_id="COMP-1", to_id="CAP-F1", type=RelationType.REALIZES),
            Relationship(from_id="COMP-1", to_id="BEH-1", type=RelationType.TRACES_TO),
            Relationship(from_id="BEH-1", to_id="BEH-1.1", type=RelationType.CONTAINS),
            Relationship(from_id="COMP-1", to_id="IF-1", type=RelationType.EXPOSES),
            Relationship(from_id="ACT-1", to_id="IF-1", type=RelationType.CONSUMES),
        ],
    )


class TestHtmlViewerV2:
    def test_generates_html_file(self, tmp_path):
        path = generate_html_viewer(_make_model(), tmp_path / "viewer.html")
        assert path.exists()
        assert path.suffix == ".html"

    def test_html_viewer_has_se_views(self, tmp_path):
        html = (generate_html_viewer(_make_model(), tmp_path / "viewer.html")).read_text()
        assert "ConOps" in html
        assert "Functional" in html
        assert "Logical" in html

    def test_html_viewer_has_entity_sections(self, tmp_path):
        html = (generate_html_viewer(_make_model(), tmp_path / "viewer.html")).read_text()
        assert "Components" in html
        assert "Capabilities" in html
        assert "Behaviors" in html

    def test_html_viewer_has_mermaid(self, tmp_path):
        html = (generate_html_viewer(_make_model(), tmp_path / "viewer.html")).read_text()
        assert "mermaid" in html.lower()

    def test_html_viewer_is_self_contained(self, tmp_path):
        html = (generate_html_viewer(_make_model(), tmp_path / "viewer.html")).read_text()
        assert "<html" in html
        assert "<style" in html
        assert "<script" in html

    def test_has_sidebar_navigation(self, tmp_path):
        html = (generate_html_viewer(_make_model(), tmp_path / "viewer.html")).read_text()
        assert "sidebar" in html

    def test_mobile_responsive(self, tmp_path):
        html = (generate_html_viewer(_make_model(), tmp_path / "viewer.html")).read_text()
        assert "viewport" in html
        assert "768px" in html

    def test_dark_theme(self, tmp_path):
        html = (generate_html_viewer(_make_model(), tmp_path / "viewer.html")).read_text()
        assert "#1a1a2e" in html

    def test_mermaid_security_level_loose(self, tmp_path):
        html = (generate_html_viewer(_make_model(), tmp_path / "viewer.html")).read_text()
        assert "loose" in html

    def test_custom_title(self, tmp_path):
        html = (generate_html_viewer(_make_model(), tmp_path / "viewer.html", title="My Project")).read_text()
        assert "My Project" in html

    def test_entity_counts_in_nav(self, tmp_path):
        html = (generate_html_viewer(_make_model(), tmp_path / "viewer.html")).read_text()
        # Entity category headers should show counts
        assert "Components (2)" in html
        assert "Behaviors (2)" in html

    def test_embedded_diagram_data(self, tmp_path):
        html = (generate_html_viewer(_make_model(), tmp_path / "viewer.html")).read_text()
        # Diagram data should be embedded as JSON
        assert "diagramData" in html or "DIAGRAM_DATA" in html

    def test_has_use_cases_nav(self, tmp_path):
        html = (generate_html_viewer(_make_model(), tmp_path / "viewer.html")).read_text()
        assert "Use Cases" in html
