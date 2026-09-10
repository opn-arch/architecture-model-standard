"""Federated slice materialization — Phase 4-C Task 17.

When ``slice.scope == "federated"``, the materializer walks the parent
:class:`ArchitecturePackage`'s ``children:`` refs, resolves each via
:func:`resolve_ref` (interpreted as ``file://<pkg.root>/<child_ref>``),
loads each child's model, and merges entities/relationships into the
fragment with ids namespaced by ``<child_arch_id>:`` to avoid collisions.

The resulting :class:`MaterializedSlice` exposes a
``federated_children`` tuple (sorted child architecture_ids) so callers
can enumerate what was merged.
"""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from architecture_model.lifecycle.model_slice import (
    Curation,
    ModelSlice,
    Selectors,
)
from architecture_model.lifecycle.model_slice_materializer import materialize
from architecture_model.lifecycle.package import load_package


PARENT_MODEL = dedent(
    """\
    meta:
      schema_version: '2.1.0'
      project: parent
    entities:
      layers:
        - id: core
          name: Core
          status: ACTIVE
      components:
        - id: COMP-PARENT
          name: Parent
          status: ACTIVE
          layer: core
    relationships: []
    """
)
PARENT_PKG = dedent(
    """\
    architecture_id: parent-pkg
    name: Parent
    slug: parent-pkg
    contract_version: "1.0.0"
    model_ref: .architecture-model.yaml
    manifest_ref: manifest.json
    children:
      - children/child-a
      - children/child-b
    """
)
CHILD_A_MODEL = dedent(
    """\
    meta:
      schema_version: '2.1.0'
      project: child-a
    entities:
      layers:
        - id: core
          name: Core
          status: ACTIVE
      components:
        - id: COMP-1
          name: Alpha
          status: ACTIVE
          layer: core
    relationships:
      - from: COMP-1
        to: COMP-1
        type: depends-on
    """
)
CHILD_A_PKG = dedent(
    """\
    architecture_id: child-a
    name: Child A
    slug: child-a
    contract_version: "1.0.0"
    model_ref: .architecture-model.yaml
    manifest_ref: manifest.json
    """
)
CHILD_B_MODEL = dedent(
    """\
    meta:
      schema_version: '2.1.0'
      project: child-b
    entities:
      layers:
        - id: core
          name: Core
          status: ACTIVE
      components:
        - id: COMP-1
          name: Beta
          status: ACTIVE
          layer: core
    relationships: []
    """
)
CHILD_B_PKG = dedent(
    """\
    architecture_id: child-b
    name: Child B
    slug: child-b
    contract_version: "1.0.0"
    model_ref: .architecture-model.yaml
    manifest_ref: manifest.json
    """
)


@pytest.fixture
def parent_pkg(tmp_path: Path):
    root = tmp_path / "parent"
    root.mkdir()
    (root / "package.yaml").write_text(PARENT_PKG)
    (root / ".architecture-model.yaml").write_text(PARENT_MODEL)
    (root / "manifest.json").write_text("{}")
    for child_slug, pkg_yaml, model_yaml in (
        ("child-a", CHILD_A_PKG, CHILD_A_MODEL),
        ("child-b", CHILD_B_PKG, CHILD_B_MODEL),
    ):
        c = root / "children" / child_slug
        c.mkdir(parents=True)
        (c / "package.yaml").write_text(pkg_yaml)
        (c / ".architecture-model.yaml").write_text(model_yaml)
        (c / "manifest.json").write_text("{}")
    return load_package(root)


def _federated_slice() -> ModelSlice:
    return ModelSlice(
        id="fed-slice-1",
        architecture_id="parent-pkg",
        model_revision="rev0",
        scope="federated",
        shared_refs="none",
        selectors=Selectors(entity_kinds=["component"], layers=["core"]),
        closure="strict",
        curation=Curation(),
    )


def test_federated_scope_merges_children(parent_pkg):
    mslice = materialize(_federated_slice(), parent_pkg)
    ids = {c.id for c in mslice.model_fragment.entities.components}
    # Parent id preserved; child ids namespaced by <arch_id>:
    assert "COMP-PARENT" in ids
    assert "child-a:COMP-1" in ids
    assert "child-b:COMP-1" in ids


def test_federated_children_field_populated(parent_pkg):
    mslice = materialize(_federated_slice(), parent_pkg)
    assert mslice.federated_children == ("child-a", "child-b")


def test_federated_relationships_namespaced(parent_pkg):
    mslice = materialize(_federated_slice(), parent_pkg)
    rels = mslice.model_fragment.relationships
    # child-a's self-loop should now be child-a:COMP-1 → child-a:COMP-1
    matches = [r for r in rels if r.from_id == "child-a:COMP-1" and r.to_id == "child-a:COMP-1"]
    assert len(matches) == 1


def test_federated_deterministic(parent_pkg):
    a = materialize(_federated_slice(), parent_pkg)
    b = materialize(_federated_slice(), parent_pkg)
    assert a.model_fragment.to_dict() == b.model_fragment.to_dict()
    assert a.federated_children == b.federated_children


def test_federated_no_children_returns_local_only(tmp_path):
    root = tmp_path / "lonely"
    root.mkdir()
    LONELY_PKG = dedent(
        """\
        architecture_id: lonely-pkg
        name: Lonely
        slug: lonely-pkg
        contract_version: "1.0.0"
        model_ref: .architecture-model.yaml
        manifest_ref: manifest.json
        """
    )
    (root / "package.yaml").write_text(LONELY_PKG)
    (root / ".architecture-model.yaml").write_text(PARENT_MODEL)
    (root / "manifest.json").write_text("{}")
    pkg = load_package(root)
    mslice = materialize(_federated_slice(), pkg)
    assert mslice.federated_children == ()
    assert {c.id for c in mslice.model_fragment.entities.components} == {"COMP-PARENT"}
