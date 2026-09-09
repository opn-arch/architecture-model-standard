"""Determinism guard for family<N>.entity_page projectors (Phase 3 Task 15).

Rebuilding an entity page from the same slice + model MUST produce
byte-identical output across runs. This test parametrizes across all
seven implemented families (1, 2, 3, 4, 6, 7, 8) and one
representative entity per supported kind per family, then asserts
``json.dumps(spec.to_dict(), sort_keys=True)`` matches on repeated
runs. Any hidden nondeterminism (dict iteration order, timestamps in
body, unsorted set output) surfaces here.
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

import pytest

from architecture_model.lifecycle.model_slice import ModelSlice, Selectors
from architecture_model.lifecycle.model_slice_materializer import materialize
from architecture_model.lifecycle.package import load_package
from architecture_model.lifecycle.projectors.entity_pages import (
    Family1EntityPage,
    Family2EntityPage,
    Family3EntityPage,
    Family4EntityPage,
    Family6EntityPage,
    Family7EntityPage,
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


_MODEL = dedent(
    """\
    meta:
      schema_version: '2.1.0'
      project: det
    entities:
      actors:
        - id: ACT-1
          name: Operator
          status: ACTIVE
      capabilities:
        - id: CAP-F1
          name: Ignition
          status: ACTIVE
          requirements: [REQ-A]
          verification: [VERIF-A]
          goals: [reliable]
          stakeholders: [ops, safety]
      behaviors:
        - id: BEH-2
          name: StartSeq
          status: ACTIVE
          requirements: [REQ-B]
      interfaces:
        - id: IF-1
          name: TickAPI
          status: ACTIVE
          type: rest
          protocol: HTTP/1.1
          slos:
            - metric: latency_p95
              target: "< 100ms"
              window: 5m
      constraints:
        - id: CON-1
          name: MaxTemp
          status: ACTIVE
          verification: [VERIF-C]
      layers:
        - id: LAY-1
          name: WebLayer
          status: ACTIVE
      components:
        - id: COMP-3
          name: Engine
          status: ACTIVE
          intent: "Runs the ignition capability"
          requirements: [REQ-1, REQ-2]
          failure_modes: [overheat]
          slos:
            - metric: latency_p99
              target: "< 500ms"
              window: 1h
    relationships:
      - {from: COMP-3, to: CAP-F1, type: realizes}
      - {from: COMP-3, to: IF-1, type: exposes}
      - {from: ACT-1, to: IF-1, type: consumes}
      - {from: CAP-F1, to: BEH-2, type: contains}
      - {from: LAY-1, to: COMP-3, type: contains}
    """
)


_PKG_YAML = dedent(
    """\
    architecture_id: det-pkg
    name: Det
    slug: det-pkg
    contract_version: "1.0.0"
    model_ref: .architecture-model.yaml
    manifest_ref: manifest.json
    """
)


_FAMILY_CLASSES = {
    1: Family1EntityPage,
    2: Family2EntityPage,
    3: Family3EntityPage,
    4: Family4EntityPage,
    6: Family6EntityPage,
    7: Family7EntityPage,
    8: Family8EntityPage,
}


@pytest.fixture
def pkg(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "package.yaml").write_text(_PKG_YAML)
    (root / ".architecture-model.yaml").write_text(_MODEL)
    (root / "manifest.json").write_text("{}")
    return load_package(root)


def _sil_fragment() -> SILFragment:
    return SILFragment(
        events=(
            SILEvent(
                component_id="COMP-3",
                ts="2026-09-08T10:00:00Z",
                kind="call",
                outcome="ok",
                duration_ms=42.0,
            ),
        ),
        summary={
            "COMP-3": {"invocations": 1.0, "failures": 0.0, "avg_duration_ms": 42.0}
        },
    )


def _run_once(pkg, family: int, entity_id: str) -> str:
    registry = ProjectorRegistry()
    registry.register(
        f"family{family}.entity_page",
        _FAMILY_CLASSES[family](),
        version="1.0.0",
    )
    slice_ = ModelSlice(
        id="s",
        architecture_id="det-pkg",
        model_revision="rev-1",
        scope=f"entity({entity_id})",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=[entity_id]),
        parameters={"hops": 3},
    )
    view = ViewSpec(
        id="v",
        slice_ref=SliceRef(slice_id="s", model_revision="rev-1"),
        projector=f"family{family}.entity_page",
        output_content_kind="prose",
        depth=0,
    )
    mat = materialize(slice_, pkg, view_spec=view)
    if family == 8:
        mat.supplementary_fragments["sil"] = _sil_fragment()
    spec = project(view, mat, registry=registry).diagram_spec
    return json.dumps(spec.to_dict(), sort_keys=True)


@pytest.mark.parametrize(
    "family,entity_id",
    [
        (1, "COMP-3"),
        (1, "CAP-F1"),
        (1, "BEH-2"),
        (2, "CAP-F1"),
        (2, "COMP-3"),
        (2, "BEH-2"),
        (3, "COMP-3"),
        (3, "LAY-1"),
        (4, "BEH-2"),
        (4, "ACT-1"),
        (6, "IF-1"),
        (6, "COMP-3"),
        (7, "COMP-3"),
        (7, "CAP-F1"),
        (7, "CON-1"),
        (7, "IF-1"),
        (7, "BEH-2"),
        (8, "COMP-3"),
        (8, "CAP-F1"),
        (8, "IF-1"),
    ],
)
def test_entity_page_byte_identical_across_runs(pkg, family, entity_id):
    a = _run_once(pkg, family, entity_id)
    b = _run_once(pkg, family, entity_id)
    assert a == b, f"family{family}.entity_page nondeterministic for {entity_id}"
