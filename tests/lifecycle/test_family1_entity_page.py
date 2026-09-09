"""Tests for family1.entity_page projector (Phase 3 Task 8).

Family 1 renders "mission/purpose" per entity: intent, goals,
stakeholders (both declared and reverse-looked-up from ``depends-on``
edges), success_criteria, ownership, maturity. Supported kinds are the
seven "core" entity kinds: component, capability, behavior, interface,
actor, constraint, layer.

Output shape (Phase 1 prose convention):

* ``DiagramSpec.id`` = ``"prose:family1.entity_page:<entity_id>"``
* ``DiagramSpec.title`` = ``"<name> (<entity_id>)"``
* ``DiagramSpec.facets["content_kind"]`` = ``"markdown"``
* ``DiagramSpec.facets["body"]`` is a Markdown string carrying only the
  sections that have content (deterministic section order).
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
    Family1EntityPage,
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
      project: fam1
    entities:
      components:
        - id: COMP-1
          name: PrimaryEngine
          status: ACTIVE
          intent: Drive the reactor cycle.
          goals:
            - Maintain 60Hz cadence
            - Recover from stalls
          stakeholders:
            - ControlTeam
          success_criteria:
            - "cycle_time_ms < 16"
          owner: alice
          maturity: stable
        - id: COMP-2
          name: Watchdog
          status: ACTIVE
        - id: COMP-3
          name: Consumer
          status: ACTIVE
      capabilities:
        - id: CAP-F1
          name: CycleControl
          status: ACTIVE
          source_block: F1
          intent: Own the operator cycle contract.
          goals:
            - Publish tick events
      constraints:
        - id: CON-1
          name: LatencyBudget
          status: ACTIVE
          intent: Cap p99 latency at 10ms.
      layers:
        - id: LAY-1
          name: Kernel
          status: ACTIVE
    relationships:
      - from: COMP-2
        to: COMP-1
        type: depends-on
      - from: COMP-3
        to: COMP-1
        type: depends-on
    """
)

PKG_YAML = dedent(
    """\
    architecture_id: fam1-pkg
    name: Fam1
    slug: fam1-pkg
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
    registry.register("family1.entity_page", Family1EntityPage(), version="1.0.0")
    slice_ = ModelSlice(
        id="s-f1",
        architecture_id="fam1-pkg",
        model_revision="rev-1",
        scope=f"entity({entity_id})",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=[entity_id]),
        parameters={"hops": 3},
    )
    view = ViewSpec(
        id="v-f1",
        slice_ref=SliceRef(slice_id="s-f1", model_revision="rev-1"),
        projector="family1.entity_page",
        output_content_kind="prose",
        depth=0,
    )
    mat = materialize(slice_, pkg, view_spec=view)
    return project(view, mat, registry=registry).diagram_spec


def test_component_page_shape_and_id(pkg):
    spec = _project_entity(pkg, "COMP-1")
    assert spec.id == "prose:family1.entity_page:COMP-1"
    assert spec.title == "PrimaryEngine (COMP-1)"
    assert spec.facets.get("content_kind") == "markdown"
    assert isinstance(spec.facets.get("body"), str)


def test_component_page_includes_all_populated_sections(pkg):
    body = _project_entity(pkg, "COMP-1").facets["body"]
    assert "## Intent" in body
    assert "Drive the reactor cycle." in body
    assert "## Goals" in body
    assert "- Maintain 60Hz cadence" in body
    assert "- Recover from stalls" in body
    assert "## Stakeholders" in body
    assert "- ControlTeam" in body
    assert "## Success Criteria" in body
    assert "cycle_time_ms < 16" in body
    assert "## Ownership" in body
    assert "alice" in body
    assert "## Maturity" in body
    assert "stable" in body


def test_stakeholders_include_reverse_depends_on(pkg):
    """Anyone who depends-on this component surfaces under Stakeholders."""
    body = _project_entity(pkg, "COMP-1").facets["body"]
    # Both declared (ControlTeam) and reverse-lookup (COMP-2, COMP-3)
    assert "- ControlTeam" in body
    assert "- COMP-2" in body
    assert "- COMP-3" in body


def test_empty_component_page_omits_all_sections(pkg):
    """No semantic fields, no depends-on inbound => no ## sections."""
    body = _project_entity(pkg, "COMP-2").facets["body"]
    # COMP-2 has zero populated fields and no inbound depends-on.
    assert "## Intent" not in body
    assert "## Goals" not in body
    assert "## Stakeholders" not in body
    assert "## Success Criteria" not in body
    assert "## Ownership" not in body
    assert "## Maturity" not in body


def test_capability_page_dispatches(pkg):
    spec = _project_entity(pkg, "CAP-F1")
    assert spec.id == "prose:family1.entity_page:CAP-F1"
    body = spec.facets["body"]
    assert "## Intent" in body
    assert "Own the operator cycle contract." in body
    assert "- Publish tick events" in body


def test_constraint_page_dispatches(pkg):
    spec = _project_entity(pkg, "CON-1")
    assert spec.id == "prose:family1.entity_page:CON-1"
    assert "Cap p99 latency at 10ms." in spec.facets["body"]


def test_layer_kind_supported(pkg):
    """Layer is one of the seven supported kinds, even without semantic
    fields it must return a DiagramSpec (not raise NotImplementedError)."""
    spec = _project_entity(pkg, "LAY-1")
    assert spec.title.startswith("Kernel")


def test_section_ordering_is_deterministic(pkg):
    """When multiple sections are present they appear in canonical order:
    Intent, Goals, Stakeholders, Success Criteria, Ownership, Maturity."""
    body = _project_entity(pkg, "COMP-1").facets["body"]
    order = ["## Intent", "## Goals", "## Stakeholders", "## Success Criteria", "## Ownership", "## Maturity"]
    positions = [body.index(h) for h in order]
    assert positions == sorted(positions)
