"""Format enrichment context for single-pass agent annotation.

Given a tree of decomposition results, produces a compact prompt
that lets the agent classify every leaf with a pattern + one-sentence contract.
"""
from __future__ import annotations

from architecture_model.orchestration.deep_decompose import DecomposeResult
from architecture_model.patterns import load_patterns


def format_enrichment_prompt(decompositions: list[DecomposeResult]) -> str:
    """Format all leaves for agent pattern/contract annotation.

    Returns a prompt string containing:
    1. Available patterns with indicators
    2. All leaf components with their files/classes/functions
    3. Instructions for annotation format
    """
    sections: list[str] = []

    # Section 1: Pattern catalog (compact)
    patterns = load_patterns()
    sections.append("## Available Patterns\n")
    for name, p in patterns.items():
        indicators = ", ".join(p["indicators"][:3])
        sections.append(f"- **{name}**: {p['description']} [{indicators}]")

    sections.append("")

    # Section 2: Leaves to annotate
    sections.append("## Components to Annotate\n")
    for decomp in decompositions:
        sections.append(f"### {decomp.block_name} ({decomp.block_id})\n")
        for sc in decomp.sub_components:
            files_str = ", ".join(sc.files[:5])
            if len(sc.files) > 5:
                files_str += f" +{len(sc.files) - 5} more"
            classes_str = ", ".join(sc.classes[:4]) if sc.classes else "-"
            funcs_str = ", ".join(sc.functions[:4]) if sc.functions else "-"
            sections.append(
                f"**{sc.id}** ({sc.line_count} lines)\n"
                f"  Files: {files_str}\n"
                f"  Classes: {classes_str}\n"
                f"  Functions: {funcs_str}\n"
            )

    # Section 3: Instructions
    sections.append("## Instructions\n")
    sections.append(
        "For each component above, respond with YAML:\n"
        "```yaml\n"
        "- id: COMP-XX-N\n"
        "  pattern: <pattern-name or 'custom'>\n"
        "  contract: <one sentence: what it does, for whom, how>\n"
        "```\n\n"
        "Rules:\n"
        "- Contract must be ONE sentence (no 'and' joining two responsibilities)\n"
        "- If no pattern fits, use 'custom' and the contract still applies\n"
        "- Use indicators + file/class names to infer pattern\n"
    )

    return "\n".join(sections)
