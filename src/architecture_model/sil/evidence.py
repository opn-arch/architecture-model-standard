"""SI&L → Promise evidence binding — Phase 5 of T0.14.

Aggregation layer: consumes existing :class:`SILRecord` objects and
lifts their signal into :class:`Promise` ``verified_by`` entries. NOT
a rewrite of :mod:`architecture_model.sil.{record,rollup,decorators}`
— those remain the source of truth. This module is the join.

Reference format for a SIL-derived evidence entry::

    SIL:<component_id>:<metric>=<value>
    SIL:<component_id>:healthy
    SIL:<component_id>:event=<event_id>

Rules:

* A SILRecord contributes evidence to a Promise iff
  ``sil_record.component_id == promise.owner_entity``.
* Evidence is emitted in a canonical order (metrics first, then event
  ids sorted ascending) so re-binding is idempotent and deterministic.
* Existing ``verified_by`` entries are preserved; duplicates removed
  while preserving first-seen order.
* TYPED_GAP promises still receive evidence — a design-declared gap
  can be evidenced (e.g. "we know we lack this and here's the SIL
  proof") without being closed.
"""

from __future__ import annotations

from dataclasses import replace

from architecture_model.core.promise import Promise
from architecture_model.sil.record import SILRecord

__all__ = ["derive_evidence_refs", "bind_evidence", "bind_evidence_bulk"]


def derive_evidence_refs(record: SILRecord) -> tuple[str, ...]:
    """Return the canonical evidence-ref tuple derived from a SILRecord.

    Order (stable across runs):

    1. ``SIL:<comp>:validation=<score>`` when metrics.validation_score is set
    2. ``SIL:<comp>:healthy`` when invocations_7d > 0 AND failure_rate_7d == 0.0
    3. ``SIL:<comp>:event=<event_id>`` for each outcome=ok event, sorted by
       event_id ascending (falls back to insertion order for events without ids)
    """
    comp = record.component_id
    refs: list[str] = []

    m = record.metrics
    if m.validation_score is not None:
        refs.append(f"SIL:{comp}:validation={m.validation_score}")
    if m.invocations_7d > 0 and m.failure_rate_7d == 0.0:
        refs.append(f"SIL:{comp}:healthy")

    ok_event_ids: list[str] = []
    for ev in record.events:
        if ev.kind == "outcome" and ev.outcome == "ok" and ev.event_id:
            ok_event_ids.append(ev.event_id)
    for eid in sorted(ok_event_ids):
        refs.append(f"SIL:{comp}:event={eid}")

    return tuple(refs)


def _dedupe_preserve_order(items: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return tuple(out)


def bind_evidence(
    promise: Promise, sil_records: list[SILRecord]
) -> Promise:
    """Return a new Promise with SIL-derived refs appended to verified_by.

    Only records whose ``component_id`` matches ``promise.owner_entity``
    contribute. If no records match, ``promise`` is returned unchanged
    (same object). Existing ``verified_by`` entries are preserved and
    duplicates are removed. Promise identity (id / attribute / content /
    owner) is invariant.
    """
    matching = [r for r in sil_records if r.component_id == promise.owner_entity]
    if not matching:
        return promise

    new_refs: list[str] = list(promise.verified_by)
    for rec in matching:
        for ref in derive_evidence_refs(rec):
            new_refs.append(ref)

    deduped = _dedupe_preserve_order(tuple(new_refs))
    if deduped == promise.verified_by:
        return promise
    return replace(promise, verified_by=deduped)


def bind_evidence_bulk(
    promises: list[Promise], sil_records: list[SILRecord]
) -> list[Promise]:
    """Apply :func:`bind_evidence` across a Promise list, preserving order."""
    if not sil_records:
        return list(promises)
    return [bind_evidence(p, sil_records) for p in promises]
