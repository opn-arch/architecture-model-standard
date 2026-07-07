"""Tests for enriched scanner — class attributes, module constants, module assignments."""
from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

from architecture_model.manifest.scanner import (
    _extract_class_attributes,
    _extract_module_constants,
    _extract_module_assignments,
    _scan_file,
)


class TestExtractClassAttributes:
    def test_simple_int_attributes(self):
        source = "class AnsiFore:\n    BLACK = 30\n    RED = 31\n    GREEN = 32\n"
        tree = ast.parse(source)
        cls_node = tree.body[0]
        attrs = _extract_class_attributes(cls_node)
        assert attrs == {"BLACK": "30", "RED": "31", "GREEN": "32"}

    def test_string_attributes(self):
        source = "class Config:\n    NAME = 'hello'\n    VERSION = '1.0'\n"
        tree = ast.parse(source)
        cls_node = tree.body[0]
        attrs = _extract_class_attributes(cls_node)
        assert attrs["NAME"] == "'hello'"
        assert attrs["VERSION"] == "'1.0'"

    def test_ignores_methods(self):
        source = "class Foo:\n    X = 1\n    def method(self):\n        pass\n"
        tree = ast.parse(source)
        cls_node = tree.body[0]
        attrs = _extract_class_attributes(cls_node)
        assert "X" in attrs
        assert "method" not in attrs

    def test_ignores_private_attrs(self):
        source = "class Foo:\n    _internal = 5\n    PUBLIC = 10\n"
        tree = ast.parse(source)
        cls_node = tree.body[0]
        attrs = _extract_class_attributes(cls_node)
        assert "_internal" not in attrs
        assert "PUBLIC" in attrs


class TestExtractModuleConstants:
    def test_basic_constants(self):
        source = "CSI = '\\033['\nOSC = '\\033]'\nBEL = '\\a'\nsome_var = 42\n"
        tree = ast.parse(source)
        consts = _extract_module_constants(tree)
        assert "CSI" in consts
        assert "OSC" in consts
        assert "BEL" in consts
        assert "some_var" not in consts

    def test_non_literal_excluded(self):
        source = "CONST = 42\nCOMPUTED = some_func()\n"
        tree = ast.parse(source)
        consts = _extract_module_constants(tree)
        assert "CONST" in consts
        assert "COMPUTED" not in consts

    def test_dunder_excluded(self):
        source = "__all__ = ['foo']\nVERSION = '1.0'\n"
        tree = ast.parse(source)
        consts = _extract_module_constants(tree)
        assert "__all__" not in consts
        assert "VERSION" in consts


class TestExtractModuleAssignments:
    def test_instance_assignments(self):
        source = "Fore = AnsiFore()\nBack = AnsiBack()\nStyle = AnsiStyle()\n"
        tree = ast.parse(source)
        assigns = _extract_module_assignments(tree)
        assert assigns["Fore"] == "AnsiFore()"
        assert assigns["Back"] == "AnsiBack()"
        assert assigns["Style"] == "AnsiStyle()"

    def test_excludes_upper_case_literals(self):
        source = "CSI = '\\033['\nFore = AnsiFore()\n"
        tree = ast.parse(source)
        assigns = _extract_module_assignments(tree)
        assert "CSI" not in assigns
        assert "Fore" in assigns

    def test_excludes_private(self):
        source = "_private = SomeClass()\nPublic = OtherClass()\n"
        tree = ast.parse(source)
        assigns = _extract_module_assignments(tree)
        assert "_private" not in assigns
        assert "Public" in assigns


class TestScanFileEnriched:
    def test_scan_includes_class_attributes(self, tmp_path):
        source = "class AnsiFore:\n    BLACK = 30\n    RED = 31\n"
        f = tmp_path / "ansi.py"
        f.write_text(source)
        result = _scan_file(tmp_path, f)
        assert result["classes"][0]["attributes"] == {"BLACK": "30", "RED": "31"}

    def test_scan_includes_module_constants(self, tmp_path):
        source = "CSI = '\\033['\n"
        f = tmp_path / "const.py"
        f.write_text(source)
        result = _scan_file(tmp_path, f)
        assert "CSI" in result["module_constants"]

    def test_scan_includes_module_assignments(self, tmp_path):
        source = "Fore = AnsiFore()\n"
        f = tmp_path / "inst.py"
        f.write_text(source)
        result = _scan_file(tmp_path, f)
        assert "Fore" in result["module_assignments"]
