"""Tests for entity-scoped materialization (Phase 3 Task 3).

The root model wired below contains ``COMP-A``, ``COMP-B``, ``COMP-C`` with
``COMP-A -realizes-> CAP-1`` and ``COMP-A -depends-on-> COMP-B
-depends-on-> COMP-C``. When ``slice.scope == "entity(COMP-A)"`` the
materializer must delegate to :func:`slice_by_entity` under the hood and
then continue with the normal closure / curation / provenance pipeline.
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


ROOT_MODEL = dedent(
    """\
    meta:
      schema_version: '2.1.0'
      project: root
    entities:
      capabilities:
        - id: CAP-1
          name: Cap One
          status: ACTIVE
          source_block: F1
        - id: CAP-2
          name: Cap Two
          status: ACTIVE
          source_block: F2
      components:
        - id: COMP-A
          name: Alpha
          status: ACTIVE
          layer: core
          source_block: F1
        - id: COMP-B
          name: Bravo
          status: ACTIVE
          layer: core
          source_block: F1
        - id: COMP-C
          name: Charlie
          status: ACTIVE
          layer: core
          source_block: F1
        - id: COMP-UNRELATED
          name: Unrelated
          status: ACTIVE
          layer: web
          source_block: F2
    relationships:
      - from: COMP-A
        to: CAP-1
        type: realizes
      - from: COMP-A
        to: COMP-B
        type: depends-on
      - from: COMP-B
        to: COMP-C
        type: depends-on
    """
)

ROOT_PKG_YAML = dedent(
    """\
    architecture_id: root-pkg
    name: Root
    slug: root-pkg
    contract_version: "1.0.0"
    model_ref: .architecture-model.yaml
    manifest_ref: manifest.json
    """
)


@pytest.fixture
def pkg(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "package.yaml").write_text(ROOT_PKG_YAML)
    (root / ".architecture-model.yaml").write_text(ROOT_MODEL)
    (root / "manifest.json").write_text("{}")
    return load_package(root)


def _entity_slice(entity_id: str, *, hops: int = 1, **overrides) -> ModelSlice:
    kwargs = dict(
        id="entity-slice",
        architecture_id="root-pkg",
        model_revision="rev-1",
        scope=f"entity({entity_id})",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=[entity_id]),
        curation=Curation(),
        parameters={"hops": hops},
    )
    kwargs.update(overrides)
    return ModelSlice(**kwargs)


def _ids(entities) -> set[str]:
    out: set[str] = set()
    for f in (
        "actors",
        "capabilities",
        "behaviors",
        "interfaces",
        "constraints",
        "layers",
        "components",
        "systems",
        "data",
        "events",
        "requirements",
        "external_systems",
    ):
        for e in getattr(entities, f, []):
            out.add(e.id)
    return out


def test_entity_scope_materializes_via_slice_by_entity(pkg):
    """``scope='entity(COMP-A)'`` with hops=1 should include COMP-A,
    COMP-B (via depends-on), and CAP-1 (via realizes)."""
    mat = materialize(_entity_slice("COMP-A", hops=1), pkg)
    ids = _ids(mat.model_fragment.entities)
    assert "COMP-A" in ids
    assert "COMP-B" in ids  # 1 hop via depends-on
    assert "CAP-1" in ids  # 1 hop via realizes
    assert "COMP-UNRELATED" not in ids
    assert "CAP-2" not in ids


def test_entity_scope_respects_hops_parameter(pkg):
    """hops=2 should reach COMP-C through the depends-on chain."""
    mat = materialize(_entity_slice("COMP-A", hops=2), pkg)
    ids = _ids(mat.model_fragment.entities)
    assert {"COMP-A", "COMP-B", "COMP-C", "CAP-1"} <= ids
    assert "COMP-UNRELATED" not in ids


def test_entity_scope_default_hops_is_one(pkg):
    """When parameters['hops'] is absent, materializer defaults to 1."""
    s = ModelSlice(
        id="default-hops",
        architecture_id="root-pkg",
        model_revision="rev-1",
        scope="entity(COMP-A)",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=["COMP-A"]),
    )
    mat = materialize(s, pkg)
    ids = _ids(mat.model_fragment.entities)
    assert "COMP-B" in ids
    assert "COMP-C" not in ids  # 2 hops away — excluded at default


def test_entity_scope_provenance_records_scope(pkg):
    mat = materialize(_entity_slice("COMP-A"), pkg)
    assert mat.provenance["scope"] == "entity(COMP-A)"


def test_entity_scope_strict_closure_keeps_only_internal_relationships(pkg):
    """Relationships kept must have both endpoints inside the fragment."""
    mat = materialize(_entity_slice("COMP-A", hops=1), pkg)
    ids = _ids(mat.model_fragment.entities)
    for r in mat.model_fragment.relationships:
        assert r.from_id in ids and r.to_id in ids


def test_entity_scope_missing_entity_raises(pkg):
    s = _entity_slice("COMP-DOES-NOT-EXIST")
    with pytest.raises(KeyError):
        materialize(s, pkg)
