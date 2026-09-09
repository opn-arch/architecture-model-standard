"""Tests for EntityPageProjector base class + kind dispatch (Phase 3 Task 7).

The base ``EntityPageProjector`` is a callable that implements the
``ProjectorFn`` contract ``(ArchitectureModel, dict) -> DiagramSpec``.
Instances dispatch on ``config["__scope_entity_kind"]`` to a
``_project_<kind>`` method the subclass provides. Unknown kinds raise
``NotImplementedError``.

Scope info (``__scope_entity_id`` and ``__scope_entity_kind``) is
injected into the projector config by
:func:`architecture_model.lifecycle.view_projection.project` from the
materialized slice's ``provenance['scope_metadata']`` for entity-scoped
slices. Tests cover both the direct dispatch mechanism and the
end-to-end wiring via ``project()``.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.core.parser import ArchitectureModel
from architecture_model.lifecycle.model_slice import ModelSlice, Selectors
from architecture_model.lifecycle.model_slice_materializer import materialize
from architecture_model.lifecycle.package import load_package
from architecture_model.lifecycle.projectors.entity_pages import EntityPageProjector
from architecture_model.lifecycle.view_projection import (
    ProjectorRegistry,
    project,
)
from architecture_model.lifecycle.view_spec import SliceRef, ViewSpec


MODEL = dedent(
    """\
    meta:
      schema_version: '2.1.0'
      project: dispatch
    entities:
      components:
        - id: COMP-1
          name: One
          status: ACTIVE
      capabilities:
        - id: CAP-F1
          name: Fone
          status: ACTIVE
          source_block: F1
      constraints:
        - id: CON-1
          name: NoLeaks
          status: ACTIVE
    """
)

PKG_YAML = dedent(
    """\
    architecture_id: dispatch-pkg
    name: Dispatch
    slug: dispatch-pkg
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


def _empty_model() -> ArchitectureModel:
    from architecture_model.core.parser import _parse_raw

    return _parse_raw(
        {
            "meta": {"schema_version": "2.1.0", "project": "t"},
            "entities": {"components": []},
            "relationships": [],
        }
    )


def test_dispatches_to_project_component_by_kind():
    """When config carries ``__scope_entity_kind='component'`` the base
    calls ``_project_component`` on the subclass."""

    class F3Test(EntityPageProjector):
        family = 3

        def _project_component(self, model, config):
            return DiagramSpec(id="c", title="component-rendered")

    result = F3Test()(_empty_model(), {"__scope_entity_kind": "component"})
    assert result.title == "component-rendered"


def test_raises_on_unsupported_kind():
    """Kinds without a matching ``_project_<kind>`` method raise
    NotImplementedError naming the family and kind."""

    class F3Test(EntityPageProjector):
        family = 3
        # no _project_constraint defined

    with pytest.raises(NotImplementedError, match="family3.entity_page.*constraint"):
        F3Test()(_empty_model(), {"__scope_entity_kind": "constraint"})


def test_raises_when_scope_kind_missing():
    """Missing ``__scope_entity_kind`` in config is a caller error and
    surfaces as NotImplementedError (empty kind name)."""

    class F1Test(EntityPageProjector):
        family = 1

    with pytest.raises(NotImplementedError, match="family1.entity_page"):
        F1Test()(_empty_model(), {})


def test_project_wires_scope_kind_from_materialized_slice(pkg):
    """End-to-end: ``project()`` reads scope_metadata from the mslice
    provenance and injects ``__scope_entity_id`` +
    ``__scope_entity_kind`` into the config the projector receives."""

    captured: dict[str, str] = {}

    class F1Wire(EntityPageProjector):
        family = 1

        def _project_component(self, model, config):
            captured["id"] = config.get("__scope_entity_id", "")
            captured["kind"] = config.get("__scope_entity_kind", "")
            return DiagramSpec(id="p", title="ok")

    registry = ProjectorRegistry()
    registry.register("family1.entity_page", F1Wire(), version="1.0.0")

    slice_ = ModelSlice(
        id="s1",
        architecture_id="dispatch-pkg",
        model_revision="rev-1",
        scope="entity(COMP-1)",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=["COMP-1"]),
    )
    view = ViewSpec(
        id="v1",
        slice_ref=SliceRef(slice_id="s1", model_revision="rev-1"),
        projector="family1.entity_page",
        output_content_kind="prose",
    )
    mat = materialize(slice_, pkg)
    project(view, mat, registry=registry)

    assert captured == {"id": "COMP-1", "kind": "component"}


def test_project_does_not_inject_for_non_entity_scope(pkg):
    """For scope='local' there is no scope_metadata; the projector must
    not receive ``__scope_entity_kind`` / ``__scope_entity_id``."""

    seen_keys: list[str] = []

    class LocalOK(EntityPageProjector):
        family = 1

        def __call__(self, model, config):
            # Bypass dispatch — record what config looks like.
            seen_keys.extend(sorted(config.keys()))
            return DiagramSpec(id="l", title="local")

    registry = ProjectorRegistry()
    registry.register("family1.local", LocalOK(), version="1.0.0")

    slice_ = ModelSlice(
        id="s2",
        architecture_id="dispatch-pkg",
        model_revision="rev-1",
        scope="local",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_kinds=["components"]),
    )
    view = ViewSpec(
        id="v2",
        slice_ref=SliceRef(slice_id="s2", model_revision="rev-1"),
        projector="family1.local",
        output_content_kind="prose",
    )
    mat = materialize(slice_, pkg)
    project(view, mat, registry=registry)

    assert "__scope_entity_id" not in seen_keys
    assert "__scope_entity_kind" not in seen_keys


def test_scope_entity_kind_stored_in_scope_metadata(pkg):
    """Materializer records ``scope_entity_kind`` (singular canonical)
    in provenance.scope_metadata alongside scope_chain / parent / peers."""

    slice_ = ModelSlice(
        id="s3",
        architecture_id="dispatch-pkg",
        model_revision="rev-1",
        scope="entity(CAP-F1)",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=["CAP-F1"]),
    )
    mat = materialize(slice_, pkg)
    scope_meta = mat.provenance.get("scope_metadata")
    assert scope_meta is not None
    assert scope_meta.get("scope_entity_id") == "CAP-F1"
    assert scope_meta.get("scope_entity_kind") == "capability"
