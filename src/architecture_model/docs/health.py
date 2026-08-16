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

    # Component Readiness (Regen Score)
    try:
        from architecture_model.core.regen_readiness import compute_regen_readiness

        readiness = compute_regen_readiness(model)
        if readiness.components:
            lines.append("## Component Readiness (Regen Score)")
            lines.append("")
            lines.append("| Component | Grade | Score | Blockers |")
            lines.append("|-----------|-------|-------|----------|")
            for rc in readiness.components:
                blockers = ", ".join(rc.blockers) if rc.blockers else "\u2014"
                lines.append(f"| {rc.component_id} | {rc.grade} | {rc.score}% | {blockers} |")
            lines.append("")
    except (ImportError, AttributeError):
        pass

    return "\n".join(lines)

    avg_conf = sum(c.confidence or 0 for c in components) / len(components)

    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Components | {len(components)} |")
    lines.append(f"| Avg Confidence | {avg_conf:.0%} |")
    lines.append(
        f"| With Signatures | {sum(1 for c in components if c.signatures)}/{len(components)} |"
    )
    lines.append(f"| With Symbols | {sum(1 for c in components if c.symbols)}/{len(components)} |")
    lines.append(
        f"| With Test Contracts | {sum(1 for c in components if c.test_contracts)}/{len(components)} |"
    )
    lines.append(f"| With Pattern | {sum(1 for c in components if c.pattern)}/{len(components)} |")
    lines.append(
        f"| With Interfaces | {sum(1 for c in components if c.interfaces)}/{len(components)} |"
    )
    lines.append("")

    # Confidence distribution
    buckets = {"≥90%": 0, "70-89%": 0, "50-69%": 0, "30-49%": 0, "<30%": 0}
    for c in components:
        conf = c.confidence or 0
        if conf >= 0.9:
            buckets["≥90%"] += 1
        elif conf >= 0.7:
            buckets["70-89%"] += 1
        elif conf >= 0.5:
            buckets["50-69%"] += 1
        elif conf >= 0.3:
            buckets["30-49%"] += 1
        else:
            buckets["<30%"] += 1

    lines.append("## Confidence Distribution")
    lines.append("")
    lines.append("| Bucket | Count | Bar |")
    lines.append("|--------|-------|-----|")
    for bucket, count in buckets.items():
        bar = "\u2588" * count
        lines.append(f"| {bucket} | {count} | {bar} |")
    lines.append("")

    # Per-component table
    lines.append("## Per-Component Metrics")
    lines.append("")
    lines.append("| Component | Confidence | Sigs | Symbols | Tests | Pattern | Files |")
    lines.append("|-----------|-----------|------|---------|-------|---------|-------|")
    for c in sorted(components, key=lambda x: -(x.confidence or 0)):
        conf = f"{c.confidence:.0%}" if c.confidence else "\u2014"
        sigs = len(c.signatures) if c.signatures else 0
        syms = len(c.symbols) if c.symbols else 0
        tests = len(c.test_contracts) if c.test_contracts else 0
        pattern = c.pattern or "\u2014"
        files = len(c.files) if c.files else 0
        lines.append(f"| {c.name} | {conf} | {sigs} | {syms} | {tests} | {pattern} | {files} |")
    lines.append("")

    # Low confidence action items
    low_conf = [c for c in components if (c.confidence or 0) < 0.5]
    if low_conf:
        lines.append("## Action Items (Low Confidence)")
        lines.append("")
        for c in low_conf:
            missing = []
            if not c.signatures:
                missing.append("signatures")
            if not c.symbols:
                missing.append("symbols")
            if not c.test_contracts:
                missing.append("test_contracts")
            if not c.pattern:
                missing.append("pattern")
            if not c.contract:
                missing.append("contract")
            lines.append(f"- **{c.name}** ({c.confidence:.0%}): missing {', '.join(missing)}")
        lines.append("")

    return "\n".join(lines)
