"""Per-stage LLM review prompt building and response parsing."""

from __future__ import annotations

import json as _json
import re
from dataclasses import dataclass, field
from typing import Any

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


@dataclass
class Correction:
    """A single auto-correction suggested by the LLM."""
    entity_id: str
    field: str
    action: str  # "improve", "add", "fix", "remove"
    value: Any = ""
    confidence: float = 0.0


@dataclass
class CorrectionResult:
    """Full parsed correction response from LLM."""
    stage_assessment: str = ""
    corrections: list[Correction] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    raw: str = ""


def build_semantic_review_prompt(
    stage_name: str,
    quality: QualityMetrics,
    gate_results: list,
    components: list[dict],
    modules: list[dict],
    summary: str = "",
) -> str:
    """Build a three-level semantic review prompt for LLM.

    Three levels:
    - Stage: overall metrics, gate results, summary
    - Component: ID, name, intent, file count, quality score
    - Module: path, function count, quality score

    Instructs LLM to return JSON with corrections.
    """
    lines = [
        f"# Pipeline Stage Review: {stage_name}",
        f"Overall quality score: {quality.score:.0f}/100",
    ]
    if quality.sub_scores:
        lines.append("\n## Stage Metrics")
        for k, v in quality.sub_scores.items():
            lines.append(f"- {k}: {v:.1f}")
    if gate_results:
        lines.append("\n## Gate Results")
        for gr in gate_results:
            lines.append(f"- {gr.message}")
    if summary:
        lines.append(f"\n## Summary\n{summary}")
    if components:
        lines.append("\n## Components")
        lines.append("| ID | Name | Intent | Files | Quality |")
        lines.append("|---|---|---|---|---|")
        for c in components:
            intent = c.get("intent", "—")
            lines.append(f"| {c['id']} | {c['name']} | {intent} | {c.get('file_count', '?')} | {c.get('quality', '?')} |")
        # Layer validation for allocate stage
        if stage_name == "allocate":
            lines.append("\n## LAYER VALIDATION")
            lines.append("For each component, verify the layer assignment is correct.")
            lines.append("If all components share the same layer, this likely indicates the layer classifier missed domain-specific patterns.")
            lines.append("Components:")
            for c in components:
                layer = c.get("layer", "unknown")
                files = c.get("files", [])
                lines.append(f"- {c['name']}: layer={layer}, files={files}")
            lines.append('Reply with corrections: {"corrections": [{"entity_id": "...", "field": "layer", "old": "...", "new": "..."}]}')
    if modules:
        lines.append("\n## Modules")
        lines.append("| Path | Functions | Quality |")
        lines.append("|---|---|---|")
        for m in modules:
            lines.append(f"| {m['path']} | {m.get('functions', '?')} | {m.get('quality', '?')} |")
    lines.extend([
        "\n## Instructions",
        "Review the stage output and return a JSON object with this exact structure:",
        "```json",
        "{",
        '  "stage_assessment": "Brief assessment of this stage",',
        '  "corrections": [',
        '    {"entity_id": "COMP-X", "field": "intent", "action": "improve", "value": "new value", "confidence": 0.9}',
        "  ],",
        '  "warnings": ["warning text"],',
        '  "suggestions": ["suggestion text"]',
        "}",
        "```",
        "",
        "Correction actions: improve, add, fix, remove.",
        "Fields: intent, moes, failure_modes, status, trade_offs, layer.",
        "Set confidence >= 0.8 for corrections you are certain about.",
        "Return ONLY the JSON object, no other text.",
    ])
    return "\n".join(lines)


def parse_correction_response(response: str) -> CorrectionResult:
    """Parse LLM response into structured corrections."""
    if not response:
        return CorrectionResult(raw=response)
    text = response.strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    try:
        data = _json.loads(text)
    except _json.JSONDecodeError:
        return CorrectionResult(raw=response)
    corrections = []
    for c in data.get("corrections", []):
        corrections.append(Correction(
            entity_id=c.get("entity_id", ""),
            field=c.get("field", ""),
            action=c.get("action", ""),
            value=c.get("value", ""),
            confidence=c.get("confidence", 0.0),
        ))
    return CorrectionResult(
        stage_assessment=data.get("stage_assessment", ""),
        corrections=corrections,
        warnings=data.get("warnings", []),
        suggestions=data.get("suggestions", []),
        raw=response,
    )
