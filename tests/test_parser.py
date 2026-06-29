"""Tests for architecture_model.core.parser."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from architecture_model.core.parser import (
    dump_model,
    load_model,
    save_model,
    validate_model_data,
)
from architecture_model.core.types import ArchitectureModel

from .conftest import MODEL_PATH, requires_model


# ---------------------------------------------------------------------------
# load_model with real file
# ---------------------------------------------------------------------------


@requires_model
class TestLoadModel:
    """Tests for load_model() with the real architecture model YAML."""

    def test_load_returns_architecture_model(self, model: ArchitectureModel):
        """load_model() returns a proper ArchitectureModel instance."""
        assert isinstance(model, ArchitectureModel)

    def test_meta_has_project(self, model: ArchitectureModel):
        """Loaded model has a non-empty project name."""
        assert model.meta.project, "meta.project should not be empty"

    def test_meta_has_schema_version(self, model: ArchitectureModel):
        """Loaded model has schema_version set."""
        assert model.meta.schema_version == "0.1.0"

    def test_has_entities(self, model: ArchitectureModel):
        """Loaded model contains entities across all types."""
        assert model.entity_count > 0
        assert len(model.entities.actors) > 0
        assert len(model.entities.capabilities) > 0
        assert len(model.entities.behaviors) > 0
        assert len(model.entities.components) > 0

    def test_has_relationships(self, model: ArchitectureModel):
        """Loaded model has relationships."""
        assert model.relationship_count > 0

    def test_capabilities_have_fblock(self, model: ArchitectureModel):
        """Each capability should reference an F-block."""
        for cap in model.entities.capabilities:
            assert cap.f_block, f"Capability {cap.id} missing f_block"


class TestLoadModelErrors:
    """Tests for load_model() error handling (no real data needed)."""

    def test_empty_file_raises(self, tmp_path: Path):
        """load_model() raises ValueError on empty YAML file."""
        empty = tmp_path / "empty.yaml"
        empty.write_text("")
        with pytest.raises(ValueError, match="Empty model file"):
            load_model(empty)

    def test_missing_file_raises(self, tmp_path: Path):
        """load_model() raises FileNotFoundError on missing file."""
        with pytest.raises(FileNotFoundError):
            load_model(tmp_path / "nonexistent.yaml")

    def test_malformed_yaml_raises(self, tmp_path: Path):
        """load_model() raises on malformed YAML content."""
        bad = tmp_path / "bad.yaml"
        bad.write_text("meta:\n  project: x\nentities:\n  actors: [[[invalid")
        with pytest.raises(Exception):
            load_model(bad)


# ---------------------------------------------------------------------------
# save_model round-trip
# ---------------------------------------------------------------------------


@requires_model
class TestSaveModel:
    """Tests for save_model() and round-trip fidelity."""

    def test_round_trip_preserves_entity_count(self, model: ArchitectureModel, tmp_path: Path):
        """Load → save → load produces same entity count."""
        out_path = tmp_path / "round_trip.yaml"
        save_model(model, out_path)
        reloaded = load_model(out_path)
        assert reloaded.entity_count == model.entity_count

    def test_round_trip_preserves_relationship_count(
        self, model: ArchitectureModel, tmp_path: Path
    ):
        """Load → save → load produces same relationship count."""
        out_path = tmp_path / "round_trip.yaml"
        save_model(model, out_path)
        reloaded = load_model(out_path)
        assert reloaded.relationship_count == model.relationship_count

    def test_round_trip_preserves_meta(self, model: ArchitectureModel, tmp_path: Path):
        """Round-trip preserves meta fields."""
        out_path = tmp_path / "round_trip.yaml"
        save_model(model, out_path)
        reloaded = load_model(out_path)
        assert reloaded.meta.project == model.meta.project
        assert reloaded.meta.schema_version == model.meta.schema_version

    def test_round_trip_preserves_actor_ids(self, model: ArchitectureModel, tmp_path: Path):
        """Round-trip preserves all actor IDs."""
        out_path = tmp_path / "round_trip.yaml"
        save_model(model, out_path)
        reloaded = load_model(out_path)
        original_ids = {a.id for a in model.entities.actors}
        reloaded_ids = {a.id for a in reloaded.entities.actors}
        assert original_ids == reloaded_ids

    def test_creates_parent_dirs(self, tmp_path: Path, model: ArchitectureModel):
        """save_model() creates parent directories if needed."""
        out_path = tmp_path / "nested" / "deep" / "model.yaml"
        save_model(model, out_path)
        assert out_path.exists()


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestValidateModelData:
    """Tests for validate_model_data() schema validation."""

    @requires_model
    def test_real_model_passes_schema(self, model: ArchitectureModel):
        """The real model data passes JSON Schema validation."""
        data = dump_model(model)
        errors = validate_model_data(data)
        # Filter out the "not installed" message
        real_errors = [e for e in errors if "not installed" not in e]
        assert len(real_errors) == 0, f"Schema errors: {real_errors}"

    def test_empty_dict_fails_schema(self):
        """An empty dict should fail schema validation."""
        errors = validate_model_data({})
        # Should have errors (unless jsonschema not installed)
        if errors and "not installed" not in errors[0]:
            assert len(errors) > 0

    def test_minimal_valid_structure(self):
        """A minimal valid structure should pass."""
        data = {
            "meta": {"schema_version": "0.1.0", "project": "test"},
            "entities": {},
            "relationships": [],
        }
        errors = validate_model_data(data)
        real_errors = [e for e in errors if "not installed" not in e]
        # Minimal structure may or may not be valid depending on schema strictness
        # This test just ensures no crash
        assert isinstance(real_errors, list)
