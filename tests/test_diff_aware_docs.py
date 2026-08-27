"""Tests for diff-aware SE doc regeneration."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from architecture_model.docs.se.generator import (
    regenerate_affected, ARTIFACT_TO_DOC_KEY,
)
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Component, Capability,
    Interface, Status, Relationship,
)


def _make_model(**overrides):
    defaults = dict(
        meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
        entities=Entities(
            components=[Component(id="COMP-1", name="A", status=Status.ACTIVE)],
            capabilities=[Capability(id="CAP-1", name="C", status=Status.ACTIVE)],
        ),
        relationships=[],
    )
    defaults.update(overrides)
    return ArchitectureModel(**defaults)


class TestArtifactToDocKeyMapping:
    def test_mapping_covers_all_diff_artifact_names(self):
        """All names returned by ModelDiff.affected_artifacts() must map to a doc key."""
        expected_artifact_names = {
            "use-cases", "functional-architecture", "logical-architecture",
            "icd", "requirements-analysis", "readme",
        }
        for name in expected_artifact_names:
            assert name in ARTIFACT_TO_DOC_KEY, f"{name} not in mapping"

    def test_mapping_values_are_valid_doc_keys(self):
        """Mapped doc keys must match STANDARD_DOCS keys."""
        from architecture_model.docs.se.generator import STANDARD_DOCS
        valid_keys = {k for k, _, _, _ in STANDARD_DOCS}
        for artifact, doc_key in ARTIFACT_TO_DOC_KEY.items():
            if doc_key is not None:  # None means skip (e.g., readme)
                assert doc_key in valid_keys, f"{artifact} maps to unknown key {doc_key}"


class TestRegenerateAffected:
    def test_no_changes_returns_empty(self, tmp_path):
        """If models are identical, no docs should be regenerated."""
        model = _make_model()
        result = regenerate_affected(model, model, tmp_path)
        assert result["generated"] == []
        assert result["reason"] == "no_changes"

    def test_added_component_regenerates_logical(self, tmp_path):
        """Adding a component should trigger logical-architecture regeneration."""
        old = _make_model()
        new = _make_model(
            entities=Entities(
                components=[
                    Component(id="COMP-1", name="A", status=Status.ACTIVE),
                    Component(id="COMP-2", name="B", status=Status.ACTIVE),
                ],
                capabilities=[Capability(id="CAP-1", name="C", status=Status.ACTIVE)],
            ),
        )
        result = regenerate_affected(old, new, tmp_path)
        generated_files = [Path(p).name for p in result["generated"]]
        assert "logical-architecture.md" in generated_files

    def test_returns_affected_artifact_names(self, tmp_path):
        """Result should include which artifacts were affected."""
        old = _make_model()
        new = _make_model(
            entities=Entities(
                components=[
                    Component(id="COMP-1", name="A", status=Status.ACTIVE),
                    Component(id="COMP-2", name="B", status=Status.ACTIVE),
                ],
                capabilities=[Capability(id="CAP-1", name="C", status=Status.ACTIVE)],
            ),
        )
        result = regenerate_affected(old, new, tmp_path)
        assert "affected_artifacts" in result
        assert len(result["affected_artifacts"]) > 0
