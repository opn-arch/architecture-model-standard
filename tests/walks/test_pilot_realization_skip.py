"""Pilot parity test: WALK-realization-skip-{capability,component} vs
legacy `_realization_skip_reasons`.

Two verdict-shape walks (one per kind, mirrors realize-* pattern) that
detect direction-inverted realizes edges — the L9 bug shape.

The viewer helper returns ``{entity_id: reason_str}`` for the direction-
inverted subset. We consider a walk card "flagged" iff its verdict is
``contradictory``. The set of flagged ids MUST equal the viewer's key
set for each kind.
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
SPEC_CAP = REPO / ".architecture/model/walks/realization-skip-capability.v3.yaml"
SPEC_COMP = REPO / ".architecture/model/walks/realization-skip-component.v3.yaml"
DEFAULT_MODEL = REPO / ".architecture-model.v3.yaml"
FRAGMENT_DIR = REPO / ".architecture/model"
LEGACY_SCRIPT = REPO / "scripts/build_v3_viewer.py"


def _load_legacy_helpers():
    spec = importlib.util.spec_from_file_location(
        "_legacy_v3_viewer_skip", LEGACY_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_legacy_v3_viewer_skip"] = mod
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
    out_edges: dict[str, list[tuple[str, str]]] = {}
    in_edges: dict[str, list[tuple[str, str]]] = {}
    for r in relationships:
        f, t, rt = r.get("from"), r.get("to"), r.get("type")
        if f is None or t is None or rt is None:
            continue
        out_edges.setdefault(f, []).append((t, rt))
        in_edges.setdefault(t, []).append((f, rt))
    return walk_model, entities_by_kind, out_edges, in_edges


@pytest.fixture(scope="module")
def viewer_reasons(merged):
    legacy = _load_legacy_helpers()
    _, entities_by_kind, out_edges, in_edges = merged
    return legacy._realization_skip_reasons(entities_by_kind, out_edges, in_edges)


def test_specs_load():
    scap = load_walk_spec(SPEC_CAP)
    scomp = load_walk_spec(SPEC_COMP)
    assert scap.id == "WALK-realization-skip-capability"
    assert scomp.id == "WALK-realization-skip-component"
    assert scap.scope.kind == "capability"
    assert scomp.scope.kind == "component"
    assert scap.audits == scomp.audits == ("CAP-WK.realization-skip",)


def test_capability_flagged_parity(merged, viewer_reasons):
    walk_model, entities_by_kind, _, _ = merged
    spec = load_walk_spec(SPEC_CAP)
    out = run_walk(spec, walk_model)
    walk_flagged = {
        c["entity_id"] for c in out["cards"]
        if c["verdict"] == "contradictory"
    }
    cap_ids = set(entities_by_kind.get("capabilities", {}).keys())
    viewer_flagged = {eid for eid in viewer_reasons if eid in cap_ids}
    assert walk_flagged == viewer_flagged, (
        f"only-walk={walk_flagged - viewer_flagged} "
        f"only-viewer={viewer_flagged - walk_flagged}"
    )


def test_component_flagged_parity(merged, viewer_reasons):
    walk_model, entities_by_kind, _, _ = merged
    spec = load_walk_spec(SPEC_COMP)
    out = run_walk(spec, walk_model)
    walk_flagged = {
        c["entity_id"] for c in out["cards"]
        if c["verdict"] == "contradictory"
    }
    comp_ids = set(entities_by_kind.get("components", {}).keys())
    viewer_flagged = {eid for eid in viewer_reasons if eid in comp_ids}
    assert walk_flagged == viewer_flagged, (
        f"only-walk={walk_flagged - viewer_flagged} "
        f"only-viewer={viewer_flagged - walk_flagged}"
    )


def test_capability_walks_every_capability(merged):
    walk_model, entities_by_kind, _, _ = merged
    spec = load_walk_spec(SPEC_CAP)
    out = run_walk(spec, walk_model)
    walked = {c["entity_id"] for c in out["cards"]}
    assert walked == set(entities_by_kind.get("capabilities", {}).keys())


def test_component_walks_every_component(merged):
    walk_model, entities_by_kind, _, _ = merged
    spec = load_walk_spec(SPEC_COMP)
    out = run_walk(spec, walk_model)
    walked = {c["entity_id"] for c in out["cards"]}
    assert walked == set(entities_by_kind.get("components", {}).keys())


def test_determinism(merged):
    walk_model, _, _, _ = merged
    for spath in (SPEC_CAP, SPEC_COMP):
        spec = load_walk_spec(spath)
        out1 = run_walk(spec, walk_model)
        out2 = run_walk(spec, walk_model)
        assert out1["cards"] == out2["cards"]
