"""Chain-closure quality module — Phase 3 of T0.14 (v3 bootstrap).

Realizes CAP-DF-VERIFY:
    "Verify delivery-down and verify-up chain closure at both structural
     and per-attribute levels. Gaps are typed (named categories), never
     silent NULLs."

Consumes a Promise-graph (see :mod:`architecture_model.core.promise`) and
emits a :class:`ChainClosureReport` with three typed gap categories:

- ``G-DELIVERY`` — a Promise has no upstream delivery lineage. Sub-cases:
  * missing ``delivered_from`` on a non-root owner
  * ``delivered_from`` points to an id absent from the graph
- ``G-VERIFY`` — a Promise (not itself a TYPED_GAP) has no
  ``verified_by`` evidence records. Also fires when a Promise's status
  is ``VERIFIED`` but ``verified_by`` is empty (structural inconsistency).
- ``G-OPEN-Q`` — a Promise whose ``attribute == "open_questions"`` and
  whose content is a non-empty question or list of questions. Each
  question yields one gap.

Promises with ``status == TYPED_GAP`` are exempt from delivery/verify
checks — the gap is already named on the Promise itself.

Root owners (typically actors) are exempt from ``G-DELIVERY``: they have
no upstream by design. Callers declare roots via ``root_owner_ids``.

closure_pct = 1 - gap_count / promise_count, clamped to [0, 1]. Empty
graph vacuously yields 1.0.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable

from architecture_model.core.promise import Promise, PromiseStatus

__all__ = [
    "GAP_DELIVERY",
    "GAP_VERIFY",
    "GAP_OPEN_Q",
    "Gap",
    "ChainClosureReport",
    "analyze_chain_closure",
]


GAP_DELIVERY = "G-DELIVERY"
GAP_VERIFY = "G-VERIFY"
GAP_OPEN_Q = "G-OPEN-Q"


@dataclass(frozen=True)
class Gap:
    """A single typed gap in the Promise-graph.

    Attributes:
        gap: One of ``G-DELIVERY`` / ``G-VERIFY`` / ``G-OPEN-Q``.
        promise_id: Id of the Promise that carries the gap.
        owner_entity: Entity that owns the offending Promise.
        attribute: Semantic field the Promise represents.
        reason: Free-text remediation hint. For ``G-OPEN-Q`` this is
            the question text itself.
    """

    gap: str
    promise_id: str
    owner_entity: str
    attribute: str
    reason: str


@dataclass(frozen=True)
class ChainClosureReport:
    """Structured chain-closure result over a Promise-graph."""

    gaps: list[Gap]
    closure_pct: float
    gap_counts: dict[str, int]
    status_counts: dict[PromiseStatus, int]
    total_promises: int


def _iter_open_questions(content: object) -> Iterable[str]:
    """Yield each question from an open_questions Promise's content."""
    if isinstance(content, str):
        stripped = content.strip()
        if stripped:
            yield stripped
        return
    if isinstance(content, (list, tuple)):
        for item in content:
            if isinstance(item, str) and item.strip():
                yield item.strip()


def analyze_chain_closure(
    promises: list[Promise],
    *,
    root_owner_ids: frozenset[str] | set[str] | None = None,
) -> ChainClosureReport:
    """Compute chain-closure over ``promises``.

    Args:
        promises: The full Promise-graph to analyze.
        root_owner_ids: Owner entity ids exempt from ``G-DELIVERY``
            (typically actors / top-level capabilities). ``None`` means
            "no exemptions" — every non-root-lineage Promise is flagged.
    """
    roots = frozenset(root_owner_ids or ())
    known_ids = {p.id for p in promises}
    gaps: list[Gap] = []
    status_counts: Counter[PromiseStatus] = Counter()

    for p in promises:
        status_counts[p.status] += 1

        # TYPED_GAP is a named absence — skip structural checks
        if p.status == PromiseStatus.TYPED_GAP:
            continue

        # G-DELIVERY
        if p.delivered_from is None:
            if p.owner_entity not in roots:
                gaps.append(
                    Gap(
                        gap=GAP_DELIVERY,
                        promise_id=p.id,
                        owner_entity=p.owner_entity,
                        attribute=p.attribute,
                        reason=(
                            f"no delivered_from and owner {p.owner_entity!r} "
                            f"not declared root"
                        ),
                    )
                )
        elif p.delivered_from not in known_ids:
            gaps.append(
                Gap(
                    gap=GAP_DELIVERY,
                    promise_id=p.id,
                    owner_entity=p.owner_entity,
                    attribute=p.attribute,
                    reason=(
                        f"broken lineage: delivered_from={p.delivered_from!r} "
                        f"not in graph"
                    ),
                )
            )

        # G-VERIFY
        if not p.verified_by:
            reason = (
                "status=VERIFIED but verified_by is empty"
                if p.status == PromiseStatus.VERIFIED
                else "no verified_by evidence"
            )
            gaps.append(
                Gap(
                    gap=GAP_VERIFY,
                    promise_id=p.id,
                    owner_entity=p.owner_entity,
                    attribute=p.attribute,
                    reason=reason,
                )
            )

        # G-OPEN-Q
        if p.attribute == "open_questions":
            for question in _iter_open_questions(p.content):
                gaps.append(
                    Gap(
                        gap=GAP_OPEN_Q,
                        promise_id=p.id,
                        owner_entity=p.owner_entity,
                        attribute=p.attribute,
                        reason=question,
                    )
                )

    # closure_pct
    total = len(promises)
    if total == 0:
        closure_pct = 1.0
    else:
        # Cap gaps-per-promise at 1 for the closure metric to keep it
        # bounded — a single Promise with 20 open questions shouldn't
        # push closure_pct below zero.
        offending_ids = {g.promise_id for g in gaps}
        raw = 1.0 - (len(offending_ids) / total)
        closure_pct = max(0.0, min(1.0, raw))

    gap_counts_dict = dict(Counter(g.gap for g in gaps))

    return ChainClosureReport(
        gaps=gaps,
        closure_pct=closure_pct,
        gap_counts=gap_counts_dict,
        status_counts=dict(status_counts),
        total_promises=total,
    )
