"""Tests for hierarchical representativeness."""
import pytest
from architecture_model.core.representativeness import (
    compute_hierarchical_representativeness,
    HierarchicalRepresentativenessResult,
)
from architecture_model.core.types import ArchitectureModel, Component, Relationship, Entities
from architecture_model.manifest.types import (
    Manifest, ModuleInfo, FunctionInfo, InterfaceEdge, RecursiveManifest, ModuleStatus,
)


def _mod(path, name, functions=None, imports=None):
    return ModuleInfo(
        file=path, name=name, docstring=None,
        functions=functions or [], imports=imports or [],
        line_count=10, status=ModuleStatus.ACTIVE, classes=[],
    )


def _make_model(components, relationships=None):
    """Build minimal ArchitectureModel."""
    model = ArchitectureModel(
        meta={"project": "test", "schema_version": "1.3"},
        entities=Entities(components=components),
        relationships=relationships or [],
    )
    return model


def test_hierarchical_basic():
    """Hierarchical check with root + one block."""
    # Root model covers all files
    root_comp = Component(id="COMP-1", name="Core", status="ACTIVE", files=["core/a.py", "core/b.py"])
    root_model = _make_model([root_comp])

    # Sub-model for F1
    sub_comp = Component(id="SUB-1", name="CoreInternal", status="ACTIVE", files=["core/a.py", "core/b.py"])
    sub_model = _make_model([sub_comp])

    # Recursive manifest
    modules = [
        _mod("core/a.py", "a", functions=[FunctionInfo(name="run", signature="()")]),
        _mod("core/b.py", "b", functions=[FunctionInfo(name="help", signature="()")]),
    ]
    manifest = Manifest(
        modules=modules, interfaces=[], functional_blocks={},
        generated_at="2026-01-01", project_root="/tmp", metrics={},
    )
    rm = RecursiveManifest(
        block_id="F1", block_name="Core", parent_model="model.yaml",
        component_id="COMP-1", manifest=manifest,
    )

    result = compute_hierarchical_representativeness(
        root_model, {"F1": sub_model}, {"F1": rm}
    )
    assert isinstance(result, HierarchicalRepresentativenessResult)
    assert result.root.file_coverage == 100.0
    assert "F1" in result.blocks
    assert result.blocks["F1"].file_coverage == 100.0
    assert result.overall > 0


def test_hierarchical_no_sub_models():
    """When no sub-models provided, overall equals root."""
    root_comp = Component(id="COMP-1", name="All", status="ACTIVE", files=["a.py"])
    root_model = _make_model([root_comp])

    modules = [_mod("a.py", "a")]
    manifest = Manifest(
        modules=modules, interfaces=[], functional_blocks={},
        generated_at="2026-01-01", project_root="/tmp", metrics={},
    )
    rm = RecursiveManifest(
        block_id="F1", block_name="All", parent_model="model.yaml",
        component_id="COMP-1", manifest=manifest,
    )

    result = compute_hierarchical_representativeness(root_model, {}, {"F1": rm})
    assert result.overall == result.root.overall
