"""Tests for module-level import-graph clustering."""
from architecture_model.core.cluster import cluster_modules


def test_clusters_connected_modules_together():
    """Modules with import edges between them land in the same cluster."""
    modules = ["a.py", "b.py", "c.py", "d.py", "e.py", "f.py"]
    edges = [
        ("a.py", "b.py"), ("b.py", "c.py"), ("a.py", "c.py"),
        ("d.py", "e.py"), ("e.py", "f.py"), ("d.py", "f.py"),
    ]
    groups = cluster_modules(modules, edges, target_k=2)
    assert len(groups) == 2
    group_sets = [set(g) for g in groups]
    assert {"a.py", "b.py", "c.py"} in group_sets
    assert {"d.py", "e.py", "f.py"} in group_sets


def test_target_k_respected():
    """Clustering produces approximately target_k groups."""
    modules = [f"mod{i}.py" for i in range(20)]
    edges = [(f"mod{i}.py", f"mod{i+1}.py") for i in range(19)]
    groups = cluster_modules(modules, edges, target_k=4)
    assert 3 <= len(groups) <= 5


def test_isolated_modules_get_assigned():
    """Modules with no edges get merged into a group."""
    modules = ["a.py", "b.py", "c.py", "isolated.py"]
    edges = [("a.py", "b.py"), ("b.py", "c.py")]
    groups = cluster_modules(modules, edges, target_k=2)
    all_assigned = set()
    for g in groups:
        all_assigned.update(g)
    assert "isolated.py" in all_assigned


def test_min_cluster_size_merges_tiny_groups():
    """Groups smaller than min_cluster_size get merged into neighbors."""
    modules = ["a.py", "b.py", "c.py", "d.py", "e.py", "tiny.py"]
    edges = [
        ("a.py", "b.py"), ("b.py", "c.py"),
        ("d.py", "e.py"),
        ("tiny.py", "a.py"),
    ]
    groups = cluster_modules(modules, edges, target_k=2, min_cluster_size=2)
    for g in groups:
        if "a.py" in g:
            assert "tiny.py" in g
            break
