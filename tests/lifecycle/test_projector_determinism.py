"""Byte-identical round-trip guards for the 4 seeded SE projectors.

Each projector must produce identical ``ProjectedView.diagram_spec`` output
across two independent invocations against the same MaterializedSlice.
Guards against accidental non-determinism (dict ordering, timestamps,
random ids) being introduced by future projector-registry refactors.
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

    ser_a = json.dumps(asdict(projected_a.diagram_spec), sort_keys=True, default=str)
    ser_b = json.dumps(asdict(projected_b.diagram_spec), sort_keys=True, default=str)
    assert ser_a == ser_b, f"{projector_name} not byte-identical across runs"
