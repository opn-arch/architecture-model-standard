"""Tests for family5.entity_page projector (Phase 5, deferred Phase 3 task).

Family 5 renders deployment topology per entity. Supported kinds:

* **environment**: kind, region, infrastructure list, constraints list,
  Deployed Components (inbound allocated-to).
* **resource**: kind, provider, location, SLA, Consumed By (inbound
  consumes / depends-on).
* **component**: Deployed To (outbound allocated-to environments).

Rendered as a Markdown ``DiagramSpec`` per Phase-1 prose convention.
Empty sections are omitted; unsupported kinds raise
``NotImplementedError``.
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
    Family5EntityPage,
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
      project: fam5
    entities:
      components:
        - id: COMP-1
          name: WebService
          status: ACTIVE
        - id: COMP-2
          name: BatchWorker
          status: ACTIVE
        - id: COMP-3
          name: Orphan
          status: ACTIVE
      environments:
        - id: ENV-1
          name: ProdUSEast
          status: ACTIVE
          kind: production
          region: us-east-1
          infrastructure:
            - k8s
            - postgres
          constraints:
            - pci-dss
            - hipaa
        - id: ENV-2
          name: Sandbox
          status: ACTIVE
          kind: development
      resources:
        - id: RES-1
          name: PrimaryDB
          status: ACTIVE
          kind: database
          provider: aws
          location: us-east-1
          sla: 99.99%
        - id: RES-2
          name: UnusedCache
          status: ACTIVE
          kind: cache
    relationships:
      - from: COMP-1
        to: ENV-1
        type: allocated-to
      - from: COMP-2
        to: ENV-1
        type: allocated-to
      - from: COMP-1
        to: RES-1
        type: consumes
      - from: COMP-2
        to: RES-1
        type: depends-on
    """
)

PKG_YAML = dedent(
    """\
    architecture_id: fam5-pkg
    name: Fam5
    slug: fam5-pkg
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
    registry.register("family5.entity_page", Family5EntityPage(), version="1.0.0")
    slice_ = ModelSlice(
        id="s-f5",
        architecture_id="fam5-pkg",
        model_revision="rev-1",
        scope=f"entity({entity_id})",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=[entity_id]),
        parameters={"hops": 3},
    )
    view = ViewSpec(
        id="v-f5",
        slice_ref=SliceRef(slice_id="s-f5", model_revision="rev-1"),
        projector="family5.entity_page",
        output_content_kind="prose",
        depth=0,
    )
    mat = materialize(slice_, pkg, view_spec=view)
    return project(view, mat, registry=registry).diagram_spec


def test_environment_shape(pkg):
    spec = _project_entity(pkg, "ENV-1")
    assert spec.id == "prose:family5.entity_page:ENV-1"
    assert spec.title == "ProdUSEast (ENV-1)"
    assert spec.facets["content_kind"] == "markdown"


def test_environment_populated_sections(pkg):
    body = _project_entity(pkg, "ENV-1").facets["body"]
    assert "## Kind" in body and "production" in body
    assert "## Region" in body and "us-east-1" in body
    assert "## Infrastructure" in body
    assert "- k8s" in body and "- postgres" in body
    assert "## Constraints" in body
    assert "- pci-dss" in body and "- hipaa" in body
    assert "## Deployed Components" in body
    assert "- COMP-1" in body and "- COMP-2" in body


def test_environment_empty_optional_sections_omitted(pkg):
    body = _project_entity(pkg, "ENV-2").facets["body"]
    # ENV-2 has kind=development, no region, no infra, no constraints,
    # no inbound allocations.
    assert "## Kind" in body  # kind always populated (enum default)
    assert "development" in body
    assert "## Region" not in body
    assert "## Infrastructure" not in body
    assert "## Constraints" not in body
    assert "## Deployed Components" not in body


def test_resource_populated_sections(pkg):
    body = _project_entity(pkg, "RES-1").facets["body"]
    assert "## Kind" in body and "database" in body
    assert "## Provider" in body and "aws" in body
    assert "## Location" in body and "us-east-1" in body
    assert "## SLA" in body and "99.99%" in body
    assert "## Consumed By" in body
    assert "- COMP-1" in body and "- COMP-2" in body


def test_resource_empty_optional_sections_omitted(pkg):
    body = _project_entity(pkg, "RES-2").facets["body"]
    assert "## Kind" in body and "cache" in body
    assert "## Provider" not in body
    assert "## Location" not in body
    assert "## SLA" not in body
    assert "## Consumed By" not in body


def test_component_shows_deployed_to(pkg):
    body = _project_entity(pkg, "COMP-1").facets["body"]
    assert "## Deployed To" in body
    assert "- ENV-1" in body


def test_component_empty_when_no_allocation(pkg):
    body = _project_entity(pkg, "COMP-3").facets["body"]
    assert "## Deployed To" not in body


def test_unsupported_kind_raises(pkg):
    # capability isn't a supported kind for family5 — but our model
    # has none. Use a scope with a bogus kind by wiring an actor.
    model2 = MODEL + dedent(
        """\
          actors:
            - id: ACT-1
              name: Op
              status: ACTIVE
        """
    )
    # Instead of rewriting the fixture, just call the projector
    # directly with a forged config.
    from architecture_model.core.parser import _parse_raw
    import yaml as _y
    registry = ProjectorRegistry()
    proj = Family5EntityPage()
    registry.register("family5.entity_page", proj, version="1.0.0")
    raw = _y.safe_load(MODEL)
    m = _parse_raw(raw)
    with pytest.raises(NotImplementedError, match="family5.entity_page"):
        proj(m, {"__scope_entity_kind": "capability", "__scope_entity_id": "X"})
