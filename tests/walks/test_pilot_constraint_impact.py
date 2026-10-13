"""Pilot parity test: WALK-constraint-impact vs. legacy
`_mermaid_constraint_impact`.

2-hop kind-dispatched traversal from each constraint:
  hop 1: inbound `constrained-by`
  hop 2 (per hop-1 node kind):
    capability/component -> outbound `contains`
    behavior             -> inbound `traces-to`
    interface            -> inbound `exposes`

Diagram-mode walk; the value is the emitted impacted subgraph.
Silent-skip when hop 2 adds no new nodes (matches viewer semantics —
identical to 1-hop realization view, no incremental information).

Strict node-set + edge-set parity: for constraints where the viewer
returns a non-None result, the walk's subgraph nodes MUST equal
sorted(viewer's node list) and edges MUST equal viewer's parsed
mermaid edges (after _mid() encoding).
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
SPEC_PATH = REPO / ".architecture/model/walks/constraint-impact.v3.yaml"
DEFAULT_MODEL = REPO / ".architecture-model.v3.yaml"
FRAGMENT_DIR = REPO / ".architecture/model"
LEGACY_SCRIPT = REPO / "scripts/build_v3_viewer.py"


def _load_legacy_helpers():
    spec = importlib.util.spec_from_file_location(
        "_legacy_v3_viewer_ci", LEGACY_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_legacy_v3_viewer_ci"] = mod
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
    return walk_model, entities_by_kind, relationships


@pytest.fixture(scope="module")
def walk_output(merged):
    walk_model, _, _ = merged
    spec = load_walk_spec(SPEC_PATH)
    return run_walk(spec, walk_model)


def test_spec_loads():
    spec = load_walk_spec(SPEC_PATH)
    assert spec.id == "WALK-constraint-impact"
    assert spec.scope.kind == "constraint"
    assert len(spec.traverse.hops) == 2
    # Hop 1 uniform.
    h1 = spec.traverse.hops[0]
    assert h1.edges == ("constrained-by",)
    assert h1.direction == "inbound"
    assert h1.by_kind == ()
    # Hop 2 kind-dispatched.
    h2 = spec.traverse.hops[1]
    assert h2.by_kind != ()
    kinds = {k for k, _ in h2.by_kind}
    assert kinds == {"capability", "component", "behavior", "interface"}
    assert spec.emit.include_subgraph is True
    assert spec.emit.silent_skip_when_last_hop_empty is True


def test_walks_every_constraint(merged, walk_output):
    _, entities_by_kind, _ = merged
    walked = {c["entity_id"] for c in walk_output["cards"]}
    assert walked == set(entities_by_kind.get("constraints", {}).keys())


def test_node_and_edge_parity(merged, walk_output):
    """For each constraint where viewer returns non-None, walk subgraph
    MUST match viewer's node list + parsed mermaid edges."""
    legacy = _load_legacy_helpers()
    _, entities_by_kind, relationships = merged
    cards = {c["entity_id"]: c for c in walk_output["cards"]}
    matched = 0
    silent = 0
    for cid, card in cards.items():
        result = legacy._mermaid_constraint_impact(
            entities_by_kind, relationships, cid
        )
        if result is None:
            # Viewer silent-skipped. Walk must be root-only.
            assert card["subgraph_edges"] == [], (
                f"viewer skipped {cid}, walk edges: {card['subgraph_edges']}"
            )
            assert card["subgraph_nodes"] == [cid], (
                f"viewer skipped {cid}, walk nodes: {card['subgraph_nodes']}"
            )
            silent += 1
            continue
        mermaid, viewer_nodes = result
        walk_nodes = set(card["subgraph_nodes"])
        assert walk_nodes == set(viewer_nodes), (
            f"node-set divergence for {cid}: "
            f"only-walk={walk_nodes - set(viewer_nodes)} "
            f"only-viewer={set(viewer_nodes) - walk_nodes}"
        )
        viewer_edges = _viewer_edges_from_mermaid(mermaid)
        walk_edges = {
            (_mid(e["from"]), _mid(e["to"]), e["type"])
            for e in card["subgraph_edges"]
        }
        assert walk_edges == viewer_edges, (
            f"edge-set divergence for {cid}: "
            f"only-walk={walk_edges - viewer_edges} "
            f"only-viewer={viewer_edges - walk_edges}"
        )
        matched += 1


def test_determinism(merged):
    walk_model, _, _ = merged
    spec = load_walk_spec(SPEC_PATH)
    out1 = run_walk(spec, walk_model)
    out2 = run_walk(spec, walk_model)
    assert out1["cards"] == out2["cards"]
