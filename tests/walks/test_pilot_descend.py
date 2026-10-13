"""Pilot parity test: WALK-descend vs. legacy _mermaid_decomposition.

Diagram-mode walk retrofit. Unlike the verdict-mode unrealized-cap pilot,
parity here is *structural*: for every entity in the model, the walk's
emitted subgraph (nodes + edges) MUST equal the induced-subgraph the
legacy viewer helper walks via BFS ≤2 hops of outbound `contains`.

Silent-skip semantics differ by design:
- Viewer returns None when the root has no outbound contains children.
- Walk still emits a card (with an empty subgraph_edges list and just the
  root in subgraph_nodes); consumers filter by empty edges.

Parity assertion: when viewer returns a non-None result, walk card's
node/edge sets MUST match. When viewer returns None, walk card MUST
carry an empty subgraph_edges list.

Overflow cap (30 nodes) is asserted as a matching numeric budget; parity
of the exact prune order is out of scope because both sides prune
deterministically but the walk trims by list-order while the viewer
increments an overflow counter. This repo's model has no descendant
tree exceeding the cap at the time of writing; the test skips assertions
on any entity where the walk reports subgraph_overflow > 0.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

from architecture_model.walks.runner import run_walk
from architecture_model.walks.spec.loader import load_walk_spec

REPO = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO / ".architecture/model/walks/descend.v3.yaml"
DEFAULT_MODEL = REPO / ".architecture-model.v3.yaml"
FRAGMENT_DIR = REPO / ".architecture/model"
LEGACY_SCRIPT = REPO / "scripts/build_v3_viewer.py"


def _load_legacy_helpers():
    spec = importlib.util.spec_from_file_location(
        "_legacy_v3_viewer_descend", LEGACY_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_legacy_v3_viewer_descend"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_yaml(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def _load_sources() -> list[tuple[str, dict]]:
    sources: list[tuple[str, dict]] = []
    if DEFAULT_MODEL.exists():
        sources.append((str(DEFAULT_MODEL), _load_yaml(DEFAULT_MODEL)))
    if FRAGMENT_DIR.exists():
        for frag in sorted(FRAGMENT_DIR.glob("*.v3.yaml")):
            sources.append((str(frag), _load_yaml(frag)))
    return sources


@pytest.fixture(scope="module")
def merged():
    """Return (walk-shape model, viewer-shape entities_by_kind, relationships)."""
    legacy = _load_legacy_helpers()
    sources = _load_sources()
    _, entities_by_kind, relationships, _ = legacy._merge_sources(sources)
    # Walk shape: entities.<kind> as list.
    walk_entities: dict[str, list[dict]] = {}
    for kind, id_map in entities_by_kind.items():
        walk_entities[kind] = list(id_map.values())
    walk_model = {
        "entities": walk_entities,
        "relationships": relationships,
    }
    return walk_model, entities_by_kind, relationships


@pytest.fixture(scope="module")
def walk_output(merged):
    walk_model, _, _ = merged
    spec = load_walk_spec(SPEC_PATH)
    return run_walk(spec, walk_model)


def test_spec_loads_and_declares_correct_shape():
    spec = load_walk_spec(SPEC_PATH)
    assert spec.id == "WALK-descend"
    assert spec.audits == ("CAP-WK.descend",)
    assert spec.scope.kind == "any"
    assert "contains" in spec.traverse.edges
    assert spec.traverse.direction == "outbound"
    assert spec.traverse.depth == 2
    assert spec.emit.include_subgraph is True
    assert spec.emit.subgraph_cap == 30


def test_walk_visits_every_entity(merged, walk_output):
    walk_model, entities_by_kind, _ = merged
    all_ids: set[str] = set()
    for id_map in entities_by_kind.values():
        all_ids.update(id_map.keys())
    walked = {c["entity_id"] for c in walk_output["cards"]}
    assert walked == all_ids, (
        f"walk must visit every entity; "
        f"missing={all_ids - walked} extra={walked - all_ids}"
    )


def test_every_card_carries_subgraph_fields(walk_output):
    for card in walk_output["cards"]:
        assert "subgraph_nodes" in card, f"{card['entity_id']} missing subgraph_nodes"
        assert "subgraph_edges" in card, f"{card['entity_id']} missing subgraph_edges"
        assert "subgraph_overflow" in card, f"{card['entity_id']} missing overflow"
        # Root is always a member of subgraph_nodes.
        assert card["entity_id"] in card["subgraph_nodes"], (
            f"root {card['entity_id']} missing from its own subgraph_nodes"
        )


def test_silent_skip_parity(merged, walk_output):
    """When viewer returns None (no outbound contains from root), walk's
    subgraph_edges MUST be empty and subgraph_nodes MUST contain only root.
    """
    legacy = _load_legacy_helpers()
    _, entities_by_kind, relationships = merged
    cards = {c["entity_id"]: c for c in walk_output["cards"]}

    silent_count = 0
    for eid, card in cards.items():
        result = legacy._mermaid_decomposition(entities_by_kind, relationships, eid)
        if result is None:
            silent_count += 1
            assert card["subgraph_edges"] == [], (
                f"viewer silent-skipped {eid} but walk emitted edges: "
                f"{card['subgraph_edges']}"
            )
            assert card["subgraph_nodes"] == [eid], (
                f"viewer silent-skipped {eid} but walk visited more nodes: "
                f"{card['subgraph_nodes']}"
            )
    # Sanity: at least some entities in a real model have no children.
    assert silent_count > 0, "expected some silent-skip cases in a real model"


def test_node_and_edge_set_parity(merged, walk_output):
    """When viewer returns a non-None result, walk's subgraph nodes/edges
    (restricted to `contains` edges) MUST match the viewer's induced
    subgraph structurally."""
    legacy = _load_legacy_helpers()
    _, entities_by_kind, relationships = merged
    cards = {c["entity_id"]: c for c in walk_output["cards"]}

    compared = 0
    for eid, card in cards.items():
        result = legacy._mermaid_decomposition(entities_by_kind, relationships, eid)
        if result is None:
            continue
        if card["subgraph_overflow"] > 0:
            # Skip overflow cases — the two implementations prune by
            # different orderings.
            continue

        _, viewer_visited = result
        walk_nodes = set(card["subgraph_nodes"])
        viewer_nodes = set(viewer_visited)
        assert walk_nodes == viewer_nodes, (
            f"node-set divergence for {eid}: "
            f"only-walk={walk_nodes - viewer_nodes} "
            f"only-viewer={viewer_nodes - walk_nodes}"
        )

        # Reconstruct viewer's edge set: BFS ≤2 hops of outbound contains
        # among visited nodes. Since the walk emits ALL contains edges
        # among visited nodes (induced subgraph), and the viewer emits
        # the same set (its depth-2 pass records cross-edges too), the
        # edge sets must equal.
        contains_out: dict[str, set[str]] = {}
        for r in relationships:
            if r.get("type") != "contains":
                continue
            f, t = r.get("from"), r.get("to")
            if f in viewer_nodes and t in viewer_nodes:
                contains_out.setdefault(f, set()).add(t)
        viewer_edges = {
            (src, tgt)
            for src, tgts in contains_out.items()
            for tgt in tgts
        }

        walk_edges = {
            (e["from"], e["to"])
            for e in card["subgraph_edges"]
            if e.get("type") == "contains"
        }
        assert walk_edges == viewer_edges, (
            f"edge-set divergence for {eid}: "
            f"only-walk={walk_edges - viewer_edges} "
            f"only-viewer={viewer_edges - walk_edges}"
        )
        compared += 1

    assert compared > 0, "expected at least one non-empty comparison"


def test_determinism(merged):
    """Two runs produce identical card lists."""
    walk_model, _, _ = merged
    spec = load_walk_spec(SPEC_PATH)
    out1 = run_walk(spec, walk_model)
    out2 = run_walk(spec, walk_model)
    assert out1["cards"] == out2["cards"]
