"""Standalone per-entity quality metrics — Phase 4 of T0.14.

Realizes CAP-DF-GATING telemetry: per-entity quality scores computed
WITHOUT chain-closure. Complementary to
:mod:`architecture_model.quality.chain_closure` — those metrics are
graph-relative (need cross-entity Promise lineage); these are
entity-relative and cheap to compute per commit.

Metrics:

* ``completeness_pct`` — fraction of canonical semantic fields
  (:data:`architecture_model.migration.v2_to_v3.SEMANTIC_FIELDS`) that
  have at least one Promise on the entity. Duplicate attributes count
  once.
* ``provenance_integrity_pct`` — fraction of the entity's Promises whose
  ``provenance`` field is non-empty. Vacuously 1.0 when the entity has
  no Promises (nothing UN-stamped).
* ``typed_gap_pct`` — fraction of the entity's Promises with
  ``status == TYPED_GAP``. Named absences are a signal of maturity, not
  a defect — this metric reports the "gap surface named" ratio.
* ``relationship_density`` — count of relationships where the entity
  appears as ``from`` or ``to``. Self-loops count once. Zero when the
  caller doesn't supply a relationships list.

``overall_score`` = weighted 0..100 rubric:

* 45 pts × ``completeness_pct``
* 25 pts × ``provenance_integrity_pct``
* 15 pts × (1 if ``typed_gap_pct`` <= 0.5 else (1 - (typed_gap_pct-0.5)*2))
* 15 pts × min(1.0, ``relationship_density`` / 10)

Rationale: completeness is the highest weight (drives regen fidelity);
provenance is next (drives auditability); typed-gap and relationship
density are corroborating signals with lower weight and diminishing
returns (10 relationships saturates the density term).
"""

from __future__ import annotations

from dataclasses import dataclass

from architecture_model.core.promise import Promise, PromiseStatus
from architecture_model.migration.v2_to_v3 import SEMANTIC_FIELDS

__all__ = ["StandaloneScore", "score_entity", "score_model"]


_RELATIONSHIP_DENSITY_SATURATION = 10


@dataclass(frozen=True)
class StandaloneScore:
    """Per-entity quality snapshot."""

    entity_id: str
    completeness_pct: float
    provenance_integrity_pct: float
    typed_gap_pct: float
    relationship_density: int
    overall_score: int
    promise_count: int


def _promises_for(entity_id: str, promises: list[Promise]) -> list[Promise]:
    return [p for p in promises if p.owner_entity == entity_id]


def _completeness(entity_promises: list[Promise]) -> float:
    if not SEMANTIC_FIELDS:
        return 1.0
    attrs = {p.attribute for p in entity_promises if p.attribute in SEMANTIC_FIELDS}
    return len(attrs) / len(SEMANTIC_FIELDS)


def _provenance_integrity(entity_promises: list[Promise]) -> float:
    if not entity_promises:
        return 1.0
    stamped = sum(1 for p in entity_promises if p.provenance)
    return stamped / len(entity_promises)


def _typed_gap_pct(entity_promises: list[Promise]) -> float:
    if not entity_promises:
        return 0.0
    gap_ct = sum(1 for p in entity_promises if p.status == PromiseStatus.TYPED_GAP)
    return gap_ct / len(entity_promises)


def _relationship_density(
    entity_id: str, relationships: list[dict] | None
) -> int:
    if not relationships:
        return 0
    touched = 0
    for r in relationships:
        if r.get("from") == entity_id or r.get("to") == entity_id:
            touched += 1
    return touched


def _typed_gap_term(pct: float) -> float:
    """Saturating penalty above 50% — too much gap surface signals stall."""
    if pct <= 0.5:
        return 1.0
    return max(0.0, 1.0 - (pct - 0.5) * 2.0)


def _overall(
    completeness: float,
    provenance: float,
    typed_gap: float,
    density: int,
) -> int:
    density_term = min(1.0, density / _RELATIONSHIP_DENSITY_SATURATION)
    raw = (
        45.0 * completeness
        + 25.0 * provenance
        + 15.0 * _typed_gap_term(typed_gap)
        + 15.0 * density_term
    )
    return int(round(max(0.0, min(100.0, raw))))


def score_entity(
    entity_id: str,
    promises: list[Promise],
    *,
    relationships: list[dict] | None = None,
) -> StandaloneScore:
    """Score a single entity from a (possibly graph-wide) Promise list."""
    owned = _promises_for(entity_id, promises)
    completeness = _completeness(owned)
    provenance = _provenance_integrity(owned)
    typed_gap = _typed_gap_pct(owned)
    density = _relationship_density(entity_id, relationships)
    overall = _overall(completeness, provenance, typed_gap, density)
    return StandaloneScore(
        entity_id=entity_id,
        completeness_pct=completeness,
        provenance_integrity_pct=provenance,
        typed_gap_pct=typed_gap,
        relationship_density=density,
        overall_score=overall,
        promise_count=len(owned),
    )


def score_model(
    entity_ids: list[str],
    promises: list[Promise],
    *,
    relationships: list[dict] | None = None,
) -> dict[str, StandaloneScore]:
    """Score every entity in ``entity_ids`` against the shared Promise pool."""
    return {
        eid: score_entity(eid, promises, relationships=relationships)
        for eid in entity_ids
    }
