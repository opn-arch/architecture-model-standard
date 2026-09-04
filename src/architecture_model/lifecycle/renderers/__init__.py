"""Renderer registry for lifecycle artifacts (T18).

Each renderer is a pure callable ``(ProjectedView | list[ProjectedView],
ArtifactSpec) -> bytes``. Renderers MUST:

* Perform no filesystem, network, environment, or logging side effects.
* Accept a single :class:`ProjectedView` or a list (first element used;
  empty list raises :class:`ValueError`).
* Reject an :class:`ArtifactSpec` whose ``renderer`` field does not match
  the renderer's own name (raises :class:`ValueError` with
  ``renderer mismatch: expected 'X', got 'Y'``).
* Return ``bytes``.

The two aggregating renderers (``ai-context``, ``zip``) are added in
T18 commit 2 and are not registered here yet.
"""
from __future__ import annotations

from typing import Callable

from architecture_model.lifecycle.artifact_spec import ArtifactSpec
from architecture_model.lifecycle.renderers.ai_context import render_ai_context
from architecture_model.lifecycle.renderers.html import render_html
from architecture_model.lifecycle.renderers.markdown import render_markdown
from architecture_model.lifecycle.renderers.svg import render_svg
from architecture_model.lifecycle.renderers.zip import BundleResolutionError, render_zip
from architecture_model.lifecycle.view_projection import ProjectedView

RendererFn = Callable[["ProjectedView | list[ProjectedView]", ArtifactSpec], bytes]

DEFAULT_RENDERERS: dict[str, RendererFn] = {
    "svg": render_svg,
    "markdown": render_markdown,
    "html": render_html,
    "ai-context": render_ai_context,
    # ``render_zip`` has a different signature (needs ``resolve_artifact``);
    # calling it via this dict without the resolver will raise ValueError.
    # Phase 2 orchestrators are expected to detect renderer=="zip" and
    # invoke ``render_zip`` directly. It is exposed here for discovery
    # symmetry.
    "zip": render_zip,  # type: ignore[dict-item]
}


def get_renderer(name: str) -> RendererFn:
    """Return the renderer registered for ``name`` or raise :class:`KeyError`."""
    return DEFAULT_RENDERERS[name]


__all__ = [
    "BundleResolutionError",
    "DEFAULT_RENDERERS",
    "RendererFn",
    "get_renderer",
    "render_ai_context",
    "render_html",
    "render_markdown",
    "render_svg",
    "render_zip",
]
