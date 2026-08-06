"""Tests for model-aware recursive manifest generation."""
from architecture_model.core.types import (
    ArchitectureModel, Component, Entities, ModelMeta, Status,
)
from architecture_model.manifest.recursive import _block_id_to_component_id


def _make_model(components):
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="2.0"),
        entities=Entities(components=components),
        relationships=[],
    )


class TestComponentIdResolution:
    def test_resolves_from_model_by_source_block(self):
        model = _make_model([
            Component(id="COMP-MY-PARSER", name="Parser", source_block="S1", status=Status.ACTIVE),
        ])
        class FakeConfig:
            source_block_dict = {"S1": {"name": "Cli"}}
        assert _block_id_to_component_id("S1", FakeConfig(), model) == "COMP-MY-PARSER"

    def test_falls_back_to_convention_without_model(self):
        class FakeConfig:
            source_block_dict = {"S1": {"name": "Cli"}}
        assert _block_id_to_component_id("S1", FakeConfig(), None) == "COMP-CLI"

    def test_falls_back_when_no_match(self):
        model = _make_model([
            Component(id="COMP-OTHER", name="Other", source_block="S99", status=Status.ACTIVE),
        ])
        class FakeConfig:
            source_block_dict = {"S1": {"name": "Cli"}}
        assert _block_id_to_component_id("S1", FakeConfig(), model) == "COMP-CLI"

    def test_multiple_components_returns_first(self):
        model = _make_model([
            Component(id="COMP-CORE", name="Core", source_block="S3", status=Status.ACTIVE),
            Component(id="COMP-VIZ", name="Viz", source_block="S3", status=Status.ACTIVE),
        ])
        class FakeConfig:
            source_block_dict = {"S3": {"name": "Core"}}
        assert _block_id_to_component_id("S3", FakeConfig(), model) == "COMP-CORE"
