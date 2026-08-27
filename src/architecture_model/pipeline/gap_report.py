"""Markdown report generator for gap analysis results."""
from __future__ import annotations

from datetime import datetime, timezone

from .gap_analysis import GapAnalysisResult


def render_gap_report(result: GapAnalysisResult) -> str:
    """Render a GapAnalysisResult as a structured Markdown report."""
    lines: list[str] = []

    # Header
    lines.append("# Gap Analysis Report")
    lines.append("")
    lines.append(f"**Repository:** {result.repo_path}")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("")

    # Executive Summary
    summary = result.summary or {}
    total_gaps = summary.get("total_gaps", 0)
    if not total_gaps:
        total_gaps = sum(len(g.added) + len(g.removed) + len(g.renamed) for g in result.stage_gaps)
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- **Stages analyzed:** {summary.get('stages_analyzed', len(result.stage_gaps))}")
    lines.append(f"- **Total gaps:** {total_gaps}")
    lines.append(f"- **Naming chains:** {len(result.naming_chains)}")
    lines.append(f"- **Propagation traces:** {len(result.propagation_traces)}")
    lines.append("")

    # Per-Stage Comparison
    if result.stage_gaps:
        lines.append("## Per-Stage Comparison")
        lines.append("")
        lines.append("| Stage | Added | Removed | Renamed | Quality Delta |")
        lines.append("|-------|------:|--------:|--------:|--------------:|")
        for g in result.stage_gaps:
            lines.append(f"| {g.stage} | {len(g.added)} | {len(g.removed)} | {len(g.renamed)} | {g.quality_delta:+.1f} |")
        lines.append("")

    # Renamed Entities
    renamed_gaps = [g for g in result.stage_gaps if g.renamed]
    if renamed_gaps:
        lines.append("## Renamed Entities")
        lines.append("")
        for g in renamed_gaps:
            lines.append(f"### Stage: {g.stage}")
            lines.append("")
            lines.append("| Deterministic Name | LLM Name | Similarity |")
            lines.append("|-------------------|----------|:----------:|")
            for r in g.renamed:
                lines.append(f"| {r['det']} | {r['llm']} | {r['similarity']:.2f} |")
            lines.append("")

    # Naming Chains
    if result.naming_chains:
        lines.append("## Naming Chains")
        lines.append("")
        all_stages = sorted({s for c in result.naming_chains for s in (set(c.stages) | set(c.llm_stages))})
        header = "| Source |"
        sep = "|--------|"
        for s in all_stages:
            header += f" {s} (det/llm) |"
            sep += "------------|"
        header += " Generic |"
        sep += ":-------:|"
        lines.append(header)
        lines.append(sep)
        for c in result.naming_chains:
            row = f"| {c.source} |"
            for s in all_stages:
                det = c.stages.get(s, "—")
                llm = c.llm_stages.get(s, "—")
                row += f" {det} / {llm} |"
            row += f" {'yes' if c.is_generic else 'no'} |"
            lines.append(row)
        lines.append("")

    # Error Propagation
    if result.propagation_traces:
        lines.append("## Error Propagation")
        lines.append("")
        for trace in result.propagation_traces:
            lines.append(f"### Origin: {trace.origin_stage} — {trace.origin_entity}")
            lines.append(f"**Issue:** {trace.origin_issue}")
            lines.append("")
            for a in trace.affected:
                lines.append(f"- **{a['stage']}** → {a['entity']}: {a['effect']}")
            lines.append("")

    # Recommendations
    recommendations: list[str] = []
    generic_count = sum(1 for c in result.naming_chains if c.is_generic)
    if generic_count:
        recommendations.append(f"{generic_count} generic name(s) detected — consider domain-aware naming in infer stage")
    if result.propagation_traces:
        recommendations.append(f"{len(result.propagation_traces)} error propagation chain(s) found — add validation gates between stages")
    if renamed_gaps:
        total_renamed = sum(len(g.renamed) for g in renamed_gaps)
        recommendations.append(f"{total_renamed} renamed entit(ies) — LLM naming diverges from deterministic; review naming heuristics")
    if not recommendations:
        recommendations.append("No significant gaps detected — pipeline is well-calibrated")

    lines.append("## Recommendations")
    lines.append("")
    for i, rec in enumerate(recommendations[:3], 1):
        lines.append(f"{i}. {rec}")
    lines.append("")

    return "\n".join(lines)
