"""Format decomposition results as compact context for agent naming."""
from __future__ import annotations

from architecture_model.orchestration.deep_decompose import DecomposeResult


def format_naming_context(result: DecomposeResult) -> str:
    """Format a DecomposeResult for the agent to assign semantic names.

    Returns a compact string showing each cluster's key files, classes,
    and inter-cluster dependencies.
    """
    if not result.sub_components:
        return f"{result.block_name}: no sub-components (below threshold)"

    lines = [f"## {result.block_name} ({result.block_id}) — {len(result.sub_components)} sub-components\n"]

    for sc in result.sub_components:
        stems = [f.rsplit("/", 1)[-1].removesuffix(".py") for f in sc.files[:8]]
        extra = f" +{len(sc.files) - 8} more" if len(sc.files) > 8 else ""
        top_classes = sc.classes[:6]
        top_funcs = sc.functions[:4]
        lines.append(f"### {sc.id} ({sc.line_count} lines, {len(sc.files)} files)")
        lines.append(f"  Files: {', '.join(stems)}{extra}")
        if top_classes:
            lines.append(f"  Classes: {', '.join(top_classes)}")
        if top_funcs:
            lines.append(f"  Functions: {', '.join(top_funcs)}")
        lines.append("")

    if result.internal_relationships:
        lines.append("### Dependencies")
        for rel in sorted(result.internal_relationships, key=lambda r: -r.edge_count):
            lines.append(f"  {rel.from_id} → {rel.to_id} ({rel.edge_count} imports)")

    return "\n".join(lines)
