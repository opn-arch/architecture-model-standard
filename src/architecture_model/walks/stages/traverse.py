"""architecture_model.walks.stages.traverse — Neighborhood expansion.

For each selected entity, walk the model's relationships according to
TraverseSpec (edges, direction, depth). Produces a subgraph per entity:
the entity plus its reachable neighbors.
"""

from __future__ import annotations

from typing import Any

from architecture_model.pipeline_v3.substrate import Stage, wrap_function
from architecture_model.walks.spec.loader import HopSpec, TraverseSpec, WalkSpec

__all__ = ["traverse_stage"]


# Plural entity bucket name -> singular kind used by ScopeSpec.kind and
# HopSpec.by_kind lookups. Mirrors the map in walks.stages.select.
_BUCKET_TO_KIND = {
    "components": "component",
    "capabilities": "capability",
    "behaviors": "behavior",
    "interfaces": "interface",
    "actors": "actor",
    "constraints": "constraint",
    "layers": "layer",
}


def _index_kind_by_id(model: dict[str, Any]) -> dict[str, str]:
    """Return {entity_id: singular_kind} across every kind bucket."""
    out: dict[str, str] = {}
    for bucket_name, bucket in model.get("entities", {}).items():
        if not isinstance(bucket, list):
            continue
        kind = _BUCKET_TO_KIND.get(bucket_name, bucket_name.rstrip("s"))
        for e in bucket:
            eid = e.get("id")
            if eid:
                out[eid] = kind
    return out


def _index_relationships(
    model: dict[str, Any],
) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """Return (outbound_by_id, inbound_by_id) indexes of relationships."""
    rels = model.get("relationships", [])
    outbound: dict[str, list[dict]] = {}
    inbound: dict[str, list[dict]] = {}
    for r in rels:
        f = r.get("from")
        t = r.get("to")
        if f:
            outbound.setdefault(f, []).append(r)
        if t:
            inbound.setdefault(t, []).append(r)
    return outbound, inbound


def _find_entity(model: dict[str, Any], eid: str) -> dict | None:
    """Locate an entity by id across all kind buckets."""
    ents = model.get("entities", {})
    for bucket in ents.values():
        if isinstance(bucket, list):
            for e in bucket:
                if e.get("id") == eid:
                    return e
    return None


def _walk_from(
    model: dict[str, Any],
    root_id: str,
    traverse: TraverseSpec,
    outbound: dict[str, list[dict]],
    inbound: dict[str, list[dict]],
    kind_by_id: dict[str, str],
) -> dict[str, Any]:
    """BFS from root_id per traverse spec. Returns {nodes, edges}.

    Two modes:
      - Legacy (traverse.hops empty): uniform BFS on (edges, direction) up
        to depth, then induced-subgraph pass among visited nodes.
      - Hop mode (traverse.hops non-empty): apply each hop's (edges,
        direction) to that hop's frontier; NO induced-subgraph pass. Used
        for kind-dispatched walks whose hops mix edge types/directions.
    """
    if traverse.hops:
        return _walk_hops(model, root_id, traverse.hops, outbound, inbound, kind_by_id)
    return _walk_uniform(model, root_id, traverse, outbound, inbound)


def _walk_hops(
    model: dict[str, Any],
    root_id: str,
    hops: tuple[HopSpec, ...],
    outbound: dict[str, list[dict]],
    inbound: dict[str, list[dict]],
    kind_by_id: dict[str, str],
) -> dict[str, Any]:
    """Multi-hop traversal: hop N walks from hop N-1's newly-visited set.

    Per-node dispatch: when a hop has non-empty ``by_kind``, the (edges,
    direction) used for each frontier node depend on that node's singular
    kind. Frontier nodes whose kind is absent from ``by_kind`` are silently
    skipped for this hop (no outgoing walk).

    Records ``hop_added: list[int]`` on the returned subgraph — the count
    of newly-visited nodes added at each hop, used by emit's silent-skip.
    """
    visited: set[str] = {root_id}
    nodes: list[dict] = []
    root_ent = _find_entity(model, root_id)
    if root_ent is not None:
        nodes.append(root_ent)
    edges_out: list[dict] = []
    frontier: list[str] = [root_id]
    hop_added: list[int] = []

    for hop in hops:
        by_kind_map = dict(hop.by_kind) if hop.by_kind else None
        # Uniform-mode defaults (used when by_kind_map is None).
        default_edge_types = set(hop.edges) if hop.edges else None
        default_direction = hop.direction
        next_frontier: list[str] = []
        added_this_hop = 0
        for cur in frontier:
            # Resolve per-node (edges, direction) via kind dispatch when set.
            if by_kind_map is not None:
                sub = by_kind_map.get(kind_by_id.get(cur, ""))
                if sub is None:
                    # Kind not in dispatch map — silent-skip this node.
                    continue
                edge_types = set(sub.edges) if sub.edges else None
                direction = sub.direction
            else:
                edge_types = default_edge_types
                direction = default_direction

            neighbors: list[tuple[dict, str]] = []
            if direction in ("outbound", "both"):
                for r in outbound.get(cur, []):
                    if edge_types is None or r.get("type") in edge_types:
                        neighbors.append((r, r.get("to", "")))
            if direction in ("inbound", "both"):
                for r in inbound.get(cur, []):
                    if edge_types is None or r.get("type") in edge_types:
                        neighbors.append((r, r.get("from", "")))
            for edge, nid in neighbors:
                if not nid:
                    continue
                # Always record the traversed edge (even to previously-visited
                # nodes) — the viewer's realize walk emits duplicate contains
                # edges when two siblings share a child, and parity requires
                # matching that shape.
                edges_out.append(edge)
                if nid not in visited:
                    visited.add(nid)
                    nent = _find_entity(model, nid)
                    if nent is not None:
                        nodes.append(nent)
                    next_frontier.append(nid)
                    added_this_hop += 1
        frontier = next_frontier
        hop_added.append(added_this_hop)

    return {
        "root_id": root_id,
        "nodes": nodes,
        "edges": edges_out,
        "hop_added": hop_added,
    }


