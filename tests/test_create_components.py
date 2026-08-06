"""Tests for create_components_from_manifest."""

from pathlib import Path
from architecture_model.manifest.types import ModuleInfo, InterfaceEdge, FunctionInfo, ClassInfo, ModuleStatus, Manifest


def _mod(file, line_count=50, functions=None, classes=None):
    return ModuleInfo(
        file=file, name=file.rsplit("/", 1)[-1].replace(".py", ""),
        docstring=None,
        functions=functions or [],
        imports=[], line_count=line_count, status=ModuleStatus.ACTIVE,
        classes=classes or [],
        exports=[], decorated_functions=[], imports_detailed=[],
        module_constants={}, module_assignments={},
    )


def _fn(name):
    return FunctionInfo(name=name, signature="() -> None", calls=[], docstring=None, raises=[])


def test_creates_components_from_grouped_modules():
    from architecture_model.manifest.grouping import create_components_from_manifest
    
    modules = [
        _mod("pkg/core.py", line_count=500, functions=[_fn("run")]),
        _mod("pkg/utils.py", line_count=100, functions=[_fn("helper")]),
        _mod("pkg/sub/a.py", line_count=50, functions=[_fn("fa")]),
        _mod("pkg/sub/b.py", line_count=50, functions=[_fn("fb")]),
    ]
    manifest = Manifest(modules=modules, interfaces=[], functional_blocks={}, generated_at="", project_root=".", metrics={})
    
    components = create_components_from_manifest(manifest, block_id="S1")
    
    # Should have fewer components than modules (sub/ files grouped)
    assert len(components) < len(modules)
    
    # Each component should have id, name, files, source_block
    for c in components:
        assert c.id.startswith("COMP-")
        assert c.name
        assert c.files
        assert c.source_block == "S1"
        assert c.status == "ACTIVE"


def test_component_files_cover_all_non_trivial():
    from architecture_model.manifest.grouping import create_components_from_manifest
    
    modules = [
        _mod("pkg/__init__.py", line_count=2),  # trivial
        _mod("pkg/__version__.py", line_count=3),  # trivial
        _mod("pkg/core.py", line_count=500, functions=[_fn("run")]),
        _mod("pkg/helpers.py", line_count=100, functions=[_fn("help")]),
    ]
    manifest = Manifest(modules=modules, interfaces=[], functional_blocks={}, generated_at="", project_root=".", metrics={})
    
    components = create_components_from_manifest(manifest, block_id="S1")
    
    all_files = [f for c in components for f in c.files]
    assert "pkg/core.py" in all_files
    assert "pkg/helpers.py" in all_files
    assert "pkg/__init__.py" not in all_files
    assert "pkg/__version__.py" not in all_files


def test_component_ids_unique():
    from architecture_model.manifest.grouping import create_components_from_manifest
    
    modules = [_mod(f"pkg/mod_{i}.py", functions=[_fn(f"f{i}")]) for i in range(5)]
    manifest = Manifest(modules=modules, interfaces=[], functional_blocks={}, generated_at="", project_root=".", metrics={})
    
    components = create_components_from_manifest(manifest, block_id="S1")
    ids = [c.id for c in components]
    assert len(ids) == len(set(ids))
