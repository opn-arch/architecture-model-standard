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
    decompose_model,
    DecompositionResult,
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
    def test_identifies_complex_source_block_group(self):
        comps = [
            Component(
                id=f"comp-{i}", name=f"mod{i}", status=Status.ACTIVE,
                source_block="S1",
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
            source_block="S2", symbols=[],
        ))
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(components=comps),
            relationships=[],
        )
        manifest = {"functional_blocks": {"S1": {"name": "Core"}, "S2": {"name": "Utils"}}}
        systems = identify_systems(model, manifest)
        assert len(systems) == 1
        assert systems[0].source_block == "S1"
        assert systems[0].name == "Core"
        assert len(systems[0].component_ids) == 3
        assert systems[0].complexity_score > SYSTEM_THRESHOLD

    def test_simple_model_no_systems(self):
        comp = Component(
            id="comp-a", name="a", status=Status.ACTIVE,
            source_block="S1", symbols=[],
        )
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(components=[comp]),
            relationships=[],
        )
        manifest = {"functional_blocks": {"S1": {"name": "Simple"}}}
        systems = identify_systems(model, manifest)
        assert len(systems) == 0

    def test_components_without_source_block_not_grouped(self):
        # A complex component without source_block should NOT become a system
        comp = Component(
            id="comp-big", name="big", status=Status.ACTIVE,
            source_block="",  # No source_block
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
        for source_block in ["S1", "S2"]:
            for i in range(2):
                comps.append(Component(
                    id=f"comp-{source_block}-{i}", name=f"{source_block}_{i}", status=Status.ACTIVE,
                    source_block=source_block,
                    symbols=[Symbol(name=f"Big{i}", kind=SymbolKind.CLASS,
                             members=[f"m{j}" for j in range(8)])
                             for _ in range(3)],
                ))
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(components=comps),
            relationships=[],
        )
        manifest = {"functional_blocks": {"S1": {"name": "Core"}, "S2": {"name": "API"}}}
        systems = identify_systems(model, manifest)
        assert len(systems) == 2
        names = {s.name for s in systems}
        assert "Core" in names
        assert "API" in names

    def test_uses_source_block_id_as_name_when_not_in_manifest(self):
        comp = Component(
            id="comp-x", name="x", status=Status.ACTIVE,
            source_block="S99",
            symbols=[Symbol(name=f"C{i}", kind=SymbolKind.CLASS,
                     members=[f"m{j}" for j in range(5)]) for i in range(6)],
        )
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(components=[comp]),
            relationships=[],
        )
        manifest = {"functional_blocks": {}}  # S99 not listed
        systems = identify_systems(model, manifest)
        assert len(systems) == 1
        assert systems[0].name == "S99"  # Falls back to ID


