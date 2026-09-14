"""lifecycle.projectors.legacy.docs_adapter — v3-shaped docs (T0.14 Phase 11).

Thin wrapper that produces a legacy-style docs bundle from a v3 model.
Accepts the v3 dict, converts via
:func:`architecture_model.pipeline_v3.adapters.legacy_pipeline.v3_to_legacy_model`,
and returns a ``{doc_name: markdown_body}`` mapping.

The bundle contains a per-component summary page plus a single
architecture-index page. Content is deterministic and side-effect
free. Legacy docs generators can be plugged in over this contract
during the Phase 10 deprecation window without changing v3 call
sites.
"""

from __future__ import annotations

from typing import Any

from architecture_model.pipeline_v3.adapters.legacy_pipeline import (
    v3_to_legacy_model,
)

__all__ = ["generate_docs_from_v3"]


def _component_page(comp: Any) -> str:
    lines = [f"# {comp.name} ({comp.id})", ""]
    if comp.files:
        lines.append("## Files")
        lines.append("")
        for f in comp.files:
            lines.append(f"- `{f}`")
        lines.append("")
    if comp.responsibilities:
        lines.append("## Responsibilities")
        lines.append("")
        for r in comp.responsibilities:
            lines.append(f"- {r}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _index_page(legacy: Any) -> str:
    lines = ["# Architecture Index", "", f"Project: **{legacy.meta.project}**", ""]
    lines.append("## Components")
    lines.append("")
    for c in legacy.entities.components:
        lines.append(f"- `{c.id}` — {c.name}")
    lines.append("")
    if legacy.relationships:
        lines.append("## Relationships")
        lines.append("")
        for r in legacy.relationships:
            lines.append(f"- {r.from_id} → {r.to_id} ({r.type.value})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generate_docs_from_v3(v3_model: dict[str, Any]) -> dict[str, str]:
    """Return a ``{doc_name: markdown_body}`` bundle for a v3 model."""
    legacy = v3_to_legacy_model(v3_model)
    out: dict[str, str] = {"index": _index_page(legacy)}
    for c in legacy.entities.components:
        out[f"component-{c.id}"] = _component_page(c)
    return out
