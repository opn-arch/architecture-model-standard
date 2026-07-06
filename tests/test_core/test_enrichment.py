"""Tests for enrich_from_manifest() — mechanical correction from AST ground truth."""

from __future__ import annotations

from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    ComponentKind,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
    Symbol,
    SymbolKind,
)
from architecture_model.core.merger import enrich_from_manifest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_model(components: list[Component], relationships: list[Relationship] | None = None) -> ArchitectureModel:
    """Build a minimal model with given components."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.0", project="test"),
        entities=Entities(components=components),
        relationships=relationships or [],
    )


def _make_manifest(modules: list[dict], interfaces: list[dict] | None = None) -> dict:
    """Build a minimal manifest dict."""
    return {
        "modules": modules,
        "interfaces": interfaces or [],
    }


# ---------------------------------------------------------------------------
# Test 1: Basic matching — component name matches module filename stem
# ---------------------------------------------------------------------------


class TestBasicMatching:
    def test_match_by_component_name(self):
        """Component name 'parser' matches module file 'dotenv/parser.py'."""
        comp = Component(
            id="comp-parser", name="parser", status=Status.ACTIVE, kind=ComponentKind.LIBRARY
        )
        manifest = _make_manifest(modules=[
            {
                "file": "dotenv/parser.py",
                "name": "parser",
                "classes": [
                    {"name": "Parser", "bases": ["object"], "methods": ["parse_stream"], "is_abstract": False, "decorators": []},
                ],
                "functions": ["make_parser(stream) -> Parser"],
                "imports_detailed": [],
            }
        ])
        model = _make_model([comp])
        result = enrich_from_manifest(model, manifest)

        assert len(result.entities.components[0].symbols) == 1
        assert result.entities.components[0].symbols[0].name == "Parser"

    def test_match_by_id_stem(self):
        """Component id 'comp-tokenizer' (stem='tokenizer') matches 'src/tokenizer.py'."""
        comp = Component(
            id="comp-tokenizer", name="Tokenizer Module", status=Status.ACTIVE, kind=ComponentKind.LIBRARY
        )
        manifest = _make_manifest(modules=[
            {
                "file": "src/tokenizer.py",
                "name": "tokenizer",
                "classes": [
                    {"name": "Tokenizer", "bases": [], "methods": ["tokenize"], "is_abstract": False, "decorators": []},
                ],
                "functions": [],
                "imports_detailed": [],
            }
        ])
        model = _make_model([comp])
        result = enrich_from_manifest(model, manifest)

        assert len(result.entities.components[0].symbols) == 1
        assert result.entities.components[0].symbols[0].name == "Tokenizer"

    def test_no_match(self):
        """Component with no matching module remains unchanged."""
        comp = Component(
            id="comp-unrelated", name="unrelated", status=Status.ACTIVE,
            kind=ComponentKind.LIBRARY, symbols=[], functions=[]
        )
        manifest = _make_manifest(modules=[
            {
                "file": "dotenv/parser.py",
                "name": "parser",
                "classes": [{"name": "Parser", "bases": [], "methods": [], "is_abstract": False, "decorators": []}],
                "functions": [],
                "imports_detailed": [],
            }
        ])
        model = _make_model([comp])
        result = enrich_from_manifest(model, manifest)

        assert result.entities.components[0].symbols == []
        assert result.entities.components[0].functions == []


# ---------------------------------------------------------------------------
# Test 2: Symbol kind inference
# ---------------------------------------------------------------------------


class TestSymbolKindInference:
    def test_dataclass(self):
        """Class with 'dataclass' decorator → SymbolKind.DATACLASS."""
        comp = Component(id="comp-models", name="models", status=Status.ACTIVE, kind=ComponentKind.LIBRARY)
        manifest = _make_manifest(modules=[
            {
                "file": "models.py",
                "name": "models",
                "classes": [
                    {"name": "Token", "bases": [], "methods": ["__init__"], "is_abstract": False, "decorators": ["dataclass"]},
                ],
                "functions": [],
                "imports_detailed": [],
            }
        ])
        model = _make_model([comp])
        result = enrich_from_manifest(model, manifest)

        sym = result.entities.components[0].symbols[0]
        assert sym.kind == SymbolKind.DATACLASS

    def test_exception(self):
        """Class with 'Exception' in bases → SymbolKind.EXCEPTION."""
        comp = Component(id="comp-errors", name="errors", status=Status.ACTIVE, kind=ComponentKind.LIBRARY)
        manifest = _make_manifest(modules=[
            {
                "file": "errors.py",
                "name": "errors",
                "classes": [
                    {"name": "ParseError", "bases": ["Exception"], "methods": [], "is_abstract": False, "decorators": []},
                ],
                "functions": [],
                "imports_detailed": [],
            }
        ])
        model = _make_model([comp])
        result = enrich_from_manifest(model, manifest)

        sym = result.entities.components[0].symbols[0]
        assert sym.kind == SymbolKind.EXCEPTION

    def test_exception_from_error_base(self):
        """Class with 'ValueError' (contains 'Error') in bases → SymbolKind.EXCEPTION."""
        comp = Component(id="comp-errors", name="errors", status=Status.ACTIVE, kind=ComponentKind.LIBRARY)
        manifest = _make_manifest(modules=[
            {
                "file": "errors.py",
                "name": "errors",
                "classes": [
                    {"name": "ValidationError", "bases": ["ValueError"], "methods": [], "is_abstract": False, "decorators": []},
                ],
                "functions": [],
                "imports_detailed": [],
            }
        ])
        model = _make_model([comp])
        result = enrich_from_manifest(model, manifest)

        sym = result.entities.components[0].symbols[0]
        assert sym.kind == SymbolKind.EXCEPTION

    def test_protocol_from_is_abstract(self):
        """Class with is_abstract=True → SymbolKind.PROTOCOL."""
        comp = Component(id="comp-base", name="base", status=Status.ACTIVE, kind=ComponentKind.LIBRARY)
        manifest = _make_manifest(modules=[
            {
                "file": "base.py",
                "name": "base",
                "classes": [
                    {"name": "BaseHandler", "bases": ["ABC"], "methods": ["handle"], "is_abstract": True, "decorators": []},
                ],
                "functions": [],
                "imports_detailed": [],
            }
        ])
        model = _make_model([comp])
        result = enrich_from_manifest(model, manifest)

        sym = result.entities.components[0].symbols[0]
        assert sym.kind == SymbolKind.PROTOCOL

    def test_protocol_from_abc_base(self):
        """Class with 'ABC' in bases → SymbolKind.PROTOCOL."""
        comp = Component(id="comp-base", name="base", status=Status.ACTIVE, kind=ComponentKind.LIBRARY)
        manifest = _make_manifest(modules=[
            {
                "file": "base.py",
                "name": "base",
                "classes": [
                    {"name": "AbstractParser", "bases": ["ABC"], "methods": ["parse"], "is_abstract": False, "decorators": []},
                ],
                "functions": [],
                "imports_detailed": [],
            }
        ])
        model = _make_model([comp])
        result = enrich_from_manifest(model, manifest)

        sym = result.entities.components[0].symbols[0]
        assert sym.kind == SymbolKind.PROTOCOL

    def test_protocol_from_protocol_base(self):
        """Class with 'Protocol' in bases → SymbolKind.PROTOCOL."""
        comp = Component(id="comp-base", name="base", status=Status.ACTIVE, kind=ComponentKind.LIBRARY)
        manifest = _make_manifest(modules=[
            {
                "file": "base.py",
                "name": "base",
                "classes": [
                    {"name": "Renderable", "bases": ["Protocol"], "methods": ["render"], "is_abstract": False, "decorators": []},
                ],
                "functions": [],
                "imports_detailed": [],
            }
        ])
        model = _make_model([comp])
        result = enrich_from_manifest(model, manifest)

        sym = result.entities.components[0].symbols[0]
        assert sym.kind == SymbolKind.PROTOCOL

    def test_regular_class(self):
        """Class with no special markers → SymbolKind.CLASS."""
        comp = Component(id="comp-utils", name="utils", status=Status.ACTIVE, kind=ComponentKind.LIBRARY)
        manifest = _make_manifest(modules=[
            {
                "file": "utils.py",
                "name": "utils",
                "classes": [
                    {"name": "Helper", "bases": ["object"], "methods": ["run", "stop"], "is_abstract": False, "decorators": []},
                ],
                "functions": [],
                "imports_detailed": [],
            }
        ])
        model = _make_model([comp])
        result = enrich_from_manifest(model, manifest)

        sym = result.entities.components[0].symbols[0]
        assert sym.kind == SymbolKind.CLASS


# ---------------------------------------------------------------------------
# Test 3: Symbol members and supers filtering
# ---------------------------------------------------------------------------


class TestSymbolMembers:
    def test_public_methods_kept(self):
        """Public methods are included in members."""
        comp = Component(id="comp-parser", name="parser", status=Status.ACTIVE, kind=ComponentKind.LIBRARY)
        manifest = _make_manifest(modules=[
            {
                "file": "parser.py",
                "name": "parser",
                "classes": [
                    {"name": "Parser", "bases": ["object"], "methods": ["parse", "reset", "__init__", "__repr__", "_internal"], "is_abstract": False, "decorators": []},
                ],
                "functions": [],
                "imports_detailed": [],
            }
        ])
        model = _make_model([comp])
        result = enrich_from_manifest(model, manifest)

        sym = result.entities.components[0].symbols[0]
        # Keep public + __init__, skip dunder (__repr__) and private (_internal)
        assert "__init__" in sym.members
        assert "parse" in sym.members
        assert "reset" in sym.members
        assert "__repr__" not in sym.members
        assert "_internal" not in sym.members

    def test_supers_filter_object(self):
        """'object' is filtered from supers list."""
        comp = Component(id="comp-parser", name="parser", status=Status.ACTIVE, kind=ComponentKind.LIBRARY)
        manifest = _make_manifest(modules=[
            {
                "file": "parser.py",
                "name": "parser",
                "classes": [
                    {"name": "Parser", "bases": ["object", "Iterable"], "methods": [], "is_abstract": False, "decorators": []},
                ],
                "functions": [],
                "imports_detailed": [],
            }
        ])
        model = _make_model([comp])
        result = enrich_from_manifest(model, manifest)

        sym = result.entities.components[0].symbols[0]
        assert "object" not in sym.supers
        assert "Iterable" in sym.supers


# ---------------------------------------------------------------------------
# Test 4: Function name extraction from signatures
# ---------------------------------------------------------------------------


class TestFunctionExtraction:
    def test_extract_function_name(self):
        """Extract function name from signature string."""
        comp = Component(id="comp-parser", name="parser", status=Status.ACTIVE, kind=ComponentKind.LIBRARY)
        manifest = _make_manifest(modules=[
            {
                "file": "parser.py",
                "name": "parser",
                "classes": [],
                "functions": ["make_parser(stream) -> Parser", "read_line()", "validate(data, strict=False) -> bool"],
                "imports_detailed": [],
            }
        ])
        model = _make_model([comp])
        result = enrich_from_manifest(model, manifest)

        assert result.entities.components[0].functions == ["make_parser", "read_line", "validate"]

    def test_empty_functions(self):
        """Module with no functions produces empty list."""
        comp = Component(id="comp-models", name="models", status=Status.ACTIVE, kind=ComponentKind.LIBRARY)
        manifest = _make_manifest(modules=[
            {
                "file": "models.py",
                "name": "models",
                "classes": [],
                "functions": [],
                "imports_detailed": [],
            }
        ])
        model = _make_model([comp])
        result = enrich_from_manifest(model, manifest)

        assert result.entities.components[0].functions == []


# ---------------------------------------------------------------------------
# Test 5: Relationship import enrichment
# ---------------------------------------------------------------------------


class TestRelationshipImports:
    def test_enrich_depends_on_with_imports(self):
        """depends-on relationship gets imports from manifest imports_detailed."""
        comp_parser = Component(id="comp-parser", name="parser", status=Status.ACTIVE, kind=ComponentKind.LIBRARY)
        comp_variables = Component(id="comp-variables", name="variables", status=Status.ACTIVE, kind=ComponentKind.LIBRARY)
        rel = Relationship(
            type=RelationType.DEPENDS_ON,
            from_id="comp-parser",
            to_id="comp-variables",
        )
        manifest = _make_manifest(
            modules=[
                {
                    "file": "dotenv/parser.py",
                    "name": "parser",
                    "classes": [],
                    "functions": [],
                    "imports_detailed": [
                        {"module": "variables", "symbols": ["Variable", "EnvVariable"], "is_relative": True},
                    ],
                },
                {
                    "file": "dotenv/variables.py",
                    "name": "variables",
                    "classes": [],
                    "functions": [],
                    "imports_detailed": [],
                },
            ],
            interfaces=[
                {"source": "dotenv/parser.py", "target": "dotenv/variables.py", "import_path": "dotenv.variables"},
            ],
        )
        model = _make_model([comp_parser, comp_variables], [rel])
        result = enrich_from_manifest(model, manifest)

        assert "Variable" in result.relationships[0].imports
        assert "EnvVariable" in result.relationships[0].imports

    def test_non_depends_on_not_enriched(self):
        """Non-depends-on relationships are not enriched with imports."""
        comp_a = Component(id="comp-a", name="a", status=Status.ACTIVE, kind=ComponentKind.LIBRARY)
        comp_b = Component(id="comp-b", name="b", status=Status.ACTIVE, kind=ComponentKind.LIBRARY)
        rel = Relationship(
            type=RelationType.REALIZES,
            from_id="comp-a",
            to_id="comp-b",
        )
        manifest = _make_manifest(
            modules=[
                {
                    "file": "a.py", "name": "a", "classes": [], "functions": [],
                    "imports_detailed": [{"module": "b", "symbols": ["Foo"], "is_relative": True}],
                },
                {"file": "b.py", "name": "b", "classes": [], "functions": [], "imports_detailed": []},
            ],
            interfaces=[{"source": "a.py", "target": "b.py", "import_path": "b"}],
        )
        model = _make_model([comp_a, comp_b], [rel])
        result = enrich_from_manifest(model, manifest)

        assert result.relationships[0].imports == []


# ---------------------------------------------------------------------------
# Test 6: Naming accuracy computation
# ---------------------------------------------------------------------------


class TestNamingAccuracy:
    def test_all_predicted_match(self):
        """All pre-existing symbol names match manifest → accuracy = 1.0."""
        comp = Component(
            id="comp-parser", name="parser", status=Status.ACTIVE, kind=ComponentKind.LIBRARY,
            symbols=[Symbol(name="Parser"), Symbol(name="Token")],
        )
        manifest = _make_manifest(modules=[
            {
                "file": "parser.py",
                "name": "parser",
                "classes": [
                    {"name": "Parser", "bases": [], "methods": [], "is_abstract": False, "decorators": []},
                    {"name": "Token", "bases": [], "methods": [], "is_abstract": False, "decorators": ["dataclass"]},
                ],
                "functions": [],
                "imports_detailed": [],
            }
        ])
        model = _make_model([comp])
        result = enrich_from_manifest(model, manifest)

        assert result.naming_accuracy == 1.0

    def test_none_predicted_match(self):
        """No pre-existing symbol names match manifest → accuracy = 0.0."""
        comp = Component(
            id="comp-parser", name="parser", status=Status.ACTIVE, kind=ComponentKind.LIBRARY,
            symbols=[Symbol(name="Wrong"), Symbol(name="Bogus")],
        )
        manifest = _make_manifest(modules=[
            {
                "file": "parser.py",
                "name": "parser",
                "classes": [
                    {"name": "Parser", "bases": [], "methods": [], "is_abstract": False, "decorators": []},
                    {"name": "Token", "bases": [], "methods": [], "is_abstract": False, "decorators": []},
                ],
                "functions": [],
                "imports_detailed": [],
            }
        ])
        model = _make_model([comp])
        result = enrich_from_manifest(model, manifest)

        assert result.naming_accuracy == 0.0

    def test_partial_match(self):
        """Some predicted match, some don't → partial accuracy."""
        comp = Component(
            id="comp-parser", name="parser", status=Status.ACTIVE, kind=ComponentKind.LIBRARY,
            symbols=[Symbol(name="Parser"), Symbol(name="Wrong"), Symbol(name="Token"), Symbol(name="Bogus")],
        )
        manifest = _make_manifest(modules=[
            {
                "file": "parser.py",
                "name": "parser",
                "classes": [
                    {"name": "Parser", "bases": [], "methods": [], "is_abstract": False, "decorators": []},
                    {"name": "Token", "bases": [], "methods": [], "is_abstract": False, "decorators": []},
                ],
                "functions": [],
                "imports_detailed": [],
            }
        ])
        model = _make_model([comp])
        result = enrich_from_manifest(model, manifest)

        assert result.naming_accuracy == 0.5  # 2 of 4 matched

    def test_no_pre_existing_symbols(self):
        """No pre-existing symbols → accuracy = 1.0 (nothing to be wrong about)."""
        comp = Component(
            id="comp-parser", name="parser", status=Status.ACTIVE, kind=ComponentKind.LIBRARY,
            symbols=[],
        )
        manifest = _make_manifest(modules=[
            {
                "file": "parser.py",
                "name": "parser",
                "classes": [
                    {"name": "Parser", "bases": [], "methods": [], "is_abstract": False, "decorators": []},
                ],
                "functions": [],
                "imports_detailed": [],
            }
        ])
        model = _make_model([comp])
        result = enrich_from_manifest(model, manifest)

        assert result.naming_accuracy == 1.0

    def test_no_matching_component(self):
        """Component with no matching module doesn't affect accuracy."""
        comp_matched = Component(
            id="comp-parser", name="parser", status=Status.ACTIVE, kind=ComponentKind.LIBRARY,
            symbols=[Symbol(name="Parser")],
        )
        comp_unmatched = Component(
            id="comp-unrelated", name="unrelated", status=Status.ACTIVE, kind=ComponentKind.LIBRARY,
            symbols=[Symbol(name="Whatever")],
        )
        manifest = _make_manifest(modules=[
            {
                "file": "parser.py",
                "name": "parser",
                "classes": [
                    {"name": "Parser", "bases": [], "methods": [], "is_abstract": False, "decorators": []},
                ],
                "functions": [],
                "imports_detailed": [],
            }
        ])
        model = _make_model([comp_matched, comp_unmatched])
        result = enrich_from_manifest(model, manifest)

        # Only comp_matched had pre-existing symbols and a match: 1/1 = 1.0
        assert result.naming_accuracy == 1.0


