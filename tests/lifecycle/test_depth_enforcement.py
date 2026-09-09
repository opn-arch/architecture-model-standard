"""Tests for depth + expand_kinds enforcement (Phase 3 Task 6).

When ``ViewSpec.depth`` and ``ViewSpec.expand_kinds`` are set on an
entity-scoped materialization, the materializer prunes ``contains``
descendants of the scope root beyond ``depth`` and stops recursion into
kinds not listed in ``expand_kinds`` (empty tuple = all kinds recurse).

The plan pseudocode signature is ``materialize(slice, model,
view_spec=view_spec)``. The real signature is ``materialize(slice, pkg,
*, view_spec=None)``.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from architecture_model.lifecycle.model_slice import ModelSlice, Selectors
from architecture_model.lifecycle.model_slice_materializer import materialize
from architecture_model.lifecycle.package import load_package
from architecture_model.lifecycle.view_spec import SliceRef, ViewSpec


MODEL = dedent(
    """\
    meta:
      schema_version: '2.1.0'
      project: depth
    entities:
      components:
        - id: COMP-1
          name: One
          status: ACTIVE
        - id: COMP-1.1
          name: OneOne
          status: ACTIVE
        - id: COMP-1.1.1
          name: OneOneOne
          status: ACTIVE
      capabilities:
        - id: CAP-F1
          name: Fone
          status: ACTIVE
          source_block: F1
        - id: CAP-F1.SUB
          name: FoneSub
          status: ACTIVE
          source_block: F1
    relationships:
      - from: COMP-1
        to: COMP-1.1
        type: contains
      - from: COMP-1.1
        to: COMP-1.1.1
        type: contains
      - from: COMP-1
        to: CAP-F1
        type: contains
      - from: CAP-F1
        to: CAP-F1.SUB
        type: contains
    """
)

PKG_YAML = dedent(
    """\
    architecture_id: depth-pkg
    name: Depth
    slug: depth-pkg
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
    (root / ".architecture-model.yaml").write_text(MODEL)
    (root / "manifest.json").write_text("{}")
    return load_package(root)


def _slice() -> ModelSlice:
    return ModelSlice(
        id="s-depth",
        architecture_id="depth-pkg",
        model_revision="rev-1",
        scope="entity(COMP-1)",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=["COMP-1"]),
        # Push hops high so slice_by_entity brings in the whole subtree
        # before depth pruning trims it back.
        parameters={"hops": 5},
    )


def _view(*, depth: int = 1, expand_kinds: tuple[str, ...] = ()) -> ViewSpec:
    return ViewSpec(
        id="v-depth",
        slice_ref=SliceRef(slice_id="s-depth", model_revision="rev-1"),
        projector="family1.entity_page",
        output_content_kind="prose",
        depth=depth,
        expand_kinds=expand_kinds,
    )


def _ids(fragment) -> set[str]:
    out: set[str] = set()
    for f in ("components", "capabilities"):
        for e in getattr(fragment.entities, f, []):
            out.add(e.id)
    return out


def test_depth_zero_returns_only_scope_root(pkg):
    mat = materialize(_slice(), pkg, view_spec=_view(depth=0))
    assert _ids(mat.model_fragment) == {"COMP-1"}


def test_depth_one_includes_direct_children_only(pkg):
    mat = materialize(_slice(), pkg, view_spec=_view(depth=1))
    ids = _ids(mat.model_fragment)
    assert "COMP-1" in ids
    assert "COMP-1.1" in ids  # direct component child
    assert "CAP-F1" in ids  # direct capability child
    assert "COMP-1.1.1" not in ids  # grandchild pruned
    assert "CAP-F1.SUB" not in ids  # grandchild pruned


def test_depth_two_includes_grandchildren(pkg):
    mat = materialize(_slice(), pkg, view_spec=_view(depth=2))
    ids = _ids(mat.model_fragment)
    assert {"COMP-1", "COMP-1.1", "COMP-1.1.1", "CAP-F1", "CAP-F1.SUB"} <= ids


def test_expand_kinds_restricts_recursion(pkg):
    """With expand_kinds=('component',), CAP-F1 (direct child) still
    appears but CAP-F1.SUB (grandchild via a capability) is pruned —
    capabilities are not in expand_kinds so they do not recurse."""
    mat = materialize(_slice(), pkg, view_spec=_view(depth=3, expand_kinds=("component",)))
    ids = _ids(mat.model_fragment)
    assert "COMP-1" in ids
    assert "COMP-1.1" in ids  # direct component child
    assert "COMP-1.1.1" in ids  # grandchild via component -> allowed
    assert "CAP-F1" in ids  # direct capability child appears
    assert "CAP-F1.SUB" not in ids  # not recursed (capability not in expand_kinds)


def test_no_view_spec_preserves_pre_phase3_behavior(pkg):
    """Without a view_spec, materialize behaves as pre-Phase-3: whole
    entity subtree (via slice_by_entity + high hops)."""
    mat = materialize(_slice(), pkg)
    ids = _ids(mat.model_fragment)
    assert {"COMP-1", "COMP-1.1", "COMP-1.1.1", "CAP-F1", "CAP-F1.SUB"} <= ids


def test_depth_ignored_for_non_entity_scope(pkg):
    """A view_spec.depth is a no-op for scope='local' (recursion only
    makes sense in the entity-scoped case)."""
    local_slice = ModelSlice(
        id="s-local",
        architecture_id="depth-pkg",
        model_revision="rev-1",
        scope="local",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_kinds=["components", "capabilities"]),
    )
    mat = materialize(local_slice, pkg, view_spec=_view(depth=0))
    ids = _ids(mat.model_fragment)
    # Nothing pruned by depth — all five entities remain.
    assert len(ids) == 5
