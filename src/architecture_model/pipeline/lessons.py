"""Lessons generator — extracts actionable insights from pipeline results."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .protocol import Diagnostic, LLMCallRecord, Uncertainty


@dataclass
class LessonEntry:
    """A single actionable lesson from a pipeline run."""

    stage: str
    summary: str
    count: int = 1
    severity: str = "info"

    @classmethod
    def from_diagnostics(
        cls, stage: str, diagnostics: list[Diagnostic]
    ) -> list[LessonEntry]:
        """Aggregate repeated diagnostic codes into lessons."""
        code_counts: Counter[str] = Counter()
        code_msg: dict[str, str] = {}
        code_sev: dict[str, str] = {}
        for d in diagnostics:
            code_counts[d.code] += 1
            code_msg[d.code] = d.message
            code_sev[d.code] = d.severity

        entries: list[LessonEntry] = []
        for code, count in code_counts.most_common():
            msg = code_msg[code]
            if count > 1:
                summary = f"{msg} ({count} instances)"
            else:
                summary = msg
            entries.append(
                cls(stage=stage, summary=summary, count=count, severity=code_sev[code])
            )
        return entries

    @classmethod
    def from_uncertainties(
        cls, stage: str, uncertainties: list[Uncertainty]
    ) -> list[LessonEntry]:
        """Summarize uncertainty patterns."""
        cat_counts: Counter[str] = Counter()
        cat_desc: dict[str, str] = {}
        for u in uncertainties:
            cat_counts[u.category] += 1
            cat_desc[u.category] = u.description

        entries: list[LessonEntry] = []
        for cat, count in cat_counts.most_common():
            if count > 1:
                summary = f"{cat.replace('_', ' ').capitalize()} required resolution ({count} instances)"
            else:
                summary = cat_desc[cat]
            entries.append(cls(stage=stage, summary=summary, count=count))
        return entries

    @classmethod
    def from_llm_calls(
        cls, stage: str, calls: list[LLMCallRecord]
    ) -> list[LessonEntry]:
        """Extract patterns from LLM usage."""
        if not calls:
            return []

        entries: list[LessonEntry] = []

        # Group by purpose
        purpose_counts: Counter[str] = Counter()
        purpose_items: Counter[str] = Counter()
        for c in calls:
            purpose_counts[c.purpose] += 1
            purpose_items[c.purpose] += c.items_produced

        for purpose, count in purpose_counts.most_common():
            items = purpose_items[purpose]
            purpose_label = purpose.replace("_", " ").capitalize()
            if items:
                entries.append(
                    cls(
                        stage=stage,
                        summary=f"{purpose_label} required LLM enrichment for {items} items",
                        count=count,
                    )
                )
            else:
                entries.append(
                    cls(
                        stage=stage,
                        summary=f"{purpose_label} required {count} LLM call{'s' if count > 1 else ''}",
                        count=count,
                    )
                )

        # Cache savings
        cached = [c for c in calls if c.cached]
        if cached:
            saved_tokens = sum(c.total_tokens for c in cached)
            entries.append(
                cls(
                    stage=stage,
                    summary=f"{len(cached)} cache hit{'s' if len(cached) > 1 else ''} saved {saved_tokens:,} tokens",
                    count=len(cached),
                )
            )

        return entries


def generate_lessons(
    entries: list[LessonEntry],
    system_name: str = "System",
) -> str:
    """Generate markdown lessons grouped by stage."""
    if not entries:
        return f"# Lessons: {system_name}\n\nNo lessons to report.\n"

    by_stage: dict[str, list[LessonEntry]] = {}
    for e in entries:
        by_stage.setdefault(e.stage, []).append(e)

    lines: list[str] = [f"# Lessons: {system_name}", ""]
    for stage, stage_entries in by_stage.items():
        lines.append(f"## Stage: {stage}")
        for e in stage_entries:
            lines.append(f"- {e.summary}")
        lines.append("")

    return "\n".join(lines)
