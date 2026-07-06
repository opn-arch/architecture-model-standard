"""Tests for Schema v1.2: Code-Grounded Architecture Model.

Tests cover:
- SymbolKind enum
- Symbol dataclass
- Component.symbols and Component.functions
- Relationship.imports
- ModelMeta.source_language
- Round-trip parsing and serialization
"""

import yaml
import pytest

from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    ComponentKind,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
    Strength,
    Symbol,
    SymbolKind,
)
from architecture_model.core.parser import _parse_raw, dump_model


# ---------------------------------------------------------------------------
# SymbolKind Enum
# ---------------------------------------------------------------------------


class TestSymbolKind:
    def test_class_kind(self):
        assert SymbolKind.CLASS == "class"

    def test_all_kinds_exist(self):
        kinds = [sk.value for sk in SymbolKind]
        assert "class" in kinds
        assert "dataclass" in kinds
        assert "exception" in kinds
        assert "protocol" in kinds
        assert "struct" in kinds
        assert "interface" in kinds
        assert "enum" in kinds
        assert "trait" in kinds
        assert "type-alias" in kinds

    def test_str_conversion(self):
        assert SymbolKind.DATACLASS.value == "dataclass"
        assert SymbolKind("exception") == SymbolKind.EXCEPTION

    def test_invalid_kind_raises(self):
        with pytest.raises(ValueError):
            SymbolKind("nonexistent")


# ---------------------------------------------------------------------------
# Symbol Dataclass
# ---------------------------------------------------------------------------


class TestSymbol:
    def test_basic_symbol(self):
        s = Symbol(name="Parser", kind=SymbolKind.CLASS)
        assert s.name == "Parser"
        assert s.kind == SymbolKind.CLASS
        assert s.members == []
        assert s.supers == []

    def test_symbol_with_members(self):
        s = Symbol(
            name="Parser",
            kind=SymbolKind.CLASS,
            members=["parse", "__init__"],
            supers=["BaseParser"],
        )
        assert s.members == ["parse", "__init__"]
        assert s.supers == ["BaseParser"]

    def test_symbol_defaults(self):
        s = Symbol(name="Foo")
        assert s.kind == SymbolKind.CLASS
        assert s.members == []
        assert s.supers == []

    def test_exception_symbol(self):
        s = Symbol(name="ParseError", kind=SymbolKind.EXCEPTION, supers=["Exception"])
        assert s.kind == SymbolKind.EXCEPTION
        assert s.supers == ["Exception"]

    def test_dataclass_symbol(self):
        s = Symbol(name="Token", kind=SymbolKind.DATACLASS, members=["key", "value"])
        assert s.kind == SymbolKind.DATACLASS
        assert s.members == ["key", "value"]


# ---------------------------------------------------------------------------
# Component.symbols and Component.functions
# ---------------------------------------------------------------------------


class TestComponentSymbols:
    def test_component_defaults_empty(self):
        c = Component(
            id="comp-x", name="x", status=Status.ACTIVE, kind=ComponentKind.LIBRARY
        )
        assert c.symbols == []
        assert c.functions == []

    def test_component_with_symbols(self):
        symbols = [
            Symbol(name="Parser", kind=SymbolKind.CLASS, members=["parse"]),
            Symbol(name="Token", kind=SymbolKind.DATACLASS),
            Symbol(name="ParseError", kind=SymbolKind.EXCEPTION, supers=["Exception"]),
        ]
        c = Component(
            id="comp-parser",
            name="parser",
            status=Status.ACTIVE,
            kind=ComponentKind.LIBRARY,
            symbols=symbols,
            functions=["make_parser", "load_file"],
        )
        assert len(c.symbols) == 3
        assert c.symbols[0].name == "Parser"
        assert c.symbols[2].kind == SymbolKind.EXCEPTION
        assert c.functions == ["make_parser", "load_file"]


# ---------------------------------------------------------------------------
# Relationship.imports
# ---------------------------------------------------------------------------


class TestRelationshipImports:
    def test_relationship_defaults_empty(self):
        r = Relationship(type=RelationType.DEPENDS_ON, from_id="a", to_id="b")
        assert r.imports == []

    def test_relationship_with_imports(self):
        r = Relationship(
            type=RelationType.DEPENDS_ON,
            from_id="comp-parser",
            to_id="comp-variables",
            imports=["Variable", "EnvVariable"],
        )
        assert r.imports == ["Variable", "EnvVariable"]


# ---------------------------------------------------------------------------
# ModelMeta.source_language
# ---------------------------------------------------------------------------


class TestModelMetaLanguage:
    def test_meta_defaults_empty(self):
        m = ModelMeta(schema_version="1.2", project="test")
        assert m.source_language == ""

    def test_meta_with_language(self):
        m = ModelMeta(schema_version="1.2", project="test", source_language="python")
        assert m.source_language == "python"


# ---------------------------------------------------------------------------
# Parsing (YAML → typed model)
# ---------------------------------------------------------------------------


