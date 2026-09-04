"""Tests for canonical package ownership + shared-file declarations."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from architecture_model.lifecycle.ownership import (
    FileOwnership,
    OwnershipConflict,
    OwnershipMap,
    UnownedFile,
    assert_no_conflicts,
    compute_ownership,
    load_remaps,
    record_remap,
)
from architecture_model.lifecycle.package import load_package

FIXTURES = Path(__file__).parent.parent / "fixtures" / "lifecycle"
TREE = FIXTURES / "ownership_tree"


def _load():
    return load_package(TREE)


def test_uniquely_owned_file_recorded():
    mp = compute_ownership(_load())
    fo = mp.files["children/child_a/src/only_a.py"]
    assert fo.owners == ("child-a",)
    assert fo.shared is False


def test_root_owned_file_recorded():
    mp = compute_ownership(_load())
    fo = mp.files["src/root_only.py"]
    assert fo.owners == ("root-pkg",)
    assert fo.shared is False


def test_shared_file_recorded_as_shared():
    mp = compute_ownership(_load())
    fo = mp.files["children/child_a/src/util.py"]
    assert fo.owners == ("child-a", "root-pkg")
    assert fo.shared is True
    # Should not appear in conflicts
    assert not any(c.path == fo.path for c in mp.conflicts)


def test_double_claimed_undeclared_is_conflict():
    mp = compute_ownership(_load())
    key = "children/child_a/src/conflict.py"
    assert key in mp.files
    fo = mp.files[key]
    assert fo.owners == ("child-a", "root-pkg")
    assert fo.shared is False
    assert any(c.path == key for c in mp.conflicts)


def test_unowned_file_listed():
    mp = compute_ownership(_load())
    assert "docs/readme.md" in mp.unowned
    # And not present in owned files
    assert "docs/readme.md" not in mp.files


def test_deterministic_order():
    mp1 = compute_ownership(_load())
    mp2 = compute_ownership(_load())
    assert list(mp1.files.keys()) == list(mp2.files.keys())
    assert [c.path for c in mp1.conflicts] == [c.path for c in mp2.conflicts]
    assert mp1.unowned == mp2.unowned


def test_assert_no_conflicts_raises_on_conflict():
    mp = compute_ownership(_load())
    with pytest.raises(OwnershipConflict):
        assert_no_conflicts(mp)


def test_assert_no_conflicts_ok_on_shared():
    mp = OwnershipMap(
        files={"a.py": FileOwnership("a.py", ("p1", "p2"), True)},
        conflicts=[],
        unowned=[],
    )
    assert_no_conflicts(mp)  # no raise


def test_assert_no_conflicts_ok_on_unowned():
    mp = OwnershipMap(files={}, conflicts=[], unowned=["orphan.py"])
    assert_no_conflicts(mp)  # no raise


def test_ownership_excludes_dot_dirs_and_pycache():
    mp = compute_ownership(_load())
    forbidden_prefixes = (".git/", "__pycache__/", ".architecture/")
    for key in list(mp.files.keys()) + mp.unowned:
        for pref in forbidden_prefixes:
            assert not key.startswith(pref), f"excluded file leaked: {key}"


def test_record_remap_appends(tmp_path):
    pkg = _load()
    remaps = tmp_path / "remaps.yaml"
    record_remap(pkg, "old-1", "new-1", remaps_path=remaps)
    record_remap(pkg, "old-2", "new-2", remaps_path=remaps)
    entries = load_remaps(remaps)
    assert len(entries) == 2
    assert entries[0]["old_slug"] == "old-1"
    assert entries[0]["new_slug"] == "new-1"
    assert entries[1]["old_slug"] == "old-2"
    assert entries[1]["new_slug"] == "new-2"
    assert entries[0]["architecture_id"] == "root-pkg"
    assert "ts" in entries[0]


def test_load_remaps_missing_file_returns_empty(tmp_path):
    assert load_remaps(tmp_path / "does-not-exist.yaml") == []


def test_record_remap_atomic_write(tmp_path):
    pkg = _load()
    remaps = tmp_path / "remaps.yaml"
    record_remap(pkg, "a", "b", remaps_path=remaps)
    record_remap(pkg, "c", "d", remaps_path=remaps)
    # No lingering temp files
    stray = [p.name for p in tmp_path.iterdir() if ".tmp-" in p.name]
    assert stray == []


def test_glob_relative_to_package_root_not_source_root(tmp_path):
    root_dir = tmp_path / "tree"
    child_dir = root_dir / "sub" / "child"
    child_dir.mkdir(parents=True)
    (root_dir / "root_top.py").write_text("")
    (child_dir / "child_top.py").write_text("")
    (root_dir / "package.yaml").write_text(
        "architecture_id: root\nname: R\nslug: root\ncontract_version: '1.0.0'\n"
        "model_ref: m.yaml\nmanifest_ref: mf.json\n"
        "children:\n  - sub/child\n"
        "owned_paths: []\n"
    )
    (child_dir / "package.yaml").write_text(
        "architecture_id: child\nname: C\nslug: child\ncontract_version: '1.0.0'\n"
        "model_ref: m.yaml\nmanifest_ref: mf.json\n"
        "owned_paths:\n  - '*.py'\n"
    )
    pkg = load_package(root_dir)
    mp = compute_ownership(pkg)
    # child_top.py should be owned by child (matches child's *.py rel-to-child)
    assert mp.files["sub/child/child_top.py"].owners == ("child",)
    # root_top.py must not be claimed by child (would be if pattern were rel to source_root)
    assert "root_top.py" in mp.unowned
