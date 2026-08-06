"""Tests for model compaction."""
import pytest
from architecture_model.orchestration.compaction import compact_for_storage
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Component, Behavior,
    Relationship, RelationType,
)

@pytest.fixture
def full_model():
    behaviors = [
        Behavior(id="BEH-1", name="create_user", status="ACTIVE"),
        Behavior(id="BEH-2", name="get_user", status="ACTIVE"),
        Behavior(id="BEH-3", name="delete_user", status="ACTIVE"),
        Behavior(id="BEH-4", name="list_logs", status="ACTIVE"),
        Behavior(id="UC-1", name="create_user (end-to-end)", status="ACTIVE",
                 steps=["create_user", "get_user"]),
    ]
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(
            components=[
                Component(id="COMP-1", name="Users", status="ACTIVE"),
                Component(id="COMP-2", name="Logs", status="ACTIVE"),
            ],
            behaviors=behaviors,
        ),
        relationships=[
            Relationship(type=RelationType.REALIZES, from_id="COMP-1", to_id="BEH-1"),
            Relationship(type=RelationType.REALIZES, from_id="COMP-1", to_id="BEH-2"),
            Relationship(type=RelationType.REALIZES, from_id="COMP-1", to_id="BEH-3"),
            Relationship(type=RelationType.REALIZES, from_id="COMP-2", to_id="BEH-4"),
            Relationship(type=RelationType.CONTAINS, from_id="UC-1", to_id="BEH-1"),
            Relationship(type=RelationType.CONTAINS, from_id="UC-1", to_id="BEH-2"),
            Relationship(type=RelationType.DEPENDS_ON, from_id="COMP-1", to_id="COMP-2"),
        ],
    )

class TestCompaction:
    def test_reduces_behavior_count(self, full_model):
        compact, offloaded = compact_for_storage(full_model)
        assert len(compact.entities.behaviors) < len(full_model.entities.behaviors)

    def test_keeps_use_cases(self, full_model):
        compact, offloaded = compact_for_storage(full_model)
        uc_ids = {b.id for b in compact.entities.behaviors if b.id.startswith("UC-")}
        assert "UC-1" in uc_ids

    def test_creates_summary_behaviors(self, full_model):
        compact, offloaded = compact_for_storage(full_model)
        summaries = [b for b in compact.entities.behaviors if b.id.startswith("BEH-SUMMARY")]
        assert len(summaries) >= 1

    def test_offloaded_contains_leaf_behaviors(self, full_model):
        compact, offloaded = compact_for_storage(full_model)
        assert len(offloaded) > 0
        all_offloaded = [b for behs in offloaded.values() for b in behs]
        assert any(b.id == "BEH-1" for b in all_offloaded)

    def test_preserves_components(self, full_model):
        compact, offloaded = compact_for_storage(full_model)
        assert len(compact.entities.components) == len(full_model.entities.components)

    def test_preserves_non_behavior_relationships(self, full_model):
        compact, offloaded = compact_for_storage(full_model)
        uses_rels = [r for r in compact.relationships
                     if (r.type.value if hasattr(r.type, 'value') else str(r.type)) == "depends-on"]
        assert len(uses_rels) == 1  # COMP-1 depends_on COMP-2 preserved

    def test_removes_offloaded_realizes_rels(self, full_model):
        compact, offloaded = compact_for_storage(full_model)
        realizes = [r for r in compact.relationships
                    if (r.type.value if hasattr(r.type, 'value') else str(r.type)) == "realizes"]
        # Should not have realizes pointing to offloaded BEH-1, BEH-2, etc.
        offloaded_ids = {b.id for behs in offloaded.values() for b in behs}
        for r in realizes:
            assert r.to_id not in offloaded_ids

    def test_compact_summary_names_are_descriptive(self, full_model):
        """Summary behavior names should NOT contain ': N behaviors' pattern."""
        compact, _ = compact_for_storage(full_model)
        summaries = [b for b in compact.entities.behaviors if b.id.startswith("BEH-SUMMARY")]
        assert len(summaries) >= 1
        for s in summaries:
            assert "behaviors" not in s.name, f"Summary name is not descriptive: {s.name}"
            assert s.name.endswith("Operations"), f"Summary name should end with 'Operations': {s.name}"
            assert s.description is not None, "Summary should have a description"
            assert "Key operations:" in s.description
