"""Generate health metrics report."""

from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel
    from architecture_model.manifest.types import Manifest


def generate_health_report(
    model: "ArchitectureModel", manifest: "Manifest | None" = None, root: "Path | None" = None
) -> str:
    """Generate architecture health metrics."""
    lines = ["# Architecture Health Report", ""]
    lines.append(f"**Project:** {model.meta.project}")
    lines.append("")

    components = model.entities.components if hasattr(model.entities, "components") else []
    if not components:
        lines.append("No components found.")
    # Token Savings section
    if root is not None:
        from ..core.compression import compute_compression_stats

        stats = compute_compression_stats(root)
        if stats["compression_ratio"] > 0:
            lines.append("## Token Savings")
            lines.append("")
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")
            lines.append(f"| Source tokens | ~{stats['source_tokens']:,} |")
            lines.append(f"| Model tokens | ~{stats['model_tokens']:,} |")
            lines.append(f"| Compression | {stats['compression_ratio']}x |")
            lines.append(f"| Tokens saved | ~{stats['tokens_saved']:,} |")
            lines.append("")

    # Component Confidence — always emit when components have confidence values
    if components:
        conf_rows = [
            (c.id, c.name, c.confidence) for c in components if c.confidence is not None
        ]
        if conf_rows:
            lines.append("## Component Confidence")
            lines.append("")
            lines.append("| Component | Name | Confidence |")
            lines.append("|-----------|------|------------|")
            for cid, cname, conf in sorted(conf_rows, key=lambda r: -(r[2] or 0)):
                lines.append(f"| {cid} | {cname} | {conf:.0%} |")
            lines.append("")

    # Component Readiness (Regen Score)
    try:
        from architecture_model.core.regen_readiness import compute_regen_readiness

        readiness = compute_regen_readiness(model)
        if readiness.components:
            lines.append("## Component Readiness (Regen Score)")
            lines.append("")
            lines.append("| Component | Name | Score | Blockers |")
            lines.append("|-----------|------|-------|----------|")
            for rc in readiness.components:
                blockers = ", ".join(rc.blockers) if rc.blockers else "\u2014"
                lines.append(f"| {rc.id} | {rc.name} | {rc.score:.0f}% | {blockers} |")
            lines.append("")
    except (ImportError, AttributeError):
        pass

    return "\n".join(lines)
