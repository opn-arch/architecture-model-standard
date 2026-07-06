"""Tests for complexity scoring and system identification."""

from __future__ import annotations

import pytest

from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
    Symbol,
    SymbolKind,
    System,
)
from architecture_model.core.decomposer import (
    compute_complexity,
    identify_systems,
    SystemCandidate,
    SYSTEM_THRESHOLD,
)


class TestComplexityScorer:
    def test_empty_component_is_zero(self):
        comp = Component(id="comp-x", name="x", status=Status.ACTIVE)
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(components=[comp]),
            relationships=[],
        )
        assert compute_complexity(comp, model) == 0.0

    def test_symbols_contribute(self):
        comp = Component(
            id="comp-x", name="x", status=Status.ACTIVE,
            symbols=[
                Symbol(name="A", kind=SymbolKind.CLASS, members=["m1", "m2"]),
                Symbol(name="B", kind=SymbolKind.CLASS, members=["m1"]),
            ],
        )
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(components=[comp]),
            relationships=[],
        )
        score = compute_complexity(comp, model)
        # 2 symbols * 2.0 + 3 members * 0.3 + 0 functions + 0 deps = 4.9
        assert score == pytest.approx(4.9)

    def test_functions_contribute(self):
        comp = Component(
            id="comp-x", name="x", status=Status.ACTIVE,
            functions=["f1", "f2", "f3", "f4"],
        )
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(components=[comp]),
            relationships=[],
        )
        score = compute_complexity(comp, model)
        # 0 symbols + 0 members + 4 * 0.5 + 0 deps = 2.0
        assert score == pytest.approx(2.0)

    def test_deps_contribute(self):
        comp = Component(id="comp-x", name="x", status=Status.ACTIVE)
        other = Component(id="comp-y", name="y", status=Status.ACTIVE)
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(components=[comp, other]),
            relationships=[
                Relationship(type=RelationType.DEPENDS_ON, from_id="comp-x", to_id="comp-y"),
                Relationship(type=RelationType.DEPENDS_ON, from_id="comp-y", to_id="comp-x"),
            ],
        )
        score = compute_complexity(comp, model)
        # 0 + 0 + 0 + 2 deps * 1.5 = 3.0
        assert score == pytest.approx(3.0)

    def test_simple_component_below_threshold(self):
        comp = Component(
            id="comp-main", name="main", status=Status.ACTIVE,
            symbols=[Symbol(name="App", kind=SymbolKind.CLASS, members=["run"])],
            functions=["main"],
        )
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(components=[comp]),
            relationships=[],
        )
        score = compute_complexity(comp, model)
        assert score < SYSTEM_THRESHOLD

    def test_complex_component_above_threshold(self):
        symbols = [
            Symbol(name=f"C{i}", kind=SymbolKind.CLASS,
                   members=[f"m{j}" for j in range(5)])
            for i in range(8)
        ]
        comp = Component(
            id="comp-core", name="core", status=Status.ACTIVE,
            symbols=symbols, functions=[f"f{i}" for i in range(10)],
        )
        other = Component(id="comp-other", name="other", status=Status.ACTIVE)
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(components=[comp, other]),
            relationships=[
                Relationship(type=RelationType.DEPENDS_ON, from_id="comp-core", to_id="comp-other"),
                Relationship(type=RelationType.DEPENDS_ON, from_id="comp-other", to_id="comp-core"),
            ],
        )
        score = compute_complexity(comp, model)
        # 8*2 + 40*0.3 + 10*0.5 + 2*1.5 = 16 + 12 + 5 + 3 = 36
        assert score > SYSTEM_THRESHOLD
        assert score == pytest.approx(36.0)

    def test_non_depends_on_rels_ignored(self):
        comp = Component(id="comp-x", name="x", status=Status.ACTIVE)
        other = Component(id="comp-y", name="y", status=Status.ACTIVE)
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(components=[comp, other]),
            relationships=[
                Relationship(type=RelationType.CONTAINS, from_id="comp-x", to_id="comp-y"),
            ],
        )
        score = compute_complexity(comp, model)
        assert score == 0.0


class TestIdentifySystems:
    def test_identifies_complex_fblock_group(self):
        comps = [
            Component(
                id=f"comp-{i}", name=f"mod{i}", status=Status.ACTIVE,
                f_block="F1",
                symbols=[
                    Symbol(name=f"C{j}", kind=SymbolKind.CLASS,
                           members=[f"m{k}" for k in range(4)])
                    for j in range(3)
                ],
            )
            for i in range(3)
        ]
        comps.append(Component(
            id="comp-simple", name="simple", status=Status.ACTIVE,
            f_block="F2", symbols=[],
        ))
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(components=comps),
            relationships=[],
        )
        manifest = {"functional_blocks": {"F1": {"name": "Core"}, "F2": {"name": "Utils"}}}
        systems = identify_systems(model, manifest)
        assert len(systems) == 1
        assert systems[0].f_block == "F1"
        assert systems[0].name == "Core"
        assert len(systems[0].component_ids) == 3
        assert systems[0].complexity_score > SYSTEM_THRESHOLD

    def test_simple_model_no_systems(self):
        comp = Component(
            id="comp-a", name="a", status=Status.ACTIVE,
            f_block="F1", symbols=[],
        )
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(components=[comp]),
            relationships=[],
        )
        manifest = {"functional_blocks": {"F1": {"name": "Simple"}}}
        systems = identify_systems(model, manifest)
        assert len(systems) == 0

    def test_components_without_fblock_not_grouped(self):
        # A complex component without f_block should NOT become a system
        comp = Component(
            id="comp-big", name="big", status=Status.ACTIVE,
            f_block="",  # No f_block
            symbols=[Symbol(name=f"C{i}", kind=SymbolKind.CLASS,
                     members=[f"m{j}" for j in range(5)]) for i in range(6)],
        )
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(components=[comp]),
            relationships=[],
        )
        manifest = {"functional_blocks": {}}
        systems = identify_systems(model, manifest)
        assert len(systems) == 0

    def test_multiple_systems_identified(self):
        # Two F-blocks both exceeding threshold
        comps = []
        for fblock in ["F1", "F2"]:
            for i in range(2):
                comps.append(Component(
                    id=f"comp-{fblock}-{i}", name=f"{fblock}_{i}", status=Status.ACTIVE,
                    f_block=fblock,
                    symbols=[Symbol(name=f"Big{i}", kind=SymbolKind.CLASS,
                             members=[f"m{j}" for j in range(8)])
                             for _ in range(3)],
                ))
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(components=comps),
            relationships=[],
        )
        manifest = {"functional_blocks": {"F1": {"name": "Core"}, "F2": {"name": "API"}}}
        systems = identify_systems(model, manifest)
        assert len(systems) == 2
        names = {s.name for s in systems}
        assert "Core" in names
        assert "API" in names

    def test_uses_fblock_id_as_name_when_not_in_manifest(self):
        comp = Component(
            id="comp-x", name="x", status=Status.ACTIVE,
            f_block="F99",
            symbols=[Symbol(name=f"C{i}", kind=SymbolKind.CLASS,
                     members=[f"m{j}" for j in range(5)]) for i in range(6)],
        )
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(components=[comp]),
            relationships=[],
        )
        manifest = {"functional_blocks": {}}  # F99 not listed
        systems = identify_systems(model, manifest)
        assert len(systems) == 1
        assert systems[0].name == "F99"  # Falls back to ID
