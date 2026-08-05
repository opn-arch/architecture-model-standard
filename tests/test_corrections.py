"""Tests for architecture_model.core.corrections module."""

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from architecture_model.core.corrections import (
    apply_corrections,
    load_corrections,
    mark_applied,
    store_correction,
)
from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
)


def _make_model(components=None, relationships=None):
    """Create a minimal ArchitectureModel for testing."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.3", project="test"),
        entities=Entities(components=components or []),
        relationships=relationships or [],
    )


class TestLoadCorrections:
    def test_load_empty(self, tmp_path):
        """No file returns empty list."""
        assert load_corrections(tmp_path) == []


class TestStoreAndLoad:
    def test_store_and_load(self, tmp_path):
        """Store a correction and load it back."""
        cor = {"type": "rename", "target": "COMP-1", "suggestion": {"name": "New Name"}, "reason": "Better name"}
        stored = store_correction(tmp_path, cor)
        loaded = load_corrections(tmp_path)
        assert len(loaded) == 1
        assert loaded[0]["id"] == stored["id"]
        assert loaded[0]["type"] == "rename"
        assert loaded[0]["applied"] is False

    def test_auto_id_generation(self, tmp_path):
        """IDs are sequential COR-1, COR-2, etc."""
        store_correction(tmp_path, {"type": "rename", "target": "X"})
        store_correction(tmp_path, {"type": "rename", "target": "Y"})
        corrections = load_corrections(tmp_path)
        assert corrections[0]["id"] == "COR-1"
        assert corrections[1]["id"] == "COR-2"


class TestApplyCorrections:
    def test_apply_rename_correction(self, tmp_path):
        comp = Component(id="COMP-1", name="OldName", status=Status.ACTIVE)
        model = _make_model(components=[comp])
        corrections = [
            {"id": "COR-1", "type": "rename", "target": "COMP-1", "suggestion": {"name": "NewName"}, "applied": False}
        ]
        updated, applied_ids = apply_corrections(model, corrections)
        assert updated.entities.components[0].name == "NewName"
        assert applied_ids == ["COR-1"]

    def test_apply_add_relationship(self, tmp_path):
        model = _make_model()
        corrections = [
            {
                "id": "COR-1",
                "type": "add_relationship",
                "suggestion": {"from": "COMP-1", "to": "COMP-2", "type": "realizes"},
                "applied": False,
            }
        ]
        updated, applied_ids = apply_corrections(model, corrections)
        assert len(updated.relationships) == 1
        assert updated.relationships[0].from_id == "COMP-1"
        assert applied_ids == ["COR-1"]

    def test_unapplied_only(self, tmp_path):
        """Already-applied corrections are skipped."""
        comp = Component(id="COMP-1", name="OldName", status=Status.ACTIVE)
        model = _make_model(components=[comp])
        corrections = [
            {"id": "COR-1", "type": "rename", "target": "COMP-1", "suggestion": {"name": "NewName"}, "applied": True}
        ]
        updated, applied_ids = apply_corrections(model, corrections)
        assert updated.entities.components[0].name == "OldName"
        assert applied_ids == []


class TestMarkApplied:
    def test_mark_applied(self, tmp_path):
        store_correction(tmp_path, {"type": "rename", "target": "X"})
        store_correction(tmp_path, {"type": "rename", "target": "Y"})
        mark_applied(tmp_path, ["COR-1"])
        corrections = load_corrections(tmp_path)
        assert corrections[0]["applied"] is True
        assert corrections[1]["applied"] is False