# ---------------------------------------------------------------------------
# Tests for compact_for_generation()
# ---------------------------------------------------------------------------


class TestCompactForGeneration:
    """Tests for compact_for_generation() truncation logic."""

    def test_truncates_large_members(self):
        from architecture_model.core.merger import compact_for_generation

        # Symbol with 20 methods (above _MAX_MEMBERS_PER_SYMBOL=8)
        many_methods = [f"method_{i}" for i in range(20)]
        comp = Component(
            id="comp-core", name="core", status=Status.ACTIVE,
            symbols=[Symbol(name="BigClass", kind=SymbolKind.CLASS, members=many_methods)],
        )
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.2", project="test"),
            entities=Entities(components=[comp]),
            relationships=[],
        )
        compacted = compact_for_generation(model)
        sym = compacted.entities.components[0].symbols[0]
        assert len(sym.members) == 8
        # Sorted alphabetically (no __init__ in this case)
        assert sym.members == sorted(sym.members)

    def test_truncates_many_symbols(self):
        from architecture_model.core.merger import compact_for_generation

        # 10 symbols (above _MAX_SYMBOLS_PER_COMPONENT=6)
        symbols = [
            Symbol(name=f"Class_{i}", kind=SymbolKind.CLASS, members=[f"m{j}" for j in range(i)])
            for i in range(10)
        ]
        comp = Component(
            id="comp-big", name="big", status=Status.ACTIVE,
            symbols=symbols,
        )
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.2", project="test"),
            entities=Entities(components=[comp]),
            relationships=[],
        )
        compacted = compact_for_generation(model)
        # Should keep top 6 by member count (Class_9, Class_8, ..., Class_4)
        assert len(compacted.entities.components[0].symbols) == 6
        # Verify they're the ones with most members
        names = [s.name for s in compacted.entities.components[0].symbols]
        assert "Class_9" in names
        assert "Class_0" not in names  # fewest members

    def test_preserves_init_method(self):
        from architecture_model.core.merger import compact_for_generation

        methods = ["__init__"] + [f"method_{i}" for i in range(15)]
        comp = Component(
            id="comp-x", name="x", status=Status.ACTIVE,
            symbols=[Symbol(name="Foo", kind=SymbolKind.CLASS, members=methods)],
        )
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.2", project="test"),
            entities=Entities(components=[comp]),
            relationships=[],
        )
        compacted = compact_for_generation(model)
        sym = compacted.entities.components[0].symbols[0]
        assert "__init__" in sym.members
        assert len(sym.members) == 8

    def test_truncates_large_functions_list(self):
        from architecture_model.core.merger import compact_for_generation

        many_funcs = [f"func_{i}" for i in range(20)]
        comp = Component(
            id="comp-utils", name="utils", status=Status.ACTIVE,
            functions=many_funcs,
        )
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.2", project="test"),
            entities=Entities(components=[comp]),
            relationships=[],
        )
        compacted = compact_for_generation(model)
        assert len(compacted.entities.components[0].functions) == 12

    def test_does_not_modify_original(self):
        from architecture_model.core.merger import compact_for_generation

        methods = [f"m_{i}" for i in range(15)]
        comp = Component(
            id="comp-x", name="x", status=Status.ACTIVE,
            symbols=[Symbol(name="Foo", kind=SymbolKind.CLASS, members=methods)],
        )
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.2", project="test"),
            entities=Entities(components=[comp]),
            relationships=[],
        )
        compact_for_generation(model)
        # Original untouched
        assert len(model.entities.components[0].symbols[0].members) == 15

    def test_small_model_unchanged(self):
        from architecture_model.core.merger import compact_for_generation

        comp = Component(
            id="comp-x", name="x", status=Status.ACTIVE,
            symbols=[Symbol(name="Foo", kind=SymbolKind.CLASS, members=["a", "b"])],
            functions=["func_a", "func_b"],
        )
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.2", project="test"),
            entities=Entities(components=[comp]),
            relationships=[],
        )
        compacted = compact_for_generation(model)
        assert len(compacted.entities.components[0].symbols[0].members) == 2
        assert len(compacted.entities.components[0].functions) == 2
