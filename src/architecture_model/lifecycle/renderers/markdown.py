"""Markdown artifact renderer.

Purpose
-------
Produce a minimal, deterministic markdown document that summarises a
:class:`~architecture_model.lifecycle.view_projection.ProjectedView`.

The document contains:

* A title (``parameters['title']`` if supplied, otherwise
  ``view.diagram_spec.title``, otherwise the view id).
* A metadata block: view id, slice id, model revision, projector and
  projector version (from ``view.provenance``).
* A fenced code block with the diagram source. If the DiagramSpec
  carries a ``mermaid`` string in ``facets['mermaid']`` we use that
  (``mermaid`` fence); otherwise a compact text listing of nodes and
  edges (``text`` fence). This is intentionally minimal — richer
  diagram-in-markdown embedding is out of scope for T18 commit 1.
* A warnings summary listing every entry of ``view.warnings``.

Purity contract
---------------
No filesystem, network, environment, or logging side effects. Pure
function of its inputs; safe for concurrent use.

Adaptation source
-----------------
No existing markdown adapter in the tree owns this responsibility (the
core ``visualize._md_to_html`` converts markdown *to* HTML — the opposite
direction). This module therefore implements a small, self-contained
markdown emitter directly. If a shared markdown emitter is introduced
later, this renderer should be refactored to delegate.

Error taxonomy
--------------
* :class:`ValueError` — ``artifact.renderer`` is not ``"markdown"``, or a
  list of views is supplied but empty.
"""
from __future__ import annotations

from typing import Any

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.lifecycle.artifact_spec import ArtifactSpec
from architecture_model.lifecycle.view_projection import ProjectedView

_NAME = "markdown"


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


def _diagram_body(spec: DiagramSpec) -> tuple[str, str]:
    """Return (fence_lang, body) for the diagram source code block."""
    mermaid = spec.facets.get("mermaid") if isinstance(spec.facets, dict) else None
    if isinstance(mermaid, str) and mermaid.strip():
        return "mermaid", mermaid.rstrip()
    lines: list[str] = [f"diagram: {spec.id} ({spec.layout})"]
    for node in spec.nodes:
        lines.append(f"  node {node.id} [{node.kind}] {node.label}")
    for edge in spec.edges:
        arrow = f" ({edge.label})" if edge.label else ""
        lines.append(f"  edge {edge.source} -> {edge.target} [{edge.kind}]{arrow}")
    return "text", "\n".join(lines)


def render_markdown(
    view: ProjectedView | list[ProjectedView], artifact: ArtifactSpec
) -> bytes:
    """Render ``view`` as a minimal markdown document. Returns UTF-8 bytes."""
    _check_renderer(artifact)
    picked = _pick_view(view)
    params: dict[str, Any] = dict(artifact.parameters)

    spec = picked.diagram_spec
    title = params.get("title") or spec.title or picked.view_id
    projector = str(picked.provenance.get("projector", ""))
    projector_version = str(picked.provenance.get("projector_version", ""))

    fence, body = _diagram_body(spec)

    out: list[str] = []
    out.append(f"# {title}")
    out.append("")
    out.append("## Metadata")
    out.append("")
    out.append(f"- view_id: `{picked.view_id}`")
    out.append(f"- slice_id: `{picked.slice_id}`")
    out.append(f"- model_revision: `{picked.model_revision}`")
    if projector:
        out.append(f"- projector: `{projector}` ({projector_version or 'unknown'})")
    out.append("")
    out.append("## Diagram")
    out.append("")
    out.append(f"```{fence}")
    out.append(body)
    out.append("```")
    out.append("")
    out.append("## Warnings")
    out.append("")
    if picked.warnings:
        for warning in picked.warnings:
            out.append(f"- {warning}")
    else:
        out.append("- (none)")
    out.append("")

    return "\n".join(out).encode("utf-8")


__all__ = ["render_markdown"]
