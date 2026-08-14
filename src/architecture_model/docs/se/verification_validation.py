# src/architecture_model/docs/se/verification_validation.py
"""Verification & Validation document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)


def generate_verification_validation(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Verification & Validation: {project}")
    lines.append("")

    # --- Verification Matrix ---
    lines.append("## Verification Matrix")
    lines.append("")
    # Map components to their test contracts
    comps_with_tests = [(c, c.test_contracts) for c in model.entities.components
                        if hasattr(c, "test_contracts") and c.test_contracts]

    if comps_with_tests:
        lines.append("| Component | Test File | Test Method | Assertion | Contract Type |")
        lines.append("|-----------|----------|-------------|-----------|---------------|")
        for comp, contracts in comps_with_tests:
            for tc in contracts[:10]:  # cap per component
                tf = getattr(tc, "test_file", "—")
                tm = getattr(tc, "test_method", "—")
                assertion = getattr(tc, "assertion", "—")
                ct = getattr(tc, "contract_type", "—")
                lines.append(f"| {comp.name} | {tf} | {tm} | {assertion} | {ct} |")
            if len(contracts) > 10:
                lines.append(f"| {comp.name} | ... | *{len(contracts) - 10} more contracts* | | |")
    else:
        lines.append("*No test contracts found on components.*")
    lines.append("")

    # --- Validation Coverage ---
    lines.append("## Validation Coverage")
    lines.append("")
    total_comps = len(model.entities.components)
    tested_comps = len(comps_with_tests)
    total_contracts = sum(len(c.test_contracts) for c, _ in comps_with_tests)
    lines.append(f"- **Components with tests:** {tested_comps}/{total_comps} ({100*tested_comps//max(total_comps,1)}%)")
    lines.append(f"- **Total test contracts:** {total_contracts}")
    lines.append("")

    # Constraint verification
    lines.append("### Constraint Verification Status")
    lines.append("")
    verifies = [r for r in model.relationships if _rel_type_str(r.type) == "verifies"]
    con_map = {c.id: c for c in model.entities.constraints}
    verified_ids = {r.to_id for r in verifies}

    if model.entities.constraints:
        lines.append("| Constraint | Type | Verified? |")
        lines.append("|-----------|------|-----------|")
        for con in model.entities.constraints:
            from architecture_model.docs.se.requirements_analysis import _constraint_type_str
            ctype = _constraint_type_str(con.type)
            verified = "Yes" if con.id in verified_ids else "No"
            lines.append(f"| {con.name} | {ctype} | {verified} |")
    else:
        lines.append("*No constraints to verify.*")
    lines.append("")

    # --- Behavior Validation ---
    lines.append("## Behavior Validation")
    lines.append("")
    if model.entities.behaviors:
        behaviors_with_steps = [b for b in model.entities.behaviors if b.steps]
        lines.append(f"- **Total behaviors:** {len(model.entities.behaviors)}")
        lines.append(f"- **Behaviors with defined steps:** {len(behaviors_with_steps)}")
        lines.append(f"- **Behaviors with preconditions:** {sum(1 for b in model.entities.behaviors if b.preconditions)}")
        lines.append(f"- **Behaviors with postconditions:** {sum(1 for b in model.entities.behaviors if b.postconditions)}")
    else:
        lines.append("*No behaviors defined.*")
    lines.append("")

    # --- Unverified Items ---
    lines.append("## Unverified Items")
    lines.append("")
    unverified: list[str] = []
    untested_comps = [c for c in model.entities.components
                      if not (hasattr(c, "test_contracts") and c.test_contracts)]
    for c in untested_comps:
        unverified.append(f"Component **{c.name}** ({c.id}) has no test contracts")
    unverified_cons = [c for c in model.entities.constraints if c.id not in verified_ids]
    for c in unverified_cons:
        unverified.append(f"Constraint **{c.name}** ({c.id}) has no verification")

    if unverified:
        for item in unverified:
            lines.append(f"- {item}")
    else:
        lines.append("*All items have verification coverage.*")
    lines.append("")

    return "\n".join(lines)
