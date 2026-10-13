"""Tests for pipeline_v3.link — T0.14 Phase 6.4.

link.py infers depends-on edges between Clusters from module import
signals. For each import in a module belonging to cluster A, if the
import resolves to a module in cluster B (A ≠ B), a link is recorded.
Weight = count of distinct (source_module, target_cluster) pairs.
"""

from __future__ import annotations

from pathlib import Path

from architecture_model.pipeline_v3.cluster import Cluster, cluster_modules
from architecture_model.pipeline_v3.link import Link, link_clusters
from architecture_model.pipeline_v3.scan import ScannedModule, ScanResult


def _mod(name: str, imports: list[str] | None = None) -> ScannedModule:
    return ScannedModule(
        file=f"src/{name.replace('.', '/')}.py",
        name=name,
        docstring="d",
        functions=[{"name": "f"}],
        classes=[],
        imports=imports or [],
        line_count=1,
    )


def _scan(*modules: ScannedModule) -> ScanResult:
    return ScanResult(source_root=Path("/tmp"), modules=list(modules))


# ---------------------------------------------------------------------------
# Core behavior
# ---------------------------------------------------------------------------


def test_link_returns_list_of_links():
    scan = _scan(_mod("a.b.x", imports=["a.c.y"]), _mod("a.c.y"))
    clusters = cluster_modules(scan, depth=2)
    links = link_clusters(clusters)
    assert isinstance(links, list)
    assert all(isinstance(l, Link) for l in links)


def test_link_import_across_clusters_produces_edge():
    scan = _scan(_mod("a.b.x", imports=["a.c.y"]), _mod("a.c.y"))
    clusters = cluster_modules(scan, depth=2)  # → a.b, a.c
    by_root = {c.root_prefix: c.id for c in clusters}
    links = link_clusters(clusters)
    assert len(links) == 1
    l = links[0]
    assert l.from_cluster == by_root["a.b"]
    assert l.to_cluster == by_root["a.c"]
    assert l.kind == "depends-on"
    assert l.weight == 1


def test_link_intra_cluster_import_is_ignored():
    """Imports within the same cluster don't create self-loops."""
    scan = _scan(
        _mod("a.b.x", imports=["a.b.y"]),
        _mod("a.b.y"),
    )
    clusters = cluster_modules(scan, depth=2)
    assert link_clusters(clusters) == []


def test_link_unresolvable_import_is_ignored():
    """Imports of stdlib / third-party (no matching cluster) are ignored."""
    scan = _scan(_mod("a.b.x", imports=["os", "sys", "third_party.lib"]))
    clusters = cluster_modules(scan, depth=2)
    assert link_clusters(clusters) == []


def test_link_weight_aggregates_multiple_edges():
    """Two modules in A each importing something in B → weight=2."""
    scan = _scan(
        _mod("a.b.x", imports=["a.c.z"]),
        _mod("a.b.y", imports=["a.c.z"]),
        _mod("a.c.z"),
    )
    clusters = cluster_modules(scan, depth=2)
    links = link_clusters(clusters)
    assert len(links) == 1
    assert links[0].weight == 2


def test_link_duplicate_import_from_same_module_counts_once():
    """Same source module importing the same target twice → weight=1."""
    scan = _scan(
        _mod("a.b.x", imports=["a.c.z", "a.c.z"]),
        _mod("a.c.z"),
    )
    clusters = cluster_modules(scan, depth=2)
    links = link_clusters(clusters)
    assert len(links) == 1
    assert links[0].weight == 1


def test_link_ordering_is_deterministic():
    scan = _scan(
        _mod("a.z.m", imports=["a.a.m"]),
        _mod("a.m.p", imports=["a.a.m"]),
        _mod("a.a.m"),
    )
    clusters = cluster_modules(scan, depth=2)
    links = link_clusters(clusters)
    pairs = [(l.from_cluster, l.to_cluster) for l in links]
    assert pairs == sorted(pairs)


def test_link_empty_clusters_returns_empty_list():
    assert link_clusters([]) == []


def test_link_matches_src_prefixed_module_against_bare_import():
    """AMS reality: modules are `src.architecture_model.foo` but imports
    are `architecture_model.foo` (without `src.`). link must resolve
    both forms."""
    scan = _scan(
        _mod("src.pkg.a.mod", imports=["pkg.b.thing"]),
        _mod("src.pkg.b.thing"),
    )
    clusters = cluster_modules(scan, depth=3)  # src.pkg.a, src.pkg.b
    links = link_clusters(clusters)
    assert len(links) == 1
    assert links[0].weight == 1


def test_link_prefers_longest_matching_prefix():
    """When both cluster A (a.b) and cluster A.sub (a.b.c) exist as clusters
    (edge case), the import `a.b.c.mod` should resolve to A.sub, not A."""
    scan = _scan(
        _mod("z.q.m", imports=["a.b.c.deep"]),
        _mod("a.b.p"),      # → cluster a.b
        _mod("a.b.c.deep"),  # → cluster a.b.c
    )
    clusters = cluster_modules(scan, depth=3)
    by_root = {c.root_prefix: c.id for c in clusters}
    links = link_clusters(clusters)
    assert len(links) == 1
    # Target should be the more-specific a.b.c cluster
    assert links[0].to_cluster == by_root["a.b.c"]
