import importlib
import pytest

RENDERER_MODULES = [
    "architecture_model.lifecycle.renderers.svg",
    "architecture_model.lifecycle.renderers.markdown",
    "architecture_model.lifecycle.renderers.html",
    "architecture_model.lifecycle.renderers.ai_context",
    "architecture_model.lifecycle.renderers.zip",
]


@pytest.mark.parametrize("mod", RENDERER_MODULES)
def test_renderer_render_is_instrumented(mod):
    m = importlib.import_module(mod)
    fn = getattr(m, "render", None)
    assert fn is not None, f"{mod} missing top-level render()"
    assert getattr(fn, "__sil_instrumented__", False)
