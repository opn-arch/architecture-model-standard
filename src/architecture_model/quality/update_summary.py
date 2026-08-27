"""Per-subsystem update summary — shows v2.1 semantic field coverage."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel


def subsystem_summary(name: str, model: "ArchitectureModel") -> dict[str, str]:
    """Generate a summary of v2.1 field coverage for a subsystem model.

    Returns dict with name and coverage fractions for each field.
    """
    from architecture_model.core.types import Status

    comps = [c for c in model.entities.components
             if (c.status.value if hasattr(c.status, 'value') else str(c.status)) == "ACTIVE"]
    caps = [c for c in model.entities.capabilities
            if (c.status.value if hasattr(c.status, 'value') else str(c.status)) == "ACTIVE"]
    ifaces = model.entities.interfaces

    # Intent: both components and capabilities
    total_intent = len(comps) + len(caps)
    has_intent = sum(1 for c in comps if c.intent) + sum(1 for c in caps if c.intent)

    # MOEs: capabilities only
    has_moes = sum(1 for c in caps if c.moes)

    # Trade-offs, failure_modes: components only
    has_tradeoffs = sum(1 for c in comps if c.trade_offs)
    has_failure = sum(1 for c in comps if c.failure_modes)

    # Contracts: interfaces
    has_contract = sum(1 for i in ifaces if i.contract)

    # Goals: components
    has_goals = sum(1 for c in comps if c.goals)

    return {
        "name": name,
        "intent": f"{has_intent}/{total_intent}",
        "moes": f"{has_moes}/{len(caps)}",
        "trade_offs": f"{has_tradeoffs}/{len(comps)}",
        "failure_modes": f"{has_failure}/{len(comps)}",
        "contracts": f"{has_contract}/{len(ifaces)}",
        "goals": f"{has_goals}/{len(comps)}",
        "components": len(comps),
        "capabilities": len(caps),
    }


def format_summaries(summaries: list[dict[str, str]]) -> str:
    """Format a list of subsystem summaries as a markdown table."""
    lines = [
        "# Subsystem v2.1 Semantic Coverage",
        "",
        "| Subsystem | Comps | Caps | Intent | MOEs | Trade-offs | Failure Modes | Contracts | Goals |",
        "|-----------|:-----:|:----:|:------:|:----:|:----------:|:-------------:|:---------:|:-----:|",
    ]
    for s in summaries:
        lines.append(
            f"| {s['name']} | {s['components']} | {s['capabilities']} "
            f"| {s['intent']} | {s['moes']} | {s['trade_offs']} "
            f"| {s['failure_modes']} | {s['contracts']} | {s['goals']} |"
        )
    return "\n".join(lines)
