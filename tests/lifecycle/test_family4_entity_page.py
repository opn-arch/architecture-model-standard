"""Tests for family4.entity_page projector (Phase 3 Task 11).

Family 4 renders scenario / interaction context per entity. Supported
kinds:

* **behavior**: triggering behaviors (inbound triggers), triggered
  behaviors (outbound triggers), participating actors (inbound consumes
  from actor entities).
* **actor**: behaviors / interfaces this actor consumes (outbound
  consumes).

Rendered as a Markdown ``DiagramSpec`` per Phase-1 prose convention.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.lifecycle.model_slice import ModelSlice, Selectors
from architecture_model.lifecycle.model_slice_materializer import materialize
from architecture_model.lifecycle.package import load_package
from architecture_model.lifecycle.projectors.entity_pages import (
    Family4EntityPage,
)
from architecture_model.lifecycle.view_projection import (
    ProjectorRegistry,
    project,
)
from architecture_model.lifecycle.view_spec import SliceRef, ViewSpec


MODEL = dedent(
    """\
    meta:
      schema_version: '2.1.0'
      project: fam4
    entities:
      actors:
        - id: ACT-1
          name: Operator
          status: ACTIVE
        - id: ACT-2
          name: Silent
          status: ACTIVE
      behaviors:
        - id: BEH-1
          name: StartCycle
          status: ACTIVE
        - id: BEH-2
          name: CompleteCycle
          status: ACTIVE
        - id: BEH-3
          name: Reset
          status: ACTIVE
      interfaces:
        - id: IF-1
          name: CommandAPI
          status: ACTIVE
    relationships:
      - from: BEH-1
        to: BEH-2
        type: triggers
      - from: BEH-3
        to: BEH-1
        type: triggers
      - from: ACT-1
        to: BEH-1
        type: consumes
      - from: ACT-1
        to: IF-1
        type: consumes
    """
)

PKG_YAML = dedent(
    """\
    architecture_id: fam4-pkg
    name: Fam4
    slug: fam4-pkg
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


def _project_entity(pkg, entity_id: str) -> DiagramSpec:
    registry = ProjectorRegistry()
    registry.register("family4.entity_page", Family4EntityPage(), version="1.0.0")
    slice_ = ModelSlice(
        id="s-f4",
        architecture_id="fam4-pkg",
        model_revision="rev-1",
        scope=f"entity({entity_id})",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=[entity_id]),
        parameters={"hops": 3},
    )
    view = ViewSpec(
        id="v-f4",
        slice_ref=SliceRef(slice_id="s-f4", model_revision="rev-1"),
        projector="family4.entity_page",
        output_content_kind="prose",
        depth=0,
    )
    mat = materialize(slice_, pkg, view_spec=view)
    return project(view, mat, registry=registry).diagram_spec


def test_behavior_shape(pkg):
    spec = _project_entity(pkg, "BEH-1")
    assert spec.id == "prose:family4.entity_page:BEH-1"
    assert spec.title == "StartCycle (BEH-1)"
    assert spec.facets["content_kind"] == "markdown"


def test_behavior_shows_triggered_by_and_triggers(pkg):
    body = _project_entity(pkg, "BEH-1").facets["body"]
    assert "## Triggered By" in body and "- BEH-3" in body
    assert "## Triggers" in body and "- BEH-2" in body


def test_behavior_shows_participating_actors(pkg):
    body = _project_entity(pkg, "BEH-1").facets["body"]
    assert "## Actors" in body and "- ACT-1" in body


def test_actor_shows_consumed_targets(pkg):
    body = _project_entity(pkg, "ACT-1").facets["body"]
    assert "## Consumes" in body
    assert "- BEH-1" in body
    assert "- IF-1" in body


def test_empty_behavior_omits_all_sections(pkg):
    """BEH-2 is only downstream of BEH-1 (inbound triggers) and has no
    actors / outbound triggers."""
    body = _project_entity(pkg, "BEH-2").facets["body"]
    assert "## Triggered By" in body  # BEH-1 triggers BEH-2
    assert "## Triggers" not in body  # no outbound triggers
    assert "## Actors" not in body  # no consumers


def test_empty_actor_omits_sections(pkg):
    body = _project_entity(pkg, "ACT-2").facets["body"]
    assert "## Consumes" not in body


def test_unsupported_kind_raises(pkg):
    registry = ProjectorRegistry()
    registry.register("family4.entity_page", Family4EntityPage(), version="1.0.0")
    slice_ = ModelSlice(
        id="s-bad",
        architecture_id="fam4-pkg",
        model_revision="rev-1",
        scope="entity(IF-1)",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=["IF-1"]),
    )
    view = ViewSpec(
        id="v-bad",
        slice_ref=SliceRef(slice_id="s-bad", model_revision="rev-1"),
        projector="family4.entity_page",
        output_content_kind="prose",
    )
    mat = materialize(slice_, pkg)
    with pytest.raises(NotImplementedError, match="family4.entity_page"):
        project(view, mat, registry=registry)
