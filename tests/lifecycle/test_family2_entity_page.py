"""Tests for family2.entity_page projector (Phase 3 Task 9).

Family 2 renders "functional decomposition" per entity. Supported kinds:

* **capability** (primary): sub-``contains`` tree, realizing components,
  outbound ``triggers`` (cross-block flow).
* **component**: which capabilities the component ``realizes``.
* **behavior**: the capability that ``contains`` this behavior.

Rendered as a Markdown ``DiagramSpec`` per the Phase-1 prose convention;
sections are emitted in canonical order and only when populated.
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
    Family2EntityPage,
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
      project: fam2
    entities:
      capabilities:
        - id: CAP-F1
          name: CycleControl
          status: ACTIVE
          source_block: F1
        - id: CAP-F1.SUB
          name: Ticker
          status: ACTIVE
          source_block: F1
        - id: CAP-F2
          name: Telemetry
          status: ACTIVE
          source_block: F2
        - id: CAP-F3
          name: Isolated
          status: ACTIVE
          source_block: F3
      components:
        - id: COMP-1
          name: Engine
          status: ACTIVE
        - id: COMP-2
          name: Reporter
          status: ACTIVE
      behaviors:
        - id: BEH-1
          name: StartCycle
          status: ACTIVE
    relationships:
      - from: CAP-F1
        to: CAP-F1.SUB
        type: contains
      - from: CAP-F1
        to: BEH-1
        type: contains
      - from: COMP-1
        to: CAP-F1
        type: realizes
      - from: COMP-2
        to: CAP-F2
        type: realizes
      - from: CAP-F1
        to: CAP-F2
        type: triggers
    """
)

PKG_YAML = dedent(
    """\
    architecture_id: fam2-pkg
    name: Fam2
    slug: fam2-pkg
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
    registry.register("family2.entity_page", Family2EntityPage(), version="1.0.0")
    slice_ = ModelSlice(
        id="s-f2",
        architecture_id="fam2-pkg",
        model_revision="rev-1",
        scope=f"entity({entity_id})",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=[entity_id]),
        parameters={"hops": 3},
    )
    view = ViewSpec(
        id="v-f2",
        slice_ref=SliceRef(slice_id="s-f2", model_revision="rev-1"),
        projector="family2.entity_page",
        output_content_kind="prose",
        depth=0,
    )
    mat = materialize(slice_, pkg, view_spec=view)
    return project(view, mat, registry=registry).diagram_spec


def test_capability_page_shape(pkg):
    spec = _project_entity(pkg, "CAP-F1")
    assert spec.id == "prose:family2.entity_page:CAP-F1"
    assert spec.title == "CycleControl (CAP-F1)"
    assert spec.facets.get("content_kind") == "markdown"


def test_capability_shows_contains_tree(pkg):
    """A capability page lists its transitive ``contains`` descendants."""
    body = _project_entity(pkg, "CAP-F1").facets["body"]
    assert "## Sub-Decomposition" in body
    assert "- CAP-F1.SUB" in body
    assert "- BEH-1" in body


def test_capability_shows_realizing_components(pkg):
    """A capability page lists components that ``realizes`` it (inbound)."""
    body = _project_entity(pkg, "CAP-F1").facets["body"]
    assert "## Realizing Components" in body
    assert "- COMP-1" in body


def test_capability_shows_outbound_triggers(pkg):
    """A capability page lists other entities it ``triggers`` (outbound)."""
    body = _project_entity(pkg, "CAP-F1").facets["body"]
    assert "## Triggers" in body
    assert "- CAP-F2" in body


def test_component_shows_realized_capabilities(pkg):
    """A component page lists capabilities it ``realizes`` (outbound)."""
    body = _project_entity(pkg, "COMP-1").facets["body"]
    assert "## Realizes" in body
    assert "- CAP-F1" in body


def test_behavior_shows_containing_capability(pkg):
    """A behavior page names the capability that ``contains`` it (inbound
    contains)."""
    body = _project_entity(pkg, "BEH-1").facets["body"]
    assert "## Belongs To" in body
    assert "CAP-F1" in body


def test_unsupported_kind_raises(pkg):
    """Kinds outside {capability, component, behavior} are not supported
    by family2 and must raise NotImplementedError."""
    registry = ProjectorRegistry()
    registry.register("family2.entity_page", Family2EntityPage(), version="1.0.0")
    slice_ = ModelSlice(
        id="s-bad",
        architecture_id="fam2-pkg",
        model_revision="rev-1",
        scope="entity(CAP-F1)",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=["CAP-F1"]),
    )
    view = ViewSpec(
        id="v-bad",
        slice_ref=SliceRef(slice_id="s-bad", model_revision="rev-1"),
        projector="family2.entity_page",
        output_content_kind="prose",
    )
    mat = materialize(slice_, pkg)
    # Force a fake kind by overriding provenance.
    mat.provenance["scope_metadata"]["scope_entity_kind"] = "interface"
    with pytest.raises(NotImplementedError, match="family2.entity_page"):
        project(view, mat, registry=registry)


def test_empty_sections_are_omitted(pkg):
    """A capability with no descendants / no realizers / no triggers
    emits a header-only body."""
    body = _project_entity(pkg, "CAP-F3").facets["body"]
    assert "## Sub-Decomposition" not in body
    assert "## Realizing Components" not in body
    assert "## Triggers" not in body
