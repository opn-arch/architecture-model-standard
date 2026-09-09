"""Tests for family6.entity_page projector (Phase 3 Task 12).

Family 6 renders interface / ICD context per entity. Supported kinds:

* **interface** (primary): type, protocol, provider, consumer, data
  format, schema, contract, endpoints.
* **component**: exposed and consumed interfaces (delegates to the
  outbound ``exposes`` / ``consumes`` indices).

Rendered as a Markdown ``DiagramSpec`` per Phase-1 prose convention.
Signatures / routes drawn from ``manifest_fragment`` are a future
extension; this task ships the model-only fields.
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
    Family6EntityPage,
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
      project: fam6
    entities:
      interfaces:
        - id: IF-1
          name: TickAPI
          status: ACTIVE
          type: rest
          protocol: HTTP/1.1
          provider: engine
          consumer: reporter
          data_format: json
          schema: "openapi:/schemas/tick.yaml"
          contract: "ICD-001"
        - id: IF-2
          name: BareBones
          status: ACTIVE
      components:
        - id: COMP-1
          name: Engine
          status: ACTIVE
        - id: COMP-2
          name: Isolated
          status: ACTIVE
    relationships:
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
    architecture_id: fam6-pkg
    name: Fam6
    slug: fam6-pkg
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
    registry.register("family6.entity_page", Family6EntityPage(), version="1.0.0")
    slice_ = ModelSlice(
        id="s-f6",
        architecture_id="fam6-pkg",
        model_revision="rev-1",
        scope=f"entity({entity_id})",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=[entity_id]),
        parameters={"hops": 3},
    )
    view = ViewSpec(
        id="v-f6",
        slice_ref=SliceRef(slice_id="s-f6", model_revision="rev-1"),
        projector="family6.entity_page",
        output_content_kind="prose",
        depth=0,
    )
    mat = materialize(slice_, pkg, view_spec=view)
    return project(view, mat, registry=registry).diagram_spec


def test_interface_shape(pkg):
    spec = _project_entity(pkg, "IF-1")
    assert spec.id == "prose:family6.entity_page:IF-1"
    assert spec.title == "TickAPI (IF-1)"
    assert spec.facets["content_kind"] == "markdown"


def test_interface_shows_all_populated_icd_fields(pkg):
    body = _project_entity(pkg, "IF-1").facets["body"]
    assert "## Type" in body and "rest" in body
    assert "## Protocol" in body and "HTTP/1.1" in body
    assert "## Provider" in body and "engine" in body
    assert "## Consumer" in body and "reporter" in body
    assert "## Data Format" in body and "json" in body
    assert "## Schema" in body and "openapi:/schemas/tick.yaml" in body
    assert "## Contract" in body and "ICD-001" in body


def test_bare_interface_omits_optional_fields(pkg):
    body = _project_entity(pkg, "IF-2").facets["body"]
    # Only "type" has a default enum value; protocol/provider/consumer/etc.
    # default to empty string and MUST NOT emit sections.
    assert "## Protocol" not in body
    assert "## Provider" not in body
    assert "## Consumer" not in body
    assert "## Schema" not in body
    assert "## Contract" not in body


def test_component_shows_exposed_and_consumed(pkg):
    body = _project_entity(pkg, "COMP-1").facets["body"]
    assert "## Exposed Interfaces" in body and "- IF-1" in body
    assert "## Consumed Interfaces" in body and "- IF-2" in body


def test_isolated_component_omits_sections(pkg):
    body = _project_entity(pkg, "COMP-2").facets["body"]
    assert "## Exposed Interfaces" not in body
    assert "## Consumed Interfaces" not in body


def test_unsupported_kind_raises(pkg):
    registry = ProjectorRegistry()
    registry.register("family6.entity_page", Family6EntityPage(), version="1.0.0")
    slice_ = ModelSlice(
        id="s-bad",
        architecture_id="fam6-pkg",
        model_revision="rev-1",
        scope="entity(COMP-1)",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=["COMP-1"]),
    )
    view = ViewSpec(
        id="v-bad",
        slice_ref=SliceRef(slice_id="s-bad", model_revision="rev-1"),
        projector="family6.entity_page",
        output_content_kind="prose",
    )
    mat = materialize(slice_, pkg)
    # Force an unsupported kind.
    mat.provenance["scope_metadata"]["scope_entity_kind"] = "actor"
    with pytest.raises(NotImplementedError, match="family6.entity_page"):
        project(view, mat, registry=registry)
