"""Tests for the language-agnostic SourceGraph protocol."""
from architecture_model.manifest.protocol import (
    DependencyEdge,
    ExportedSymbol,
    SourceGraph,
    SourceUnit,
)


class TestSourceUnit:
    def test_export_names(self):
        unit = SourceUnit(
            file="src/foo.py",
            exports=[ExportedSymbol(name="bar"), ExportedSymbol(name="baz", kind="class")],
        )
        assert unit.export_names == ["bar", "baz"]

    def test_defaults(self):
        unit = SourceUnit(file="x.py")
        assert unit.has_content is True
        assert unit.exports == []
        assert unit.language == ""


class TestSourceGraphFromJson:
    def test_canonical_format(self):
        data = {
            "root": "/tmp/repo",
            "language": "typescript",
            "units": [
                {"file": "src/index.ts", "exports": [{"name": "main", "kind": "function"}]},
                {"file": "src/utils.ts", "has_content": True, "exports": ["helper"]},
            ],
            "edges": [{"source": "src/index.ts", "target": "src/utils.ts", "symbols": ["helper"]}],
        }
        g = SourceGraph.from_json(data)
        assert g.root == "/tmp/repo"
        assert g.language == "typescript"
        assert len(g.units) == 2
        assert g.units[0].exports[0].kind == "function"
        assert g.units[1].exports[0].name == "helper"
        assert g.units[1].exports[0].kind == "function"  # default
        assert len(g.edges) == 1
        assert g.edges[0].symbols == ["helper"]

    def test_shorthand_format(self):
        data = {
            "files": [{"file": "main.go", "exports": ["Run"]}],
            "dependencies": [["main.go", "lib.go"]],
        }
        g = SourceGraph.from_json(data)
        assert len(g.units) == 1
        assert g.units[0].file == "main.go"
        assert len(g.edges) == 1
        assert g.edges[0].source == "main.go"
        assert g.edges[0].target == "lib.go"

    def test_empty(self):
        g = SourceGraph.from_json({})
        assert g.units == []
        assert g.edges == []

    def test_language_inherits_to_units(self):
        data = {
            "language": "rust",
            "units": [{"file": "src/lib.rs"}],
        }
        g = SourceGraph.from_json(data)
        assert g.units[0].language == "rust"


class TestSourceGraphToJson:
    def test_roundtrip(self):
        original = SourceGraph(
            root="/repo",
            language="python",
            units=[
                SourceUnit(file="a.py", exports=[ExportedSymbol(name="foo", kind="function", signature="() -> int", doc="Does foo")]),
            ],
            edges=[DependencyEdge(source="a.py", target="b.py", symbols=["bar"])],
        )
        data = original.to_json()
        restored = SourceGraph.from_json(data)
        assert len(restored.units) == 1
        assert restored.units[0].file == "a.py"
        assert restored.units[0].exports[0].signature == "() -> int"
        assert restored.edges[0].symbols == ["bar"]


class TestSourceGraphFromManifest:
    def test_converts_modules_and_interfaces(self):
        from dataclasses import dataclass, field as dc_field

        # Minimal mock of Manifest types
        @dataclass
        class FnInfo:
            name: str
            signature: str = ""
            docstring: str = ""

        @dataclass
        class ClsInfo:
            name: str
            method_details: list = dc_field(default_factory=list)

        @dataclass
        class ModInfo:
            file: str
            functions: list = dc_field(default_factory=list)
            classes: list = dc_field(default_factory=list)

        @dataclass
        class Edge:
            source: str
            target: str

        @dataclass
        class FakeManifest:
            modules: list = dc_field(default_factory=list)
            interfaces: list = dc_field(default_factory=list)

        manifest = FakeManifest(
            modules=[
                ModInfo(file="src/core.py", functions=[FnInfo(name="run", signature="(x: int) -> bool", docstring="Run the thing\nMore details")], classes=[ClsInfo(name="Engine")]),
                ModInfo(file="src/_internal.py", functions=[FnInfo(name="_helper")], classes=[]),
            ],
            interfaces=[Edge(source="src/core.py", target="src/_internal.py")],
        )
        g = SourceGraph.from_manifest(manifest)
        assert len(g.units) == 2
        assert g.language == "python"
        # Public function exported
        core_unit = g.units[0]
        assert any(e.name == "run" for e in core_unit.exports)
        assert any(e.name == "Engine" and e.kind == "class" for e in core_unit.exports)
        # Private function NOT exported
        assert not any(e.name == "_helper" for e in g.units[1].exports)
        # Edge preserved
        assert len(g.edges) == 1
        assert g.edges[0].source == "src/core.py"


class TestGroupSourceGraph:
    def test_groups_by_subdirectory(self):
        from architecture_model.manifest.grouping import group_source_graph

        graph = SourceGraph(
            units=[
                SourceUnit(file="src/main.py", exports=[ExportedSymbol(name="main")]),
                SourceUnit(file="src/auth/login.py", exports=[ExportedSymbol(name="login")]),
                SourceUnit(file="src/auth/logout.py", exports=[ExportedSymbol(name="logout")]),
                SourceUnit(file="src/api/routes.py", exports=[ExportedSymbol(name="Router", kind="class")]),
            ],
            edges=[DependencyEdge(source="src/auth/login.py", target="src/auth/logout.py")],
        )
        groups = group_source_graph(graph)
        assert len(groups) >= 2
        # Auth files should be grouped together (subdirectory affinity — locked as subdir of src/)
        auth_group = next((g for g in groups if "src/auth/login.py" in g.modules), None)
        assert auth_group is not None
        assert "src/auth/logout.py" in auth_group.modules

    def test_trivial_units_excluded(self):
        from architecture_model.manifest.grouping import group_source_graph

        graph = SourceGraph(
            units=[
                SourceUnit(file="src/main.py", exports=[ExportedSymbol(name="run")]),
                SourceUnit(file="src/empty.py", has_content=True, exports=[]),  # no exports = trivial
            ],
            edges=[],
        )
        groups = group_source_graph(graph)
        all_files = [f for g in groups for f in g.modules]
        assert "src/main.py" in all_files
        assert "src/empty.py" not in all_files