class TestParseV12:
    def test_parse_component_with_symbols(self):
        raw = {
            "meta": {"schema_version": "1.2", "project": "test", "source_language": "python"},
            "entities": {
                "components": [
                    {
                        "id": "comp-parser",
                        "name": "parser",
                        "kind": "library",
                        "status": "ACTIVE",
                        "symbols": [
                            {"name": "Parser", "kind": "class", "members": ["parse", "__init__"], "supers": []},
                            {"name": "Token", "kind": "dataclass", "members": ["key", "value"]},
                            {"name": "ParseError", "kind": "exception", "supers": ["Exception"]},
                        ],
                        "functions": ["make_parser", "load_file"],
                    }
                ]
            },
            "relationships": [],
        }
        model = _parse_raw(raw)
        assert model.meta.source_language == "python"
        comp = model.entities.components[0]
        assert len(comp.symbols) == 3
        assert comp.symbols[0].name == "Parser"
        assert comp.symbols[0].kind == SymbolKind.CLASS
        assert comp.symbols[0].members == ["parse", "__init__"]
        assert comp.symbols[1].kind == SymbolKind.DATACLASS
        assert comp.symbols[1].members == ["key", "value"]
        assert comp.symbols[2].kind == SymbolKind.EXCEPTION
        assert comp.symbols[2].supers == ["Exception"]
        assert comp.functions == ["make_parser", "load_file"]

    def test_parse_relationship_with_imports(self):
        raw = {
            "meta": {"schema_version": "1.2", "project": "test"},
            "entities": {
                "components": [
                    {"id": "comp-a", "name": "a", "status": "ACTIVE"},
                    {"id": "comp-b", "name": "b", "status": "ACTIVE"},
                ]
            },
            "relationships": [
                {"type": "depends-on", "from": "comp-a", "to": "comp-b", "imports": ["Foo", "Bar"]}
            ],
        }
        model = _parse_raw(raw)
        rel = model.relationships[0]
        assert rel.imports == ["Foo", "Bar"]

    def test_parse_invalid_symbol_kind_defaults_to_class(self):
        raw = {
            "meta": {"schema_version": "1.2", "project": "test"},
            "entities": {
                "components": [
                    {
                        "id": "comp-x",
                        "name": "x",
                        "status": "ACTIVE",
                        "symbols": [{"name": "Foo", "kind": "nonexistent"}],
                    }
                ]
            },
            "relationships": [],
        }
        model = _parse_raw(raw)
        assert model.entities.components[0].symbols[0].kind == SymbolKind.CLASS

    def test_parse_backward_compatible_no_symbols(self):
        """v1.1 models without symbols/functions/imports should parse fine."""
        raw = {
            "meta": {"schema_version": "1.1", "project": "old"},
            "entities": {
                "components": [
                    {"id": "comp-x", "name": "x", "kind": "library", "status": "ACTIVE"}
                ]
            },
            "relationships": [{"type": "depends-on", "from": "comp-x", "to": "comp-y"}],
        }
        model = _parse_raw(raw)
        assert model.entities.components[0].symbols == []
        assert model.entities.components[0].functions == []
        assert model.relationships[0].imports == []
        assert model.meta.source_language == ""


# ---------------------------------------------------------------------------
# Serialization Round-Trip
# ---------------------------------------------------------------------------


class TestSerializeV12:
    def test_round_trip_symbols(self):
        raw = {
            "meta": {"schema_version": "1.2", "project": "test", "source_language": "python"},
            "entities": {
                "components": [
                    {
                        "id": "comp-p",
                        "name": "p",
                        "kind": "library",
                        "status": "ACTIVE",
                        "symbols": [
                            {"name": "Foo", "kind": "class", "members": ["bar", "baz"], "supers": ["Base"]},
                            {"name": "MyError", "kind": "exception", "supers": ["RuntimeError"]},
                        ],
                        "functions": ["helper", "util"],
                    }
                ]
            },
            "relationships": [
                {"type": "depends-on", "from": "comp-p", "to": "comp-q", "imports": ["X", "Y"]}
            ],
        }
        model = _parse_raw(raw)
        dumped = dump_model(model)

        # Check meta
        assert dumped["meta"]["source_language"] == "python"

        # Check component symbols
        comp = dumped["entities"]["components"][0]
        assert len(comp["symbols"]) == 2
        assert comp["symbols"][0]["name"] == "Foo"
        assert comp["symbols"][0]["kind"] == "class"
        assert comp["symbols"][0]["members"] == ["bar", "baz"]
        assert comp["symbols"][0]["supers"] == ["Base"]
        assert comp["symbols"][1]["name"] == "MyError"
        assert comp["symbols"][1]["kind"] == "exception"
        assert comp["functions"] == ["helper", "util"]

        # Check relationship imports
        rel = dumped["relationships"][0]
        assert rel["imports"] == ["X", "Y"]

    def test_round_trip_empty_symbols_not_serialized(self):
        """Components without symbols should not have empty symbols/functions in output."""
        raw = {
            "meta": {"schema_version": "1.2", "project": "test"},
            "entities": {
                "components": [
                    {"id": "comp-x", "name": "x", "kind": "library", "status": "ACTIVE"}
                ]
            },
            "relationships": [{"type": "depends-on", "from": "comp-x", "to": "comp-y"}],
        }
        model = _parse_raw(raw)
        dumped = dump_model(model)
        comp = dumped["entities"]["components"][0]
        assert "symbols" not in comp
        assert "functions" not in comp
        rel = dumped["relationships"][0]
        assert "imports" not in rel

    def test_round_trip_source_language_empty_not_serialized(self):
        raw = {
            "meta": {"schema_version": "1.2", "project": "test"},
            "entities": {},
            "relationships": [],
        }
        model = _parse_raw(raw)
        dumped = dump_model(model)
        assert "source_language" not in dumped["meta"]
