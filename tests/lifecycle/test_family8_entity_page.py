"""Tests for family8.entity_page projector (Phase 3 Task 14).

Family 8 renders health + evolution content per entity from
supplementary fragments (SI&L rollup, drift flags). Supported kinds:
component, capability, interface. Unsupported kinds raise
``NotImplementedError``. When no supplementary data is present the
projector emits a minimal DiagramSpec (empty body).
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
    Family8EntityPage,
)
from architecture_model.lifecycle.supplementary_loaders import (
    SILEvent,
    SILFragment,
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
      project: fam8
    entities:
      components:
        - id: COMP-1
          name: Engine
          status: ACTIVE
        - id: COMP-QUIET
          name: NoTelemetry
          status: ACTIVE
      capabilities:
        - id: CAP-F1
          name: Ignition
          status: ACTIVE
      interfaces:
        - id: IF-1
          name: TickAPI
          status: ACTIVE
    relationships: []
    """
)

PKG_YAML = dedent(
    """\
    architecture_id: fam8-pkg
    name: Fam8
    slug: fam8-pkg
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


def _sil_fragment() -> SILFragment:
    events = (
        SILEvent(
            component_id="COMP-1",
            ts="2026-09-08T10:00:00Z",
            kind="call",
            outcome="ok",
            duration_ms=42.0,
        ),
        SILEvent(
            component_id="COMP-1",
            ts="2026-09-08T10:00:01Z",
            kind="call",
            outcome="error",
            duration_ms=60.0,
        ),
    )
    summary = {
        "COMP-1": {
            "invocations": 2.0,
            "failures": 1.0,
            "avg_duration_ms": 51.0,
        }
    }
    return SILFragment(events=events, summary=summary)


def _project(pkg, entity_id: str, *, with_sil: bool = True) -> DiagramSpec:
    registry = ProjectorRegistry()
    registry.register("family8.entity_page", Family8EntityPage(), version="1.0.0")
    slice_ = ModelSlice(
        id="s-f8",
        architecture_id="fam8-pkg",
        model_revision="rev-1",
        scope=f"entity({entity_id})",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=[entity_id]),
        parameters={"hops": 3},
    )
    view = ViewSpec(
        id="v-f8",
        slice_ref=SliceRef(slice_id="s-f8", model_revision="rev-1"),
        projector="family8.entity_page",
        output_content_kind="prose",
        depth=0,
    )
    mat = materialize(slice_, pkg, view_spec=view)
    if with_sil:
        mat.supplementary_fragments["sil"] = _sil_fragment()
    return project(view, mat, registry=registry).diagram_spec


def test_component_shape(pkg):
    spec = _project(pkg, "COMP-1")
    assert spec.id == "prose:family8.entity_page:COMP-1"
    assert spec.title == "Engine (COMP-1)"
    assert spec.facets["content_kind"] == "markdown"


def test_component_sil_rollup(pkg):
    body = _project(pkg, "COMP-1").facets["body"]
    assert "## SI&L Rollup" in body
    assert "Invocations: 2" in body
    assert "Failures: 1" in body
    assert "Avg Duration" in body and "51" in body


def test_component_recent_events(pkg):
    body = _project(pkg, "COMP-1").facets["body"]
    assert "## Recent Events" in body
    assert "2026-09-08T10:00:00Z" in body
    assert "ok" in body and "error" in body


def test_component_without_sil_data(pkg):
    body = _project(pkg, "COMP-QUIET").facets["body"]
    # SI&L fragment present but no summary entry for this component.
    assert "## SI&L Rollup" not in body
    assert "## Recent Events" not in body


def test_component_no_fragment_at_all(pkg):
    body = _project(pkg, "COMP-1", with_sil=False).facets["body"]
    assert body == ""


def test_capability_supported(pkg):
    # Capability with no SI&L data — must not raise.
    spec = _project(pkg, "CAP-F1")
    assert spec.id == "prose:family8.entity_page:CAP-F1"
    assert spec.facets["body"] == ""


def test_interface_supported(pkg):
    spec = _project(pkg, "IF-1")
    assert spec.id == "prose:family8.entity_page:IF-1"


def test_unsupported_kind_raises(pkg):
    registry = ProjectorRegistry()
    registry.register("family8.entity_page", Family8EntityPage(), version="1.0.0")
    slice_ = ModelSlice(
        id="s-bad",
        architecture_id="fam8-pkg",
        model_revision="rev-1",
        scope="entity(COMP-1)",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=["COMP-1"]),
    )
    view = ViewSpec(
        id="v-bad",
        slice_ref=SliceRef(slice_id="s-bad", model_revision="rev-1"),
        projector="family8.entity_page",
        output_content_kind="prose",
    )
    mat = materialize(slice_, pkg)
    mat.provenance["scope_metadata"]["scope_entity_kind"] = "actor"
    with pytest.raises(NotImplementedError, match="family8.entity_page"):
        project(view, mat, registry=registry)
