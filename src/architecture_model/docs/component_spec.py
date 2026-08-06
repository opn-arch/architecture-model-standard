"""Per-component spec sheet generator."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel, Component


def _rel_type_str(rel_type) -> str:
    return rel_type.value if hasattr(rel_type, 'value') else str(rel_type)


def _resolve_name(comp_id: str, model: "ArchitectureModel") -> str:
    """Resolve component ID to 'ID (Name)'."""
    for comp in model.entities.components:
        if comp.id == comp_id:
            return f"{comp.id} ({comp.name})"
    return comp_id


def generate_component_spec(comp: "Component", model: "ArchitectureModel") -> str:
    """Generate a rich markdown spec sheet for a single component."""
    lines: list[str] = []

    # Header
    lines.append(f"# Component: {comp.name} ({comp.id})")
    lines.append("")

    # Status & Description
    lines.append(f"**Status:** {comp.status or '—'}")
    lines.append(f"**Description:** {comp.description or '—'}")
    lines.append("")

    # Files
    lines.append("## Files")
    lines.append("")
    if comp.files:
        lines.append("| File | Functions | Classes |")
        lines.append("|------|-----------|---------|")
        for f in comp.files:
            funcs = "—"
            classes = "—"
            if comp.extensions:
                file_stats = comp.extensions.get("file_stats", {}).get(f, {})
                if file_stats:
                    funcs = str(file_stats.get("functions", "—"))
                    classes = str(file_stats.get("classes", "—"))
            lines.append(f"| `{f}` | {funcs} | {classes} |")
    else:
        lines.append("None")
    lines.append("")

    # Responsibilities
    lines.append("## Responsibilities")
    lines.append("")
    if comp.responsibilities:
        for r in comp.responsibilities:
            lines.append(f"- {r}")
    else:
        lines.append("—")
    lines.append("")

    # Relationships
    outgoing = [r for r in model.relationships if r.from_id == comp.id]
    incoming = [r for r in model.relationships if r.to_id == comp.id]

    lines.append("## Relationships")
    lines.append("")
    lines.append("### Dependencies (outgoing)")
    lines.append("")
    if outgoing:
        lines.append("| Target | Type | Description |")
        lines.append("|--------|------|-------------|")
        for r in outgoing:
            target = _resolve_name(r.to_id, model)
            lines.append(f"| {target} | {_rel_type_str(r.type)} | {r.description or '—'} |")
    else:
        lines.append("None")
    lines.append("")

    lines.append("### Dependents (incoming)")
    lines.append("")
    if incoming:
        lines.append("| Source | Type | Description |")
        lines.append("|--------|------|-------------|")
        for r in incoming:
            source = _resolve_name(r.from_id, model)
            lines.append(f"| {source} | {_rel_type_str(r.type)} | {r.description or '—'} |")
    else:
        lines.append("None")
    lines.append("")

    # Behaviors Realized
    realized_behavior_ids = {
        r.to_id for r in model.relationships
        if         r.from_id == comp.id and _rel_type_str(r.type) == "realizes"
    }
    behaviors = getattr(model.entities, 'behaviors', []) or []
    realized = [b for b in behaviors if b.id in realized_behavior_ids]

    lines.append("## Behaviors Realized")
    lines.append("")
    if realized:
        for b in realized:
            lines.append(f"- {b.name} ({b.id})")
    else:
        lines.append("None")
    lines.append("")

    # Public API (signatures)
    if comp.signatures:
        lines.append("## Public API")
        lines.append("")
        lines.append("| Function | Parameters | Returns | Description |")
        lines.append("|----------|-----------|---------|-------------|")
        for sig in comp.signatures:
            params = ", ".join(sig.params) if sig.params else ""
            doc = getattr(sig, "body_hint", "") or ""
            lines.append(f"| `{sig.name}` | `{params}` | `{sig.returns}` | {doc} |")
        lines.append("")

    # Interface Dependencies
    if comp.interfaces:
        lines.append("## Interface Dependencies")
        lines.append("")
        for iface in comp.interfaces:
            target = _resolve_name(iface.target_component, model)
            symbols = ", ".join(iface.symbols) if iface.symbols else ""
            lines.append(f"- **{iface.kind}** `{iface.name}` → {target} [{symbols}]")
        lines.append("")

    # Patterns
    lines.append("## Patterns")
    lines.append("")
    if comp.pattern:
        lines.append(f"- {comp.pattern}")
    else:
        lines.append("None")
    lines.append("")

    # Confidence
    confidence = None
    if comp.confidence is not None:
        confidence = comp.confidence
    elif comp.extensions:
        prov = comp.extensions.get("source_block_provenance", {})
        if isinstance(prov, dict):
            confidence = prov.get("confidence")

    lines.append("## Confidence")
    lines.append("")
    if confidence is not None:
        lines.append(f"{confidence:.0%}")
    else:
        lines.append("—")
    lines.append("")

    return "\n".join(lines)
