"""Automatic behavior-to-behavior trigger detection from call graph."""
from __future__ import annotations

from architecture_model.core.types import Behavior, Relationship, RelationType
from architecture_model.manifest.call_graph import CallGraph, trace_flow


def detect_behavior_triggers(
    behaviors: list[Behavior],
    call_graph: CallGraph,
    behavior_entries: dict[str, str],  # beh_id -> qname of entry function
    max_depth: int = 4,
) -> list[Relationship]:
    """Detect triggers relationships between behaviors via call graph.

    For each behavior's entry function, trace its call graph (BFS).
    If the trace reaches the entry function of another behavior -> triggers edge.
    """
    # Reverse index: qname -> behavior_id
    entry_to_beh: dict[str, str] = {qname: beh_id for beh_id, qname in behavior_entries.items()}

    triggers: list[Relationship] = []
    seen: set[tuple[str, str]] = set()

    for beh in behaviors:
        entry_qname = behavior_entries.get(beh.id)
        if not entry_qname or entry_qname not in call_graph.edges:
            continue

        flow = trace_flow(call_graph, entry_qname, max_depth=max_depth)

        for file, fname in flow.steps:
            qname = f"{file}:{fname}"
            if qname == entry_qname:
                continue
            if qname in entry_to_beh:
                target_beh_id = entry_to_beh[qname]
                if target_beh_id == beh.id:
                    continue
                pair = (beh.id, target_beh_id)
                if pair not in seen:
                    seen.add(pair)
                    triggers.append(Relationship(
                        type=RelationType.TRIGGERS,
                        from_id=beh.id,
                        to_id=target_beh_id,
                    ))

    return triggers


def build_behavior_entry_map(
    behaviors: list[Behavior],
    call_graph: CallGraph,
) -> dict[str, str]:
    """Infer behavior entry function qnames from behavior name + source_file.

    Heuristic: behavior.name (snake_cased) matches a function in behavior.source_file.
    Falls back to first function in the source file with best name overlap.
    """
    # Build file -> qnames index
    file_funcs: dict[str, list[str]] = {}
    for qname, loc in call_graph.locations.items():
        file_funcs.setdefault(loc, []).append(qname)

    entries: dict[str, str] = {}
    for beh in behaviors:
        if not beh.source_file:
            continue

        # Try exact name match
        snake_name = beh.name.lower().replace(" ", "_").replace("-", "_")
        candidate = f"{beh.source_file}:{snake_name}"
        if candidate in call_graph.locations or candidate in call_graph.edges:
            entries[beh.id] = candidate
            continue

        # Try matching any function in source file
        file_qnames = file_funcs.get(beh.source_file, [])
        if file_qnames:
            best = None
            best_score = -1
            for qn in file_qnames:
                fname = qn.split(":", 1)[1]
                # Simple character overlap score
                score = len(set(fname.lower()) & set(snake_name))
                if score > best_score:
                    best = qn
                    best_score = score
            if best:
                entries[beh.id] = best

    return entries
