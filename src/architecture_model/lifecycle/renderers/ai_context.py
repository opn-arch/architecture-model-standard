"""AI-context artifact renderer (T18 commit 2).

Purpose
-------
Render a :class:`~architecture_model.lifecycle.view_projection.ProjectedView`
into a compact, LLM-friendly plain-text context payload summarizing the
projected DiagramSpec (nodes, edges, warnings, provenance).

Purity contract
---------------
No filesystem, network, environment, or logging side effects. Pure
function of its inputs.

Adaptation source
-----------------
The historical LLM context formatter
``architecture_model.integrations.llm_context.format_model_context``
consumes a full ``ArchitectureModel`` and is not currently present in
this tree. Rather than reconstruct a synthetic model from a DiagramSpec
(lossy round-trip), this renderer emits a self-contained textual
summary directly from ``ProjectedView`` fields. This mirrors the pattern
used by the HTML renderer in T18 commit 1.

If ``artifact.parameters`` carries ``max_tokens`` (int), the output is
soft-capped to roughly ``max_tokens * 4`` characters (a conventional
~4 chars/token heuristic); unknown parameters are silently ignored.

Error taxonomy
--------------
* :class:`ValueError` — ``artifact.renderer`` is not ``"ai-context"``,
  or a list of views is supplied but empty.
"""
from __future__ import annotations

from architecture_model.lifecycle.artifact_spec import ArtifactSpec
from architecture_model.lifecycle.view_projection import ProjectedView

_NAME = "ai-context"


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


def render_ai_context(
    view: ProjectedView | list[ProjectedView], artifact: ArtifactSpec
) -> bytes:
    """Render ``view`` as a deterministic LLM-context text block.

    Returns UTF-8 encoded bytes.
    """
    _check_renderer(artifact)
    picked = _pick_view(view)
    spec = picked.diagram_spec

    lines: list[str] = []
    lines.append(f"# AI Context: {spec.title or picked.view_id}")
    lines.append("")
    lines.append("## Provenance")
    lines.append(f"view_id: {picked.view_id}")
    lines.append(f"slice_id: {picked.slice_id}")
    lines.append(f"model_revision: {picked.model_revision}")
    projector = picked.provenance.get("projector", "")
    projector_version = picked.provenance.get("projector_version", "")
    if projector:
        lines.append(f"projector: {projector}")
    if projector_version:
        lines.append(f"projector_version: {projector_version}")
    lines.append("")

    lines.append(f"## Nodes ({len(spec.nodes)})")
    for node in spec.nodes:
        lines.append(f"- [{node.kind}] {node.id}: {node.label}")
    lines.append("")

    lines.append(f"## Edges ({len(spec.edges)})")
    for edge in spec.edges:
        label = f" — {edge.label}" if edge.label else ""
        lines.append(f"- ({edge.kind}) {edge.source} -> {edge.target}{label}")
    lines.append("")

    if picked.warnings:
        lines.append(f"## Warnings ({len(picked.warnings)})")
        for warn in picked.warnings:
            lines.append(f"- {warn}")
        lines.append("")

    text = "\n".join(lines)

    max_tokens = artifact.parameters.get("max_tokens")
    if isinstance(max_tokens, int) and max_tokens > 0:
        cap = max_tokens * 4
        if len(text) > cap:
            text = text[:cap]

    return text.encode("utf-8")


__all__ = ["render_ai_context"]
