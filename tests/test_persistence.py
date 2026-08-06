"""Tests for architecture_model.persistence.store."""
import json
from pathlib import Path

import pytest

from architecture_model.persistence.store import (
    save_project, load_project, save_block, ProjectSnapshot,
)


def _make_minimal_model():
    from architecture_model.core.types import ArchitectureModel, Entities, Component, ModelMeta
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(components=[
            Component(id="COMP-1", name="Core", status="ACTIVE"),
        ]),
        relationships=[],
    )


def _make_minimal_manifest(root: Path):
    from architecture_model.manifest.types import Manifest, MetricsResult
    return Manifest(
        modules=[], interfaces=[], functional_blocks={},
        generated_at="2026-07-31T00:00:00Z",
        project_root=str(root),
        metrics=MetricsResult(values={
            "total_modules": 5, "total_functions": 20, "total_classes": 10,
            "total_lines": 1000,
        }),
    )


def _make_repr_result():
    from architecture_model.core.representativeness import RepresentativenessResult
    return RepresentativenessResult(
        file_coverage=1.0, relationship_accuracy=1.0,
        boundary_coherence=0.95, behavioral_coverage=0.98,
        overall=0.98, low_coherence_components=["Models"],
    )


class TestSaveProject:
    def test_creates_architecture_dir(self, tmp_path):
        model = _make_minimal_model()
        manifest = _make_minimal_manifest(tmp_path)
        result = save_project(tmp_path, model, manifest)
        assert result == tmp_path / ".architecture"
        assert result.is_dir()

    def test_saves_model_yaml(self, tmp_path):
        model = _make_minimal_model()
        manifest = _make_minimal_manifest(tmp_path)
        save_project(tmp_path, model, manifest)
        assert (tmp_path / ".architecture-model.yaml").exists()

    def test_saves_manifest_json(self, tmp_path):
        model = _make_minimal_model()
        manifest = _make_minimal_manifest(tmp_path)
        save_project(tmp_path, model, manifest)
        manifest_path = tmp_path / ".architecture" / "manifest.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert "generated_at" in data

    def test_saves_metrics_json(self, tmp_path):
        model = _make_minimal_model()
        manifest = _make_minimal_manifest(tmp_path)
        rep = _make_repr_result()
        save_project(tmp_path, model, manifest, representativeness=rep)
        metrics_path = tmp_path / ".architecture" / "metrics.json"
        assert metrics_path.exists()
        data = json.loads(metrics_path.read_text())
        assert data["representativeness"]["file_coverage"] == 1.0
        assert data["representativeness"]["overall"] == 0.98

    def test_saves_telemetry(self, tmp_path):
        model = _make_minimal_model()
        manifest = _make_minimal_manifest(tmp_path)
        telemetry = {"token_budget": 4000, "iterations": 1}
        save_project(tmp_path, model, manifest, telemetry=telemetry)
        data = json.loads((tmp_path / ".architecture" / "metrics.json").read_text())
        assert data["telemetry"]["token_budget"] == 4000

    def test_saves_manifest_metrics(self, tmp_path):
        model = _make_minimal_model()
        manifest = _make_minimal_manifest(tmp_path)
        save_project(tmp_path, model, manifest)
        data = json.loads((tmp_path / ".architecture" / "metrics.json").read_text())
        assert data["manifest_metrics"]["total_modules"] == 5  # MetricsResult.to_dict() returns values dict


class TestSaveBlock:
    def test_creates_block_dir(self, tmp_path):
        model = _make_minimal_model()
        manifest = _make_minimal_manifest(tmp_path)
        result = save_block(tmp_path, "S1", model, manifest)
        assert result == tmp_path / ".architecture" / "S1"
        assert result.is_dir()

    def test_saves_block_model(self, tmp_path):
        model = _make_minimal_model()
        manifest = _make_minimal_manifest(tmp_path)
        save_block(tmp_path, "S1", model, manifest)
        assert (tmp_path / ".architecture" / "S1" / ".architecture-model.yaml").exists()

    def test_saves_block_manifest(self, tmp_path):
        model = _make_minimal_model()
        manifest = _make_minimal_manifest(tmp_path)
        save_block(tmp_path, "S1", model, manifest)
        assert (tmp_path / ".architecture" / "S1" / "manifest.json").exists()

    def test_saves_block_metrics(self, tmp_path):
        model = _make_minimal_model()
        manifest = _make_minimal_manifest(tmp_path)
        rep = _make_repr_result()
        save_block(tmp_path, "S1", model, manifest, representativeness=rep)
        data = json.loads((tmp_path / ".architecture" / "S1" / "metrics.json").read_text())
        assert data["representativeness"]["boundary_coherence"] == 0.95


class TestLoadProject:
    def test_load_roundtrip(self, tmp_path):
        model = _make_minimal_model()
        manifest = _make_minimal_manifest(tmp_path)
        rep = _make_repr_result()
        save_project(tmp_path, model, manifest, representativeness=rep,
                     telemetry={"iterations": 2})

        snapshot = load_project(tmp_path)
        assert snapshot.model is not None
        assert snapshot.manifest_dict.get("generated_at") is not None
        assert snapshot.metrics["representativeness"]["overall"] == 0.98
        assert snapshot.metrics["telemetry"]["iterations"] == 2

    def test_load_empty_dir(self, tmp_path):
        snapshot = load_project(tmp_path)
        assert snapshot.model is None
        assert snapshot.manifest_dict == {}
        assert snapshot.metrics == {}
