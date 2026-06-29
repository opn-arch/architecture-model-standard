"""Tests for architecture_model.core.slicer."""

from __future__ import annotations

import pytest

from architecture_model.core.slicer import (
    slice_by_fblock,
    slice_by_layer,
    slice_by_status,
    slice_for_artifact,
)
from architecture_model.core.types import ArchitectureModel, Status

from .conftest import requires_model


# ---------------------------------------------------------------------------
# slice_by_fblock
# ---------------------------------------------------------------------------


@requires_model
class TestSliceByFblock:
    """Test slicing model by F-block identifier."""

    def test_returns_only_fblock_capabilities(self, model: ArchitectureModel):
        """Sliced model contains only capabilities for the requested F-block."""
        sliced = slice_by_fblock(model, "F1")
        for cap in sliced.entities.capabilities:
            assert cap.f_block == "F1", f"Cap {cap.id} has f_block={cap.f_block}, expected F1"

    def test_returns_only_fblock_components(self, model: ArchitectureModel):
        """Sliced model contains only components allocated to the requested F-block."""
        sliced = slice_by_fblock(model, "F2")
        for comp in sliced.entities.components:
            assert comp.f_block == "F2", f"Comp {comp.id} has f_block={comp.f_block}, expected F2"

    def test_slice_is_proper_subset(self, model: ArchitectureModel):
        """Sliced model has fewer or equal entities than the full model."""
        sliced = slice_by_fblock(model, "F1")
        assert sliced.entity_count <= model.entity_count

    def test_slice_has_relationships(self, model: ArchitectureModel):
        """Sliced model includes relationships for sliced entities."""
        sliced = slice_by_fblock(model, "F1")
        # Should have at least some relationships if model has behaviors tagged F1
        if sliced.entities.behaviors:
            assert sliced.relationship_count > 0

    def test_nonexistent_fblock_returns_empty(self, model: ArchitectureModel):
        """Slicing by non-existent F-block returns empty entities."""
        sliced = slice_by_fblock(model, "F99")
        assert len(sliced.entities.capabilities) == 0
        assert len(sliced.entities.components) == 0

    def test_no_relationship_mode(self, model: ArchitectureModel):
        """include_relationships=False returns no relationships."""
        sliced = slice_by_fblock(model, "F1", include_relationships=False)
        assert sliced.relationship_count == 0

    def test_behaviors_tagged_with_fblock(self, model: ArchitectureModel):
        """Sliced behaviors should all be tagged with the F-block."""
        sliced = slice_by_fblock(model, "F1")
        for beh in sliced.entities.behaviors:
            assert "F1" in beh.tags, f"Behavior {beh.id} not tagged with F1"


# ---------------------------------------------------------------------------
# slice_for_artifact
# ---------------------------------------------------------------------------


REGISTERED_ARTIFACTS = [
    "functional-architecture",
    "logical-architecture",
    "use-cases",
    "icd",
    "requirements-analysis",
    "operations-manual",
    "conops",
    "testing",
    "deployment-guide",
    "data-dictionary",
]


