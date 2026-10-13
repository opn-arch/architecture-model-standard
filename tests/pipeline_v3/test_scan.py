"""Tests for pipeline_v3.scan — Phase 6.1 of T0.14.

Reality scan: consume a repo and produce a v3-native ScanResult that
downstream stages (derive_promises, cluster, ...) consume.

Bridges existing manifest/scanner via delegation — this module does NOT
re-implement AST scanning; it lifts Manifest into a Promise-graph-ready
shape with deterministic ordering.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from architecture_model.pipeline_v3.scan import (
    ScanResult,
    ScannedModule,
    scan_repo,
)


# ---------------------------------------------------------------------------
# Fixture: a tiny synthetic package
# ---------------------------------------------------------------------------

@pytest.fixture
def tiny_repo(tmp_path: Path) -> Path:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text('"""Pkg root."""\n')
    (tmp_path / "pkg" / "core.py").write_text(
        '"""Core logic for the tiny repo."""\n'
        "def foo(x: int) -> int:\n"
        '    """Return x plus one."""\n'
        "    return x + 1\n"
        "class Bar:\n"
        "    def m(self) -> None: pass\n"
    )
    (tmp_path / "pkg" / "util.py").write_text(
        '"""Utility helpers."""\n'
        "import json\n"
        "def to_json(d): return json.dumps(d)\n"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------

def test_scan_returns_scan_result(tiny_repo):
    result = scan_repo(tiny_repo)
    assert isinstance(result, ScanResult)
    assert result.source_root == tiny_repo


def test_scan_finds_modules(tiny_repo):
    result = scan_repo(tiny_repo)
    module_names = {m.name for m in result.modules}
    assert "pkg.core" in module_names
    assert "pkg.util" in module_names


def test_scanned_module_carries_docstring(tiny_repo):
    result = scan_repo(tiny_repo)
    core = next(m for m in result.modules if m.name == "pkg.core")
    assert core.docstring == "Core logic for the tiny repo."


def test_scanned_module_carries_functions(tiny_repo):
    result = scan_repo(tiny_repo)
    core = next(m for m in result.modules if m.name == "pkg.core")
    function_names = {f["name"] for f in core.functions}
    assert "foo" in function_names


def test_scanned_module_carries_classes(tiny_repo):
    result = scan_repo(tiny_repo)
    core = next(m for m in result.modules if m.name == "pkg.core")
    class_names = {c["name"] for c in core.classes}
    assert "Bar" in class_names


def test_scanned_module_carries_imports(tiny_repo):
    result = scan_repo(tiny_repo)
    util = next(m for m in result.modules if m.name == "pkg.util")
    assert "json" in util.imports


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_scan_modules_deterministically_ordered(tiny_repo):
    result = scan_repo(tiny_repo)
    names = [m.name for m in result.modules]
    assert names == sorted(names)


def test_scan_is_idempotent(tiny_repo):
    a = scan_repo(tiny_repo)
    b = scan_repo(tiny_repo)
    assert [m.name for m in a.modules] == [m.name for m in b.modules]
    for ma, mb in zip(a.modules, b.modules):
        assert ma.docstring == mb.docstring
        assert ma.imports == mb.imports


def test_scan_result_carries_signal_count(tiny_repo):
    result = scan_repo(tiny_repo)
    assert result.module_count == len(result.modules)
    assert result.module_count >= 2  # pkg.core + pkg.util at minimum


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_scan_empty_repo(tmp_path: Path):
    result = scan_repo(tmp_path)
    assert isinstance(result, ScanResult)
    assert result.modules == []
    assert result.module_count == 0


def test_scan_skips_test_files_by_default(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "mod.py").write_text("x = 1\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mod.py").write_text("def test_x(): pass\n")
    result = scan_repo(tmp_path)
    names = {m.name for m in result.modules}
    assert "pkg.mod" in names
    assert not any("test_" in n for n in names)
