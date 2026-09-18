"""architecture_model.walks.stages.rollup — Category-aware verdict propagation.

Propagates verdicts along a relationship type per RollupSpec. Strategy
depends on attribute category:

  - A (authoring): union — parent inherits children's items.
  - B (specification): conjunction — parent verdict = ∧ children (worst).
  - C (promise): contract-composition — any-child-ok if the child
    realizes the parent's promise surface; else worst-child.

Concrete strategies:
  - ``worst-child``: parent's verdict = worst of children's.
  - ``any-child-ok``: parent OK if any child is ready-to-code.
  - ``union``: verdict remains; reasons union.
  - ``conjunction``: same as worst-child (semantic alias).
  - ``contract-composition``: any-child-ok fused with worst-child on
    unrealized subset.
"""

from __future__ import annotations

from typing import Any

from architecture_model.pipeline_v3.substrate import Stage, wrap_function
from architecture_model.walks.spec.loader import RollupSpec, WalkSpec
from architecture_model.walks.verdict import VERDICT_SEVERITY, Verdict

__all__ = ["rollup_stage"]


def _severity(verdict_name: str) -> int:
    try:
        return VERDICT_SEVERITY[Verdict(verdict_name)]
    except (KeyError, ValueError):
        return 999


def _index_children(
    model: dict[str, Any], via: str
) -> dict[str, list[str]]:
    """Map parent_id -> [child_ids] via the given relationship type."""
    idx: dict[str, list[str]] = {}
    for r in model.get("relationships", []):
        if r.get("type") != via:
            continue
        idx.setdefault(r.get("from", ""), []).append(r.get("to", ""))
    return idx


def _rollup(
    classifications: list[dict[str, Any]], rollup: RollupSpec, model: dict[str, Any]
) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {
        c["entity_id"]: c for c in classifications if c.get("entity_id")
    }
    children = _index_children(model, rollup.via)

    def _resolve(parent_id: str, visited: set[str]) -> dict[str, Any]:
        if parent_id in visited:
            return by_id[parent_id]
        visited.add(parent_id)
        parent = by_id.get(parent_id)
        if parent is None:
            return {}

        child_ids = children.get(parent_id, [])
        if not child_ids:
            return parent

        # Recursively resolve children first.
        for cid in child_ids:
            if cid in by_id:
                _resolve(cid, visited)

        child_verdicts = [
            by_id[cid]["verdict"] for cid in child_ids if cid in by_id
        ]
        if not child_verdicts:
            return parent

        strategy = rollup.strategy
        parent_verdict = parent["verdict"]
        new_verdict = parent_verdict
        note: str | None = None

        if strategy in ("worst-child", "conjunction"):
            all_verdicts = child_verdicts + [parent_verdict]
            new_verdict = max(all_verdicts, key=_severity)
            note = f"rollup {strategy} via {rollup.via}: worst of {sorted(set(all_verdicts))}"
        elif strategy == "any-child-ok":
            if any(v == Verdict.READY_TO_CODE.value for v in child_verdicts):
                new_verdict = Verdict.READY_TO_CODE.value
                note = f"rollup any-child-ok via {rollup.via}: at least one ready"
            else:
                new_verdict = max(child_verdicts, key=_severity)
                note = f"rollup any-child-ok via {rollup.via}: no child ready; worst child"
        elif strategy == "union":
            # Verdict unchanged; reasons will be unioned below.
            note = f"rollup union via {rollup.via}: reasons unioned"
        elif strategy == "contract-composition":
            # C-category promise composition.
            if any(v == Verdict.READY_TO_CODE.value for v in child_verdicts):
                new_verdict = (
                    Verdict.READY_TO_CODE.value
                    if all(v == Verdict.READY_TO_CODE.value for v in child_verdicts)
                    else Verdict.NEEDS_ENRICHMENT.value
                )
                note = f"rollup contract-composition via {rollup.via}: partial coverage"
            else:
                new_verdict = max(child_verdicts, key=_severity)
                note = f"rollup contract-composition via {rollup.via}: no realized child"

        parent["verdict"] = new_verdict
        parent.setdefault("rollup_notes", []).append(note or "")
        # Union child reasons.
        for cid in child_ids:
            if cid in by_id:
                parent.setdefault("reasons", []).extend(
                    f"[via {cid}] {r}" for r in by_id[cid].get("reasons", [])
                )
        return parent

    for pid in list(by_id.keys()):
        _resolve(pid, set())

    return classifications


def _run_rollup(input: dict[str, Any]) -> dict[str, Any]:
    spec: WalkSpec = input["spec"]
    classifications = input["classifications"]
    if spec.rollup is None:
        return input
    rolled = _rollup(classifications, spec.rollup, input["model"])
    return {**input, "classifications": rolled}


def rollup_stage() -> Stage:
    return wrap_function("rollup", _run_rollup)
