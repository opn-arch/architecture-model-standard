"""Tests for multi-language scanner."""
import pytest
from pathlib import Path

from architecture_model.manifest.multi_scanner import scan_all_languages, _merge_graphs
from architecture_model.manifest.protocol import (
    DependencyEdge, ExportedSymbol, SourceGraph, SourceUnit,
)


class TestMergeGraphs:
    def test_merges_units_and_edges(self):
        g1 = SourceGraph(
            units=[SourceUnit(file="a.py", exports=[ExportedSymbol(name="foo")])],
            edges=[DependencyEdge(source="a.py", target="b.py")],
            language="python",
        )
        g2 = SourceGraph(
            units=[SourceUnit(file="Main.kt", exports=[ExportedSymbol(name="Main", kind="class")])],
            edges=[],
            language="kotlin",
        )
        merged = _merge_graphs([g1, g2])
        assert len(merged.units) == 2
        assert len(merged.edges) == 1
        assert "kotlin" in merged.language
        assert "python" in merged.language

    def test_empty_merge(self):
        merged = _merge_graphs([])
        assert len(merged.units) == 0

    def test_single_language(self):
        g = SourceGraph(units=[], language="python")
        merged = _merge_graphs([g])
        assert merged.language == "python"


class TestScanAllLanguages:
    def test_python_only(self, tmp_path):
        """Python-only repo uses manifest scanner."""
        # Must be in a subdirectory (manifest generator skips root-level files)
        pkg = tmp_path / "mypackage"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "app.py").write_text("def hello(): pass")
        graph = scan_all_languages(tmp_path)
        assert len(graph.units) >= 1
        assert "python" in graph.language

    def test_kotlin_only(self, tmp_path):
        """Kotlin-only project."""
        (tmp_path / "Main.kt").write_text("class Main")
        graph = scan_all_languages(tmp_path)
        assert len(graph.units) == 1
        assert "kotlin" in graph.language

    def test_mixed_python_kotlin(self, tmp_path):
        """Mixed project gets both languages."""
        pkg = tmp_path / "mypackage"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "app.py").write_text("def hello(): pass")
        (tmp_path / "android").mkdir()
        (tmp_path / "android" / "Main.kt").write_text("class Main")
        graph = scan_all_languages(tmp_path)
        languages = {u.language for u in graph.units}
        assert "python" in languages
        assert "kotlin" in languages

    def test_finds_kotlin_in_android_structure(self, tmp_path):
        """Finds Kotlin source root in Android project layout."""
        # Create Android project structure
        src = tmp_path / "myapp" / "app" / "src" / "main" / "java" / "com" / "example"
        src.mkdir(parents=True)
        (src / "Main.kt").write_text("package com.example\nclass Main")
        graph = scan_all_languages(tmp_path)
        kt_units = [u for u in graph.units if u.language == "kotlin"]
        assert len(kt_units) >= 1

    def test_real_logs_db(self):
        """Scan the actual logs_db repo (Python + Kotlin)."""
        repo = Path("/Users/baigm2/Documents/Projects/logs_db")
        if not repo.exists():
            pytest.skip("logs_db not available")
        graph = scan_all_languages(repo)
        languages = {u.language for u in graph.units}
        assert "python" in languages
        assert "kotlin" in languages
        py_count = sum(1 for u in graph.units if u.language == "python")
        kt_count = sum(1 for u in graph.units if u.language == "kotlin")
        assert py_count >= 50  # lots of Python files
        assert kt_count >= 8  # Android app files
