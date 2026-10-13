"""architecture_model.walks.verdict — Verdict taxonomy for classify stage.

Per Q4-locked: five verdicts replacing binary sufficient/insufficient.
Each verdict drives a distinct remediation.
"""

from __future__ import annotations

from enum import Enum

__all__ = ["Verdict", "VERDICT_SEVERITY"]


class Verdict(str, Enum):
    """The five verdicts an entity can receive.

    - READY_TO_CODE: attributes coherent + specific enough → realize.
    - NEEDS_DECOMP: attributes rich but heterogeneous → split entity.
    - NEEDS_ENRICHMENT: attributes sparse → author more.
    - NEEDS_VALIDATION: attributes present but unverified → gather evidence.
    - CONTRADICTORY: attributes conflict internally → resolve.
    """

    READY_TO_CODE = "ready-to-code"
    NEEDS_DECOMP = "needs-decomp"
    NEEDS_ENRICHMENT = "needs-enrichment"
    NEEDS_VALIDATION = "needs-validation"
    CONTRADICTORY = "contradictory"


# Severity ordering for viewer badges. Higher = worse.
VERDICT_SEVERITY: dict[Verdict, int] = {
    Verdict.READY_TO_CODE: 0,
    Verdict.NEEDS_VALIDATION: 1,
    Verdict.NEEDS_ENRICHMENT: 2,
    Verdict.NEEDS_DECOMP: 3,
    Verdict.CONTRADICTORY: 4,
}
