"""Tests for the pipeline HTML dashboard data builder."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import yaml


def _load_materialized(tmp_root: Path):
    from architecture_model.lifecycle.model_slice import ModelSlice
    from architecture_model.lifecycle.model_slice_materializer import materialize
    from architecture_model.lifecycle.package import load_package

    fx = Path("tests/fixtures/lifecycle/pipeline_dashboard_pkg")
    shutil.copytree(fx, tmp_root / "pkg")
    pkg = load_package(tmp_root / "pkg")
    slice_dict = yaml.safe_load(
        Path("tests/fixtures/lifecycle/pipeline.slice.yaml").read_text()
    )
    return materialize(ModelSlice.model_validate(slice_dict), pkg)


def test_build_produces_nodes_edges_and_badges(tmp_path):
    from architecture_model.lifecycle.renderers.pipeline_html_data import build

    ms = _load_materialized(tmp_path)
    data = build(ms, sil_store=None)

    node_ids = {n["id"] for n in data["nodes"]}
    assert node_ids == {
        "CAP-INGEST",
        "CAP-RENDER",
        "COMP-COLLECTOR",
        "COMP-BUILDER",
        "COMP-VIEWER",
        "CON-LATENCY",
    }

    assert len(data["edges"]) == 5
    edge_pairs = {(e["from"], e["to"], e["type"]) for e in data["edges"]}
    assert ("COMP-COLLECTOR", "CAP-INGEST", "realizes") in edge_pairs

    assert data["badges"] == {} or all(v == {} for v in data["badges"].values())


def test_build_populates_badges_from_sil_store():
    from architecture_model.lifecycle.renderers.pipeline_html_data import build

    tmp = Path(tempfile.mkdtemp())
    ms = _load_materialized(tmp)

    class StubSILStore:
        def rollup(self, component_id):
            if component_id == "COMP-COLLECTOR":
                return {
                    "validation_score": 87,
                    "invocations_7d": 42,
                    "failure_rate_7d": 0.02,
                    "avg_duration_ms": 120.5,
                }
            return None

    data = build(ms, sil_store=StubSILStore())
    assert data["badges"]["COMP-COLLECTOR"]["validation_score"] == 87
    assert data["badges"]["COMP-COLLECTOR"]["invocations_7d"] == 42
    assert data["badges"].get("CAP-INGEST", {}) == {}
