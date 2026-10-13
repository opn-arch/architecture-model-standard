"""lifecycle.projectors.legacy.visualize_adapter — v3-shaped visualize (T0.14 Phase 11).

Thin wrapper over the 2.x diagram generator. Accepts a v3 model dict,
converts it via
:func:`architecture_model.pipeline_v3.adapters.legacy_pipeline.v3_to_legacy_model`,
and returns a ``{diagram_name: markdown_body}`` mapping.

Kept minimal on purpose — the real projector work has moved to the
lifecycle substrate (families 1-8). This adapter only exists so v3
call sites can invoke surviving legacy visualize helpers during the
Phase 10 deprecation window without re-implementing them.
"""

from __future__ import annotations

from typing import Any

from architecture_model.pipeline_v3.adapters.legacy_pipeline import (
    v3_to_legacy_model,
)

__all__ = ["render_diagrams_from_v3"]


def render_diagrams_from_v3(v3_model: dict[str, Any]) -> dict[str, str]:
    """Render diagrams for a v3 model via the legacy generator.

    Returns a ``{name: body}`` mapping. Falls back to an inline
    Mermaid graph when the legacy ``generate_all_diagrams`` helper
    is unavailable or fails — the adapter contract is that at least
    one non-empty diagram is always returned when the model has any
    components.
    """
    legacy = v3_to_legacy_model(v3_model)
    try:
        from architecture_model.docs.diagrams import generate_all_diagrams
        result = generate_all_diagrams(legacy)  # type: ignore[arg-type]
        if isinstance(result, dict) and result:
            return {str(k): str(v) for k, v in result.items() if v}
    except Exception:
        # Fall through to the inline fallback below.
        pass

    lines = ["graph TD"]
    for c in legacy.entities.components:
        lines.append(f'    {c.id}["{c.name} ({c.id})"]')
    for r in legacy.relationships:
        lines.append(f"    {r.from_id} --> {r.to_id}")
    body = "```mermaid\n" + "\n".join(lines) + "\n```"
    return {"component-diagram": body}
