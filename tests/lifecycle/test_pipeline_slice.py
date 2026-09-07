"""B3.1.1 — pipeline dashboard slice spec + materialization.

The interactive dashboard consumes a ModelSlice fragment containing all
capabilities, components, and constraints of a package plus their
allocation edges (``realizes``, ``allocated-to``, ``constrained-by``).
This test proves the shipped fixture at
``tests/fixtures/lifecycle/pipeline.slice.yaml`` materializes correctly
against a small ArchitecturePackage.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from architecture_model.lifecycle.model_slice import ModelSlice
from architecture_model.lifecycle.model_slice_materializer import materialize
from architecture_model.lifecycle.package import load_package


FIXTURES = Path(__file__).parent.parent / "fixtures" / "lifecycle"
PKG_FIXTURE = FIXTURES / "pipeline_dashboard_pkg"
SLICE_YAML = FIXTURES / "pipeline.slice.yaml"


def _ids(entities, field: str) -> set[str]:
    return {e.id for e in getattr(entities, field, [])}


def test_pipeline_slice_materializes_on_fixture(tmp_path):
    """Copy sample_package_tree; run architect_slice_materialize with
    spec loaded from tests/fixtures/lifecycle/pipeline.slice.yaml;
    assert output fragment contains all capabilities, components, and
    constraint entities and their allocation edges."""
    # Copy the fixture package tree into tmp_path so the test is hermetic.
    pkg_dir = tmp_path / "pkg"
    shutil.copytree(PKG_FIXTURE, pkg_dir)

    # Load the shipped slice spec (must be a fixture, per plan).
    with SLICE_YAML.open() as fh:
        slice_spec = ModelSlice.model_validate(yaml.safe_load(fh))

    pkg = load_package(pkg_dir)
    mat = materialize(slice_spec, pkg)

    frag = mat.model_fragment

    # All capabilities present.
    assert _ids(frag.entities, "capabilities") == {"CAP-INGEST", "CAP-RENDER"}
    # All components present.
    assert _ids(frag.entities, "components") == {
        "COMP-COLLECTOR",
        "COMP-BUILDER",
        "COMP-VIEWER",
    }
    # All constraints present.
    assert _ids(frag.entities, "constraints") == {"CON-LATENCY"}

    # All allocation edges present (both endpoints inside fragment,
    # so strict closure retains them).
    edges = {(r.from_id, r.to_id, r.type.value) for r in frag.relationships}
    assert edges == {
        ("COMP-COLLECTOR", "CAP-INGEST", "realizes"),
        ("COMP-BUILDER", "CAP-RENDER", "realizes"),
        ("COMP-VIEWER", "CAP-RENDER", "allocated-to"),
        ("COMP-BUILDER", "CON-LATENCY", "constrained-by"),
        ("COMP-VIEWER", "CON-LATENCY", "constrained-by"),
    }

    # No dangling-endpoint warnings — every rel's endpoints are selected.
    dangling = [w for w in mat.warnings if w.code == "SLICE.DANGLING_STRIPPED"]
    assert dangling == []

    # Slice identity preserved on the materialized envelope.
    assert mat.slice_id == "pipeline-dashboard"
    assert mat.architecture_id == "pipeline-dashboard-pkg"
    assert mat.model_revision == "rev-1"
