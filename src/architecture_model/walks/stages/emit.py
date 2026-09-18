"""architecture_model.walks.stages.emit — Card assembly.

Produce viewer-consumable Card records from classifications. Each Card
carries the walk id, entity, verdict, reasons, evidence, and severity.

Composition-friendly: Cards include the entity payload verbatim so a
downstream walk consuming this walk's output via ``from_walk`` can
re-classify without model access.
"""

from __future__ import annotations

from typing import Any

from architecture_model.pipeline_v3.substrate import Stage, wrap_function
from architecture_model.walks.spec.loader import WalkSpec
from architecture_model.walks.verdict import VERDICT_SEVERITY, Verdict

__all__ = ["emit_stage"]


def _severity_for(verdict: str) -> int:
    try:
        return VERDICT_SEVERITY[Verdict(verdict)]
    except (KeyError, ValueError):
        return -1


def _run_emit(input: dict[str, Any]) -> dict[str, Any]:
    spec: WalkSpec = input["spec"]
    classifications = input["classifications"]

    cards = []
    for c in classifications:
        card = {
            "walk_id": spec.id,
            "audits": list(spec.audits),
            "entity_id": c.get("entity_id"),
            "entity": c["entity"],
            "verdict": c["verdict"],
            "severity": _severity_for(c["verdict"]),
            "reasons": list(c.get("reasons", [])),
            "verified_by": list(c.get("verified_by", [])),
            "evidence_tier": c.get("evidence_tier", "structural"),
            "rollup_notes": list(c.get("rollup_notes", [])),
            "card_template": spec.emit.card_template,
        }
        # Diagram-mode: attach the traverse subgraph (nodes + edges) so the
        # viewer / a downstream renderer can produce a graph visualization
        # from the same source as verdict-mode walks.
        if spec.emit.include_subgraph:
            sub = c.get("subgraph") or {}
            nodes = list(sub.get("nodes", []))
            edges = list(sub.get("edges", []))
            overflow = 0
            cap = spec.emit.subgraph_cap
            if cap is not None and len(nodes) > cap:
                overflow = len(nodes) - cap
                nodes = nodes[:cap]
                # Prune edges whose endpoints didn't survive the cap.
                node_ids = {n.get("id") for n in nodes if isinstance(n, dict)}
                edges = [
                    e for e in edges
                    if e.get("from") in node_ids and e.get("to") in node_ids
                ]
            # Silent-skip: reduce to root-only when the 1-hop edge count
            # falls outside the neighbor threshold band [1, threshold].
            # Counts edges (not unique neighbor nodes) so parallel typed
            # edges to the same neighbor each contribute — matches the
            # viewer's `_mermaid_neighbors` skip condition.
            thr = spec.emit.subgraph_neighbor_threshold
            root_id = c.get("entity_id")
            if thr is not None:
                edge_count = len(edges)
                if edge_count == 0 or edge_count > thr:
                    nodes = [
                        n for n in nodes
                        if isinstance(n, dict) and n.get("id") == root_id
                    ]
                    edges = []
                    overflow = 0
            # Silent-skip: hop-mode walks reduce to root-only when the
            # LAST traversal hop added no new nodes (matches viewer's
            # _mermaid_constraint_impact "hop 2 empty" skip).
            if spec.emit.silent_skip_when_last_hop_empty:
                hop_added = sub.get("hop_added") or []
                if hop_added and hop_added[-1] == 0:
                    nodes = [
                        n for n in nodes
                        if isinstance(n, dict) and n.get("id") == root_id
                    ]
                    edges = []
                    overflow = 0
            card["subgraph_nodes"] = [n.get("id") for n in nodes if isinstance(n, dict)]
            card["subgraph_edges"] = [
                {"from": e.get("from"), "to": e.get("to"), "type": e.get("type")}
                for e in edges
            ]
            card["subgraph_overflow"] = overflow
        cards.append(card)

    # Deterministic order — sort by (severity desc, entity_id).
    cards.sort(key=lambda c: (-int(c["severity"]), c.get("entity_id") or ""))

    return {
        "walk_id": spec.id,
        "audits": list(spec.audits),
        "cards": cards,
    }


def emit_stage() -> Stage:
    return wrap_function("emit", _run_emit)
