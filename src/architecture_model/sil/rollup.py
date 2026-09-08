"""B2.1.3 — Roll up runtime SI&L records into an architecture-component record.

Given an architecture-component ``SILRecord`` and the runtime records for the
pipeline stages / MCP tools / renderers that touch the modules allocated to
that architecture component, produce a merged copy of the arch record with:

* ``rollup.runtime_components`` — insertion-ordered, deduped list of runtime
  component IDs whose scope overlaps the arch component's modules.
* ``metrics.invocations_7d`` — sum across runtime records.
* ``metrics.avg_duration_ms`` — invocation-weighted average.
* ``metrics.failure_rate_7d`` — invocation-weighted average.

Arch-only metric fields (``validation_score``, ``drift_flag_count``,
``regen_readiness``, ``lesson_count``) are preserved from the input.
The input record is never mutated.
"""

from __future__ import annotations

import copy
import os
from dataclasses import replace
from datetime import datetime, timezone

from architecture_model.sil.record import Metrics, Rollup, SILRecord


def _now_iso() -> str:
    """Return current UTC time as ISO 8601, or ``AMS_DETERMINISTIC_NOW`` if set.

    Mirrors the pattern established in ``pipeline/synthesize.py`` (B1.2.8) so
    rolled-up records are byte-identical across runs under the reproducibility
    harness.
    """
    pinned = os.environ.get("AMS_DETERMINISTIC_NOW")
    if pinned:
        return pinned
    return datetime.now(timezone.utc).isoformat()


def rollup_component(
    arch: SILRecord,
    runtime: list[SILRecord],
    *,
    allocation_map: dict[str, list[str]],
    module_to_runtime: dict[str, list[str]],
) -> SILRecord:
    """Merge runtime records that touch modules allocated to ``arch``.

    See module docstring for aggregation rules. Returns a new ``SILRecord``;
    ``arch`` is not mutated.
    """
    # 1. Collect runtime IDs touching any allocated module, deduped, insertion order.
    modules = allocation_map.get(arch.component_id, [])
    runtime_ids: list[str] = []
    seen: set[str] = set()
    for module in modules:
        for rid in module_to_runtime.get(module, []):
            if rid not in seen:
                seen.add(rid)
                runtime_ids.append(rid)

    # 2. Filter runtime records to that set, preserving discovery order.
    by_id = {r.component_id: r for r in runtime if r.component_id in seen}
    relevant = [by_id[rid] for rid in runtime_ids if rid in by_id]

    # 3. Aggregate metrics. Zero-invocation records still appear in
    #    runtime_components but contribute nothing to weighted averages.
    total_inv = sum(r.metrics.invocations_7d for r in relevant)
    if total_inv > 0:
        weighted_duration = (
            sum(r.metrics.avg_duration_ms * r.metrics.invocations_7d for r in relevant)
            / total_inv
        )
        weighted_failure = (
            sum(r.metrics.failure_rate_7d * r.metrics.invocations_7d for r in relevant)
            / total_inv
        )
    else:
        weighted_duration = 0.0
        weighted_failure = 0.0

    # 4. Build merged metrics: preserve arch-only fields, override runtime ones.
    merged_metrics = replace(
        arch.metrics,
        invocations_7d=total_inv,
        avg_duration_ms=weighted_duration,
        failure_rate_7d=weighted_failure,
    )

    # 5. Build merged record without mutating input (deep-copy events list too).
    return SILRecord(
        component_id=arch.component_id,
        kind=arch.kind,
        name=arch.name,
        metrics=merged_metrics,
        last_touched_revision=arch.last_touched_revision,
        last_touched_at=arch.last_touched_at,
        events=copy.deepcopy(arch.events),
        rollup=Rollup(
            runtime_components=runtime_ids,
            aggregated_at=_now_iso(),
        ),
    )
