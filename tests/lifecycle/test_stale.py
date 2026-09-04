"""Tests for the semantic-intersection stale graph (T11)."""
from __future__ import annotations

from pathlib import Path

import pytest

from architecture_model.lifecycle.package import load_package
from architecture_model.lifecycle.stale import (
    CycleError,
    DependencyGraph,
    StaleNode,
    StaleSet,
    build_graph,
    mark_stale,
    stale_report,
)


FIXTURE = Path(__file__).parent.parent / "fixtures" / "lifecycle" / "sample_package_tree"


# ---------------------------------------------------------------------------
# DependencyGraph primitives
# ---------------------------------------------------------------------------

def _node(nid: str, kind: str = "slice", owned=(), inputs=()) -> StaleNode:
    return StaleNode(
        node_id=nid, kind=kind, owned_paths=tuple(owned), inputs=tuple(inputs)
    )


def test_add_node_add_edge_descendants_ancestors():
    g = DependencyGraph()
    g.add_node(_node("a", "package"))
    g.add_node(_node("b", "model"))
    g.add_node(_node("c", "manifest"))
    g.add_node(_node("d", "artifact"))
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    g.add_edge("b", "d")
    assert g.descendants("a") == {"b", "c", "d"}
    assert g.descendants("b") == {"c", "d"}
    assert g.descendants("d") == set()
    assert g.ancestors("c") == {"a", "b"}
    assert g.ancestors("a") == set()


def test_topological_order_is_deterministic():
    g = DependencyGraph()
    for nid in ["x", "y", "z", "w"]:
        g.add_node(_node(nid))
    g.add_edge("x", "y")
    g.add_edge("y", "z")
    g.add_edge("x", "w")
    order = g.topological_order()
    assert order.index("x") < order.index("y") < order.index("z")
    assert order.index("x") < order.index("w")
    # Repeat runs stable
    assert g.topological_order() == order


def test_cycle_detected_by_topological_order():
    g = DependencyGraph()
    g.add_node(_node("a"))
    g.add_node(_node("b"))
    g.add_edge("a", "b")
    g.add_edge("b", "a")
    with pytest.raises(CycleError):
        g.topological_order()


def test_add_edge_unknown_node_raises():
    g = DependencyGraph()
    g.add_node(_node("a"))
    with pytest.raises(KeyError):
        g.add_edge("a", "missing")


# ---------------------------------------------------------------------------
# build_graph
# ---------------------------------------------------------------------------

def test_build_graph_from_sample_package_tree():
    pkg = load_package(FIXTURE)
    graph = build_graph(pkg)
    order = graph.topological_order()
    # Expected nodes for each of the 4 packages: package, model, manifest.
    expected_ids = {
        "package:root-pkg", "model:root-pkg", "manifest:root-pkg",
        "package:core-pkg", "model:core-pkg", "manifest:core-pkg",
        "package:manifest-pkg", "model:manifest-pkg", "manifest:manifest-pkg",
        "package:config-pkg", "model:config-pkg", "manifest:config-pkg",
    }
    assert expected_ids.issubset(set(order))
    # package → model → manifest edges
    assert "model:root-pkg" in graph.descendants("package:root-pkg")
    assert "manifest:root-pkg" in graph.descendants("model:root-pkg")
    # child.model → parent.model
    assert "model:root-pkg" in graph.descendants("model:core-pkg")


# ---------------------------------------------------------------------------
# mark_stale — semantic intersection
# ---------------------------------------------------------------------------

def test_mark_stale_matches_owned_paths_and_propagates():
    g = DependencyGraph()
    g.add_node(_node("pkg:root", "package", owned=["package.yaml"]))
    g.add_node(_node("model:root", "model", owned=[".architecture-model.yaml"]))
    g.add_node(_node("slice:core", "slice", owned=["core/**"]))
    g.add_node(_node("view:core", "view"))  # transitive only
    g.add_node(_node("artifact:core", "artifact"))
    g.add_edge("model:root", "slice:core")
    g.add_edge("slice:core", "view:core")
    g.add_edge("view:core", "artifact:core")

    result = mark_stale(g, [Path("core/api.py")], package_root=Path("/root"))
    assert isinstance(result, StaleSet)
    assert "slice:core" in result.nodes
    assert "view:core" in result.nodes
    assert "artifact:core" in result.nodes
    assert "pkg:root" not in result.nodes
    assert "model:root" not in result.nodes
    # Reasons non-empty and deterministic
    assert result.reasons["slice:core"]
    assert "slice:core" in result.reasons["view:core"] or "upstream" in result.reasons["view:core"]


def test_mark_stale_semantic_intersection_no_match_leaves_slice_clean():
    g = DependencyGraph()
    g.add_node(_node("slice:core", "slice", owned=["core/**"]))
    g.add_node(_node("view:core", "view"))
    g.add_edge("slice:core", "view:core")

    result = mark_stale(g, [Path("cli/main.py")], package_root=Path("/root"))
    assert "slice:core" not in result.nodes
    assert "view:core" not in result.nodes


def test_mark_stale_empty_owned_paths_never_auto_invalidated():
    g = DependencyGraph()
    g.add_node(_node("view:x", "view", owned=()))
    result = mark_stale(g, [Path("anything.py")], package_root=Path("/root"))
    assert "view:x" not in result.nodes


def test_mark_stale_transitive_only_for_empty_paths():
    g = DependencyGraph()
    g.add_node(_node("model:root", "model", owned=[".architecture-model.yaml"]))
    g.add_node(_node("artifact:svg", "artifact", owned=()))
    g.add_edge("model:root", "artifact:svg")
    result = mark_stale(g, [Path(".architecture-model.yaml")], package_root=Path("/root"))
    assert "artifact:svg" in result.nodes
    assert "model:root" in result.nodes


def test_mark_stale_deterministic():
    g = DependencyGraph()
    g.add_node(_node("a", "slice", owned=["a/**"]))
    g.add_node(_node("b", "slice", owned=["b/**"]))
    g.add_node(_node("c", "view"))
    g.add_edge("a", "c")
    g.add_edge("b", "c")
    r1 = mark_stale(g, [Path("a/x"), Path("b/y")], package_root=Path("/root"))
    r2 = mark_stale(g, [Path("b/y"), Path("a/x")], package_root=Path("/root"))
    assert r1.nodes == r2.nodes
    assert r1.reasons == r2.reasons


# ---------------------------------------------------------------------------
# stale_report — cache
# ---------------------------------------------------------------------------

def test_stale_report_writes_cache(tmp_path):
    # Copy fixture to a tmp so we can write .architecture/ safely.
    import shutil
    dst = tmp_path / "pkg"
    shutil.copytree(FIXTURE, dst)
    pkg = load_package(dst)
    report = stale_report(pkg, [Path("children/core/foo.py")])
    assert isinstance(report, list)
    cache = dst / ".architecture" / "stale.yaml"
    assert cache.exists()
    # Sorted by (kind, node_id)
    keys = [(n.kind, n.node_id) for n in report]
    assert keys == sorted(keys)


def test_stale_report_no_crash_on_missing_cache(tmp_path):
    import shutil
    dst = tmp_path / "pkg"
    shutil.copytree(FIXTURE, dst)
    pkg = load_package(dst)
    # No .architecture dir yet.
    assert not (dst / ".architecture").exists()
    result = stale_report(pkg, [])
    assert isinstance(result, list)