def _walk_uniform(
    model: dict[str, Any],
    root_id: str,
    traverse: TraverseSpec,
    outbound: dict[str, list[dict]],
    inbound: dict[str, list[dict]],
) -> dict[str, Any]:
    """BFS from root_id per traverse spec. Returns {nodes, edges}."""
    max_depth = traverse.depth if traverse.depth is not None else 10_000
    edge_types = set(traverse.edges) if traverse.edges else None
    direction = traverse.direction

    visited: set[str] = {root_id}
    frontier: list[tuple[str, int]] = [(root_id, 0)]
    edges_out: list[dict] = []
    nodes: list[dict] = []
    root_ent = _find_entity(model, root_id)
    if root_ent is not None:
        nodes.append(root_ent)

    while frontier:
        cur, depth = frontier.pop(0)
        if depth >= max_depth:
            continue

        neighbors: list[tuple[dict, str]] = []
        if direction in ("outbound", "both"):
            for r in outbound.get(cur, []):
                if edge_types is None or r.get("type") in edge_types:
                    neighbors.append((r, r.get("to", "")))
        if direction in ("inbound", "both"):
            for r in inbound.get(cur, []):
                if edge_types is None or r.get("type") in edge_types:
                    neighbors.append((r, r.get("from", "")))

        for edge, nid in neighbors:
            if not nid:
                continue
            # Record every traversed edge, even to already-visited nodes.
            # A pair of nodes may be connected by multiple relationship
            # types; missing any of them would break browse-style walks
            # whose value is exactly "all typed edges touching root".
            edges_out.append(edge)
            if nid not in visited:
                visited.add(nid)
                nent = _find_entity(model, nid)
                if nent is not None:
                    nodes.append(nent)
                frontier.append((nid, depth + 1))

    # Induced-subgraph pass: also record edges (of matching direction + type)
    # between already-visited nodes that the BFS spanning tree omitted. This
    # makes the returned edges a proper induced subgraph, matching viewer
    # semantics for diagram-mode walks and remaining a superset for edge-
    # counting classifiers (which only care about root-anchored edges).
    # Skipped when depth == 1 because 1-hop walks want root-anchored edges
    # only (matches _mermaid_neighbors semantics).
    if max_depth > 1:
        seen_edges: set[int] = {id(e) for e in edges_out}
        for src in visited:
            if direction in ("outbound", "both"):
                for r in outbound.get(src, []):
                    if edge_types is not None and r.get("type") not in edge_types:
                        continue
                    if r.get("to") in visited and id(r) not in seen_edges:
                        edges_out.append(r)
                        seen_edges.add(id(r))
            if direction in ("inbound", "both"):
                for r in inbound.get(src, []):
                    if edge_types is not None and r.get("type") not in edge_types:
                        continue
                    if r.get("from") in visited and id(r) not in seen_edges:
                        edges_out.append(r)
                        seen_edges.add(id(r))

    return {"root_id": root_id, "nodes": nodes, "edges": edges_out}


def _run_traverse(input: dict[str, Any]) -> dict[str, Any]:
    spec: WalkSpec = input["spec"]
    model = input["model"]
    entities = input["entities"]

    outbound, inbound = _index_relationships(model)
    kind_by_id = _index_kind_by_id(model)
    subgraphs = []
    for e in entities:
        eid = e.get("id")
        if not eid:
            continue
        sub = _walk_from(model, eid, spec.traverse, outbound, inbound, kind_by_id)
        sub["entity"] = e
        subgraphs.append(sub)

    return {
        "model": model,
        "spec": spec,
        "entities": entities,
        "subgraphs": subgraphs,
    }


def traverse_stage() -> Stage:
    return wrap_function("traverse", _run_traverse)
