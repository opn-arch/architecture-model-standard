"""resolve_ref helper for federated refs — Phase 4-C Task 16.

Supports two ref forms:

* ``file://<path>/package.yaml`` — loads the child package directly from a
  local filesystem path. Handy for monorepos and adjacent working trees.
* ``repo://<name>`` — resolves ``name`` through the parent project's
  ``.architecture/repos.yaml`` mapping and loads the target package.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from architecture_model.lifecycle.model_slice_materializer import resolve_ref
from architecture_model.lifecycle.package import ArchitecturePackage


CHILD_PKG_YAML = dedent(
    """\
    architecture_id: child-pkg
    name: Child
    slug: child-pkg
    contract_version: "1.0.0"
    model_ref: .architecture-model.yaml
    manifest_ref: manifest.json
    """
)
CHILD_MODEL = "meta:\n  schema_version: '2.1.0'\n  project: c\nentities: {}\nrelationships: []\n"


def _write_child(dir_path: Path) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / "package.yaml").write_text(CHILD_PKG_YAML)
    (dir_path / ".architecture-model.yaml").write_text(CHILD_MODEL)
    (dir_path / "manifest.json").write_text("{}")
    return dir_path


def test_resolve_ref_file_form_directory(tmp_path):
    child = _write_child(tmp_path / "child-a")
    pkg = resolve_ref(f"file://{child}")
    assert isinstance(pkg, ArchitecturePackage)
    assert pkg.id == "child-pkg"


def test_resolve_ref_file_form_yaml_path(tmp_path):
    child = _write_child(tmp_path / "child-b")
    pkg = resolve_ref(f"file://{child / 'package.yaml'}")
    assert isinstance(pkg, ArchitecturePackage)
    assert pkg.id == "child-pkg"


def test_resolve_ref_repo_form(tmp_path):
    child = _write_child(tmp_path / "somewhere" / "child-c")
    registry_dir = tmp_path / "arch"
    registry_dir.mkdir()
    (registry_dir / "repos.yaml").write_text(f"data-service: {child}\n")
    pkg = resolve_ref("repo://data-service", repo_registry=registry_dir / "repos.yaml")
    assert isinstance(pkg, ArchitecturePackage)
    assert pkg.id == "child-pkg"


def test_resolve_ref_unknown_scheme_raises(tmp_path):
    with pytest.raises(ValueError, match="unknown ref scheme"):
        resolve_ref("http://example.com/pkg.yaml")


def test_resolve_ref_repo_missing_registry_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        resolve_ref("repo://nope", repo_registry=tmp_path / "does-not-exist.yaml")


def test_resolve_ref_repo_name_not_in_registry(tmp_path):
    registry = tmp_path / "repos.yaml"
    registry.write_text("known: /some/path\n")
    with pytest.raises(KeyError, match="unknown"):
        resolve_ref("repo://unknown", repo_registry=registry)


def test_resolve_ref_empty_ref_raises():
    with pytest.raises(ValueError):
        resolve_ref("")
