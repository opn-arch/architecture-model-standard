"""NetworkX export adapter for AMS models (Stage 1).

Converts an AMS v3 model dict into a ``networkx.MultiDiGraph`` with
deterministic node/edge ordering. Promises and evidence are promoted to
first-class sub-nodes when ``promises_as_nodes`` is True, wired via
synthetic ``has-promise`` and ``verified-by`` edges.

Design invariants:
    - Parallel typed edges preserved (browse regression: same node pair,
      different relationship types → distinct edges with unique keys).
    - Deterministic: two builds from the same input produce identical
      node/edge iteration order.
    - YAML remains source of truth; graph is a derived view.
    - Zero touch on walks/traverse.

Public API:
    to_networkx(model, *, promises_as_nodes, include_verified_by,
                include_semantic_fields) -> nx.MultiDiGraph
    BUCKET_ORDER, EDGE_TYPES, SEMANTIC_FIELDS
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import networkx as nx  # pragma: no cover


BUCKET_ORDER: tuple[str, ...] = (
    "capabilities",
    "components",
    "behaviors",
    "interfaces",
    "actors",
    "constraints",
    "layers",
    "environments",
    "resources",
)

# Singular kind label per bucket for node.kind attr.
BUCKET_TO_KIND: dict[str, str] = {
    "capabilities": "capability",
    "components": "component",
    "behaviors": "behavior",
    "interfaces": "interface",
    "actors": "actor",
    "constraints": "constraint",
    "layers": "layer",
    "environments": "environment",
    "resources": "resource",
}

# 17 canonical relationship types + 2 synthetic types introduced by
# promise/evidence promotion.
EDGE_TYPES: frozenset[str] = frozenset(
    {
        # canonical
        "realizes",
        "contains",
        "depends-on",
        "constrained-by",
        "traces-to",
        "exposes",
        "consumes",
        "triggers",
        "allocated-to",
        "produces",
        "subscribes-to",
        "transforms",
        "supersedes",
        "migrates-to",
        "mounted-on",
        "connected-at",
        "routed-through",
        # synthetic (Stage 1 promotion)
        "has-promise",
        "verified-by",
    }
)

# Semantic bag propagated onto entity nodes when include_semantic_fields=True.
SEMANTIC_FIELDS: tuple[str, ...] = (
    "intent",
    "goals",
    "stakeholders",
    "success_criteria",
    "failure_modes",
    "trade_offs",
    "assumptions",
    "open_questions",
    "requirements",
    "verification",
    "slos",
    "owner",
    "maturity",
    "dependencies_rationale",
)

# Structural fields consumed explicitly (not part of semantic bag).
_STRUCTURAL_FIELDS: frozenset[str] = frozenset(
    {"id", "name", "status", "kind", "promises"}
)


def _import_networkx():
    """Soft-import networkx with an actionable install hint."""
    try:
        import networkx as nx  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "networkx is required for graph export. Install with:\n"
            "  pip install 'architecture-model-standard[graph]'\n"
            "or:\n"
            "  pip install networkx"
        ) from exc
    return nx


def _evidence_node_id(uri: str) -> str:
    """Stable evidence node id: ev:<sha1(uri)[:8]>."""
    digest = hashlib.sha1(uri.encode("utf-8")).hexdigest()[:8]
    return f"ev:{digest}"


def _entity_node_attrs(
    entity: dict,
    bucket: str,
    *,
    include_semantic_fields: bool,
) -> dict[str, Any]:
    """Build attribute dict for an entity node."""
    attrs: dict[str, Any] = {
        "kind": BUCKET_TO_KIND.get(bucket, bucket.rstrip("s")),
        "bucket": bucket,
        "name": entity.get("name", entity.get("id", "")),
        "status": entity.get("status", ""),
    }
    if include_semantic_fields:
        for field in SEMANTIC_FIELDS:
            if field in entity and entity[field] not in (None, "", [], {}):
                attrs[field] = entity[field]
    return attrs


def _promise_node_attrs(promise: dict, owner_id: str, index: int) -> dict[str, Any]:
    """Build attribute dict for a promoted promise sub-node."""
    return {
        "kind": "promise",
        "owner_id": owner_id,
        "promise_index": index,
        "promise_id": promise.get("id", ""),
        "attr": promise.get("attribute", promise.get("attr", "")),
        "value": promise.get("content", promise.get("value", "")),
        "status": promise.get("status", ""),
        "confidence": promise.get("confidence", ""),
    }


def _evidence_node_attrs(uri: str, evidence_kind: str = "") -> dict[str, Any]:
    """Build attribute dict for a promoted evidence node."""
    return {
        "kind": "evidence",
        "uri": uri,
        "evidence_kind": evidence_kind,
    }


def _extract_evidence_uris(promise: dict) -> list[tuple[str, str]]:
    """Extract [(uri, evidence_kind), ...] from a promise's verified_by field.

    verified_by may be:
      - str: single URI
      - list of str: multiple URIs
      - list of dict: [{"uri": ..., "kind": ...}, ...]
    """
    raw = promise.get("verified_by")
    if not raw:
        return []
    if isinstance(raw, str):
        return [(raw, "")]
    if isinstance(raw, list):
        out: list[tuple[str, str]] = []
        for item in raw:
            if isinstance(item, str):
                out.append((item, ""))
            elif isinstance(item, dict):
                uri = item.get("uri", "")
                if uri:
                    out.append((uri, item.get("kind", "")))
        return out
    return []


def to_networkx(
    model: dict,
    *,
    promises_as_nodes: bool = True,
    include_verified_by: bool = True,
    include_semantic_fields: bool = True,
) -> "nx.MultiDiGraph":
    """Build a deterministic MultiDiGraph from an AMS model dict.

    Args:
        model: Model dict with ``entities`` (dict-of-lists per bucket) and
            ``relationships`` (list of {from, to, type, ...}).
        promises_as_nodes: Promote promises to first-class sub-nodes with
            ``has-promise`` edges from owner. Default True.
        include_verified_by: When promises_as_nodes is True, also promote
            evidence URIs to nodes and wire ``verified-by`` edges from
            promise to evidence. Default True. Ignored if
            promises_as_nodes is False.
        include_semantic_fields: Propagate SEMANTIC_FIELDS onto entity
            nodes. Default True.

    Returns:
        nx.MultiDiGraph with entity + optional promise/evidence nodes and
        typed edges. Edge key = relationship type.

    Raises:
        ImportError: networkx not installed (with install hint).
    """
    nx = _import_networkx()
    G = nx.MultiDiGraph()

    entities = model.get("entities", {}) or {}

    # Pass 1: entity nodes, deterministic bucket + id ordering.
    entity_ids: set[str] = set()
    for bucket in BUCKET_ORDER:
        bucket_entities = entities.get(bucket, []) or []
        # Sort by id (stable string sort).
        for ent in sorted(bucket_entities, key=lambda e: e.get("id", "")):
            eid = ent.get("id")
            if not eid:
                continue
            attrs = _entity_node_attrs(
                ent, bucket, include_semantic_fields=include_semantic_fields
            )
            G.add_node(eid, **attrs)
            entity_ids.add(eid)

    # Pass 2: promise + evidence promotion (optional).
    if promises_as_nodes:
        # Evidence dedup by URI, first-seen wins.
        evidence_seen: dict[str, str] = {}  # uri -> node_id
        # Collect all (owner, promise_idx, promise, evidence_list) in deterministic order.
        promise_records: list[tuple[str, int, dict, list[tuple[str, str]]]] = []
        for bucket in BUCKET_ORDER:
            bucket_entities = entities.get(bucket, []) or []
            for ent in sorted(bucket_entities, key=lambda e: e.get("id", "")):
                eid = ent.get("id")
                if not eid:
                    continue
                promises = ent.get("promises", []) or []
                for idx, promise in enumerate(promises):
                    if not isinstance(promise, dict):
                        continue
                    ev = (
                        _extract_evidence_uris(promise)
                        if include_verified_by
                        else []
                    )
                    promise_records.append((eid, idx, promise, ev))

        # Add promise nodes + has-promise edges.
        for owner_id, idx, promise, ev_list in promise_records:
            pnode = f"{owner_id}#p{idx}"
            G.add_node(pnode, **_promise_node_attrs(promise, owner_id, idx))
            G.add_edge(owner_id, pnode, key="has-promise", type="has-promise")

            # Evidence promotion.
            if include_verified_by:
                for uri, ev_kind in ev_list:
                    if uri in evidence_seen:
                        ev_node = evidence_seen[uri]
                    else:
                        ev_node = _evidence_node_id(uri)
                        evidence_seen[uri] = ev_node
                        G.add_node(ev_node, **_evidence_node_attrs(uri, ev_kind))
                    G.add_edge(pnode, ev_node, key="verified-by", type="verified-by")

    # Pass 3: canonical relationships, sorted deterministically.
    relationships = model.get("relationships", []) or []

    def _rel_key(r: dict) -> tuple[str, str, str]:
        return (r.get("from", ""), r.get("to", ""), r.get("type", ""))

    for rel in sorted(relationships, key=_rel_key):
        src = rel.get("from")
        dst = rel.get("to")
        rtype = rel.get("type", "depends-on")
        if not src or not dst:
            continue
        # Copy all extras (weight, note, direction, ...) as edge attrs.
        edge_attrs: dict[str, Any] = {"type": rtype}
        for k, v in rel.items():
            if k in ("from", "to", "type"):
                continue
            edge_attrs[k] = v
        # Key = rtype gives parallel typed edges (browse regression).
        G.add_edge(src, dst, key=rtype, **edge_attrs)

    return G


__all__ = [
    "to_networkx",
    "BUCKET_ORDER",
    "BUCKET_TO_KIND",
    "EDGE_TYPES",
    "SEMANTIC_FIELDS",
]
