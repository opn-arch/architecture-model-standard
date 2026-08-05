"""Tests for manifest_to_source_graph adapter."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass, field

from architecture_model.manifest.types import ModuleInfo, FunctionInfo, ModuleStatus
from architecture_model.manifest.protocol import SourceGraph, DependencyEdge
from architecture_model.orchestration.auto_enrich import manifest_to_source_graph


def _make_manifest(modules):
    """Create a minimal Manifest with given modules."""
    from architecture_model.manifest.types import Manifest, MetricsResult
    return Manifest(
        modules=modules,
        interfaces=[],
        functional_blocks={},
        generated_at="",
        project_root="/repo",
        metrics=MetricsResult(values={}),
    )


def _make_module(file: str, imports: list[str]) -> ModuleInfo:
    return ModuleInfo(
        file=file,
        name=file.replace("/", ".").replace(".py", ""),
        docstring=None,
        functions=[],
        imports=imports,
        line_count=10,
        status=ModuleStatus.ACTIVE,
        classes=[],
    )


def _make_model(components):
    """Create a mock model with components."""
    model = MagicMock()
    model.entities.components = components
    return model


def _make_component(id: str, name: str, files: list[str]):
    from architecture_model.core.types import Component, Status
    return Component(id=id, name=name, status=Status.ACTIVE, files=files)


class TestManifestToSourceGraph:
    def test_cross_component_imports_create_edges(self):
        """Manifest with cross-component imports → SourceGraph has edges."""
        comp_a = _make_component("C1", "CompA", ["src/a/main.py", "src/a/utils.py"])
        comp_b = _make_component("C2", "CompB", ["src/b/core.py", "src/b/helpers.py"])
        model = _make_model([comp_a, comp_b])

        modules = [
            _make_module("src/a/main.py", ["src.b.core"]),  # A imports from B
            _make_module("src/a/utils.py", []),
            _make_module("src/b/core.py", []),
            _make_module("src/b/helpers.py", ["src.a.utils"]),  # B imports from A
        ]
        manifest = _make_manifest(modules)

        graph = manifest_to_source_graph(manifest, model)

        assert isinstance(graph, SourceGraph)
        assert len(graph.edges) >= 2  # at least 2 cross-component edges

        # Check edge from src/a/main.py -> src/b/core.py
        sources = {(e.source, e.target) for e in graph.edges}
        assert ("src/a/main.py", "src/b/core.py") in sources
        assert ("src/b/helpers.py", "src/a/utils.py") in sources

    def test_intra_component_imports_no_cross_edges(self):
        """Manifest with only intra-component imports → no cross-component edges in graph."""
        comp_a = _make_component("C1", "CompA", ["src/a/main.py", "src/a/utils.py"])
        comp_b = _make_component("C2", "CompB", ["src/b/core.py"])
        model = _make_model([comp_a, comp_b])

        modules = [
            _make_module("src/a/main.py", ["src.a.utils"]),  # intra-component
            _make_module("src/a/utils.py", []),
            _make_module("src/b/core.py", []),
        ]
        manifest = _make_manifest(modules)

        graph = manifest_to_source_graph(manifest, model)

        assert isinstance(graph, SourceGraph)
        # Graph may have edges but extract_component_interfaces would skip intra-component ones
        # The adapter should still produce edges for all resolved imports
        # Let's verify we get edges (intra-component import resolves)
        # The key test: no cross-boundary edges exist
        file_to_comp = {}
        for c in [comp_a, comp_b]:
            for f in c.files:
                file_to_comp[f] = c

        cross_edges = [
            e for e in graph.edges
            if file_to_comp.get(e.source) and file_to_comp.get(e.target)
            and file_to_comp[e.source] is not file_to_comp[e.target]
        ]
        assert len(cross_edges) == 0

    def test_unresolvable_imports_skipped(self):
        """Imports that don't map to any manifest module are skipped."""
        comp_a = _make_component("C1", "CompA", ["src/a/main.py"])
        model = _make_model([comp_a])

        modules = [
            _make_module("src/a/main.py", ["os", "sys", "nonexistent.module"]),
        ]
        manifest = _make_manifest(modules)

        graph = manifest_to_source_graph(manifest, model)

        assert isinstance(graph, SourceGraph)
        assert len(graph.edges) == 0  # none resolve to manifest modules
