"""WP-10: Model changelog generation."""
from architecture_model.core.changelog import generate_changelog
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Component, Status,
)


class TestChangelog:
    def test_detects_added_component(self):
        old = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(), relationships=[],
        )
        new = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-02"),
            entities=Entities(components=[
                Component(id="COMP-1", name="New", status=Status.ACTIVE),
            ]),
            relationships=[],
        )
        log = generate_changelog(old, new)
        assert "Added" in log
        assert "COMP-1" in log

    def test_detects_removed_component(self):
        old = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(components=[
                Component(id="COMP-1", name="Old", status=Status.ACTIVE),
            ]),
            relationships=[],
        )
        new = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-02"),
            entities=Entities(), relationships=[],
        )
        log = generate_changelog(old, new)
        assert "Removed" in log
        assert "COMP-1" in log
