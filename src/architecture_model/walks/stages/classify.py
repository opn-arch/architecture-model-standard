"""architecture_model.walks.stages.classify — Verdict assignment.

For each entity + subgraph, evaluate ClassifySpec verdict rules in
order. First matching verdict wins. If no rule matches and an
attribute is missing, apply on_missing_attributes fallback.

Predicate DSL (extended from select):
  - has:<attr>              non-empty attribute
  - missing:<attr>          absent/empty attribute
  - count:<attr> >= N       list-length comparison
  - count:<attr> > N
  - verified:<attr>         attribute has verified_by paths
  - unverified:<attr>       attribute lacks verified_by paths
  - combined via " and " / " or "
"""

from __future__ import annotations

import re
from typing import Any

from architecture_model.pipeline_v3.substrate import Stage, wrap_function
from architecture_model.walks.attribute import Attribute
from architecture_model.walks.spec.loader import WalkSpec
from architecture_model.walks.verdict import Verdict

__all__ = ["classify_stage"]


_COUNT_RE = re.compile(r"count:(\w+)\s*(>=|>|<=|<|==)\s*(\d+)")


def _as_attribute(raw: Any) -> Attribute:
    """Interpret an entity field as an Attribute (may be bare value or full dict)."""
    return Attribute.from_dict(raw) if raw is not None else Attribute(value=None)


def _eval_atom(atom: str, entity: dict[str, Any]) -> bool:
    atom = atom.strip()
    if atom in ("true", ""):
        return True
    if atom == "false":
        return False
    if atom.startswith("has:"):
        attr = atom[4:].strip()
        return not _as_attribute(entity.get(attr)).is_empty()
    if atom.startswith("missing:"):
        attr = atom[8:].strip()
        return _as_attribute(entity.get(attr)).is_empty()
    if atom.startswith("verified:"):
        attr = atom[9:].strip()
        a = _as_attribute(entity.get(attr))
        return len(a.verified_by) > 0
    if atom.startswith("unverified:"):
        attr = atom[11:].strip()
        a = _as_attribute(entity.get(attr))
        return not a.is_empty() and len(a.verified_by) == 0
    m = _COUNT_RE.match(atom)
    if m:
        attr, op, n = m.group(1), m.group(2), int(m.group(3))
        v = entity.get(attr)
        length = len(v) if hasattr(v, "__len__") else 0
        return {
            ">=": length >= n,
            ">": length > n,
            "<=": length <= n,
            "<": length < n,
            "==": length == n,
        }[op]
    return False


def _eval_predicate(predicate: str, entity: dict[str, Any]) -> bool:
    p = predicate.strip()
    if " and " in p:
        return all(_eval_atom(a, entity) for a in p.split(" and "))
    if " or " in p:
        return any(_eval_atom(a, entity) for a in p.split(" or "))
    return _eval_atom(p, entity)


def _classify_one(
    entity: dict[str, Any], spec: WalkSpec
) -> tuple[str, list[str]]:
    """Return (verdict_name, list_of_reasons)."""
    reasons: list[str] = []
    for rule in spec.classify.verdicts:
        try:
            matched = _eval_predicate(rule.when, entity)
        except Exception as e:  # noqa: BLE001 — user rules must not crash walk
            reasons.append(f"rule '{rule.name}' errored: {e}")
            continue
        if matched:
            reasons.append(f"matched rule '{rule.name}': {rule.when}")
            return rule.name, reasons
    # No rule matched — apply fallback
    fallback = spec.classify.on_missing_attributes
    reasons.append(f"no verdict rule matched; fallback → {fallback}")
    return fallback, reasons


def _run_classify(input: dict[str, Any]) -> dict[str, Any]:
    spec: WalkSpec = input["spec"]
    subgraphs = input["subgraphs"]

    classifications: list[dict[str, Any]] = []
    for sub in subgraphs:
        entity = sub["entity"]
        verdict, reasons = _classify_one(entity, spec)
        classifications.append(
            {
                "entity": entity,
                "entity_id": entity.get("id"),
                "verdict": verdict,
                "reasons": reasons,
                "subgraph": sub,
            }
        )

    return {
        "model": input["model"],
        "spec": spec,
        "classifications": classifications,
    }


def classify_stage() -> Stage:
    return wrap_function("classify", _run_classify)


# Public re-export for consumer inspection.
KNOWN_VERDICTS = {v.value for v in Verdict}
