"""ProjectedView provenance carries freshness + revision fields.

Task 10 of Phase 1 substrate-and-liveness plan. The `project()` function
stamps provenance with a `freshness` marker (fresh|stale|pending) and a
`revision` field mirroring the materialized slice's model_revision, so
downstream consumers can tell if an artifact reflects HEAD's model.
"""
from pathlib import Path

import pytest

from architecture_model.lifecycle.freshness import FRESHNESS_VALUES
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
        selectors=Selectors(entity_ids=[
            "ACT-1", "CAP-F1", "BEH-1", "COMP-1", "IF-1", "CON-1", "app",
        ]),
    )
    return materialize(slice_, pkg)


def test_freshness_values_are_the_three_expected():
    assert set(FRESHNESS_VALUES) == {"fresh", "stale", "pending"}


def test_project_stamps_freshness_and_revision(materialized_sample_slice):
    view_spec = ViewSpec(
        id="test-view",
        slice_ref=SliceRef(slice_id="test-slice", model_revision="rev-1"),
        projector="se.conops",
        output_content_kind="diagram",
    )
    projected = project(view_spec, materialized_sample_slice, registry=DEFAULT_REGISTRY)
    assert projected.provenance["freshness"] == "fresh"
    assert projected.provenance["revision"] == "rev-1"
    # Existing provenance keys preserved
    assert projected.provenance["projector"] == "se.conops"
    assert "produced_at" in projected.provenance