@requires_model
class TestSliceForArtifact:
    """Test artifact-specific slicing."""

    @pytest.mark.parametrize("artifact_name", REGISTERED_ARTIFACTS)
    def test_registered_artifact_returns_subset(self, model: ArchitectureModel, artifact_name: str):
        """Each registered artifact returns a proper model subset."""
        sliced = slice_for_artifact(model, artifact_name)
        assert isinstance(sliced, ArchitectureModel)
        # Sliced should not have MORE entities than the full model
        assert sliced.entity_count <= model.entity_count

    @pytest.mark.parametrize("artifact_name", REGISTERED_ARTIFACTS)
    def test_registered_artifact_preserves_meta(self, model: ArchitectureModel, artifact_name: str):
        """Sliced model preserves meta from original."""
        sliced = slice_for_artifact(model, artifact_name)
        assert sliced.meta.project == model.meta.project
        assert sliced.meta.schema_version == model.meta.schema_version

    def test_functional_has_capabilities(self, model: ArchitectureModel):
        """functional-architecture slice includes capabilities."""
        sliced = slice_for_artifact(model, "functional-architecture")
        assert len(sliced.entities.capabilities) > 0

    def test_functional_has_no_components(self, model: ArchitectureModel):
        """functional-architecture slice should not include components."""
        sliced = slice_for_artifact(model, "functional-architecture")
        assert len(sliced.entities.components) == 0

    def test_logical_has_layers_and_components(self, model: ArchitectureModel):
        """logical-architecture slice includes layers and components."""
        sliced = slice_for_artifact(model, "logical-architecture")
        assert len(sliced.entities.layers) > 0
        assert len(sliced.entities.components) > 0

    def test_icd_has_interfaces(self, model: ArchitectureModel):
        """icd slice includes interfaces."""
        sliced = slice_for_artifact(model, "icd")
        assert len(sliced.entities.interfaces) > 0

    def test_use_cases_has_actors_and_behaviors(self, model: ArchitectureModel):
        """use-cases slice includes actors and behaviors."""
        sliced = slice_for_artifact(model, "use-cases")
        assert len(sliced.entities.actors) > 0
        assert len(sliced.entities.behaviors) > 0

    def test_requirements_has_constraints(self, model: ArchitectureModel):
        """requirements-analysis slice includes constraints."""
        sliced = slice_for_artifact(model, "requirements-analysis")
        assert len(sliced.entities.constraints) > 0

    def test_unregistered_artifact_returns_full_copy(self, model: ArchitectureModel):
        """Unregistered artifact name returns a deep copy of the full model."""
        sliced = slice_for_artifact(model, "nonexistent-artifact-xyz")
        assert sliced.entity_count == model.entity_count
        assert sliced.relationship_count == model.relationship_count

    def test_sliced_model_no_extra_entities_leaked(self, model: ArchitectureModel):
        """Sliced model IDs should be a subset of the full model IDs."""
        sliced = slice_for_artifact(model, "logical-architecture")
        sliced_ids = sliced.all_entity_ids
        full_ids = model.all_entity_ids
        leaked = sliced_ids - full_ids
        assert len(leaked) == 0, f"Leaked IDs: {leaked}"


# ---------------------------------------------------------------------------
# slice_by_status
# ---------------------------------------------------------------------------


@requires_model
class TestSliceByStatus:
    """Test filtering model by entity status."""

    def test_active_filter(self, model: ArchitectureModel):
        """Filtering for ACTIVE returns only active entities."""
        sliced = slice_by_status(model, Status.ACTIVE)
        for cap in sliced.entities.capabilities:
            assert cap.status == Status.ACTIVE
        for comp in sliced.entities.components:
            assert comp.status == Status.ACTIVE

    def test_status_filter_is_subset(self, model: ArchitectureModel):
        """Status-filtered model is a subset of the original."""
        sliced = slice_by_status(model, Status.ACTIVE)
        assert sliced.entity_count <= model.entity_count


# ---------------------------------------------------------------------------
# slice_by_layer
# ---------------------------------------------------------------------------


@requires_model
class TestSliceByLayer:
    """Test slicing by architectural layer."""

    def test_slice_by_existing_layer(self, model: ArchitectureModel):
        """Slicing by existing layer returns components in that layer."""
        if not model.entities.layers:
            pytest.skip("No layers in model")
        layer_id = model.entities.layers[0].id
        sliced = slice_by_layer(model, layer_id)
        assert isinstance(sliced, ArchitectureModel)
        for comp in sliced.entities.components:
            assert comp.layer == layer_id

    def test_slice_by_nonexistent_layer(self, model: ArchitectureModel):
        """Slicing by non-existent layer returns empty components."""
        sliced = slice_by_layer(model, "nonexistent-layer-99")
        assert len(sliced.entities.components) == 0
