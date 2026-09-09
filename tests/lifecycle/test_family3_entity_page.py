"""Tests for family3.entity_page projector (Phase 3 Task 10).

Family 3 renders structural context per entity. Supported kinds:

* **component**: internal parts (contains descendants), depends-on graph
  (outbound + inbound), exposed interfaces, consumed interfaces,
  ``dependencies_rationale`` from schema 2.1.
* **layer**: same structure minus interfaces / rationale.

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
    Family3EntityPage,
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
      project: fam3
    entities:
      layers:
        - id: LAY-1
          name: Kernel
          status: ACTIVE
        - id: LAY-2
          name: Empty
          status: ACTIVE
      components:
        - id: COMP-1
          name: Engine
          status: ACTIVE
          dependencies_rationale:
            COMP-2: "Needs telemetry timestamps"
        - id: COMP-1.A
          name: EngineParts
          status: ACTIVE
        - id: COMP-2
          name: Telemetry
          status: ACTIVE
        - id: COMP-3
          name: Watchdog
          status: ACTIVE
      interfaces:
        - id: IF-1
          name: TickAPI
          status: ACTIVE
        - id: IF-2
          name: LogsAPI
          status: ACTIVE
    relationships:
      - from: COMP-1
        to: COMP-1.A
        type: contains
      - from: COMP-1
        to: COMP-2
        type: depends-on
      - from: COMP-3
        to: COMP-1
        type: depends-on
      - from: COMP-1
        to: IF-1
        type: exposes
      - from: COMP-1
        to: IF-2
        type: consumes
    """
)

PKG_YAML = dedent(
    """\
    architecture_id: fam3-pkg
    name: Fam3
    slug: fam3-pkg
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
    registry.register("family3.entity_page", Family3EntityPage(), version="1.0.0")
    slice_ = ModelSlice(
        id="s-f3",
        architecture_id="fam3-pkg",
        model_revision="rev-1",
        scope=f"entity({entity_id})",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=[entity_id]),
        parameters={"hops": 3},
    )
    view = ViewSpec(
        id="v-f3",
        slice_ref=SliceRef(slice_id="s-f3", model_revision="rev-1"),
        projector="family3.entity_page",
        output_content_kind="prose",
        depth=0,
    )
    mat = materialize(slice_, pkg, view_spec=view)
    return project(view, mat, registry=registry).diagram_spec


def test_component_shape(pkg):
    spec = _project_entity(pkg, "COMP-1")
    assert spec.id == "prose:family3.entity_page:COMP-1"
    assert spec.title == "Engine (COMP-1)"
    assert spec.facets["content_kind"] == "markdown"


def test_component_lists_all_structural_sections(pkg):
    body = _project_entity(pkg, "COMP-1").facets["body"]
    assert "## Internal Parts" in body and "- COMP-1.A" in body
    assert "## Depends On" in body and "- COMP-2" in body
    assert "## Depended On By" in body and "- COMP-3" in body
    assert "## Exposed Interfaces" in body and "- IF-1" in body
    assert "## Consumed Interfaces" in body and "- IF-2" in body
    assert "## Dependencies Rationale" in body
    assert "Needs telemetry timestamps" in body


def test_layer_kind_supported(pkg):
    spec = _project_entity(pkg, "LAY-1")
    assert spec.title == "Kernel (LAY-1)"


def test_empty_component_omits_sections(pkg):
    body = _project_entity(pkg, "COMP-2").facets["body"]
    # COMP-2 has NO contains descendants, NO outbound depends-on, but IS
    # depended-on by COMP-1 => "Depended On By" appears.
    assert "## Internal Parts" not in body
    assert "## Depends On\n" not in body
    assert "## Depended On By" in body and "- COMP-1" in body


def test_unsupported_kind_raises(pkg):
    registry = ProjectorRegistry()
    registry.register("family3.entity_page", Family3EntityPage(), version="1.0.0")
    slice_ = ModelSlice(
        id="s-bad",
        architecture_id="fam3-pkg",
        model_revision="rev-1",
        scope="entity(IF-1)",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=["IF-1"]),
    )
    view = ViewSpec(
        id="v-bad",
        slice_ref=SliceRef(slice_id="s-bad", model_revision="rev-1"),
        projector="family3.entity_page",
        output_content_kind="prose",
    )
    mat = materialize(slice_, pkg)
    with pytest.raises(NotImplementedError, match="family3.entity_page"):
        project(view, mat, registry=registry)
