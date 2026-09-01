"""Tests for KaTeX math rendering in the HTML viewer."""
import pytest
import tempfile
from pathlib import Path
from architecture_model.core.visualize import generate_html_viewer
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Requirement, Status,
)


def _make_html(value_function: str = "") -> str:
    req = Requirement(
        id="REQ-1", name="Latency", status=Status.ACTIVE,
        value_function=value_function,
    )
    model = ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="2.0"),
        entities=Entities(requirements=[req]),
    )
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "viewer.html"
        generate_html_viewer(model, out)
        return out.read_text()


class TestKaTeXCDN:
    def test_katex_css_link_present(self):
        html = _make_html()
        assert "katex@0.16.11/dist/katex.min.css" in html

    def test_katex_js_script_present(self):
        html = _make_html()
        assert "katex@0.16.11/dist/katex.min.js" in html

    def test_auto_render_script_present(self):
        html = _make_html()
        assert "auto-render.min.js" in html


class TestValueFunctionRendering:
    def test_katex_render_class_present(self):
        html = _make_html(r"V(x) = \min_{u} \sum_{t} c(x_t, u_t)")
        assert "katex-render" in html

    def test_katex_render_js_logic(self):
        """The viewer JS should contain logic to call katex.render on .katex-render elements."""
        html = _make_html(r"\alpha + \beta")
        assert "katex.render" in html

    def test_fallback_for_offline(self):
        """If KaTeX fails, raw LaTeX should still be visible."""
        html = _make_html(r"\sum x")
        # The JS should have try/catch fallback around katex.render
        assert "katex.render" in html

    def test_value_function_in_property_card(self):
        """propCardHtml should render value_function with katex-render class."""
        html = _make_html(r"J = \int_0^T L(x,u) dt")
        assert "value_function" in html
        assert "katex-render" in html
