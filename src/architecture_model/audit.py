"""Six-pipeline completeness audit.

Verifies that every operational pipeline (BEH-P1 EXTRACT, BEH-26 SLICE,
BEH-27 SELF-IMPROVEMENT, BEH-28 DEV-LOOP, BEH-LLM, BEH-SIL, BEH-FBK) has:
- Description on every sub-behavior
- Triggers DAG connecting steps
- Traces-to component allocation
- Contains parent relationship

Reports counts + gaps. Exit code non-zero on gaps when --strict.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from architecture_model.core.parser import load_model


PIPELINES = {
    "BEH-P1":  "EXTRACT",
    "BEH-26":  "SLICE",
    "BEH-27":  "SELF-IMPROVEMENT",
    "BEH-28":  "DEV-LOOP",
    "BEH-LLM": "LLM-PROVIDER",
    "BEH-SIL": "SI&L LOGGING",
    "BEH-FBK": "FEEDBACK JOURNALS",
}


def run_audit(model_path: str | Path, pipeline: str | None = None, strict: bool = False) -> int:
    model = load_model(Path(model_path))
    behaviors = list(model.entities.behaviors)
    relationships = list(model.relationships) if hasattr(model, "relationships") else []

    def gf(r):
        return getattr(r, "from_id", None) or getattr(r, "from_", None)
    def gt(r):
        return getattr(r, "to_id", None) or getattr(r, "to_", None)
    def rtype(r):
        rt = getattr(r, "type", None) or getattr(r, "relation_type", None)
        return rt.value if hasattr(rt, "value") else str(rt)

    triggers = defaultdict(set)
    traces_to = defaultdict(set)
    contains = defaultdict(set)
    for r in relationships:
        t = rtype(r)
        f, to = gf(r), gt(r)
        if t == "triggers":
            triggers[f].add(to)
        elif t == "traces-to":
            traces_to[to].add(f)   # keyed by behavior
        elif t == "contains":
            contains[f].add(to)

    behaviors_by_id = {b.id: b for b in behaviors}

    targets = [pipeline] if pipeline else list(PIPELINES.keys())
    total_gaps = 0

    print(f"# Six-Pipeline Completeness Audit\n\nModel: {model_path}\n")
    for anchor in targets:
        if anchor not in PIPELINES:
            print(f"unknown pipeline: {anchor}")
            continue
        label = PIPELINES[anchor]
        subs = [b for b in behaviors if b.id == anchor or b.id.startswith(anchor + ".")]
        n = len(subs)
        missing_desc = [b.id for b in subs if not (b.description or "").strip()]
        missing_trace = [b.id for b in subs if b.id != anchor and not traces_to.get(b.id)]
        missing_trig_out = [b.id for b in subs if b.id != anchor and b.id not in triggers and not any(b.id in t for t in triggers.values())]
        missing_contains = [b.id for b in subs if b.id != anchor and b.id not in contains.get(anchor, set())]

        print(f"## {anchor} — {label}")
        print(f"- Sub-behaviors: {n}")
        print(f"- Missing description: {len(missing_desc)}")
        print(f"- Missing traces-to (component): {len(missing_trace)}")
        print(f"- Isolated (no trigger in or out): {len(missing_trig_out)}")
        print(f"- Not contained by parent: {len(missing_contains)}")
        if missing_desc:
            print(f"  desc gaps: {missing_desc[:5]}{'...' if len(missing_desc)>5 else ''}")
        if missing_trace:
            print(f"  trace gaps: {missing_trace[:5]}{'...' if len(missing_trace)>5 else ''}")
        print()
        total_gaps += len(missing_desc) + len(missing_trace) + len(missing_trig_out) + len(missing_contains)

    print(f"---\nTotal gaps: {total_gaps}")
    if strict and total_gaps > 0:
        return 1
    return 0
