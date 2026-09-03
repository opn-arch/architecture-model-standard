"""Tests for ArchitecturePackage descriptor + recursive loader."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from architecture_model.lifecycle.package import (
    ArchitecturePackage,
    PackageCycleError,
    PackageDuplicateIdError,
    PackagePathTraversalError,
    PackageVersionError,
    PackageRef,
    SharedPath,
    iter_descendants,
    load_package,
    resolve,
)
from architecture_model.lifecycle.serialization import canonical_yaml_load

FIXTURES = Path(__file__).parent.parent / "fixtures" / "lifecycle"
SAMPLE = FIXTURES / "sample_package_tree"


def test_load_valid_root_package():
    pkg = load_package(SAMPLE)
    assert pkg.architecture_id == "root-pkg"
    assert pkg.name == "Root Package"
    assert pkg.slug == "root-pkg"
    assert pkg.contract_version == "1.0.0"
    assert pkg.model_ref == ".architecture-model.yaml"
    assert pkg.manifest_ref == "manifest.json"
    assert pkg.revisions_dir == "revisions"
    assert pkg.root == SAMPLE.resolve()
    assert set(pkg.children) == {"children/manifest", "children/core", "children/config"}


def test_load_accepts_directory_or_yaml_path():
    pkg_dir = load_package(SAMPLE)
    pkg_file = load_package(SAMPLE / "package.yaml")
    assert pkg_dir.architecture_id == pkg_file.architecture_id
    assert pkg_dir.root == pkg_file.root


def test_load_rejects_wrong_contract_version():
    with pytest.raises(PackageVersionError):
        load_package(FIXTURES / "bad_version")


def test_load_rejects_path_traversal():
    with pytest.raises(PackagePathTraversalError):
        load_package(FIXTURES / "bad_traversal")


def test_load_rejects_extra_fields(tmp_path):
    (tmp_path / "package.yaml").write_text(
        "architecture_id: p\nname: P\nslug: p\ncontract_version: '1.0.0'\n"
        "model_ref: .architecture-model.yaml\nmanifest_ref: manifest.json\n"
        "totally_unknown_field: 42\n"
    )
    with pytest.raises(ValidationError):
        load_package(tmp_path)


def test_load_rejects_bad_slug(tmp_path):
    (tmp_path / "package.yaml").write_text(
        "architecture_id: p\nname: P\nslug: BadSlug\ncontract_version: '1.0.0'\n"
        "model_ref: .architecture-model.yaml\nmanifest_ref: manifest.json\n"
    )
    with pytest.raises(ValidationError):
        load_package(tmp_path)


def test_iter_descendants_deterministic_order():
    pkg = load_package(SAMPLE)
    descendants = list(iter_descendants(pkg))
    slugs = [p.slug for p in descendants]
    # Root's children are core-pkg, manifest-pkg, config-pkg; sorted by slug
    assert slugs == ["config-pkg", "core-pkg", "manifest-pkg"]


def test_iter_descendants_include_self_flag():
    pkg = load_package(SAMPLE)
    all_pkgs = list(iter_descendants(pkg, include_self=True))
    assert all_pkgs[0].architecture_id == "root-pkg"
    assert len(all_pkgs) == 4


def test_iter_descendants_detects_cycle():
    pkg = load_package(FIXTURES / "bad_cycle")
    with pytest.raises(PackageCycleError):
        list(iter_descendants(pkg, include_self=True))


def test_iter_descendants_detects_duplicate_id():
    pkg = load_package(FIXTURES / "bad_duplicate_id")
    with pytest.raises(PackageDuplicateIdError):
        list(iter_descendants(pkg, include_self=True))


def test_resolve_finds_child_by_id():
    pkg = load_package(SAMPLE)
    found = resolve(pkg, "core-pkg")
    assert found is not None
    assert found.architecture_id == "core-pkg"


def test_resolve_returns_none_for_missing_id():
    pkg = load_package(SAMPLE)
    assert resolve(pkg, "does-not-exist") is None


def test_shared_paths_parsed_correctly():
    pkg = load_package(SAMPLE)
    assert len(pkg.shared_paths) == 1
    sp = pkg.shared_paths[0]
    assert isinstance(sp, SharedPath)
    assert sp.path == "src/shared/util.py"
    assert sp.owners == ["root-pkg", "core-pkg"]


def test_refs_parsed_correctly():
    pkg = load_package(SAMPLE)
    assert len(pkg.refs) == 1
    ref = pkg.refs[0]
    assert isinstance(ref, PackageRef)
    assert ref.architecture_id == "external-pkg"
    assert ref.at == "git+https://example.com/ext.git#abc123"


def test_defaults_applied(tmp_path):
    (tmp_path / "package.yaml").write_text(
        "architecture_id: minimal-pkg\nname: Minimal\nslug: minimal-pkg\n"
        "contract_version: '1.0.0'\nmodel_ref: .architecture-model.yaml\n"
        "manifest_ref: manifest.json\n"
    )
    pkg = load_package(tmp_path)
    assert pkg.children == []
    assert pkg.owned_paths == []
    assert pkg.shared_paths == []
    assert pkg.refs == []
    assert pkg.revisions_dir == "revisions"
    assert pkg.metadata.description is None
    assert pkg.metadata.tags == []


def test_json_schema_validates_sample_root():
    jsonschema = pytest.importorskip("jsonschema")
    schema_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "architecture_model"
        / "spec"
        / "package.schema.json"
    )
    schema = json.loads(schema_path.read_text())
    data = canonical_yaml_load((SAMPLE / "package.yaml").read_text())
    jsonschema.validate(data, schema)
