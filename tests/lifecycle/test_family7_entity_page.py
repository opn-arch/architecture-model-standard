"""Tests for family7.entity_page projector (Phase 3 Task 13).

Family 7 renders quality + verification content per entity:
requirements, verification refs, failure_modes (FMEA), assumptions,
open_questions, SLOs. Supported kinds: component, capability, behavior,
interface, constraint. Unsupported kinds raise ``NotImplementedError``.

All output uses the Phase-1 prose ``DiagramSpec`` convention
(``id=prose:family7.entity_page:<entity_id>``,
``facets={"content_kind":"markdown","body":...}``).
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
    Family7EntityPage,
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
      project: fam7
    entities:
      components:
        - id: COMP-1
          name: Engine
          status: ACTIVE
          requirements:
            - REQ-1
            - REQ-2
          failure_modes:
            - overheat
            - stall
          assumptions:
            - "coolant available"
          open_questions:
            - "what MTBF?"
          verification:
            - VERIF-1
          slos:
            - metric: latency_p95
              target: "< 100ms"
              window: 5m
        - id: COMP-BARE
          name: Bare
          status: ACTIVE
      capabilities:
        - id: CAP-F1
          name: Ignition
          status: ACTIVE
          requirements: [REQ-3]
          failure_modes: [misfire]
          verification: [VERIF-2]
      behaviors:
        - id: BEH-1
          name: StartSequence
          status: ACTIVE
          requirements: [REQ-4]
          assumptions: ["battery charged"]
      interfaces:
        - id: IF-1
          name: TickAPI
          status: ACTIVE
          slos:
            - metric: latency_p99
              target: "< 500ms"
              window: 1h
          verification: [VERIF-3]
      constraints:
        - id: CON-1
          name: MaxTemp
          status: ACTIVE
          assumptions: ["ambient < 40C"]
          verification: [VERIF-4]
    relationships: []
    """
)

PKG_YAML = dedent(
    """\
    architecture_id: fam7-pkg
    name: Fam7
    slug: fam7-pkg
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
    registry.register("family7.entity_page", Family7EntityPage(), version="1.0.0")
    slice_ = ModelSlice(
        id="s-f7",
        architecture_id="fam7-pkg",
        model_revision="rev-1",
        scope=f"entity({entity_id})",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=[entity_id]),
        parameters={"hops": 3},
    )
    view = ViewSpec(
        id="v-f7",
        slice_ref=SliceRef(slice_id="s-f7", model_revision="rev-1"),
        projector="family7.entity_page",
        output_content_kind="prose",
        depth=0,
    )
    mat = materialize(slice_, pkg, view_spec=view)
    return project(view, mat, registry=registry).diagram_spec


def test_component_shape(pkg):
    spec = _project_entity(pkg, "COMP-1")
    assert spec.id == "prose:family7.entity_page:COMP-1"
    assert spec.title == "Engine (COMP-1)"
    assert spec.facets["content_kind"] == "markdown"


def test_component_full_render(pkg):
    body = _project_entity(pkg, "COMP-1").facets["body"]
    assert "## Requirements" in body and "- REQ-1" in body and "- REQ-2" in body
    assert "## Verification" in body and "- VERIF-1" in body
    assert "## Failure Modes" in body and "- overheat" in body and "- stall" in body
    assert "## Assumptions" in body and "- coolant available" in body
    assert "## Open Questions" in body and "- what MTBF?" in body
    assert "## SLOs" in body and "- latency_p95 < 100ms (5m)" in body


def test_bare_component_omits_all_sections(pkg):
    body = _project_entity(pkg, "COMP-BARE").facets["body"]
    assert body == ""


def test_capability_render(pkg):
    body = _project_entity(pkg, "CAP-F1").facets["body"]
    assert "## Requirements" in body and "- REQ-3" in body
    assert "## Verification" in body and "- VERIF-2" in body
    assert "## Failure Modes" in body and "- misfire" in body
    # Capability has no slos field.
    assert "## SLOs" not in body


def test_behavior_render(pkg):
    body = _project_entity(pkg, "BEH-1").facets["body"]
    assert "## Requirements" in body and "- REQ-4" in body
    assert "## Assumptions" in body and "- battery charged" in body
    assert "## SLOs" not in body


def test_interface_render(pkg):
    body = _project_entity(pkg, "IF-1").facets["body"]
    assert "## SLOs" in body and "- latency_p99 < 500ms (1h)" in body
    assert "## Verification" in body and "- VERIF-3" in body


def test_constraint_render(pkg):
    body = _project_entity(pkg, "CON-1").facets["body"]
    assert "## Assumptions" in body and "- ambient < 40C" in body
    assert "## Verification" in body and "- VERIF-4" in body


def test_unsupported_kind_raises(pkg):
    registry = ProjectorRegistry()
    registry.register("family7.entity_page", Family7EntityPage(), version="1.0.0")
    slice_ = ModelSlice(
        id="s-bad",
        architecture_id="fam7-pkg",
        model_revision="rev-1",
        scope="entity(COMP-1)",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=["COMP-1"]),
    )
    view = ViewSpec(
        id="v-bad",
        slice_ref=SliceRef(slice_id="s-bad", model_revision="rev-1"),
        projector="family7.entity_page",
        output_content_kind="prose",
    )
    mat = materialize(slice_, pkg)
    mat.provenance["scope_metadata"]["scope_entity_kind"] = "actor"
    with pytest.raises(NotImplementedError, match="family7.entity_page"):
        project(view, mat, registry=registry)
