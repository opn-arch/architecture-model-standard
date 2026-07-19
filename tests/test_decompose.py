"""Tests for model decomposition into recursive sub-models."""
import json
import textwrap
from pathlib import Path

import yaml

from architecture_model.core.types import (
    ArchitectureModel, Component, ComponentKind, Entities, ModelMeta,
    Relationship, RelationType, Status, Strength,
)
from architecture_model.core.parser import save_model
from architecture_model.decompose import decompose_model, write_sub_models


def _setup_project(tmp_path):
    """Create a minimal project with parent model, config, and recursive manifest.

    Uses src-layout so discover_config() finds source_root=src/myproject
    and creates F1 for the 'core' subpackage.
    """
    # Source files (need __init__.py at package root for src-layout detection)
    pkg_root = tmp_path / "src" / "myproject"
    pkg_root.mkdir(parents=True)
    (pkg_root / "__init__.py").write_text("")

    pkg = pkg_root / "core"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "parser.py").write_text(textwrap.dedent('''
        """Parser module."""
        def parse(data: str) -> dict:
            """Parse input data into structured format."""
            return {"raw": data}

        def validate(data: str) -> bool:
            """Check if data is valid."""
            return bool(data)
    '''))
    (pkg / "validator.py").write_text(textwrap.dedent('''
        """Validator module."""
        def check(model: dict) -> list:
            """Run validation checks."""
            return []
    '''))

    # Parent model
    model = ArchitectureModel(
        meta=ModelMeta(schema_version="2.0", project="test", generated_at="2026-01-01"),
        entities=Entities(
            components=[
                Component(id="COMP-CORE", name="Core", status=Status.ACTIVE, kind=ComponentKind.PACKAGE),
                Component(id="COMP-CORE-PARSER", name="Parser", status=Status.ACTIVE,
                         files=["src/myproject/core/parser.py"], kind=ComponentKind.MODULE),
                Component(id="COMP-CORE-VALIDATOR", name="Validator", status=Status.ACTIVE,
                         files=["src/myproject/core/validator.py"], kind=ComponentKind.MODULE),
            ],
        ),
        relationships=[
            Relationship(type=RelationType.CONTAINS, from_id="COMP-CORE", to_id="COMP-CORE-PARSER"),
            Relationship(type=RelationType.CONTAINS, from_id="COMP-CORE", to_id="COMP-CORE-VALIDATOR"),
            Relationship(type=RelationType.DEPENDS_ON, from_id="COMP-CORE-VALIDATOR", to_id="COMP-CORE-PARSER"),
        ],
    )
    save_model(model, tmp_path / ".architecture-model.yaml")

    # Discover the block ID that will be assigned by discover_config
    # (sorted subdirs of src/myproject → core → F1)
    block_id = "F1"

    # Recursive manifest
    manifest_dir = tmp_path / "output" / "manifests" / block_id
    manifest_dir.mkdir(parents=True)
    manifest = {
        "block_id": block_id,
        "block_name": "Core",
        "parent_model": ".architecture-model.yaml",
        "component_id": "COMP-CORE",
        "manifest": {
            "generated_at": "2026-01-01",
            "project_root": str(tmp_path),
            "metrics": {"py_files": 3, "functions": 3},
            "functional_blocks": {},
            "modules": [
                {
                    "file": "src/myproject/core/parser.py",
                    "name": "Parser module",
                    "docstring": "Parser module.",
                    "functions": [
                        {"name": "parse", "signature": "parse(data: str) -> dict",
                         "calls": [], "docstring": "Parse input data into structured format.", "raises": []},
                        {"name": "validate", "signature": "validate(data: str) -> bool",
                         "calls": ["bool"], "docstring": "Check if data is valid.", "raises": []},
                    ],
                    "imports": [], "line_count": 10, "status": "active", "classes": [],
                    "exports": [], "decorated_functions": [], "imports_detailed": [],
                    "module_constants": {}, "module_assignments": {},
                },
                {
                    "file": "src/myproject/core/validator.py",
                    "name": "Validator module",
                    "docstring": "Validator module.",
                    "functions": [
                        {"name": "check", "signature": "check(model: dict) -> list",
                         "calls": [], "docstring": "Run validation checks.", "raises": []},
                    ],
                    "imports": [], "line_count": 5, "status": "active", "classes": [],
                    "exports": [], "decorated_functions": [], "imports_detailed": [],
                    "module_constants": {}, "module_assignments": {},
                },
            ],
            "interfaces": [
                {"source": "src/myproject/core/validator.py",
                 "target": "src/myproject/core/parser.py",
                 "import_path": "myproject.core.parser"},
            ],
        },
        "children": {},
    }
    (manifest_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    return tmp_path, block_id


def test_decompose_produces_sub_model(tmp_path):
    root, block_id = _setup_project(tmp_path)
    results = decompose_model(root)
    assert block_id in results, f"Expected {block_id} in {list(results.keys())}"
    sub = results[block_id]
    assert sub.meta.parent_model == "../../.architecture-model.yaml"
    assert sub.meta.refines_component == "COMP-CORE"
    # Should include parser + validator (not the parent COMP-CORE which has no files)
    assert len(sub.entities.components) == 2


def test_decompose_derives_capabilities(tmp_path):
    root, block_id = _setup_project(tmp_path)
    results = decompose_model(root)
    sub = results[block_id]
    # parse, validate, check = 3 capabilities
    assert len(sub.entities.capabilities) >= 3


def test_decompose_derives_interfaces(tmp_path):
    root, block_id = _setup_project(tmp_path)
    results = decompose_model(root)
    sub = results[block_id]
    assert len(sub.entities.interfaces) >= 1  # validator -> parser


def test_decompose_preserves_parent_relationships(tmp_path):
    root, block_id = _setup_project(tmp_path)
    results = decompose_model(root)
    sub = results[block_id]
    dep_rels = [r for r in sub.relationships if r.type == RelationType.DEPENDS_ON]
    assert len(dep_rels) >= 1


def test_write_sub_models(tmp_path):
    root, block_id = _setup_project(tmp_path)
    results = decompose_model(root)
    out_dir = tmp_path / ".architecture-models"
    written = write_sub_models(results, out_dir)
    assert len(written) >= 1
    assert (out_dir / block_id / ".architecture-model.yaml").exists()
    data = yaml.safe_load((out_dir / block_id / ".architecture-model.yaml").read_text())
    assert data["meta"]["parent_model"] == "../../.architecture-model.yaml"
    assert "entities" in data


def test_decompose_cli(tmp_path):
    """Test the CLI decompose command end-to-end."""
    from architecture_model.cli.main import main

    root, block_id = _setup_project(tmp_path)
    out_dir = tmp_path / ".architecture-models"
    ret = main(["decompose", str(root), "-o", str(out_dir)])
    assert ret == 0
    assert (out_dir / block_id / ".architecture-model.yaml").exists()


def test_cross_block_dependencies(tmp_path):
    """Test cross-block dependency computation from import analysis."""
    from architecture_model.manifest.recursive import compute_block_dependencies
    from architecture_model.manifest.types import Manifest, MetricsResult, ModuleInfo, RecursiveManifest, ScanReport

    # Simulate two blocks: F1 (core) imports from F2 (utils)
    mod_core = ModuleInfo(
        file="src/pkg/core/parser.py",
        name="parser",
        docstring="",
        functions=[],
        line_count=10,
        status="active",
        classes=[],
        imports=["src.pkg.utils.helpers"],
        imports_detailed=[{"module": "src/pkg/utils/helpers"}],
    )
    mod_utils = ModuleInfo(
        file="src/pkg/utils/helpers.py",
        name="helpers",
        docstring="",
        functions=[],
        line_count=10,
        status="active",
        classes=[],
        imports=[],
        imports_detailed=[],
    )
    manifest_core = Manifest(
        generated_at="2026-01-01", project_root=str(tmp_path),
        metrics=MetricsResult(values={}), functional_blocks={},
        modules=[mod_core], interfaces=[], scan_report=ScanReport(),
    )
    manifest_utils = Manifest(
        generated_at="2026-01-01", project_root=str(tmp_path),
        metrics=MetricsResult(values={}), functional_blocks={},
        modules=[mod_utils], interfaces=[], scan_report=ScanReport(),
    )
    manifests = {
        "F1": RecursiveManifest(block_id="F1", block_name="Core", parent_model="m.yaml",
                                component_id="COMP-CORE", manifest=manifest_core),
        "F2": RecursiveManifest(block_id="F2", block_name="Utils", parent_model="m.yaml",
                                component_id="COMP-UTILS", manifest=manifest_utils),
    }

    class FakeConfig:
        fblock_dict = {
            "F1": {"name": "Core", "dirs": ["src/pkg/core"]},
            "F2": {"name": "Utils", "dirs": ["src/pkg/utils"]},
        }

    deps = compute_block_dependencies(manifests, FakeConfig())
    assert "F2" in deps["F1"], f"F1 should depend on F2, got {deps}"
    assert deps["F2"] == [], f"F2 should have no deps, got {deps['F2']}"


def test_derive_interfaces_uses_imports_detailed(tmp_path):
    """derive_interfaces resolves imports_detailed (relative + absolute) to edges."""
    from architecture_model.manifest.interfaces import derive_interfaces
    from architecture_model.manifest.types import ImportDetail, ModuleInfo, ScanReport

    mod_a = ModuleInfo(
        file="src/pkg/core/parser.py", name="parser", docstring="",
        functions=[], line_count=10, status="active", classes=[],
        imports=[], imports_detailed=[
            ImportDetail(module="types", is_relative=True),  # from .types
            ImportDetail(module="pkg.utils.helpers", is_relative=False),  # absolute
        ],
    )
    mod_b = ModuleInfo(
        file="src/pkg/core/types.py", name="types", docstring="",
        functions=[], line_count=5, status="active", classes=[],
        imports=[], imports_detailed=[],
    )
    mod_c = ModuleInfo(
        file="src/pkg/utils/helpers.py", name="helpers", docstring="",
        functions=[], line_count=5, status="active", classes=[],
        imports=[], imports_detailed=[],
    )
    edges = derive_interfaces([mod_a, mod_b, mod_c], tmp_path)
    sources_targets = {(e.source, Path(e.target).stem) for e in edges}
    assert ("src/pkg/core/parser.py", "types") in sources_targets, f"Missing relative import edge: {sources_targets}"
    assert ("src/pkg/core/parser.py", "helpers") in sources_targets, f"Missing absolute import edge: {sources_targets}"


def test_capabilities_filter_private_and_exports():
    """Capabilities skip _private functions and respect __init__.py exports."""
    from architecture_model.decompose import _derive_capabilities

    manifest_data = {
        "manifest": {
            "modules": [
                {
                    "file": "src/pkg/core/__init__.py",
                    "exports": ["parse", "validate"],  # only these exported
                    "functions": [],
                },
                {
                    "file": "src/pkg/core/parser.py",
                    "functions": [
                        {"name": "parse", "docstring": "Parse data"},
                        {"name": "validate", "docstring": "Validate data"},
                        {"name": "_internal_helper", "docstring": ""},
                        {"name": "utility_not_exported", "docstring": ""},
                    ],
                },
            ],
        },
    }
    caps = _derive_capabilities(manifest_data, "F1")
    names = [c.name for c in caps]
    assert "parse" in names
    assert "validate" in names
    assert "_internal_helper" not in names, "Private functions should be filtered"
    assert "utility_not_exported" not in names, "Non-exported functions should be filtered"
    assert len(caps) == 2


def test_capabilities_fallback_no_exports():
    """Without __init__.py exports, include all non-underscore functions."""
    from architecture_model.decompose import _derive_capabilities

    manifest_data = {
        "manifest": {
            "modules": [
                {
                    "file": "src/pkg/core/parser.py",
                    "functions": [
                        {"name": "parse", "docstring": "Parse"},
                        {"name": "_helper", "docstring": ""},
                        {"name": "do_stuff", "docstring": ""},
                    ],
                },
            ],
        },
    }
    caps = _derive_capabilities(manifest_data, "F1")
    names = [c.name for c in caps]
    assert "parse" in names
    assert "do_stuff" in names
    assert "_helper" not in names
    assert len(caps) == 2
