"""Tests for Schema v1.3: System entity type and parser support."""

from __future__ import annotations

import yaml
import pytest

from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    Entities,
    Layer,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
    Symbol,
    SymbolKind,
    System,
)
from architecture_model.core.parser import _parse_raw, dump_model


class TestSystemEntity:
    def test_system_has_required_fields(self):
        sys = System(
            id="sys-core", name="Core Engine", status=Status.ACTIVE,
            layer="layer-core", source_block="S1",
            complexity_score=18.5,
            sub_model_ref="systems/core-engine.yaml",
            component_ids=["comp-core", "comp-parser"],
        )
        assert sys.id == "sys-core"
        assert sys.name == "Core Engine"
        assert sys.sub_model_ref == "systems/core-engine.yaml"
        assert sys.complexity_score == 18.5
        assert len(sys.component_ids) == 2

    def test_system_defaults(self):
        sys = System(id="sys-x", name="X", status=Status.ACTIVE)
        assert sys.layer == ""
        assert sys.source_block == ""
        assert sys.complexity_score == 0.0
        assert sys.sub_model_ref == ""
        assert sys.component_ids == []

    def test_entities_has_systems_list(self):
        entities = Entities(systems=[
            System(id="sys-a", name="A", status=Status.ACTIVE)
        ])
        assert len(entities.systems) == 1

    def test_entities_systems_default_empty(self):
        entities = Entities()
        assert entities.systems == []


class TestSystemParsing:
    def test_parse_system_from_yaml(self):
        raw = yaml.safe_load("""
meta:
  schema_version: "1.3"
  project: click
entities:
  systems:
  - id: sys-cmd
    name: Command Engine
    status: ACTIVE
    layer: layer-core
    source_block: S1
    complexity_score: 18.5
    sub_model_ref: systems/command-engine.yaml
    component_ids: [comp-core, comp-parser]
  components: []
relationships: []
""")
        model = _parse_raw(raw)
        assert len(model.entities.systems) == 1
        sys = model.entities.systems[0]
        assert sys.id == "sys-cmd"
        assert sys.name == "Command Engine"
        assert sys.status == Status.ACTIVE
        assert sys.layer == "layer-core"
        assert sys.source_block == "S1"
        assert sys.complexity_score == 18.5
        assert sys.sub_model_ref == "systems/command-engine.yaml"
        assert sys.component_ids == ["comp-core", "comp-parser"]

    def test_parse_model_without_systems(self):
        """v1.2 models (no systems key) should parse fine."""
        raw = yaml.safe_load("""
meta:
  schema_version: "1.2"
  project: test
entities:
  components:
  - id: comp-a
    name: a
    status: ACTIVE
relationships: []
""")
        model = _parse_raw(raw)
        assert model.entities.systems == []
        assert len(model.entities.components) == 1

    def test_dump_system_round_trips(self):
        sys = System(
            id="sys-x", name="X System", status=Status.ACTIVE,
            layer="layer-api",
            source_block="S2",
            sub_model_ref="systems/x.yaml",
            component_ids=["comp-a", "comp-b"],
            complexity_score=12.0,
        )
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(systems=[sys]),
            relationships=[],
        )
        dumped = dump_model(model)
        reparsed = _parse_raw(dumped)
        assert len(reparsed.entities.systems) == 1
        rs = reparsed.entities.systems[0]
        assert rs.id == "sys-x"
        assert rs.name == "X System"
        assert rs.layer == "layer-api"
        assert rs.source_block == "S2"
        assert rs.sub_model_ref == "systems/x.yaml"
        assert rs.component_ids == ["comp-a", "comp-b"]
        assert rs.complexity_score == 12.0

    def test_dump_preserves_systems_and_components(self):
        """Both systems and components coexist."""
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(
                systems=[System(id="sys-a", name="A", status=Status.ACTIVE,
                    component_ids=["comp-x", "comp-y"])],
                components=[Component(id="comp-z", name="z", status=Status.ACTIVE)],
            ),
            relationships=[
                Relationship(type=RelationType.DEPENDS_ON, from_id="sys-a", to_id="comp-z"),
            ],
        )
        dumped = dump_model(model)
        reparsed = _parse_raw(dumped)
        assert len(reparsed.entities.systems) == 1
        assert len(reparsed.entities.components) == 1
        assert len(reparsed.relationships) == 1
