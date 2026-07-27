"""Tests for typed scanner output (ModuleInfo instead of raw dict)."""

import pytest
from pathlib import Path
from architecture_model.manifest.types import ModuleInfo, ModuleStatus


def test_scan_file_returns_module_info(tmp_path):
    f = tmp_path / "example.py"
    f.write_text('"""Example module."""\n\ndef hello(name: str) -> str:\n    return f"hi {name}"\n')
    from architecture_model.manifest.scanner import scan_file
    result = scan_file(tmp_path, f)
    assert isinstance(result, ModuleInfo)
    assert result.status == ModuleStatus.DORMANT
    assert len(result.functions) == 1
    assert result.functions[0].name == "hello"


def test_scan_file_parse_error(tmp_path):
    f = tmp_path / "bad.py"
    f.write_text("def broken(\n")
    from architecture_model.manifest.scanner import scan_file
    result = scan_file(tmp_path, f)
    assert result.status != ModuleStatus.ACTIVE  # small file = DORMANT via fallback


def test_scan_file_extracts_constants(tmp_path):
    f = tmp_path / "consts.py"
    f.write_text('FOO = "bar"\nBAZ = 42\n')
    from architecture_model.manifest.scanner import scan_file
    result = scan_file(tmp_path, f)
    assert "FOO" in result.module_constants
    assert "BAZ" in result.module_constants


def test_scan_file_backward_compat(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text('"""Module."""\nx = 1\n')
    from architecture_model.manifest.scanner import scan_file
    d = scan_file(tmp_path, f).to_dict()
    required_keys = {"file", "name", "docstring", "functions", "imports",
                     "line_count", "status", "classes", "exports",
                     "decorated_functions", "imports_detailed",
                     "module_constants", "module_assignments"}
    assert required_keys.issubset(d.keys())


def test_deprecated_scan_file_returns_dict(tmp_path):
    """_scan_file (deprecated) should still return a dict for backward compat."""
    f = tmp_path / "mod.py"
    f.write_text('"""Module."""\ndef greet(): pass\n')
    from architecture_model.manifest.scanner import _scan_file
    result = _scan_file(tmp_path, f)
    assert isinstance(result, dict)
    assert "file" in result
    assert "functions" in result


def test_deprecated_collect_py_files(tmp_path):
    """_collect_py_files (deprecated) should still work."""
    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / "a.py").write_text("x = 1\n")
    (sub / "b.py").write_text("y = 2\n")
    from architecture_model.manifest.scanner import _collect_py_files
    files = _collect_py_files(tmp_path, "pkg")
    assert len(files) == 2
