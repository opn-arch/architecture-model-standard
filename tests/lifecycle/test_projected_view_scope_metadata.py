"""Tests for ProjectedView scope metadata (Phase 3 Task 4).

Adds four optional fields — ``scope_chain``, ``parent``, ``peers``,
``roll_up`` — computed for entity-scoped views. Non-entity scopes leave
them at their zero-value defaults.

The plan pseudocode calls ``project(materialize(slice_(...)), ViewSpec(...))``
directly against an in-memory model; the real API materializes against an
:class:`ArchitecturePackage`. Tests use a small on-disk pkg with a
containment chain ``COMP-1 -> COMP-1.2 -> COMP-1.2.3`` plus a peer
``COMP-1.2.4``.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from architecture_model.lifecycle.view_spec import SliceRef, ViewSpec
from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.lifecycle.model_slice import ModelSlice, Selectors
from architecture_model.lifecycle.model_slice_materializer import materialize
from architecture_model.lifecycle.package import load_package
from architecture_model.lifecycle.view_projection import (
    ProjectedView,
    ProjectorRegistry,
    project,
)


ROOT_MODEL = dedent(
    """\
    meta:
      schema_version: '2.1.0'
      project: hier
    entities:
      components:
        - id: COMP-1
          name: One
          status: ACTIVE
        - id: COMP-1.2
          name: OneTwo
          status: ACTIVE
        - id: COMP-1.2.3
          name: OneTwoThree
          status: ACTIVE
        - id: COMP-1.2.4
          name: OneTwoFour
          status: ACTIVE
        - id: COMP-2
          name: Two
          status: ACTIVE
    relationships:
      - from: COMP-1
        to: COMP-1.2
        type: contains
      - from: COMP-1.2
        to: COMP-1.2.3
        type: contains
      - from: COMP-1.2
        to: COMP-1.2.4
        type: contains
    """
)

PKG_YAML = dedent(
    """\
    architecture_id: hier-pkg
    name: Hierarchy
    slug: hier-pkg
    contract_version: "1.0.0"
    model_ref: .architecture-model.yaml
    manifest_ref: manifest.json
    """
)


@pytest.fixture
def pkg(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "package.yaml").write_text(PKG_YAML)
    (root / ".architecture-model.yaml").write_text(ROOT_MODEL)
    (root / "manifest.json").write_text("{}")
    return load_package(root)


def _echo_projector(fragment, config):
    return DiagramSpec(
        id="diagram:echo",
        title="echo",
        facets={"content_kind": "prose", "body": "ok"},
    )


@pytest.fixture
def registry():
    r = ProjectorRegistry()
    r.register("echo", _echo_projector)
    return r


def _view(slice_id: str, model_revision: str) -> ViewSpec:
    return ViewSpec(
        id="v-echo",
        slice_ref=SliceRef(slice_id=slice_id, model_revision=model_revision),
        projector="echo",
        output_content_kind="prose",
    )


def _entity_slice(entity_id: str) -> ModelSlice:
    return ModelSlice(
        id=f"slice-{entity_id.lower()}",
        architecture_id="hier-pkg",
        model_revision="rev-1",
        scope=f"entity({entity_id})",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=[entity_id]),
    )


def _local_slice() -> ModelSlice:
    return ModelSlice(
        id="slice-local",
        architecture_id="hier-pkg",
        model_revision="rev-1",
        scope="local",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_kinds=["components"]),
    )


def test_entity_scoped_view_has_scope_chain(pkg, registry):
    mat = materialize(_entity_slice("COMP-1.2.3"), pkg)
    view = project(_view(mat.slice_id, mat.model_revision), mat, registry=registry)
    assert view.scope_chain == ("ROOT", "COMP-1", "COMP-1.2", "COMP-1.2.3")
    assert view.parent == "COMP-1.2"
    assert "COMP-1.2.4" in view.peers
    assert "COMP-1.2.3" not in view.peers  # self is not a peer
    assert view.roll_up is False


def test_entity_scoped_view_root_has_no_parent(pkg, registry):
    """A top-level entity (no incoming ``contains``) has parent=None
    and scope_chain=('ROOT', <id>)."""
    mat = materialize(_entity_slice("COMP-1"), pkg)
    view = project(_view(mat.slice_id, mat.model_revision), mat, registry=registry)
    assert view.scope_chain == ("ROOT", "COMP-1")
    assert view.parent is None
    assert view.peers == ()


def test_root_scoped_view_has_empty_scope_chain(pkg, registry):
    mat = materialize(_local_slice(), pkg)
    view = project(_view(mat.slice_id, mat.model_revision), mat, registry=registry)
    assert view.scope_chain == ()
    assert view.parent is None
    assert view.peers == ()
    assert view.roll_up is False


def test_projected_view_defaults_when_no_metadata():
    """The dataclass defaults are backward-compatible."""
    v = ProjectedView(
        view_id="v",
        slice_id="s",
        model_revision="rev-1",
        diagram_spec=DiagramSpec(
            id="diagram:x",
            title="x",
            facets={"content_kind": "prose", "body": ""},
        ),
        provenance={},
    )
    assert v.scope_chain == ()
    assert v.parent is None
    assert v.peers == ()
    assert v.roll_up is False


def test_entity_scope_peers_deterministic_order(pkg, registry):
    """Peers are returned in ascending id order for determinism."""
    mat = materialize(_entity_slice("COMP-1.2.3"), pkg)
    view = project(_view(mat.slice_id, mat.model_revision), mat, registry=registry)
    assert list(view.peers) == sorted(view.peers)
