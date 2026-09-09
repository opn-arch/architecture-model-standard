"""Per-component spec sheet generator."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

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


# --- Phase 2 (schema 2.1) semantic-field rendering helpers ---------------
#
# Guiding invariant: when a Phase 2 field is empty/absent, EMIT NOTHING.
# The pre-Phase-2 markdown must remain byte-identical for 2.0 models.
# See docs/plans/2026-09-08-phase-2-schema-and-semantic-content.md Task 7.


def _render_failure_mode(item: Any) -> str:
    """Render one entry from ``failure_modes`` (str-or-FailureMode)."""
    if isinstance(item, str):
        return f"- {item}"
    # Typed FailureMode dataclass (frozen; has .id/.cause/.effect/etc.)
    cause = getattr(item, "cause", "") or ""
    effect = getattr(item, "effect", "") or ""
    likelihood = getattr(item, "likelihood", None)
    likelihood_v = likelihood.value if hasattr(likelihood, "value") else (likelihood or "")
    severity = getattr(item, "severity", None)
    severity_v = severity.value if hasattr(severity, "value") else (severity or "")
    mitigation = getattr(item, "mitigation", "") or ""
    fid = getattr(item, "id", "") or ""
    parts = [f"- **{fid}** — {cause} → {effect}"]
    meta = []
    if likelihood_v:
        meta.append(f"likelihood: {likelihood_v}")
    if severity_v:
        meta.append(f"severity: {severity_v}")
    if meta:
        parts.append(f"  ({', '.join(meta)})")
    if mitigation:
        parts.append(f"  Mitigation: {mitigation}")
    return "\n".join(parts)


def _render_trade_off(item: Any) -> str:
    """Render one entry from ``trade_offs`` (str-or-TradeOff)."""
    if isinstance(item, str):
        return f"- {item}"
    tid = getattr(item, "id", "") or ""
    decision = getattr(item, "decision", "") or ""
    rationale = getattr(item, "rationale", "") or ""
    revisit = getattr(item, "revisit_when", "") or ""
    lines = [f"- **{tid}** — {decision}"]
    if rationale:
        lines.append(f"  Rationale: {rationale}")
    if revisit:
        lines.append(f"  Revisit when: {revisit}")
    return "\n".join(lines)


def _render_slo(slo: Any) -> str:
    """Render one SLO (typed)."""
    metric = getattr(slo, "metric", "") or ""
    target = getattr(slo, "target", "") or ""
    window = getattr(slo, "window", "") or ""
    current = getattr(slo, "current", None)
    line = f"| `{metric}` | `{target}` | {window} |"
    if current is not None:
        line += f" current: {current}"
    return line


def _append_semantic_sections(lines: list[str], comp: "Component") -> None:
    """Append Phase 2 semantic sections to ``lines`` in stable order.

    Every section is guarded on a truthy field check; nothing is emitted
    if the component has no Phase 2 fields set (byte-identity vs 2.0).
    """
    intent = getattr(comp, "intent", None)
    if intent:
        lines.append("## Intent")
        lines.append("")
        lines.append(intent)
        lines.append("")

    failure_modes = getattr(comp, "failure_modes", None) or []
    if failure_modes:
        lines.append("## Failure Modes")
        lines.append("")
        for fm in failure_modes:
            lines.append(_render_failure_mode(fm))
        lines.append("")

    trade_offs = getattr(comp, "trade_offs", None) or []
    if trade_offs:
        lines.append("## Trade-Offs")
        lines.append("")
        for t in trade_offs:
            lines.append(_render_trade_off(t))
        lines.append("")

    slos = getattr(comp, "slos", None) or []
    if slos:
        lines.append("## SLOs")
        lines.append("")
        lines.append("| Metric | Target | Window |")
        lines.append("|--------|--------|--------|")
        for slo in slos:
            lines.append(_render_slo(slo))
        lines.append("")

    owner = getattr(comp, "owner", None)
    maturity = getattr(comp, "maturity", None)
    maturity_v = maturity.value if hasattr(maturity, "value") else maturity
    if owner or maturity_v:
        lines.append("## Ownership")
        lines.append("")
        if owner:
            lines.append(f"**Owner:** {owner}")
        if maturity_v:
            lines.append(f"**Maturity:** {maturity_v}")
        lines.append("")

    deps_rationale = getattr(comp, "dependencies_rationale", None) or {}
    if deps_rationale:
        lines.append("## Dependency Rationale")
        lines.append("")
        for target, why in deps_rationale.items():
            lines.append(f"- **{target}** — {why}")
        lines.append("")


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

    # --- Phase 2 (schema 2.1) semantic sections ---
    # All sections are conditional; when every field is absent (2.0 model)
    # nothing is emitted here → byte-identity vs pre-Phase-2 output.
    _append_semantic_sections(lines, comp)

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
