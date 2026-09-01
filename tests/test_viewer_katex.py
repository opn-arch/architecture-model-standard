"""Tests for offline-safe math rendering in the HTML viewer."""
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


class TestValueFunctionRendering:
    def test_math_expression_class_present(self):
        html = _make_html(r"V(x) = \min_{u} \sum_{t} c(x_t, u_t)")
        assert "math-expression" in html

    def test_does_not_call_unavailable_math_globals(self):
        html = _make_html(r"\alpha + \beta")
        assert "katex.render" not in html
        assert "renderMathInElement" not in html

    def test_raw_expression_is_embedded_for_offline_display(self):
        html = _make_html(r"\sum x")
        assert r"\\sum x" in html

    def test_value_function_in_property_card(self):
        """propCardHtml should render value_function as styled code text."""
        html = _make_html(r"J = \int_0^T L(x,u) dt")
        assert "value_function" in html
        assert "math-expression" in html
