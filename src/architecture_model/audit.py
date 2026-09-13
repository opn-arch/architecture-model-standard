"""Six-pipeline completeness audit (CLI wrapper over the validator rule).

Delegates to the first-class `_check_pipeline_completeness` rule in
`architecture_model.core.validator` so this CLI and every `validate_model`
run share one source of truth. Reports per-pipeline counts + gaps and
returns a non-zero exit code on gaps when `--strict`.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.validator import PIPELINE_ANCHORS, validate_model


def run_audit(model_path: str | Path, pipeline: str | None = None, strict: bool = False) -> int:
    model = load_model(Path(model_path))
    behaviors = list(model.entities.behaviors)
    result = validate_model(model)

    # Bucket pipeline-completeness issues by anchor.
    by_anchor: dict[str, dict[str, list[str]]] = {
        a: {
            "PIPELINE_MISSING_DESCRIPTION": [],
            "PIPELINE_MISSING_TRACE": [],
            "PIPELINE_ISOLATED": [],
            "PIPELINE_MISSING_CONTAINMENT": [],
        }
        for a in PIPELINE_ANCHORS
    }
    for issue in result.issues:
        code = issue.code or ""
        if not code.startswith("PIPELINE_"):
            continue
        eid = issue.entity_id or ""
        # Match longest anchor prefix so BEH-P1 wins over BEH- style ties.
        matched = ""
        for a in PIPELINE_ANCHORS:
            if (eid == a or eid.startswith(a + ".")) and len(a) > len(matched):
                matched = a
        if matched and code in by_anchor[matched]:
            by_anchor[matched][code].append(eid)

    targets = [pipeline] if pipeline else list(PIPELINE_ANCHORS.keys())
    total_gaps = 0

    print(f"# Six-Pipeline Completeness Audit\n\nModel: {model_path}\n")
    for anchor in targets:
        if anchor not in PIPELINE_ANCHORS:
            print(f"unknown pipeline: {anchor}")
            continue
        label = PIPELINE_ANCHORS[anchor]
        subs = [b for b in behaviors if b.id == anchor or b.id.startswith(anchor + ".")]
        buckets = by_anchor.get(anchor, defaultdict(list))
        missing_desc = buckets["PIPELINE_MISSING_DESCRIPTION"]
        missing_trace = buckets["PIPELINE_MISSING_TRACE"]
        isolated = buckets["PIPELINE_ISOLATED"]
        missing_contains = buckets["PIPELINE_MISSING_CONTAINMENT"]

        print(f"## {anchor} — {label}")
        print(f"- Sub-behaviors: {len(subs)}")
        print(f"- Missing description: {len(missing_desc)}")
        print(f"- Missing traces-to (component): {len(missing_trace)}")
        print(f"- Isolated (no trigger in or out): {len(isolated)}")
        print(f"- Not contained by parent: {len(missing_contains)}")
        if missing_desc:
            print(f"  desc gaps: {missing_desc[:5]}{'...' if len(missing_desc)>5 else ''}")
        if missing_trace:
            print(f"  trace gaps: {missing_trace[:5]}{'...' if len(missing_trace)>5 else ''}")
        if isolated:
            print(f"  isolated: {isolated[:5]}{'...' if len(isolated)>5 else ''}")
        if missing_contains:
            print(f"  containment gaps: {missing_contains[:5]}{'...' if len(missing_contains)>5 else ''}")
        print()
        total_gaps += len(missing_desc) + len(missing_trace) + len(isolated) + len(missing_contains)

    print(f"---\nTotal gaps: {total_gaps}")
    if strict and total_gaps > 0:
        return 1
    return 0
