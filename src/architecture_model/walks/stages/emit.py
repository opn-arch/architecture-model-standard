"""architecture_model.walks.stages.emit — Card assembly.

Produce viewer-consumable Card records from classifications. Each Card
carries the walk id, entity, verdict, reasons, evidence, and severity.

Composition-friendly: Cards include the entity payload verbatim so a
downstream walk consuming this walk's output via ``from_walk`` can
re-classify without model access.
"""

from __future__ import annotations

from typing import Any

from architecture_model.pipeline_v3.substrate import Stage, wrap_function
from architecture_model.walks.spec.loader import WalkSpec
from architecture_model.walks.verdict import VERDICT_SEVERITY, Verdict

__all__ = ["emit_stage"]


def _severity_for(verdict: str) -> int:
    try:
        return VERDICT_SEVERITY[Verdict(verdict)]
    except (KeyError, ValueError):
        return -1


def _run_emit(input: dict[str, Any]) -> dict[str, Any]:
    spec: WalkSpec = input["spec"]
    classifications = input["classifications"]

    cards = []
    for c in classifications:
        cards.append(
            {
                "walk_id": spec.id,
                "audits": list(spec.audits),
                "entity_id": c.get("entity_id"),
                "entity": c["entity"],
                "verdict": c["verdict"],
                "severity": _severity_for(c["verdict"]),
                "reasons": list(c.get("reasons", [])),
                "verified_by": list(c.get("verified_by", [])),
                "evidence_tier": c.get("evidence_tier", "structural"),
                "rollup_notes": list(c.get("rollup_notes", [])),
                "card_template": spec.emit.card_template,
            }
        )

    # Deterministic order — sort by (severity desc, entity_id).
    cards.sort(key=lambda c: (-int(c["severity"]), c.get("entity_id") or ""))

    return {
        "walk_id": spec.id,
        "audits": list(spec.audits),
        "cards": cards,
    }


def emit_stage() -> Stage:
    return wrap_function("emit", _run_emit)
