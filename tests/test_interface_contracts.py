"""Tests for extract_component_interfaces."""
from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    ComponentInterface,
    Entities,
    ModelMeta,
)
from architecture_model.manifest.protocol import (
    DependencyEdge,
    ExportedSymbol,
    SourceGraph,
    SourceUnit,
)
from architecture_model.orchestration.auto_enrich import extract_component_interfaces


def _make_model(components):
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(components=components),
    )


class TestExtractComponentInterfaces:
    def test_cross_boundary_creates_provides_and_requires(self):
        auth = Component(id="COMP-1", name="Auth", status="ACTIVE", files=["src/auth.py"])
        api = Component(id="COMP-2", name="API", status="ACTIVE", files=["src/api.py"])
        model = _make_model([auth, api])

        graph = SourceGraph(
            units=[
                SourceUnit(file="src/auth.py", exports=[ExportedSymbol(name="login")]),
                SourceUnit(file="src/api.py", exports=[ExportedSymbol(name="handle")]),
            ],
            edges=[DependencyEdge(source="src/api.py", target="src/auth.py", symbols=["login"])],
        )

        added = extract_component_interfaces(model, graph)
        assert added == 2
        assert any(i.kind == "requires" and i.target_component == "COMP-1" for i in api.interfaces)
        assert any(i.kind == "provides" and i.target_component == "COMP-2" for i in auth.interfaces)

    def test_internal_edges_ignored(self):
        comp = Component(id="COMP-1", name="Core", status="ACTIVE", files=["a.py", "b.py"])
        model = _make_model([comp])

        graph = SourceGraph(
            units=[
                SourceUnit(file="a.py", exports=[ExportedSymbol(name="foo")]),
                SourceUnit(file="b.py", exports=[ExportedSymbol(name="bar")]),
            ],
            edges=[DependencyEdge(source="a.py", target="b.py")],
        )

        added = extract_component_interfaces(model, graph)
        assert added == 0
        assert comp.interfaces == []

    def test_no_duplicates(self):
        auth = Component(id="COMP-1", name="Auth", status="ACTIVE", files=["auth.py"])
        api = Component(id="COMP-2", name="API", status="ACTIVE", files=["api.py", "api2.py"])
        model = _make_model([auth, api])

        graph = SourceGraph(
            units=[
                SourceUnit(file="auth.py", exports=[ExportedSymbol(name="login")]),
                SourceUnit(file="api.py", exports=[ExportedSymbol(name="h1")]),
                SourceUnit(file="api2.py", exports=[ExportedSymbol(name="h2")]),
            ],
            edges=[
                DependencyEdge(source="api.py", target="auth.py", symbols=["login"]),
                DependencyEdge(source="api2.py", target="auth.py", symbols=["login"]),
            ],
        )

        added = extract_component_interfaces(model, graph)
        # Only one requires and one provides (deduplicated by component pair)
        assert added == 2

    def test_symbols_from_exports_when_edge_has_none(self):
        a = Component(id="C1", name="A", status="ACTIVE", files=["a.py"])
        b = Component(id="C2", name="B", status="ACTIVE", files=["b.py"])
        model = _make_model([a, b])

        graph = SourceGraph(
            units=[
                SourceUnit(file="a.py", exports=[ExportedSymbol(name="x")]),
                SourceUnit(file="b.py", exports=[ExportedSymbol(name="y"), ExportedSymbol(name="z")]),
            ],
            edges=[DependencyEdge(source="a.py", target="b.py", symbols=[])],  # no symbols on edge
        )

        extract_component_interfaces(model, graph)
        # Should fall back to target file's exports
        req = next(i for i in a.interfaces if i.kind == "requires")
        assert "y" in req.symbols
        assert "z" in req.symbols
