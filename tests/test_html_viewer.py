"""Tests for HTML diagram viewer generation (v2 — SE navigation + entity explorer)."""
import json
import re
from html.parser import HTMLParser
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
        assert "var D =" in html or "DIAGRAM_DATA" in html or "diagramData" in html

    def test_embedded_data_contains_project_namespace(self, tmp_path):
        html = generate_html_viewer(_make_model(), tmp_path / "viewer.html").read_text()

        class DataParser(HTMLParser):
            data = ""
            active = False
            def handle_starttag(self, tag, attrs):
                self.active = tag == "script" and dict(attrs).get("id") == "viewer-data"
            def handle_data(self, value):
                if self.active:
                    self.data += value

        parser = DataParser()
        parser.feed(html)
        data = json.loads(parser.data)

        assert data["meta"]["project"] == "test"

    def test_generated_html_has_no_external_resources(self, tmp_path):
        html = generate_html_viewer(_make_model(), tmp_path / "viewer.html").read_text()

        assert not re.search(r"(?:src|href)=[\"']https?://", html)

    def test_has_use_cases_nav(self, tmp_path):
        html = (generate_html_viewer(_make_model(), tmp_path / "viewer.html")).read_text()
        assert "Use Cases" in html

    def test_has_7_se_views(self, tmp_path):
        html = (generate_html_viewer(_make_model(), tmp_path / "viewer.html")).read_text()
        for view in ["ConOps", "Functional Architecture", "Logical Architecture",
                     "Use Cases", "ICD", "Requirements", "System Decomposition"]:
            assert view in html, f"Missing SE view: {view}"

    def test_has_breadcrumb_support(self, tmp_path):
        html = (generate_html_viewer(_make_model(), tmp_path / "viewer.html")).read_text()
        assert "navHistory" in html
        assert "breadcrumbs" in html
        assert "goBack" in html

    def test_has_property_cards(self, tmp_path):
        html = (generate_html_viewer(_make_model(), tmp_path / "viewer.html")).read_text()
        assert "prop-card" in html or "properties" in html

    def test_has_click_handlers(self, tmp_path):
        html = (generate_html_viewer(_make_model(), tmp_path / "viewer.html")).read_text()
        assert "showEntity" in html
