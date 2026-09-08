"""Byte-identical round-trip guards for the 4 seeded SE projectors.

Each projector must produce identical ``ProjectedView.diagram_spec`` output
across two independent invocations against the same MaterializedSlice.
Guards against accidental non-determinism (dict ordering, timestamps,
random ids) being introduced by future projector-registry refactors.

We compare ``diagram_spec`` only, not the full ``ProjectedView``:
``ProjectedView.provenance.produced_at`` is wall-clock and legitimately
differs across runs.

Note for Task 2-4 authors reusing this fixture: the ``Selectors`` here
enumerates every entity ID so all projectors have material to render.
Tasks that need to prove projector scope-filtering behavior must build
their own narrower ``Selectors`` rather than inherit this one.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from architecture_model.lifecycle.model_slice import ModelSlice, Selectors
from architecture_model.lifecycle.model_slice_materializer import materialize
from architecture_model.lifecycle.package import load_package
from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY, project
from architecture_model.lifecycle.view_spec import SliceRef, ViewSpec

FIXTURE_MODEL = (
    Path(__file__).parent.parent / "fixtures" / "lifecycle" / "sample_model.yaml"
)

PKG_YAML = """\
architecture_id: test-arch
name: Test
slug: test-arch
contract_version: "1.0.0"
model_ref: .architecture-model.yaml
manifest_ref: manifest.json
"""


@pytest.fixture
def materialized_sample_slice(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "package.yaml").write_text(PKG_YAML)
    (root / ".architecture-model.yaml").write_text(FIXTURE_MODEL.read_text())
    (root / "manifest.json").write_text("{}")
    pkg = load_package(root)
    slice_ = ModelSlice(
        id="test-slice",
        architecture_id="test-arch",
        model_revision="rev-1",
        scope="local",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(
            entity_ids=[
                "ACT-1",
                "CAP-F1",
                "BEH-1",
                "COMP-1",
                "IF-1",
                "CON-1",
                "app",
            ]
        ),
    )
    return materialize(slice_, pkg)


@pytest.mark.parametrize(
    "projector_name",
    ["se.conops", "se.functional", "se.logical", "se.use_cases"],
)
def test_projector_output_is_byte_identical(
    projector_name, materialized_sample_slice
):
    view_spec = ViewSpec(
        id=f"test-{projector_name}",
        slice_ref=SliceRef(slice_id="test-slice", model_revision="rev-1"),
        projector=projector_name,
        output_content_kind="diagram",
    )

    projected_a = project(view_spec, materialized_sample_slice, registry=DEFAULT_REGISTRY)
    projected_b = project(view_spec, materialized_sample_slice, registry=DEFAULT_REGISTRY)

    # Structural equality catches object-level drift that a stringifying
    # serializer might paper over.
    assert projected_a.diagram_spec == projected_b.diagram_spec, (
        f"{projector_name} diagram_spec objects not equal across runs"
    )

    # Byte-identity via strict canonical JSON. No ``default=`` fallback:
    # any non-JSON-serializable field surfacing here means the projector
    # is emitting non-primitive state and must be fixed at the source.
    ser_a = json.dumps(asdict(projected_a.diagram_spec), sort_keys=True)
    ser_b = json.dumps(asdict(projected_b.diagram_spec), sort_keys=True)
    assert ser_a == ser_b, f"{projector_name} not byte-identical across runs"
