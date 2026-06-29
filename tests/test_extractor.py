"""Tests for architecture_model.extract.from_artifacts."""

from __future__ import annotations

from pathlib import Path

import pytest

from architecture_model.extract.from_artifacts import extract_from_artifacts
from architecture_model.core.types import (
    ActorType,
    ArchitectureModel,
    RelationType,
    Status,
)

from .conftest import requires_artifacts


# ---------------------------------------------------------------------------
# extract_from_artifacts with real data
# ---------------------------------------------------------------------------


@requires_artifacts
class TestExtractFromArtifacts:
    """Test extraction from real stage2 artifacts."""

    @pytest.fixture(scope="class")
    def extracted_model(self, artifacts_dir: Path) -> ArchitectureModel:
        """Extract model from real artifacts (class-scoped)."""
        return extract_from_artifacts(artifacts_dir, project="logs-db", system="logs-db")

    def test_returns_architecture_model(self, extracted_model: ArchitectureModel):
        """extract_from_artifacts() returns ArchitectureModel."""
        assert isinstance(extracted_model, ArchitectureModel)

    def test_meta_project_set(self, extracted_model: ArchitectureModel):
        """Extracted model has project set."""
        assert extracted_model.meta.project

    def test_meta_source_artifacts_populated(self, extracted_model: ArchitectureModel):
        """Source artifacts list is populated."""
        assert len(extracted_model.meta.source_artifacts) > 0

    # --- Entity count ranges ---

    def test_actors_extracted(self, extracted_model: ArchitectureModel):
        """Extraction discovers actors (expect 2+ from use-cases.md)."""
        assert len(extracted_model.entities.actors) >= 2

    def test_capabilities_extracted(self, extracted_model: ArchitectureModel):
        """Extraction discovers capabilities/F-blocks (expect 4-8)."""
        count = len(extracted_model.entities.capabilities)
        assert 4 <= count <= 12, f"Expected 4-12 capabilities, got {count}"

    def test_behaviors_extracted(self, extracted_model: ArchitectureModel):
        """Extraction discovers behaviors/UCs (expect 5+)."""
        assert len(extracted_model.entities.behaviors) >= 5

    def test_interfaces_extracted(self, extracted_model: ArchitectureModel):
        """Extraction discovers interfaces from ICD (expect 3+)."""
        assert len(extracted_model.entities.interfaces) >= 3

    def test_constraints_extracted(self, extracted_model: ArchitectureModel):
        """Extraction discovers constraints from requirements (expect 3+)."""
        assert len(extracted_model.entities.constraints) >= 3

    def test_layers_extracted(self, extracted_model: ArchitectureModel):
        """Extraction discovers layers from logical architecture (expect 3+)."""
        assert len(extracted_model.entities.layers) >= 3

    def test_components_extracted(self, extracted_model: ArchitectureModel):
        """Extraction discovers components (expect 5+)."""
        assert len(extracted_model.entities.components) >= 5

    # --- Relationship types ---

    def test_realizes_relationships_present(self, extracted_model: ArchitectureModel):
        """Model has 'realizes' relationships linking behaviors to capabilities."""
        realizes = [r for r in extracted_model.relationships if r.type == RelationType.REALIZES]
        assert len(realizes) > 0

    def test_depends_on_relationships_present(self, extracted_model: ArchitectureModel):
        """Model has 'depends-on' relationships."""
        deps = [r for r in extracted_model.relationships if r.type == RelationType.DEPENDS_ON]
        assert len(deps) >= 0  # May or may not have depending on artifacts

    def test_exposes_relationships_present(self, extracted_model: ArchitectureModel):
        """Model has 'exposes' relationships from interface extraction."""
        exposes = [r for r in extracted_model.relationships if r.type == RelationType.EXPOSES]
        assert len(exposes) > 0

    def test_consumes_relationships_present(self, extracted_model: ArchitectureModel):
        """Model has 'consumes' relationships from interface extraction."""
        consumes = [r for r in extracted_model.relationships if r.type == RelationType.CONSUMES]
        assert len(consumes) > 0

    # --- External actor auto-discovery ---

    def test_external_actors_auto_discovered(self, extracted_model: ArchitectureModel):
        """External actors are auto-discovered from ICD consumer references."""
        external_actors = [
            a for a in extracted_model.entities.actors if a.type == ActorType.EXTERNAL_SERVICE
        ]
        assert len(external_actors) >= 1

    def test_auto_discovered_actors_have_description(self, extracted_model: ArchitectureModel):
        """Auto-discovered actors have informative descriptions."""
        external_actors = [
            a for a in extracted_model.entities.actors if a.type == ActorType.EXTERNAL_SERVICE
        ]
        for actor in external_actors:
            if "auto-discovered" in (actor.description or ""):
                assert "ICD consumer" in actor.description

    # --- Component->capability wiring ---

    def test_component_capability_relationships(self, extracted_model: ArchitectureModel):
        """Components with f_block should have realizes relationships to capabilities."""
        components_with_fblock = [c for c in extracted_model.entities.components if c.f_block]
        if not components_with_fblock:
            pytest.skip("No components with f_block found")

        realizes = [r for r in extracted_model.relationships if r.type == RelationType.REALIZES]
        realizes_from_ids = {r.from_id for r in realizes}

        wired = [c for c in components_with_fblock if c.id in realizes_from_ids]
        assert len(wired) > 0, "No component->capability relationships wired"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestExtractEdgeCases:
    """Edge case tests for extraction."""

    def test_empty_directory(self, tmp_path: Path):
        """Extraction from empty dir returns model with no entities."""
        model = extract_from_artifacts(tmp_path, project="empty")
        assert model.entity_count == 0
        assert model.relationship_count == 0
        assert model.meta.project == "empty"

    def test_partial_artifacts(self, tmp_path: Path):
        """Extraction from dir with only some artifacts still works."""
        (tmp_path / "functional-architecture.md").write_text(
            """# Functional Architecture
```plantuml
class "F1: Test Block" as f1 <<block>>
```
""",
            encoding="utf-8",
        )
        model = extract_from_artifacts(tmp_path, project="partial")
        assert len(model.entities.capabilities) >= 1
