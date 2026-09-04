"""Tests for the ModelSlice materializer (T14 commit 1: local/descendants)."""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from architecture_model.lifecycle.model_slice import (
    Curation,
    ModelSlice,
    Selectors,
)
from architecture_model.lifecycle.model_slice_materializer import (
    MATERIALIZER_VERSION,
    MaterializationWarning,
    MaterializedSlice,
    materialize,
)
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
          description: original description
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
          files:
            - src/core/alpha.py
          tags: [primary]
          description: alpha desc
        - id: COMP-B
          name: Bravo
          status: ACTIVE
          layer: web
          source_block: F2
          files:
            - src/web/bravo.py
          tags: [secondary]
        - id: COMP-C
          name: Charlie
          status: ACTIVE
          layer: core
          source_block: F1
          files:
            - src/core/charlie.py
      layers:
        - id: core
          name: Core Layer
          status: ACTIVE
        - id: web
          name: Web Layer
          status: ACTIVE
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

CHILD_MODEL = dedent(
    """\
    meta:
      schema_version: '2.1.0'
      project: child
    entities:
      components:
        - id: COMP-CHILD
          name: Child Comp
          status: ACTIVE
          layer: core
          source_block: F1
    relationships: []
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
    children:
      - children/child
    """
)

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


@pytest.fixture
def pkg(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "package.yaml").write_text(ROOT_PKG_YAML)
    (root / ".architecture-model.yaml").write_text(ROOT_MODEL)
    (root / "manifest.json").write_text("{}")
    child = root / "children" / "child"
    child.mkdir(parents=True)
    (child / "package.yaml").write_text(CHILD_PKG_YAML)
    (child / ".architecture-model.yaml").write_text(CHILD_MODEL)
    (child / "manifest.json").write_text("{}")
    return load_package(root)


def _make_slice(
    *,
    scope: str = "local",
    closure: str = "strict",
    shared_refs: str = "none",
    selectors: dict | None = None,
    curation: dict | None = None,
    parameters: dict | None = None,
    id: str = "s1",
) -> ModelSlice:
    sel = Selectors(**(selectors or {"entity_ids": ["COMP-A"]}))
    cur = Curation(**(curation or {}))
    return ModelSlice(
        id=id,
        architecture_id="root-pkg",
        model_revision="rev-1",
        scope=scope,
        closure=closure,
        shared_refs=shared_refs,
        selectors=sel,
        curation=cur,
        parameters=parameters or {},
    )


def _ids(entities) -> set[str]:
    out = set()
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
    ):
        for e in getattr(entities, f, []):
            out.add(e.id)
    return out


# --- Selectors -----------------------------------------------------------


def test_entity_ids_selector_local_strict(pkg):
    s = _make_slice(selectors={"entity_ids": ["COMP-A", "CAP-1"]})
    mat = materialize(s, pkg)
    assert _ids(mat.model_fragment.entities) == {"COMP-A", "CAP-1"}
    # only the rel with both endpoints inside
    rels = [(r.from_id, r.to_id, r.type.value) for r in mat.model_fragment.relationships]
    assert rels == [("COMP-A", "CAP-1", "realizes")]


def test_entity_kinds_components_only(pkg):
    s = _make_slice(selectors={"entity_kinds": ["components"]})
    mat = materialize(s, pkg)
    assert _ids(mat.model_fragment.entities) == {"COMP-A", "COMP-B", "COMP-C"}


def test_entity_kinds_singular_alias(pkg):
    s = _make_slice(selectors={"entity_kinds": ["component"]})
    mat = materialize(s, pkg)
    assert _ids(mat.model_fragment.entities) == {"COMP-A", "COMP-B", "COMP-C"}


def test_layers_selector(pkg):
    s = _make_slice(selectors={"layers": ["core"]})
    mat = materialize(s, pkg)
    # components whose layer=core, plus the Layer entity itself
    assert _ids(mat.model_fragment.entities) == {"COMP-A", "COMP-C", "core"}


def test_fblocks_selector(pkg):
    s = _make_slice(selectors={"fblocks": ["F1"]})
    mat = materialize(s, pkg)
    assert _ids(mat.model_fragment.entities) == {"COMP-A", "COMP-C", "CAP-1"}


def test_tags_selector(pkg):
    s = _make_slice(selectors={"tags": ["primary"]})
    mat = materialize(s, pkg)
    assert _ids(mat.model_fragment.entities) == {"COMP-A"}


def test_paths_selector_glob(pkg):
    s = _make_slice(selectors={"paths": ["src/core/*.py"]})
    mat = materialize(s, pkg)
    assert _ids(mat.model_fragment.entities) == {"COMP-A", "COMP-C"}


def test_selector_intersection(pkg):
    # kinds AND layers AND fblocks
    s = _make_slice(selectors={
        "entity_kinds": ["components"],
        "layers": ["core"],
        "fblocks": ["F1"],
    })
    mat = materialize(s, pkg)
    assert _ids(mat.model_fragment.entities) == {"COMP-A", "COMP-C"}


def test_selector_unmatched_emits_warning(pkg):
    s = _make_slice(selectors={"entity_ids": ["COMP-A", "MISSING-X"]})
    mat = materialize(s, pkg)
    codes = [w.code for w in mat.warnings]
    assert "SLICE.SELECTOR_UNMATCHED" in codes


# --- Closure -------------------------------------------------------------


