"""Tests for `architecture-model repair` — backfill missing entities from subsidiary models."""

import yaml
from pathlib import Path

import pytest

from architecture_model.core.parser import load_model, save_model
from architecture_model.core.repair import find_dangling_ids, backfill_from_source, repair_model
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Relationship, RelationType,
    Component, Capability, Behavior, Interface, Status,
)


def _make_model_with_dangles():
    """Model with relationships referencing non-existent entities."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="2.0", project="test"),
        entities=Entities(
            components=[Component(id="COMP-1", name="Parser", status=Status.ACTIVE)],
            capabilities=[Capability(id="CAP-1", name="Parsing", status=Status.ACTIVE)],
            behaviors=[Behavior(id="BEH-1", name="Parse File", status=Status.ACTIVE)],
        ),
        relationships=[
            Relationship(type=RelationType.REALIZES, from_id="COMP-1", to_id="CAP-1"),
            # Dangling: BEH-99 and BEH-100 don't exist
            Relationship(type=RelationType.TRIGGERS, from_id="BEH-1", to_id="BEH-99"),
            Relationship(type=RelationType.CONTAINS, from_id="BEH-1", to_id="BEH-100"),
            # Dangling: CAP-50 doesn't exist
            Relationship(type=RelationType.REALIZES, from_id="COMP-1", to_id="CAP-50"),
            # Dangling: COMP-99 doesn't exist
            Relationship(type=RelationType.DEPENDS_ON, from_id="COMP-1", to_id="COMP-99"),
        ],
    )


def _make_source_model():
    """Source model containing the missing entities."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="2.0", project="test-full"),
        entities=Entities(
            behaviors=[
                Behavior(id="BEH-99", name="Tokenize", status=Status.ACTIVE,
                         steps=["read_chars", "emit_tokens"]),
                Behavior(id="BEH-100", name="Build AST", status=Status.ACTIVE),
                Behavior(id="BEH-200", name="Unrelated", status=Status.ACTIVE),
            ],
            capabilities=[
                Capability(id="CAP-50", name="Tokenization", status=Status.ACTIVE),
            ],
            components=[
                Component(id="COMP-99", name="Lexer", status=Status.ACTIVE),
            ],
        ),
        relationships=[],
    )


class TestFindDanglingIds:
    def test_finds_missing_from_ids(self):
        model = _make_model_with_dangles()
        dangling = find_dangling_ids(model)
        assert "BEH-99" in dangling
        assert "BEH-100" in dangling
        assert "CAP-50" in dangling
        assert "COMP-99" in dangling

    def test_existing_ids_not_dangling(self):
        model = _make_model_with_dangles()
        dangling = find_dangling_ids(model)
        assert "COMP-1" not in dangling
        assert "CAP-1" not in dangling
        assert "BEH-1" not in dangling

    def test_no_dangles_returns_empty(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.0", project="clean"),
            entities=Entities(
                components=[Component(id="COMP-1", name="A", status=Status.ACTIVE)],
            ),
            relationships=[],
        )
        assert find_dangling_ids(model) == set()


class TestBackfillFromSource:
    def test_backfills_missing_behaviors(self):
        model = _make_model_with_dangles()
        source = _make_source_model()
        filled = backfill_from_source(model, source)
        beh_ids = {b.id for b in filled.entities.behaviors}
        assert "BEH-99" in beh_ids
        assert "BEH-100" in beh_ids

    def test_backfilled_entity_has_fields(self):
        model = _make_model_with_dangles()
        source = _make_source_model()
        filled = backfill_from_source(model, source)
        beh99 = next(b for b in filled.entities.behaviors if b.id == "BEH-99")
        assert beh99.name == "Tokenize"
        assert beh99.steps == ["read_chars", "emit_tokens"]

    def test_backfills_missing_capabilities(self):
        model = _make_model_with_dangles()
        source = _make_source_model()
        filled = backfill_from_source(model, source)
        cap_ids = {c.id for c in filled.entities.capabilities}
        assert "CAP-50" in cap_ids

    def test_backfills_missing_components(self):
        model = _make_model_with_dangles()
        source = _make_source_model()
        filled = backfill_from_source(model, source)
        comp_ids = {c.id for c in filled.entities.components}
        assert "COMP-99" in comp_ids

    def test_does_not_duplicate_existing(self):
        model = _make_model_with_dangles()
        source = _make_source_model()
        filled = backfill_from_source(model, source)
        comp_1_count = sum(1 for c in filled.entities.components if c.id == "COMP-1")
        assert comp_1_count == 1

    def test_unresolved_ids_not_added(self):
        """BEH-200 exists in source but isn't dangling — shouldn't be added."""
        model = _make_model_with_dangles()
        source = _make_source_model()
        filled = backfill_from_source(model, source)
        beh_ids = {b.id for b in filled.entities.behaviors}
        assert "BEH-200" not in beh_ids

    def test_returns_stats(self):
        model = _make_model_with_dangles()
        source = _make_source_model()
        filled, stats = backfill_from_source(model, source, return_stats=True)
        assert stats["backfilled"] >= 4
        assert stats["still_dangling"] == 0


class TestRepairModel:
    def test_repair_with_source_files(self, tmp_path):
        """End-to-end: repair model using source model files."""
        model = _make_model_with_dangles()
        model_path = tmp_path / ".architecture-model.yaml"
        save_model(model, model_path)

        source = _make_source_model()
        source_path = tmp_path / ".architecture-models" / "full-model.yaml"
        source_path.parent.mkdir(parents=True)
        save_model(source, source_path)

        result = repair_model(model_path, source_paths=[source_path])
        assert result["backfilled"] >= 4
        assert result["score_before"] == 0 or result["score_before"] is not None

        # Reload and verify
        repaired = load_model(model_path)
        beh_ids = {b.id for b in repaired.entities.behaviors}
        assert "BEH-99" in beh_ids
        assert "BEH-100" in beh_ids

    def test_repair_auto_discovers_sources(self, tmp_path):
        """repair_model with no source_paths auto-discovers .architecture-models/."""
        model = _make_model_with_dangles()
        model_path = tmp_path / ".architecture-model.yaml"
        save_model(model, model_path)

        source = _make_source_model()
        # Place in standard location
        source_path = tmp_path / ".architecture-models" / "full-model.yaml"
        source_path.parent.mkdir(parents=True)
        save_model(source, source_path)

        result = repair_model(model_path)
        assert result["backfilled"] >= 4
