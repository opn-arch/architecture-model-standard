"""Tests for the root architecture package index."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from architecture_model.lifecycle import journal as journal_mod
from architecture_model.lifecycle.journal import Journal
from architecture_model.lifecycle.package import load_package
from architecture_model.lifecycle.package_index import (
    IndexEntry,
    find_by_id,
    find_by_slug,
    find_containing,
    load_index,
    rebuild_index,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "lifecycle"
SAMPLE = FIXTURES / "sample_package_tree"


def _stage(tmp_path: Path) -> Path:
    """Copy the sample package tree into tmp_path/repo and return repo root."""
    repo = tmp_path / "repo"
    shutil.copytree(SAMPLE, repo / "pkg")
    return repo


def _root_pkg(repo: Path):
    return load_package(repo / "pkg")


def test_rebuild_index_writes_file_atomically(tmp_path: Path):
    repo = _stage(tmp_path)
    pkg = _root_pkg(repo)
    idx_path = rebuild_index(repo, pkg)
    assert idx_path == repo / ".architecture" / "package-index.yaml"
    assert idx_path.exists()
    data = yaml.safe_load(idx_path.read_text(encoding="utf-8"))
    assert data["contract_version"] == "1.0.0"
    assert "entries" in data and isinstance(data["entries"], list)


def test_rebuild_index_records_all_descendants(tmp_path: Path):
    repo = _stage(tmp_path)
    pkg = _root_pkg(repo)
    rebuild_index(repo, pkg)
    entries = load_index(repo / ".architecture" / "package-index.yaml")
    ids = {e.architecture_id for e in entries}
    assert ids == {"root-pkg", "core-pkg", "config-pkg", "manifest-pkg"}


def test_rebuild_index_records_journal_event(tmp_path: Path):
    repo = _stage(tmp_path)
    pkg = _root_pkg(repo)
    rebuild_index(repo, pkg)
    j = Journal(repo / ".architecture" / "journal.jsonl")
    events = [e["event"] for e in j.replay()]
    assert journal_mod.INDEX_REBUILD_COMMIT in events
    assert journal_mod.INDEX_REBUILD_COMMIT == "index.rebuild.commit"


def test_rebuild_index_deterministic_order(tmp_path: Path):
    repo = _stage(tmp_path)
    pkg = _root_pkg(repo)
    rebuild_index(repo, pkg)
    entries = load_index(repo / ".architecture" / "package-index.yaml")
    slugs = [e.slug for e in entries]
    assert slugs == sorted(slugs)
    assert slugs == ["config-pkg", "core-pkg", "manifest-pkg", "root-pkg"]


def test_rebuild_index_parent_ids(tmp_path: Path):
    repo = _stage(tmp_path)
    pkg = _root_pkg(repo)
    rebuild_index(repo, pkg)
    entries = load_index(repo / ".architecture" / "package-index.yaml")
    by_id = {e.architecture_id: e for e in entries}
    assert by_id["root-pkg"].parent_id is None
    for child in ("core-pkg", "config-pkg", "manifest-pkg"):
        assert by_id[child].parent_id == "root-pkg"


def test_load_index_roundtrip(tmp_path: Path):
    repo = _stage(tmp_path)
    pkg = _root_pkg(repo)
    idx_path = rebuild_index(repo, pkg)
    entries_a = load_index(idx_path)
    # write to alternate path via rebuild_index index_path override
    alt = tmp_path / "alt-index.yaml"
    rebuild_index(repo, pkg, index_path=alt)
    entries_b = load_index(alt)
    assert entries_a == entries_b


def test_load_index_rejects_wrong_contract_version(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "contract_version: '9.9.9'\n"
        "generated_at: '2026-01-01T00:00:00.000000Z'\n"
        "repo_root: '/repo'\n"
        "entries: []\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_index(bad)


def test_find_by_id(tmp_path: Path):
    repo = _stage(tmp_path)
    pkg = _root_pkg(repo)
    rebuild_index(repo, pkg)
    entries = load_index(repo / ".architecture" / "package-index.yaml")
    assert find_by_id(entries, "core-pkg").architecture_id == "core-pkg"
    assert find_by_id(entries, "nope") is None


def test_find_by_slug(tmp_path: Path):
    repo = _stage(tmp_path)
    pkg = _root_pkg(repo)
    rebuild_index(repo, pkg)
    entries = load_index(repo / ".architecture" / "package-index.yaml")
    assert find_by_slug(entries, "config-pkg").architecture_id == "config-pkg"
    assert find_by_slug(entries, "nope") is None


def test_find_containing_returns_deepest_owner(tmp_path: Path):
    repo = _stage(tmp_path)
    pkg = _root_pkg(repo)
    rebuild_index(repo, pkg)
    entries = load_index(repo / ".architecture" / "package-index.yaml")
    # source file located inside child package dir
    source = repo / "pkg" / "children" / "core" / "some_module.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("# marker\n", encoding="utf-8")
    hit = find_containing(entries, repo, source)
    assert hit is not None
    assert hit.architecture_id == "core-pkg"
    # source at root-only path
    root_source = repo / "pkg" / "top_module.py"
    root_source.write_text("# marker\n", encoding="utf-8")
    hit2 = find_containing(entries, repo, root_source)
    assert hit2 is not None
    assert hit2.architecture_id == "root-pkg"


def test_find_containing_returns_none_for_outside_paths(tmp_path: Path):
    repo = _stage(tmp_path)
    pkg = _root_pkg(repo)
    rebuild_index(repo, pkg)
    entries = load_index(repo / ".architecture" / "package-index.yaml")
    outside = tmp_path / "elsewhere" / "foo.py"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("x\n", encoding="utf-8")
    assert find_containing(entries, repo, outside) is None
