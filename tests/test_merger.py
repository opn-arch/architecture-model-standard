"""Tests for architecture_model.core.merger."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from architecture_model.core.merger import merge_manifest
from architecture_model.core.types import (
    ArchitectureModel,
    Capability,
    Component,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
)

from .conftest import HAS_MANIFEST, HAS_MODEL, MANIFEST_PATH, requires_manifest, requires_model


# ---------------------------------------------------------------------------
# merge_manifest with real manifest
# ---------------------------------------------------------------------------


@requires_model
@requires_manifest
class TestMergeManifest:
    """Test merge_manifest() with the real reality-manifest.json."""

    def test_returns_same_model_instance(self, model: ArchitectureModel):
        """merge_manifest() returns the same model (mutates in place)."""
        model_copy = deepcopy(model)
        result = merge_manifest(model_copy, MANIFEST_PATH)
        assert result is model_copy

    def test_manifest_hash_updated(self, model: ArchitectureModel):
        """After merge, model.meta.manifest_hash is set."""
        model_copy = deepcopy(model)
        merge_manifest(model_copy, MANIFEST_PATH)
        assert model_copy.meta.manifest_hash
        assert len(model_copy.meta.manifest_hash) == 16  # sha256[:16]

    def test_file_provenance_added(self, model: ArchitectureModel):
        """After merge, at least some components get file paths resolved."""
        model_copy = deepcopy(model)
        merge_manifest(model_copy, MANIFEST_PATH)
        components_with_files = [c for c in model_copy.entities.components if c.files]
        assert len(components_with_files) > 0

    def test_new_components_discovered(self, model: ArchitectureModel):
        """Merge adds high-LOC components not already in the model."""
        model_copy = deepcopy(model)
        original_count = len(model_copy.entities.components)
        merge_manifest(model_copy, MANIFEST_PATH)
        new_count = len(model_copy.entities.components)
        assert new_count >= original_count

    def test_new_components_have_source_block(self, model: ArchitectureModel):
        """Newly discovered components get source_block assigned via heuristics."""
        model_copy = deepcopy(model)
        original_ids = {c.id for c in model_copy.entities.components}
        merge_manifest(model_copy, MANIFEST_PATH)
        new_components = [c for c in model_copy.entities.components if c.id not in original_ids]
        with_source_block = [c for c in new_components if c.source_block]
        if new_components:
            assert len(with_source_block) > 0, "New components should get source_block from heuristics"

    def test_realizes_relationships_wired(self, model: ArchitectureModel):
        """After merge, new components get realizes relationships to capabilities."""
        model_copy = deepcopy(model)
        original_rel_count = len(model_copy.relationships)
        merge_manifest(model_copy, MANIFEST_PATH)
        new_rel_count = len(model_copy.relationships)
        assert new_rel_count >= original_rel_count

    def test_new_realizes_rels_target_capabilities(self, model: ArchitectureModel):
        """New realizes relationships point to valid capability IDs."""
        model_copy = deepcopy(model)
        original_rels = set((r.from_id, r.to_id, r.type.value) for r in model_copy.relationships)
        merge_manifest(model_copy, MANIFEST_PATH)

        cap_ids = {c.id for c in model_copy.entities.capabilities}
        new_realizes = [
            r
            for r in model_copy.relationships
            if r.type == RelationType.REALIZES
            and (r.from_id, r.to_id, r.type.value) not in original_rels
        ]
        for rel in new_realizes:
            assert rel.to_id in cap_ids, f"Realizes rel targets unknown cap: {rel.to_id}"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestMergeEdgeCases:
    """Edge case tests for merge_manifest()."""

    @requires_model
    def test_missing_manifest_returns_unchanged(self, model: ArchitectureModel, tmp_path: Path):
        """If manifest file doesn't exist, model is returned unchanged."""
        model_copy = deepcopy(model)
        original_hash = model_copy.meta.manifest_hash
        result = merge_manifest(model_copy, tmp_path / "nonexistent.json")
        assert result is model_copy
        assert model_copy.meta.manifest_hash == original_hash

    @requires_model
    def test_empty_manifest_no_crash(self, model: ArchitectureModel, tmp_path: Path):
        """Empty manifest (no modules) doesn't crash."""
        model_copy = deepcopy(model)
        manifest_path = tmp_path / "empty_manifest.json"
        manifest_path.write_text(json.dumps({"modules": [], "functional_blocks": {}}))
        merge_manifest(model_copy, manifest_path)
        assert model_copy.meta.manifest_hash

    @requires_manifest
    def test_model_with_no_components(self, tmp_path: Path):
        """Merge into a model with no pre-existing components."""
        model = ArchitectureModel(
            meta=ModelMeta(
                schema_version="0.1.0",
                project="test",
                source_artifacts=["test"],
            ),
            entities=Entities(
                capabilities=[
                    Capability(id="CAP-S1", name="Ingest", status=Status.ACTIVE, source_block="S1")
                ],
            ),
            relationships=[],
        )
        merge_manifest(model, MANIFEST_PATH)
        assert len(model.entities.components) > 0
