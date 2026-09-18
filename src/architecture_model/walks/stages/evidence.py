"""architecture_model.walks.stages.evidence — Attach verified_by paths.

For each classified entity, gather evidence at the declared tier and
attach verified_by paths to the card. Tiers:

  - structural: attribute presence + edges (cheapest)
  - behavioral: paired tests / verify_by paths on attributes
  - semantic: intent/goals/requirements text quality (heuristic)

Evidence is additive — sources listed in EvidenceSpec.sources are all
consulted. Missing sources are silent-skipped.
"""

from __future__ import annotations

from typing import Any

from architecture_model.pipeline_v3.substrate import Stage, wrap_function
from architecture_model.walks.attribute import Attribute
from architecture_model.walks.spec.loader import EvidenceSpec, WalkSpec

__all__ = ["evidence_stage"]


def _collect_from_model(entity: dict[str, Any]) -> list[str]:
    """Return verified_by paths from all attributes on the entity."""
    paths: list[str] = []
    for k, v in entity.items():
        if k in ("id", "name", "kind", "status"):
            continue
        try:
            a = Attribute.from_dict(v) if v is not None else Attribute(value=None)
        except Exception:  # noqa: BLE001
            continue
        paths.extend(a.verified_by)
    return paths


def _collect_evidence(
    entity: dict[str, Any], evidence: EvidenceSpec
) -> list[str]:
    paths: list[str] = []
    for src in evidence.sources:
        if src == "model":
            paths.extend(_collect_from_model(entity))
        # Additional sources (promises, tests, docs) resolved lazily by
        # future retrofits — silent-skip for now (L7/L10).
    # Deterministic order.
    return sorted(dict.fromkeys(paths))


def _run_evidence(input: dict[str, Any]) -> dict[str, Any]:
    spec: WalkSpec = input["spec"]
    classifications = input["classifications"]
    for c in classifications:
        c["verified_by"] = _collect_evidence(c["entity"], spec.evidence)
        c["evidence_tier"] = spec.evidence.tier
    return input


def evidence_stage() -> Stage:
    return wrap_function("evidence", _run_evidence)
