"""Per-stage LLM review prompt building and response parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .protocol import QualityMetrics


@dataclass
class ReviewResult:
    """Parsed LLM review response."""
    rating: int = 0
    suggestions: list[str] = field(default_factory=list)
    raw: str = ""


def build_review_prompt(
    stage_name: str,
    quality: QualityMetrics,
    summary: str = "",
) -> str:
    """Build a review prompt for an LLM to assess a pipeline stage's output."""
    lines = [
        f"## Pipeline Stage Review: {stage_name}",
        f"Overall score: {quality.score:.0f}/100",
        "",
        "### Sub-scores:",
    ]
    for k, v in quality.sub_scores.items():
        lines.append(f"- {k}: {v:.1f}")

    if quality.component_scores:
        lines.append("")
        lines.append("### Per-component quality:")
        for comp_id, comp_q in quality.component_scores.items():
            lines.append(f"- {comp_id}: {comp_q.score:.0f}/100")
            for sk, sv in comp_q.sub_scores.items():
                lines.append(f"  - {sk}: {sv:.1f}")

    if summary:
        lines.append("")
        lines.append(f"### Stage summary: {summary}")

    lines.extend([
        "",
        "Rate this stage output 1-10 and provide actionable suggestions.",
        "Format:",
        "QUALITY: X/10",
        "SUGGESTIONS:",
        "- suggestion 1",
        "- suggestion 2",
    ])
    return "\n".join(lines)


def parse_review_response(response: str) -> ReviewResult:
    """Parse an LLM review response into structured data."""
    if not response:
        return ReviewResult(raw=response)

    # Extract rating
    rating = 0
    rating_match = re.search(r"QUALITY:\s*(\d+)/10", response)
    if rating_match:
        rating = int(rating_match.group(1))

    # Extract suggestions
    suggestions: list[str] = []
    in_suggestions = False
    for line in response.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("SUGGESTIONS"):
            in_suggestions = True
            continue
        if in_suggestions and stripped.startswith("- "):
            suggestions.append(stripped[2:].strip())

    return ReviewResult(rating=rating, suggestions=suggestions, raw=response)
