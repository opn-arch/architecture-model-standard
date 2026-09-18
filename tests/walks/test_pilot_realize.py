"""Pilot parity test: WALK-realize-* vs. legacy _mermaid_realization.

Kind-dispatched 2-hop retrofit. Seven WalkSpecs (one per entity kind)
each declare their own hop sequence via TraverseSpec.hops. Parity is
structural — node/edge set equality against the viewer's induced
realization chain.

Silent-skip semantics differ by design:
- Viewer returns None when hop-1 (the primary realization dimension) is
  empty for the given entity.
- Walk still emits a card with only the root in subgraph_nodes and an
  empty subgraph_edges list. Consumers filter by empty edges.
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
WALKS_DIR = REPO / ".architecture/model/walks"
DEFAULT_MODEL = REPO / ".architecture-model.v3.yaml"
FRAGMENT_DIR = REPO / ".architecture/model"
LEGACY_SCRIPT = REPO / "scripts/build_v3_viewer.py"

SPECS = {
    "capability": WALKS_DIR / "realize-capability.v3.yaml",
    "component": WALKS_DIR / "realize-component.v3.yaml",
    "behavior": WALKS_DIR / "realize-behavior.v3.yaml",
    "interface": WALKS_DIR / "realize-interface.v3.yaml",
    "layer": WALKS_DIR / "realize-layer.v3.yaml",
    "actor": WALKS_DIR / "realize-actor.v3.yaml",
    "constraint": WALKS_DIR / "realize-constraint.v3.yaml",
}


def _load_legacy_helpers():
    spec = importlib.util.spec_from_file_location(
        "_legacy_v3_viewer_realize", LEGACY_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_legacy_v3_viewer_realize"] = mod
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
    """Replicate the viewer's out_edges/in_edges shape:
    {node_id: [(other_id, rel_type), ...]}."""
    out_edges: dict[str, list[tuple[str, str]]] = {}
    in_edges: dict[str, list[tuple[str, str]]] = {}
    for r in relationships:
        f, t, rt = r.get("from"), r.get("to"), r.get("type")
        if f is None or t is None or rt is None:
            continue
        out_edges.setdefault(f, []).append((t, rt))
        in_edges.setdefault(t, []).append((f, rt))
    return out_edges, in_edges


# Parses viewer Mermaid edge lines like: `  n_COMP_1 -->|realizes| n_CAP_2`
# and reverses viewer's _mid() encoding (`n_` prefix, `.`/`-`/`/` -> `_`).
_EDGE_RE = re.compile(r"^\s*(\S+)\s*-->\|([^|]+)\|\s*(\S+)\s*$")


def _viewer_edges_from_mermaid(mermaid: str) -> set[tuple[str, str, str]]:
    """Extract (mid_from, label, mid_to) triples from viewer's mermaid output.
    ``mid`` is the _mid()-encoded id; not the original entity id."""
    edges: set[tuple[str, str, str]] = set()
    for line in mermaid.splitlines():
        m = _EDGE_RE.match(line)
        if not m:
            continue
        edges.add((m.group(1), m.group(3), m.group(2)))
    return edges


def _mid(eid: str) -> str:
    """Mirror viewer's _mid(): 'n' + alnum-only chars from eid."""
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


@pytest.mark.parametrize("kind", list(SPECS.keys()))
def test_spec_loads_and_declares_hop_mode(kind):
    spec = load_walk_spec(SPECS[kind])
    assert spec.id == f"WALK-realize-{kind}"
    assert spec.audits == ("CAP-WK.realize",)
    assert spec.scope.kind == kind
    assert spec.traverse.hops, f"realize-{kind} should use hop mode"
    assert spec.emit.include_subgraph is True


@pytest.mark.parametrize("kind", list(SPECS.keys()))
def test_walk_visits_every_entity_of_kind(merged, kind):
    walk_model, entities_by_kind, _, _, _ = merged
    plural = {
        "capability": "capabilities",
        "component": "components",
        "behavior": "behaviors",
        "interface": "interfaces",
        "layer": "layers",
        "actor": "actors",
        "constraint": "constraints",
    }[kind]
    expected = set(entities_by_kind.get(plural, {}).keys())
    if not expected:
        pytest.skip(f"no {plural} in model")
    spec = load_walk_spec(SPECS[kind])
    out = run_walk(spec, walk_model)
    walked = {c["entity_id"] for c in out["cards"]}
    assert walked == expected, (
        f"walk must visit every {kind}; "
        f"missing={expected - walked} extra={walked - expected}"
    )


@pytest.mark.parametrize("kind", list(SPECS.keys()))
def test_realize_structural_parity(merged, kind):
    """For each entity of `kind`, walk's subgraph MUST equal viewer's
    realization chain (nodes + typed edges)."""
    legacy = _load_legacy_helpers()
    walk_model, entities_by_kind, relationships, out_edges, in_edges = merged
    plural = {
        "capability": "capabilities",
        "component": "components",
        "behavior": "behaviors",
        "interface": "interfaces",
        "layer": "layers",
        "actor": "actors",
        "constraint": "constraints",
    }[kind]
    entity_ids = list(entities_by_kind.get(plural, {}).keys())
    if not entity_ids:
        pytest.skip(f"no {plural} in model")

    spec = load_walk_spec(SPECS[kind])
    out = run_walk(spec, walk_model)
    cards = {c["entity_id"]: c for c in out["cards"]}

    matched = 0
    silent = 0
    for eid in entity_ids:
        card = cards[eid]
        result = legacy._mermaid_realization(
            entities_by_kind, relationships, eid, kind, out_edges, in_edges
        )
        if result is None:
            # Silent-skip: walk must emit a card with only root visited.
            silent += 1
            assert card["subgraph_edges"] == [], (
                f"viewer silent-skipped {kind} {eid} but walk edges: "
                f"{card['subgraph_edges']}"
            )
            assert card["subgraph_nodes"] == [eid], (
                f"viewer silent-skipped {kind} {eid} but walk nodes: "
                f"{card['subgraph_nodes']}"
            )
            continue
        _, viewer_nodes = result
        walk_nodes = set(card["subgraph_nodes"])
        assert walk_nodes == set(viewer_nodes), (
            f"node-set divergence for {kind} {eid}: "
            f"only-walk={walk_nodes - set(viewer_nodes)} "
            f"only-viewer={set(viewer_nodes) - walk_nodes}"
        )
        # Edge parity: parse the viewer's mermaid and compare (from, to, label)
        # sets after mapping walk ids through _mid().
        mermaid, _ = result
        viewer_edges = _viewer_edges_from_mermaid(mermaid)
        walk_edges = {
            (_mid(e["from"]), _mid(e["to"]), e["type"])
            for e in card["subgraph_edges"]
        }
        assert walk_edges == viewer_edges, (
            f"edge-set divergence for {kind} {eid}: "
            f"only-walk={walk_edges - viewer_edges} "
            f"only-viewer={viewer_edges - walk_edges}"
        )
        matched += 1

    assert matched > 0 or silent > 0, (
        f"expected at least one non-empty comparison for {kind}"
    )


def test_all_realize_walks_deterministic(merged):
    walk_model, _, _, _, _ = merged
    for path in SPECS.values():
        spec = load_walk_spec(path)
        out1 = run_walk(spec, walk_model)
        out2 = run_walk(spec, walk_model)
        assert out1["cards"] == out2["cards"], (
            f"non-deterministic output for {spec.id}"
        )
