"""Per-component spec sheet generator."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel, Component


def _resolve_name(comp_id: str, model: "ArchitectureModel") -> str:
    """Resolve component ID to 'ID (Name)'."""
    for comp in model.entities.components:
        if comp.id == comp_id:
            return f"{comp.id} ({comp.name})"
    return comp_id


def generate_component_spec(comp: "Component", model: "ArchitectureModel") -> str:
    """Generate a markdown spec sheet for a single component."""
    lines: list[str] = []

    # Header
    lines.append(f"# {comp.id}: {comp.name}")
    lines.append("")

    # Metadata
    meta_parts = []
    if comp.status:
        meta_parts.append(f"**Status:** {comp.status}")
    if comp.pattern:
        meta_parts.append(f"**Pattern:** {comp.pattern}")
    if comp.f_block:
        meta_parts.append(f"**F-Block:** {comp.f_block}")
    if comp.confidence is not None:
        meta_parts.append(f"**Confidence:** {comp.confidence:.0%}")
    if meta_parts:
        lines.append(" | ".join(meta_parts))
        lines.append("")

    # Contract
    if comp.contract:
        lines.append("## Contract")
        lines.append("")
        lines.append(comp.contract)
        lines.append("")

    # Files
    if comp.files:
        lines.append("## Files")
        lines.append("")
        for f in comp.files:
            lines.append(f"- `{f}`")
        lines.append("")

    # Responsibilities
    if comp.responsibilities:
        lines.append("## Responsibilities")
        lines.append("")
        for r in comp.responsibilities:
            lines.append(f"- {r}")
        lines.append("")

    # Public API
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

    # Classes
    if comp.symbols:
        lines.append("## Classes")
        lines.append("")
        lines.append("| Class | Kind | Bases | Methods |")
        lines.append("|-------|------|-------|---------|")
        for sym in comp.symbols:
            kind = sym.kind.value if hasattr(sym.kind, "value") else str(sym.kind)
            bases = ", ".join(sym.supers) if sym.supers else ""
            methods = ", ".join(sym.members) if sym.members else ""
            lines.append(f"| `{sym.name}` | {kind} | {bases} | {methods} |")
        lines.append("")

    # Dependencies
    if comp.interfaces:
        lines.append("## Dependencies")
        lines.append("")
        for iface in comp.interfaces:
            target = _resolve_name(iface.target_component, model)
            symbols = ", ".join(iface.symbols) if iface.symbols else ""
            lines.append(f"- **{iface.kind}** `{iface.name}` → {target} [{symbols}]")
        lines.append("")

    # Test Coverage
    if comp.test_contracts:
        lines.append("## Test Coverage")
        lines.append("")
        contracts = comp.test_contracts[:20]
        for tc in contracts:
            lines.append(f"- `{tc.test_file}::{tc.test_method}` — {tc.contract_type}")
        if len(comp.test_contracts) > 20:
            lines.append(f"- ... and {len(comp.test_contracts) - 20} more")
        lines.append("")

    return "\n".join(lines)
