"""Tests for pipeline_v3.cluster — T0.14 Phase 6.3.

cluster.py groups ScannedModules into Clusters by dotted-name prefix.
Each Cluster is a candidate v3 component. Grouping depth is configurable;
default groups by the first 3 dotted segments (e.g. src.pkg.subpkg.mod →
cluster root "src.pkg.subpkg").

Cluster ids are deterministic: COMP-<sha1[:8]> of the root prefix.
"""

from __future__ import annotations

from pathlib import Path

from architecture_model.pipeline_v3.cluster import Cluster, cluster_modules
from architecture_model.pipeline_v3.scan import ScannedModule, ScanResult


def _mod(name: str) -> ScannedModule:
    return ScannedModule(
        file=f"src/{name.replace('.', '/')}.py",
        name=name,
        docstring="d",
        functions=[{"name": "f"}],
        classes=[],
        imports=[],
        line_count=1,
    )


def _scan(*names: str) -> ScanResult:
    return ScanResult(source_root=Path("/tmp"), modules=[_mod(n) for n in names])


# ---------------------------------------------------------------------------
# Core clustering behavior
# ---------------------------------------------------------------------------


def test_cluster_returns_list_of_clusters():
    scan = _scan("a.b.c", "a.b.d")
    clusters = cluster_modules(scan)
    assert isinstance(clusters, list)
    assert all(isinstance(c, Cluster) for c in clusters)


def test_cluster_groups_modules_by_prefix():
    scan = _scan("a.b.c", "a.b.d", "a.e.f")
    clusters = cluster_modules(scan, depth=2)
    assert len(clusters) == 2
    by_root = {c.root_prefix: c for c in clusters}
    assert set(by_root) == {"a.b", "a.e"}
    assert sorted(m.name for m in by_root["a.b"].modules) == ["a.b.c", "a.b.d"]
    assert [m.name for m in by_root["a.e"].modules] == ["a.e.f"]


def test_cluster_default_depth_is_three():
    scan = _scan("a.b.c.d", "a.b.c.e", "a.b.x.y")
    clusters = cluster_modules(scan)  # default depth=3
    assert {c.root_prefix for c in clusters} == {"a.b.c", "a.b.x"}


def test_cluster_shorter_than_depth_uses_whole_name_as_root():
    scan = _scan("a", "a.b", "c")
    clusters = cluster_modules(scan, depth=3)
    roots = {c.root_prefix for c in clusters}
    # "a" (1 segment) and "a.b" (2 segments) both fall under depth-3 window
    # so their prefix IS the whole name
    assert roots == {"a", "a.b", "c"}


def test_cluster_id_is_deterministic_sha1_prefix():
    import hashlib

    scan = _scan("a.b.c")
    c = cluster_modules(scan, depth=3)[0]
    expected = "COMP-" + hashlib.sha1(b"a.b.c").hexdigest()[:8]
    assert c.id == expected


def test_cluster_id_stable_across_runs():
    scan = _scan("a.b.c", "a.b.d")
    ids1 = [c.id for c in cluster_modules(scan)]
    ids2 = [c.id for c in cluster_modules(scan)]
    assert ids1 == ids2


def test_cluster_name_is_last_prefix_segment():
    scan = _scan("src.pkg.pipeline_v3.scan", "src.pkg.pipeline_v3.cluster")
    c = cluster_modules(scan, depth=3)[0]
    assert c.name == "pipeline_v3"


def test_cluster_ordering_is_deterministic():
    scan = _scan("z.a.b", "a.x.y", "m.n.o")
    clusters = cluster_modules(scan)
    roots = [c.root_prefix for c in clusters]
    assert roots == sorted(roots)


def test_cluster_modules_are_sorted_by_name():
    scan = ScanResult(
        source_root=Path("/tmp"),
        modules=[_mod("a.b.z"), _mod("a.b.a"), _mod("a.b.m")],
    )
    c = cluster_modules(scan, depth=2)[0]
    assert [m.name for m in c.modules] == ["a.b.a", "a.b.m", "a.b.z"]


def test_cluster_empty_scan_returns_empty_list():
    scan = ScanResult(source_root=Path("/tmp"), modules=[])
    assert cluster_modules(scan) == []


def test_cluster_module_count_property():
    scan = _scan("a.b.c", "a.b.d")
    c = cluster_modules(scan, depth=2)[0]
    assert c.module_count == 2


def test_cluster_depth_one_groups_by_top_level():
    scan = _scan("a.x.y", "a.z.w", "b.p.q")
    clusters = cluster_modules(scan, depth=1)
    roots = {c.root_prefix for c in clusters}
    assert roots == {"a", "b"}
