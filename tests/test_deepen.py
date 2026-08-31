"""Tests for core/deepen.py — entity-level deepening via scoped pipeline."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Relationship, RelationType,
    Component, Capability, Behavior, Interface, Layer, Status, Priority,
    ActorType, Actor,
)
from architecture_model.core.deepen import resolve_entity_files, deepen_entity


def _make_model():
    return ArchitectureModel(
        meta=ModelMeta(schema_version="2.0", project="test"),
        entities=Entities(
            components=[
                Component(id="COMP-1", name="Parser", status=Status.ACTIVE,
                          files=["src/parser.py", "src/tokenizer.py"]),
                Component(id="COMP-2", name="Validator", status=Status.ACTIVE,
                          files=["src/validator.py"]),
                Component(id="COMP-3", name="Bare", status=Status.ACTIVE),
            ],
            capabilities=[
                Capability(id="CAP-1", name="Parsing", status=Status.ACTIVE),
            ],
            behaviors=[
                Behavior(id="BEH-1", name="Parse File", status=Status.ACTIVE),
            ],
            interfaces=[
                Interface(id="IF-1", name="Parse API", status=Status.ACTIVE,
                          provider="COMP-1"),
            ],
            layers=[
                Layer(id="LAY-1", name="Core", status=Status.ACTIVE,
                      directories=["src/"]),
            ],
        ),
        relationships=[
            Relationship(type=RelationType.REALIZES, from_id="COMP-1", to_id="CAP-1"),
            Relationship(type=RelationType.TRACES_TO, from_id="COMP-1", to_id="BEH-1"),
            Relationship(type=RelationType.EXPOSES, from_id="COMP-1", to_id="IF-1"),
            Relationship(type=RelationType.CONTAINS, from_id="LAY-1", to_id="COMP-1"),
            Relationship(type=RelationType.CONTAINS, from_id="LAY-1", to_id="COMP-2"),
        ],
    )


class TestResolveEntityFiles:
    def test_component_returns_own_files(self):
        files = resolve_entity_files(_make_model(), "COMP-1")
        assert set(files) == {"src/parser.py", "src/tokenizer.py"}

    def test_component_no_files(self):
        files = resolve_entity_files(_make_model(), "COMP-3")
        assert files == []

    def test_capability_via_realizes(self):
        """CAP-1 is realized by COMP-1 → returns COMP-1's files."""
        files = resolve_entity_files(_make_model(), "CAP-1")
        assert set(files) == {"src/parser.py", "src/tokenizer.py"}

    def test_behavior_via_traces_to(self):
        """BEH-1 is traced to COMP-1 → returns COMP-1's files."""
        files = resolve_entity_files(_make_model(), "BEH-1")
        assert set(files) == {"src/parser.py", "src/tokenizer.py"}

    def test_interface_via_component_id(self):
        """IF-1 has component_id=COMP-1 → returns COMP-1's files."""
        files = resolve_entity_files(_make_model(), "IF-1")
        assert set(files) == {"src/parser.py", "src/tokenizer.py"}

    def test_layer_via_contains(self):
        """LAY-1 contains COMP-1 and COMP-2 → union of their files."""
        files = resolve_entity_files(_make_model(), "LAY-1")
        assert set(files) == {"src/parser.py", "src/tokenizer.py", "src/validator.py"}

    def test_unknown_entity_raises(self):
        with pytest.raises(ValueError, match="not found"):
            resolve_entity_files(_make_model(), "COMP-999")


class TestDeepenEntity:
    def test_returns_updated_model(self, tmp_path):
        """deepen_entity returns model (even if pipeline unavailable, merges manifest data)."""
        model = _make_model()
        # Create minimal source files
        src = tmp_path / "src"
        src.mkdir()
        (src / "parser.py").write_text("def parse(x):\n    return x\n")
        (src / "tokenizer.py").write_text("class Tokenizer:\n    pass\n")

        result = deepen_entity(tmp_path, model, "COMP-1")
        # Should return an ArchitectureModel
        assert isinstance(result, ArchitectureModel)
        # COMP-1 should still exist
        comp_ids = [c.id for c in result.entities.components]
        assert "COMP-1" in comp_ids

    def test_no_files_raises(self, tmp_path):
        """Entity with no resolvable files raises ValueError."""
        model = _make_model()
        with pytest.raises(ValueError, match="No source files"):
            deepen_entity(tmp_path, model, "COMP-3")
