"""Tests for code_structure module (AST → StructuralGraph)."""

import pytest
from architecture_model.training.code_structure import (
    ClassInfo,
    FunctionInfo,
    ImportEdge,
    StructuralGraph,
    parse_code_structure,
    parse_multi_file_code,
)


class TestStructuralGraphProperties:
    """Test computed properties on StructuralGraph."""

    def test_class_names(self):
        graph = StructuralGraph(
            classes=[
                ClassInfo(name="Foo", methods=["bar"]),
                ClassInfo(name="Baz", methods=["qux"]),
            ]
        )
        assert graph.class_names == {"Foo", "Baz"}

    def test_method_names_qualified(self):
        graph = StructuralGraph(
            classes=[
                ClassInfo(name="Foo", methods=["bar", "baz"]),
                ClassInfo(name="Qux", methods=["run"]),
            ]
        )
        assert graph.method_names == {"Foo.bar", "Foo.baz", "Qux.run"}

    def test_function_names(self):
        graph = StructuralGraph(
            functions=[
                FunctionInfo(name="helper"),
                FunctionInfo(name="main"),
            ]
        )
        assert graph.function_names == {"helper", "main"}

    def test_import_modules(self):
        graph = StructuralGraph(
            imports=[
                ImportEdge(from_module="app", to_module="os"),
                ImportEdge(from_module="app", to_module="sys"),
            ]
        )
        assert graph.import_modules == {"os", "sys"}

    def test_empty_graph_properties(self):
        graph = StructuralGraph()
        assert graph.class_names == set()
        assert graph.method_names == set()
        assert graph.function_names == set()
        assert graph.import_modules == set()


class TestParseCodeStructure:
    """Test parse_code_structure() on single-file code."""

    def test_simple_class_with_methods(self):
        code = """\
class AuthService:
    def __init__(self, db):
        self.db = db

    def login(self, user, password):
        pass

    def logout(self):
        pass
"""
        graph = parse_code_structure(code, module_name="auth.service")
        assert len(graph.classes) == 1
        cls = graph.classes[0]
        assert cls.name == "AuthService"
        assert "__init__" in cls.methods
        assert "login" in cls.methods
        assert "logout" in cls.methods
        assert cls.module == "auth.service"

    def test_class_with_bases(self):
        code = """\
class Animal:
    pass

class Dog(Animal):
    def bark(self):
        pass
"""
        graph = parse_code_structure(code)
        dog = next(c for c in graph.classes if c.name == "Dog")
        assert "Animal" in dog.bases
        assert "bark" in dog.methods

    def test_multiple_bases(self):
        code = """\
class Mixin:
    pass

class Base:
    pass

class Child(Base, Mixin):
    pass
"""
        graph = parse_code_structure(code)
        child = next(c for c in graph.classes if c.name == "Child")
        assert "Base" in child.bases
        assert "Mixin" in child.bases

    def test_top_level_functions(self):
        code = """\
def process(data, config=None):
    return data

def helper(x, y, z):
    pass
"""
        graph = parse_code_structure(code, module_name="utils")
        assert len(graph.functions) == 2
        proc = next(f for f in graph.functions if f.name == "process")
        assert "data" in proc.args
        assert "config" in proc.args
        assert proc.module == "utils"

    def test_import_statement(self):
        code = """\
import os
import sys
"""
        graph = parse_code_structure(code, module_name="app")
        assert len(graph.imports) == 2
        to_modules = {e.to_module for e in graph.imports}
        assert "os" in to_modules
        assert "sys" in to_modules
        assert all(e.from_module == "app" for e in graph.imports)

    def test_from_import_statement(self):
        code = """\
from pathlib import Path
from typing import Optional, List
"""
        graph = parse_code_structure(code, module_name="mod")
        to_modules = {e.to_module for e in graph.imports}
        assert "pathlib" in to_modules
        assert "typing" in to_modules

    def test_dunder_methods_skipped_except_init(self):
        code = """\
class Widget:
    def __init__(self):
        pass

    def __repr__(self):
        return "Widget()"

    def __str__(self):
        return "widget"

    def render(self):
        pass
"""
        graph = parse_code_structure(code)
        widget = graph.classes[0]
        assert "__init__" in widget.methods
        assert "render" in widget.methods
        assert "__repr__" not in widget.methods
        assert "__str__" not in widget.methods

    def test_private_methods_skipped(self):
        code = """\
class Service:
    def __init__(self):
        pass

    def _internal_helper(self):
        pass

    def public_method(self):
        pass
"""
        graph = parse_code_structure(code)
        svc = graph.classes[0]
        assert "__init__" in svc.methods
        assert "public_method" in svc.methods
        assert "_internal_helper" not in svc.methods

    def test_syntax_error_returns_empty_graph(self):
        code = "def broken(:\n    pass"
        graph = parse_code_structure(code)
        assert graph.classes == []
        assert graph.functions == []
        assert graph.imports == []

    def test_nested_functions_not_included(self):
        """Only top-level functions, not nested ones."""
        code = """\
def outer():
    def inner():
        pass
    return inner()
"""
        graph = parse_code_structure(code)
        assert len(graph.functions) == 1
        assert graph.functions[0].name == "outer"

    def test_module_name_default(self):
        code = "class X: pass"
        graph = parse_code_structure(code)
        assert graph.classes[0].module == "module"


class TestParseMultiFileCode:
    """Test parse_multi_file_code() on multi-file format."""

    def test_basic_multi_file(self):
        code = """\
# src/auth/service.py
class AuthService:
    def login(self, user, password):
        pass

# src/api/router.py
from fastapi import APIRouter

router = APIRouter()
"""
        graph = parse_multi_file_code(code)
        assert "auth.service" in graph.modules
        assert "api.router" in graph.modules
        assert "AuthService" in graph.class_names

    def test_module_name_extraction(self):
        """Module name derived from path: src/auth/service.py → auth.service."""
        code = """\
# src/mypackage/utils/helpers.py
def helper():
    pass
"""
        graph = parse_multi_file_code(code)
        assert "mypackage.utils.helpers" in graph.modules

    def test_flat_path_module_name(self):
        """Top-level file: app.py → app."""
        code = """\
# app.py
def main():
    pass
"""
        graph = parse_multi_file_code(code)
        assert "app" in graph.modules

    def test_merges_classes_from_multiple_files(self):
        code = """\
# src/models/user.py
class User:
    def __init__(self, name):
        self.name = name

# src/models/post.py
class Post:
    def __init__(self, title):
        self.title = title
"""
        graph = parse_multi_file_code(code)
        assert graph.class_names == {"User", "Post"}
        user = next(c for c in graph.classes if c.name == "User")
        assert user.module == "models.user"

    def test_merges_imports_from_multiple_files(self):
        code = """\
# src/a.py
import os

# src/b.py
import sys
"""
        graph = parse_multi_file_code(code)
        assert graph.import_modules == {"os", "sys"}

    def test_empty_input(self):
        graph = parse_multi_file_code("")
        assert graph.classes == []
        assert graph.functions == []
        assert graph.modules == []

    def test_no_markers(self):
        """Code without file markers treated as single module."""
        code = """\
class Standalone:
    def run(self):
        pass
"""
        graph = parse_multi_file_code(code)
        assert "Standalone" in graph.class_names
