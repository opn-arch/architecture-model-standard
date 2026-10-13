"""Pilot parity test: WALK-browse vs. legacy _mermaid_neighbors.

1-hop typed-edge neighborhood walk. Uniform across all entity kinds;
silent-skips when the neighbor count is 0 or > 20 (threshold enforced
by EmitSpec.subgraph_neighbor_threshold).

Strict edge-set parity: walk cards' (from, to, type) triples MUST equal
the viewer's mermaid-parsed edges after _mid() encoding.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest
import yaml

from architecture_model.walks.runner import run_walk
from architecture_model.walks.spec.loader import load_walk_spec

REPO = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO / ".architecture/model/walks/browse.v3.yaml"
DEFAULT_MODEL = REPO / ".architecture-model.v3.yaml"
FRAGMENT_DIR = REPO / ".architecture/model"
LEGACY_SCRIPT = REPO / "scripts/build_v3_viewer.py"


def _load_legacy_helpers():
    spec = importlib.util.spec_from_file_location(
        "_legacy_v3_viewer_browse", LEGACY_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_legacy_v3_viewer_browse"] = mod
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


def _build_edge_maps(relationships: list) -> tuple[dict, dict]:
    out_edges: dict[str, list[tuple[str, str]]] = {}
    in_edges: dict[str, list[tuple[str, str]]] = {}
    for r in relationships:
        f, t, rt = r.get("from"), r.get("to"), r.get("type")
        if f is None or t is None or rt is None:
            continue
        out_edges.setdefault(f, []).append((t, rt))
        in_edges.setdefault(t, []).append((f, rt))
    return out_edges, in_edges


_EDGE_RE = re.compile(r"^\s*(\S+)\s*-->\|([^|]+)\|\s*(\S+)\s*$")


def _viewer_edges_from_mermaid(mermaid: str) -> set[tuple[str, str, str]]:
    edges: set[tuple[str, str, str]] = set()
    for line in mermaid.splitlines():
        m = _EDGE_RE.match(line)
        if not m:
            continue
        edges.add((m.group(1), m.group(3), m.group(2)))
    return edges


def _mid(eid: str) -> str:
    return "n" + "".join(c for c in eid if c.isalnum())


@pytest.fixture(scope="module")
def merged():
    legacy = _load_legacy_helpers()
    sources = _load_sources()
    _, entities_by_kind, relationships, _ = legacy._merge_sources(sources)
    walk_entities: dict[str, list[dict]] = {}
    for kind, id_map in entities_by_kind.items():
        walk_entities[kind] = list(id_map.values())
    walk_model = {
        "entities": walk_entities,
        "relationships": relationships,
    }
    out_edges, in_edges = _build_edge_maps(relationships)
    return walk_model, entities_by_kind, relationships, out_edges, in_edges


@pytest.fixture(scope="module")
def walk_output(merged):
    walk_model, _, _, _, _ = merged
    spec = load_walk_spec(SPEC_PATH)
    return run_walk(spec, walk_model)


def test_spec_loads():
    spec = load_walk_spec(SPEC_PATH)
    assert spec.id == "WALK-browse"
    assert spec.audits == ("CAP-WK.browse",)
    assert spec.scope.kind == "any"
    assert spec.traverse.depth == 1
    assert spec.traverse.direction == "both"
    assert spec.traverse.edges == ()
    assert spec.emit.subgraph_neighbor_threshold == 20


def test_walk_visits_every_entity(merged, walk_output):
    _, entities_by_kind, _, _, _ = merged
    all_ids: set[str] = set()
    for id_map in entities_by_kind.values():
        all_ids.update(id_map.keys())
    walked = {c["entity_id"] for c in walk_output["cards"]}
    assert walked == all_ids


def test_silent_skip_parity(merged, walk_output):
    """When viewer returns None (0 neighbors or > 20), walk card MUST
    have empty subgraph_edges and subgraph_nodes == [root]."""
    legacy = _load_legacy_helpers()
    _, entities_by_kind, relationships, out_edges, in_edges = merged
    cards = {c["entity_id"]: c for c in walk_output["cards"]}
    silent = 0
    for eid, card in cards.items():
        result = legacy._mermaid_neighbors(
            entities_by_kind, relationships, eid, out_edges, in_edges
        )
        if result is not None:
            continue
        silent += 1
        assert card["subgraph_edges"] == [], (
            f"viewer silent-skipped {eid}, walk edges: {card['subgraph_edges']}"
        )
        assert card["subgraph_nodes"] == [eid], (
            f"viewer silent-skipped {eid}, walk nodes: {card['subgraph_nodes']}"
        )
    assert silent > 0, "expected some silent-skip cases"


def test_edge_set_parity(merged, walk_output):
    """When viewer returns non-None, walk's (from, to, type) set MUST
    equal the viewer's parsed mermaid edges after _mid encoding."""
    legacy = _load_legacy_helpers()
    _, entities_by_kind, relationships, out_edges, in_edges = merged
    cards = {c["entity_id"]: c for c in walk_output["cards"]}
    matched = 0
    for eid, card in cards.items():
        result = legacy._mermaid_neighbors(
            entities_by_kind, relationships, eid, out_edges, in_edges
        )
        if result is None:
            continue
        mermaid, viewer_nodes = result
        walk_nodes = set(card["subgraph_nodes"])
        assert walk_nodes == set(viewer_nodes), (
            f"node-set divergence for {eid}: "
            f"only-walk={walk_nodes - set(viewer_nodes)} "
            f"only-viewer={set(viewer_nodes) - walk_nodes}"
        )
        viewer_edges = _viewer_edges_from_mermaid(mermaid)
        walk_edges = {
            (_mid(e["from"]), _mid(e["to"]), e["type"])
            for e in card["subgraph_edges"]
        }
        assert walk_edges == viewer_edges, (
            f"edge-set divergence for {eid}: "
            f"only-walk={walk_edges - viewer_edges} "
            f"only-viewer={viewer_edges - walk_edges}"
        )
        matched += 1
    assert matched > 0


def test_determinism(merged):
    walk_model, _, _, _, _ = merged
    spec = load_walk_spec(SPEC_PATH)
    out1 = run_walk(spec, walk_model)
    out2 = run_walk(spec, walk_model)
    assert out1["cards"] == out2["cards"]
