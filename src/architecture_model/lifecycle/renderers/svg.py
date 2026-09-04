"""SVG artifact renderer.

Purpose
-------
Render a :class:`~architecture_model.lifecycle.view_projection.ProjectedView`
into deterministic, standalone SVG bytes.

Purity contract
---------------
This function performs NO filesystem, network, environment, or logging
side effects. It is a pure function of its inputs and safe for
concurrent use.

Adaptation source
-----------------
Wraps :func:`architecture_model.core.diagram_renderer.render_diagram_svg`,
extracting the ``DiagramSpec`` from ``view.diagram_spec`` and encoding
the returned string as UTF-8. The upstream renderer is treated as an
opaque, deterministic, dependency-free SVG string generator.

Error taxonomy
--------------
* :class:`ValueError` — ``artifact.renderer`` is not ``"svg"``, or a list
  of views is supplied but empty.
"""
from __future__ import annotations

from typing import Any

from architecture_model.core.diagram_renderer import (
    DiagramRenderOptions,
    render_diagram_svg,
)
from architecture_model.lifecycle.artifact_spec import ArtifactSpec
from architecture_model.lifecycle.view_projection import ProjectedView

_NAME = "svg"


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


def render_svg(
    view: ProjectedView | list[ProjectedView], artifact: ArtifactSpec
) -> bytes:
    """Render ``view`` as SVG. Returns UTF-8 encoded bytes."""
    _check_renderer(artifact)
    picked = _pick_view(view)
    options = _options_from_parameters(artifact.parameters)
    svg_text = render_diagram_svg(picked.diagram_spec, options)
    return svg_text.encode("utf-8")


__all__ = ["render_svg"]
