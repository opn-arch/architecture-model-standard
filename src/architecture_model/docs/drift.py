"""Generate drift/change report between model versions."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel


def generate_drift_report(old_model: "ArchitectureModel", new_model: "ArchitectureModel") -> str:
    """Generate change report comparing two model versions."""
    from architecture_model.core.differ import diff_models

    diff = diff_models(old_model, new_model)
    lines = ["# Architecture Drift Report", ""]

    if not diff.has_changes:
        lines.append("**No changes detected.** Model is current.")
        return "\n".join(lines)

    lines.append("## Summary")
    lines.append("")
    lines.append("| Change Type | Count |")
    lines.append("|-------------|-------|")
    lines.append(f"| Added | {diff.added_count} |")
    lines.append(f"| Removed | {diff.removed_count} |")
    lines.append(f"| Modified | {diff.modified_count} |")
    lines.append("")

    if diff.entity_changes:
        lines.append("## Entity Changes")
        lines.append("")
        lines.append("| Type | Entity | Change | Details |")
        lines.append("|------|--------|--------|---------|")
        for ch in diff.entity_changes:
            lines.append(f"| {ch.entity_type} | {ch.entity_name} ({ch.entity_id}) | {ch.change_type.value} | {ch.details[:60]} |")
        lines.append("")

    if diff.relationship_changes:
        lines.append("## Relationship Changes")
        lines.append("")
        lines.append("| Type | From \u2192 To | Change |")
        lines.append("|------|-----------|--------|")
        for ch in diff.relationship_changes:
            lines.append(f"| {ch.rel_type} | {ch.from_id} \u2192 {ch.to_id} | {ch.change_type.value} |")
        lines.append("")

    affected = diff.affected_artifacts()
    if affected:
        lines.append("## Affected Documents")
        lines.append("")
        for a in sorted(affected):
            lines.append(f"- {a}")
        lines.append("")

    return "\n".join(lines)
