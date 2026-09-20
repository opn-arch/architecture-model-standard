"""Prompt refiner meta-walk (CAP-DF Part 15).

Realizes ``CAP-WK.prompt-refinement``.

Analyzes ``.architecture/llm_calls.jsonl`` and (optionally)
``.architecture/llm/endpoints.yaml`` to emit ``PromptTemplateCard``
verdicts per prompt template:

* ``high-failure`` — ``output_used=False`` rate ≥ 30% with ≥ 3 calls.
* ``high-cost``   — median ``total_tokens`` ≥ 4× overall median with ≥ 3 calls.
* ``unused``      — declared endpoint with zero journal entries.
* ``stable``      — declared, present, no failure/cost flag.

Verdicts are deterministic; the walk is a pure meta-walk (Tier T1, no
LLM). Thresholds live as module constants for easy tuning.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from architecture_model.feedback import llm_calls as _journal


HIGH_FAILURE_MIN_CALLS = 3
HIGH_FAILURE_RATE = 0.30
HIGH_COST_MIN_CALLS = 3
HIGH_COST_MULTIPLE = 4.0


@dataclass(frozen=True)
class PromptTemplateCard:
    """One refiner verdict for one prompt template (or declared endpoint)."""

    template_id: str
    verdict: str  # "stable" | "high-failure" | "high-cost" | "unused"
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RefinerReport:
    """Cards + aggregate counts by verdict."""

    cards: tuple[PromptTemplateCard, ...]
    counts: dict[str, int]


def _load_declared_templates(repo_path: Path) -> dict[str, str]:
    """Return ``{template_id: endpoint_id}`` from endpoints.yaml.

    Missing file → empty dict (unused-detection skipped downstream).
    Entries without a ``prompt_template`` field are skipped.
    """
    import yaml

    path = repo_path / ".architecture" / "llm" / "endpoints.yaml"
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}
    out: dict[str, str] = {}
    for entry in data.get("endpoints", []) or []:
        if not isinstance(entry, dict):
            continue
        tmpl = entry.get("prompt_template") or entry.get("task_class")
        if not tmpl:
            continue
        eid = entry.get("id", "")
        # If multiple endpoints share a template, keep the first — the
        # unused check only needs to know that ANY declared endpoint
        # names the template.
        out.setdefault(str(tmpl), str(eid))
    return out


def _bucket_by_template(
    records: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        tmpl = r.get("prompt_template") or ""
        if not tmpl:
            continue
        out.setdefault(tmpl, []).append(r)
    return out


def refine_prompts(repo_path: Path) -> RefinerReport:
    """Analyze the LLM call journal and emit prompt-template verdicts.

    Reads ``<repo>/.architecture/llm_calls.jsonl`` and optionally
    ``<repo>/.architecture/llm/endpoints.yaml``. Missing journal is
    treated as empty (all declared templates → ``unused``).
    """
    repo = Path(repo_path)
    records = _journal.read(repo)
    declared = _load_declared_templates(repo)
    buckets = _bucket_by_template(records)

    # Overall median tokens across all templates with ≥1 call (used as
    # the high-cost baseline).
    all_tokens = [
        int(r.get("total_tokens", 0) or 0)
        for r in records
        if int(r.get("total_tokens", 0) or 0) > 0
    ]
    overall_median = statistics.median(all_tokens) if all_tokens else 0.0

    cards: list[PromptTemplateCard] = []
    seen_templates: set[str] = set()

    # Present templates → classify against thresholds.
    for tmpl, entries in sorted(buckets.items()):
        seen_templates.add(tmpl)
        sample_size = len(entries)
        failures = sum(
            1 for e in entries if e.get("output_used", True) is False
        )
        failure_rate = failures / sample_size if sample_size else 0.0
        tokens = [
            int(e.get("total_tokens", 0) or 0)
            for e in entries
            if int(e.get("total_tokens", 0) or 0) > 0
        ]
        median_tokens = statistics.median(tokens) if tokens else 0.0

        verdict = "stable"
        if (
            sample_size >= HIGH_FAILURE_MIN_CALLS
            and failure_rate >= HIGH_FAILURE_RATE
        ):
            verdict = "high-failure"
        elif (
            sample_size >= HIGH_COST_MIN_CALLS
            and overall_median > 0
            and median_tokens >= HIGH_COST_MULTIPLE * overall_median
        ):
            verdict = "high-cost"

        details: dict[str, Any] = {
            "sample_size": sample_size,
            "failure_rate": round(failure_rate, 3),
            "median_tokens": median_tokens,
        }
        eid = declared.get(tmpl)
        if eid:
            details["endpoint_id"] = eid
        cards.append(
            PromptTemplateCard(
                template_id=tmpl, verdict=verdict, details=details
            )
        )

    # Declared-but-absent templates → unused.
    for tmpl, eid in sorted(declared.items()):
        if tmpl in seen_templates:
            continue
        cards.append(
            PromptTemplateCard(
                template_id=tmpl,
                verdict="unused",
                details={"sample_size": 0, "endpoint_id": eid},
            )
        )

    counts: dict[str, int] = {}
    for c in cards:
        counts[c.verdict] = counts.get(c.verdict, 0) + 1
    return RefinerReport(cards=tuple(cards), counts=counts)


__all__ = [
    "HIGH_COST_MIN_CALLS",
    "HIGH_COST_MULTIPLE",
    "HIGH_FAILURE_MIN_CALLS",
    "HIGH_FAILURE_RATE",
    "PromptTemplateCard",
    "RefinerReport",
    "refine_prompts",
]
