"""T0.6: Delivery-down attribute propagation on .architecture-model.plan-b.yaml.

Rule: for every parent->child edge (contains / realizes / traces-to inverted),
fill each Phase 2 semantic attribute on child ONLY IF child value is empty.
Never overwrite child content — child's populated value IS the focused
delivery of parent's value. Empty child fields inherit as placeholders
awaiting focus.

Propagation edges (child <- parent):
  * cap (child) <- cap (parent) via `contains` (parent contains child)
  * component (child) <- cap (parent) via `realizes` (child realizes parent)
  * behavior (child) <- cap (parent) via `traces-to` (child traces-to parent)

Attributes: intent (str), goals, stakeholders, success_criteria,
failure_modes, trade_offs, assumptions, open_questions, moes,
requirements, verification, slos, dependencies_rationale (all lists);
owner (str), maturity (str).
"""

from __future__ import annotations

import copy
from pathlib import Path
from ruamel.yaml import YAML

PLAN_B = Path(".architecture-model.plan-b.yaml")

STR_ATTRS = ("intent", "owner", "maturity")
LIST_ATTRS = (
    "goals",
    "stakeholders",
    "success_criteria",
    "failure_modes",
    "trade_offs",
    "assumptions",
    "open_questions",
    "moes",
    "requirements",
    "verification",
    "slos",
    "dependencies_rationale",
)


def _empty(val) -> bool:
    if val is None:
        return True
    if isinstance(val, (list, tuple, dict, str)) and len(val) == 0:
        return True
    return False


def _fill(child: dict, parent: dict) -> int:
    """Return number of attributes filled on child."""
    filled = 0
    for attr in STR_ATTRS:
        if _empty(child.get(attr)) and not _empty(parent.get(attr)):
            child[attr] = copy.deepcopy(parent[attr])
            filled += 1
    for attr in LIST_ATTRS:
        if _empty(child.get(attr)) and not _empty(parent.get(attr)):
            child[attr] = copy.deepcopy(parent[attr])
            filled += 1
    return filled


def main() -> int:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    with PLAN_B.open() as f:
        doc = yaml.load(f)

    ents = doc["entities"]
    caps = {c["id"]: c for c in ents.get("capabilities") or []}
    comps = {c["id"]: c for c in ents.get("components") or []}
    behs = {b["id"]: b for b in ents.get("behaviors") or []}

    contains_edges = []  # (parent_id, child_id)
    realizes_edges = []  # (comp_id, cap_id)  child = comp, parent = cap
    traces_edges = []  # (beh_id, cap_id)    child = beh,  parent = cap

    for rel in doc.get("relationships") or []:
        rtype = rel.get("type")
        src = rel.get("from") or rel.get("from_id")
        dst = rel.get("to") or rel.get("to_id")
        if rtype == "contains" and src in caps and dst in caps:
            # dumper form: `from: CAP-CHILD, to: CAP-PARENT` (per T0.4 rels)
            # e.g. {from: CAP-PB-PROMISE-GRAPH, to: CAP-PB-MODEL, type: contains}
            # so child=src, parent=dst
            contains_edges.append((dst, src))
        elif rtype == "realizes" and src in comps and dst in caps:
            realizes_edges.append((src, dst))
        elif rtype == "traces-to" and src in behs and dst in caps:
            traces_edges.append((src, dst))

    total = 0
    per_edge = {"contains(cap<-cap)": 0, "realizes(comp<-cap)": 0, "traces-to(beh<-cap)": 0}

    for parent_id, child_id in contains_edges:
        n = _fill(caps[child_id], caps[parent_id])
        per_edge["contains(cap<-cap)"] += n
        total += n

    for comp_id, cap_id in realizes_edges:
        n = _fill(comps[comp_id], caps[cap_id])
        per_edge["realizes(comp<-cap)"] += n
        total += n

    for beh_id, cap_id in traces_edges:
        n = _fill(behs[beh_id], caps[cap_id])
        per_edge["traces-to(beh<-cap)"] += n
        total += n

    with PLAN_B.open("w") as f:
        yaml.dump(doc, f)

    print(f"Total attributes filled: {total}")
    for k, v in per_edge.items():
        print(f"  {k}: {v}")
    print(f"Edges processed: contains={len(contains_edges)} realizes={len(realizes_edges)} traces-to={len(traces_edges)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