def test_closure_strict_drops_dangling_and_warns(pkg):
    # Only COMP-A selected → both its outgoing rels are dangling
    s = _make_slice(selectors={"entity_ids": ["COMP-A"]}, closure="strict")
    mat = materialize(s, pkg)
    assert mat.model_fragment.relationships == []
    dangling = [w for w in mat.warnings if w.code == "SLICE.DANGLING_STRIPPED"]
    assert len(dangling) == 2  # A->CAP-1 and A->COMP-B


def test_closure_boundary_stubs_preserves_rels_and_stubs_targets(pkg):
    s = _make_slice(
        selectors={"entity_ids": ["COMP-A"]}, closure="boundary-stubs"
    )
    mat = materialize(s, pkg)
    ids = _ids(mat.model_fragment.entities)
    assert "COMP-A" in ids
    assert "CAP-1" in ids  # stub added
    assert "COMP-B" in ids  # stub added
    assert set(mat.stub_entity_ids) == {"CAP-1", "COMP-B"}
    # Confirm stub marker on one
    for c in mat.model_fragment.entities.components:
        if c.id == "COMP-B":
            assert c.extensions.get("stub") is True
            assert c.extensions.get("origin_ref") == "root-pkg"


def test_closure_transitive_depth1_expands_one_hop(pkg):
    s = _make_slice(
        selectors={"entity_ids": ["COMP-A"]},
        closure="transitive",
        parameters={"transitive_depth": 1},
    )
    mat = materialize(s, pkg)
    ids = _ids(mat.model_fragment.entities)
    # COMP-A neighbours: CAP-1 and COMP-B
    assert ids == {"COMP-A", "CAP-1", "COMP-B"}


def test_closure_transitive_depth_clamped_to_3(pkg):
    s = _make_slice(
        selectors={"entity_ids": ["COMP-A"]},
        closure="transitive",
        parameters={"transitive_depth": 10},
    )
    mat = materialize(s, pkg)
    ids = _ids(mat.model_fragment.entities)
    # Reaches everything reachable within 3 hops: A -> CAP-1, B ; B -> C
    assert {"COMP-A", "CAP-1", "COMP-B", "COMP-C"}.issubset(ids)


# --- Curation ------------------------------------------------------------


def test_curation_exclude(pkg):
    s = _make_slice(
        selectors={"entity_kinds": ["components"]},
        curation={"exclude": ["COMP-B"]},
    )
    mat = materialize(s, pkg)
    assert "COMP-B" not in _ids(mat.model_fragment.entities)


def test_curation_include_readds(pkg):
    s = _make_slice(
        selectors={"entity_ids": ["COMP-A"]},
        curation={"include": ["CAP-2"]},
    )
    mat = materialize(s, pkg)
    assert "CAP-2" in _ids(mat.model_fragment.entities)


def test_curation_redactions_clear_description(pkg):
    s = _make_slice(
        selectors={"entity_ids": ["COMP-A", "CAP-1"]},
        curation={"redactions": ["CAP-1"]},
    )
    mat = materialize(s, pkg)
    cap = next(c for c in mat.model_fragment.entities.capabilities if c.id == "CAP-1")
    assert cap.description == ""
    assert cap.id == "CAP-1"
    assert cap.name == "Cap One"
    # Not-redacted entity preserved.
    comp = next(c for c in mat.model_fragment.entities.components if c.id == "COMP-A")
    assert comp.description == "alpha desc"


# --- Scope ---------------------------------------------------------------


def test_scope_descendants_merges_child_entities(pkg):
    s = _make_slice(
        scope="descendants",
        selectors={"entity_kinds": ["components"]},
    )
    mat = materialize(s, pkg)
    assert "COMP-CHILD" in _ids(mat.model_fragment.entities)


def test_scope_federated_not_implemented(pkg):
    s = _make_slice(scope="federated", selectors={"entity_ids": ["COMP-A"]})
    with pytest.raises(NotImplementedError, match="federated"):
        materialize(s, pkg)


def test_shared_refs_explicit_not_implemented(pkg):
    s = _make_slice(shared_refs="explicit")
    with pytest.raises(NotImplementedError, match="shared_refs"):
        materialize(s, pkg)


def test_shared_refs_transitive_not_implemented(pkg):
    s = _make_slice(shared_refs="transitive")
    with pytest.raises(NotImplementedError, match="shared_refs"):
        materialize(s, pkg)


# --- Provenance / Idempotency -------------------------------------------


def test_provenance_keys(pkg):
    s = _make_slice(selectors={"entity_ids": ["COMP-A"]})
    mat = materialize(s, pkg)
    prov = mat.provenance
    for key in (
        "selectors_applied",
        "closure",
        "shared_refs",
        "scope",
        "source_model_digest",
        "produced_at",
        "materializer_version",
    ):
        assert key in prov
    assert prov["materializer_version"] == MATERIALIZER_VERSION
    assert prov["produced_at"].endswith("Z")
    assert prov["closure"] == "strict"


def test_idempotency(pkg):
    s = _make_slice(
        selectors={"entity_kinds": ["components"], "layers": ["core"]},
        curation={"exclude": ["COMP-B"]},
    )
    m1 = materialize(s, pkg)
    m2 = materialize(s, pkg)
    assert _ids(m1.model_fragment.entities) == _ids(m2.model_fragment.entities)
    assert [
        (r.from_id, r.to_id, r.type.value) for r in m1.model_fragment.relationships
    ] == [
        (r.from_id, r.to_id, r.type.value) for r in m2.model_fragment.relationships
    ]
    assert m1.stub_entity_ids == m2.stub_entity_ids
    assert m1.warnings == m2.warnings
    # Digest of source model is stable
    assert m1.provenance["source_model_digest"] == m2.provenance["source_model_digest"]
