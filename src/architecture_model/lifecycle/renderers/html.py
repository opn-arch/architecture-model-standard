"""HTML artifact renderer.

Purpose
-------
Wrap the SVG rendering of a
:class:`~architecture_model.lifecycle.view_projection.ProjectedView` in a
minimal, self-contained HTML5 document that can be opened in any browser
without external assets.

Purity contract
---------------
No filesystem, network, environment, or logging side effects. Pure
function of its inputs.

Adaptation source
-----------------
The full-featured HTML viewer in
:func:`architecture_model.core.visualize.generate_html_viewer` is
purpose-built for interactive multi-view browsing, requires a model +
project root, and *writes to disk*. It is unsuitable as a per-artifact
renderer bound to a single :class:`ProjectedView`.

This module therefore delegates SVG generation to
:func:`architecture_model.core.diagram_renderer.render_diagram_svg` (via
:mod:`architecture_model.lifecycle.renderers.svg`) and wraps the result
in a small deterministic HTML skeleton. If a shared, in-memory HTML
document builder is later extracted from ``visualize``, this renderer
should delegate to it.

Error taxonomy
--------------
* :class:`ValueError` — ``artifact.renderer`` is not ``"html"``, or a
  list of views is supplied but empty.
"""
from __future__ import annotations

from html import escape
from typing import Any

from architecture_model.core.diagram_renderer import (
    DiagramRenderOptions,
    render_diagram_svg,
)
from architecture_model.lifecycle.artifact_spec import ArtifactSpec
from architecture_model.lifecycle.view_projection import ProjectedView

_NAME = "html"


def _pick_view(view: ProjectedView | list[ProjectedView]) -> ProjectedView:
    if isinstance(view, list):
        if not view:
            raise ValueError("no view to render")
        return view[0]
    return view


def _check_renderer(artifact: ArtifactSpec) -> None:
    if artifact.renderer != _NAME:
        raise ValueError(
            f"renderer mismatch: expected {_NAME!r}, got {artifact.renderer!r}"
        )


def _options_from_parameters(params: dict[str, Any]) -> DiagramRenderOptions | None:
    theme = params.get("theme")
    if theme in {"light", "dark"}:
        return DiagramRenderOptions(theme=theme)
    return None


def render_html(
    view: ProjectedView | list[ProjectedView], artifact: ArtifactSpec
) -> bytes:
    """Render ``view`` as a minimal standalone HTML document."""
    _check_renderer(artifact)
    picked = _pick_view(view)
    params: dict[str, Any] = dict(artifact.parameters)

    spec = picked.diagram_spec
    title = params.get("title") or spec.title or picked.view_id
    options = _options_from_parameters(params)
    svg = render_diagram_svg(spec, options)

    warnings_html = ""
    if picked.warnings:
        items = "".join(f"<li>{escape(w)}</li>" for w in picked.warnings)
        warnings_html = f"<section class=\"warnings\"><h2>Warnings</h2><ul>{items}</ul></section>"

    document = (
        "<!DOCTYPE html>"
        "<html lang=\"en\"><head>"
        "<meta charset=\"utf-8\">"
        f"<title>{escape(title)}</title>"
        "<style>body{font-family:system-ui,sans-serif;margin:1.5rem;}"
        ".meta{color:#475569;font-size:0.9rem;}"
        ".warnings{margin-top:1rem;}"
        ".diagram{margin:1rem 0;}</style>"
        "</head><body>"
        f"<h1>{escape(title)}</h1>"
        "<p class=\"meta\">"
        f"view_id: <code>{escape(picked.view_id)}</code> &middot; "
        f"slice_id: <code>{escape(picked.slice_id)}</code> &middot; "
        f"revision: <code>{escape(picked.model_revision)}</code>"
        "</p>"
        f"<div class=\"diagram\">{svg}</div>"
        f"{warnings_html}"
        "</body></html>"
    )
    return document.encode("utf-8")


__all__ = ["render_html"]