class TestDecomposeModel:
    def _make_complex_model(self):
        """Model with S1 (3 complex components) and S2 (1 simple)."""
        complex_comps = [
            Component(
                id=f"comp-c{i}", name=f"c{i}", status=Status.ACTIVE,
                source_block="S1",
                symbols=[
                    Symbol(name=f"Big{i}_{j}", kind=SymbolKind.CLASS,
                           members=[f"m{k}" for k in range(6)])
                    for j in range(2)
                ],
                functions=[f"func_{i}_{k}" for k in range(3)],
            )
            for i in range(3)
        ]
        simple_comp = Component(
            id="comp-simple", name="simple", status=Status.ACTIVE,
            source_block="S2",
        )
        all_comps = complex_comps + [simple_comp]

        # Intra-system rel: comp-c0 → comp-c1 (both in S1)
        # Inter-system rel: comp-c0 → comp-simple (S1 → S2)
        rels = [
            Relationship(type=RelationType.DEPENDS_ON, from_id="comp-c0", to_id="comp-c1",
                         imports=["ClassB"]),
            Relationship(type=RelationType.DEPENDS_ON, from_id="comp-c0", to_id="comp-simple"),
            Relationship(type=RelationType.DEPENDS_ON, from_id="comp-c2", to_id="comp-simple"),
        ]

        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test-proj"),
            entities=Entities(components=all_comps),
            relationships=rels,
        )
        manifest = {"functional_blocks": {"S1": {"name": "Core Engine"}, "S2": {"name": "Utils"}}}
        return model, manifest

    def test_decompose_creates_system(self):
        model, manifest = self._make_complex_model()
        result = decompose_model(model, manifest)

        assert isinstance(result, DecompositionResult)
        assert len(result.top_level.entities.systems) == 1
        sys = result.top_level.entities.systems[0]
        assert sys.name == "Core Engine"
        assert sys.source_block == "S1"
        assert set(sys.component_ids) == {"comp-c0", "comp-c1", "comp-c2"}
        assert "systems/" in sys.sub_model_ref
        assert sys.complexity_score > SYSTEM_THRESHOLD

    def test_decompose_removes_promoted_components(self):
        model, manifest = self._make_complex_model()
        result = decompose_model(model, manifest)

        # Only simple_comp remains in top-level components
        top_comp_ids = [c.id for c in result.top_level.entities.components]
        assert "comp-simple" in top_comp_ids
        assert "comp-c0" not in top_comp_ids
        assert "comp-c1" not in top_comp_ids

    def test_decompose_sub_model_has_components(self):
        model, manifest = self._make_complex_model()
        result = decompose_model(model, manifest)

        sys = result.top_level.entities.systems[0]
        sub = result.sub_models[sys.id]
        sub_comp_ids = [c.id for c in sub.entities.components]
        assert "comp-c0" in sub_comp_ids
        assert "comp-c1" in sub_comp_ids
        assert "comp-c2" in sub_comp_ids
        assert "comp-simple" not in sub_comp_ids

    def test_intra_system_rels_in_sub_model(self):
        model, manifest = self._make_complex_model()
        result = decompose_model(model, manifest)

        sys = result.top_level.entities.systems[0]
        sub = result.sub_models[sys.id]
        sub_rels = [(r.from_id, r.to_id) for r in sub.relationships]
        assert ("comp-c0", "comp-c1") in sub_rels

    def test_inter_system_rels_promoted(self):
        model, manifest = self._make_complex_model()
        result = decompose_model(model, manifest)

        sys = result.top_level.entities.systems[0]
        # comp-c0 → comp-simple and comp-c2 → comp-simple
        # Both should be promoted as sys → comp-simple (deduplicated)
        top_rels = [(r.from_id, r.to_id) for r in result.top_level.relationships
                    if r.type == RelationType.DEPENDS_ON]
        assert (sys.id, "comp-simple") in top_rels

    def test_inter_system_rels_deduplicated(self):
        model, manifest = self._make_complex_model()
        result = decompose_model(model, manifest)

        sys = result.top_level.entities.systems[0]
        # Two rels (comp-c0→simple, comp-c2→simple) should merge into one
        deps_to_simple = [r for r in result.top_level.relationships
                          if r.from_id == sys.id and r.to_id == "comp-simple"]
        assert len(deps_to_simple) == 1

    def test_sub_model_meta_has_system_name(self):
        model, manifest = self._make_complex_model()
        result = decompose_model(model, manifest)

        sys = result.top_level.entities.systems[0]
        sub = result.sub_models[sys.id]
        assert sub.meta.system == "Core Engine"
        assert sub.meta.project == "test-proj"

    def test_no_systems_returns_unchanged(self):
        """When no F-block exceeds threshold, model returned as-is."""
        comp = Component(
            id="comp-a", name="a", status=Status.ACTIVE,
            source_block="S1",
        )
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.3", project="test"),
            entities=Entities(components=[comp]),
            relationships=[],
        )
        manifest = {"functional_blocks": {"S1": {"name": "Simple"}}}
        result = decompose_model(model, manifest)

        assert len(result.top_level.entities.systems) == 0
        assert len(result.top_level.entities.components) == 1
        assert result.sub_models == {}
