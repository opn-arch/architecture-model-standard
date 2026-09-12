"""Every component must be transitively contained by a layer.

Guards the ISO/IEC/IEEE 42010 logical-viewpoint invariant: no orphaned
components in the logical architecture. Containment is transitive over
`contains` edges — a layer may contain a component directly, or contain
a parent component which contains the sub-component.
"""

from pathlib import Path

import pytest
import yaml


MODEL_PATH = Path(__file__).resolve().parents[1] / ".architecture-model.yaml"


def _fid(r): return r.get("from_id") or r.get("from")
def _tid(r): return r.get("to_id") or r.get("to")


@pytest.fixture(scope="module")
def raw_model():
    with MODEL_PATH.open() as f:
        return yaml.safe_load(f)


def test_every_component_reachable_from_some_layer(raw_model):
    comps = {c["id"] for c in raw_model["entities"]["components"]}
    layers = {l["id"] for l in raw_model["entities"]["layers"]}

    # Build contains adjacency: parent -> {children}
    adj: dict[str, set[str]] = {}
    for r in raw_model["relationships"]:
        if r.get("type") != "contains":
            continue
        a, b = _fid(r), _tid(r)
        if a and b:
            adj.setdefault(a, set()).add(b)

    # BFS from every layer over `contains` edges, collect reached components
    reached: set[str] = set()
    stack = list(layers)
    seen = set(stack)
    while stack:
        node = stack.pop()
        for child in adj.get(node, ()):
            if child in comps:
                reached.add(child)
            if child not in seen:
                seen.add(child)
                stack.append(child)

    orphans = sorted(comps - reached)
    assert not orphans, (
        f"{len(orphans)} component(s) not transitively contained by any layer: "
        f"{orphans}"
    )


def test_every_top_level_component_directly_contained_by_layer(raw_model):
    """Top-level components (no parent_id) must have a direct LAY-* contains edge."""
    layers = {l["id"] for l in raw_model["entities"]["layers"]}
    top_comps = {
        c["id"] for c in raw_model["entities"]["components"]
        if not c.get("parent_id")
    }

    direct = {
        _tid(r) for r in raw_model["relationships"]
        if r.get("type") == "contains" and _fid(r) in layers
    }

    missing = sorted(top_comps - direct)
    assert not missing, (
        f"{len(missing)} top-level component(s) missing direct layer containment: "
        f"{missing}"
    )
