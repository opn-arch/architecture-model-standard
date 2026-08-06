"""Tests for deepened manifest types and AST extraction."""
import textwrap
from pathlib import Path

from architecture_model.manifest.types import FunctionInfo
from architecture_model.manifest.scanner import scan_file


def test_function_info_new_fields_defaults():
    fi = FunctionInfo(name="foo", signature="foo()")
    assert fi.calls == []
    assert fi.docstring is None
    assert fi.raises == []


def test_function_info_new_fields_explicit():
    fi = FunctionInfo(name="foo", signature="foo()", docstring="doc", calls=["bar"], raises=["ValueError"])
    assert fi.docstring == "doc"
    assert fi.calls == ["bar"]
    assert fi.raises == ["ValueError"]


def test_scanner_extracts_function_docstring(tmp_path):
    src = tmp_path / "example.py"
    src.write_text(textwrap.dedent('''
        def greet(name: str) -> str:
            """Return a greeting for the given name."""
            return f"Hello, {name}"
    '''))
    info = scan_file(tmp_path, src)
    assert info.functions[0].docstring == "Return a greeting for the given name."


def test_scanner_extracts_function_calls(tmp_path):
    src = tmp_path / "example.py"
    src.write_text(textwrap.dedent('''
        def process(data):
            validated = validate(data)
            result = transform(validated)
            return format_output(result)
    '''))
    info = scan_file(tmp_path, src)
    func = info.functions[0]
    assert "validate" in func.calls
    assert "transform" in func.calls
    assert "format_output" in func.calls


def test_scanner_extracts_raises(tmp_path):
    src = tmp_path / "example.py"
    src.write_text(textwrap.dedent('''
        def divide(a, b):
            if b == 0:
                raise ValueError("Cannot divide by zero")
            if not isinstance(a, (int, float)):
                raise TypeError("a must be numeric")
            return a / b
    '''))
    info = scan_file(tmp_path, src)
    func = info.functions[0]
    assert "ValueError" in func.raises
    assert "TypeError" in func.raises


def test_scanner_docstring_none_when_absent(tmp_path):
    src = tmp_path / "example.py"
    src.write_text('def nodoc(): return 42\n')
    info = scan_file(tmp_path, src)
    assert info.functions[0].docstring is None


def test_to_dict_includes_new_fields_when_present(tmp_path):
    src = tmp_path / "example.py"
    src.write_text(textwrap.dedent('''
        def greet(name: str) -> str:
            """Say hello."""
            return format_name(name)
    '''))
    info = scan_file(tmp_path, src)
    d = info.to_dict()
    func_dict = d["functions"][0]
    assert func_dict["docstring"] == "Say hello."
    assert "format_name" in func_dict["calls"]


def test_to_dict_omits_empty_new_fields():
    fi = FunctionInfo(name="foo", signature="foo()")
    from architecture_model.manifest.types import ModuleInfo, ModuleStatus
    mod = ModuleInfo(
        file="test.py", name="Test", docstring=None,
        functions=[fi], imports=[], line_count=1,
        status=ModuleStatus.DORMANT, classes=[],
    )
    d = mod.to_dict()
    func_dict = d["functions"][0]
    assert "calls" not in func_dict
    assert "docstring" not in func_dict
    assert "raises" not in func_dict


import yaml as _yaml

from architecture_model.manifest.types import RecursiveManifest, Manifest, MetricsResult, ScanReport


def test_recursive_manifest_type():
    rm = RecursiveManifest(
        block_id="S1", block_name="Core", parent_model=".architecture-model.yaml",
        component_id="COMP-CORE",
        manifest=Manifest(
            generated_at="2026-01-01", project_root="/tmp",
            metrics=MetricsResult(), functional_blocks={}, modules=[], interfaces=[],
        ),
    )
    d = rm.to_dict()
    assert d["block_id"] == "S1"
    assert d["component_id"] == "COMP-CORE"
    assert "manifest" in d
    assert d["children"] == {}


def test_recursive_generator(tmp_path):
    from architecture_model.manifest.recursive import generate_recursive_manifests
    pkg = tmp_path / "src" / "proj"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text('def hello(): return "hi"\n')
    (tmp_path / ".architecture-model.yaml").write_text(_yaml.dump({
        "project": {"name": "test", "system": "test-system"}, "source_root": "src/proj",
        "functional_blocks": {"S1": {"name": "Core", "dirs": ["src/proj"], "files": [], "description_source": "x"}}
    }))
    results = generate_recursive_manifests(tmp_path)
    assert "S1" in results
    rm = results["S1"]
    assert rm.block_name == "Core"
    assert len(rm.manifest.modules) >= 1


def test_write_recursive_manifests(tmp_path):
    from architecture_model.manifest.recursive import write_recursive_manifests
    rm = RecursiveManifest(
        block_id="S1", block_name="Core", parent_model=".architecture-model.yaml",
        component_id="COMP-CORE",
        manifest=Manifest(
            generated_at="2026-01-01", project_root="/tmp",
            metrics=MetricsResult(), functional_blocks={}, modules=[], interfaces=[],
        ),
    )
    out_dir = tmp_path / "output"
    written = write_recursive_manifests({"S1": rm}, out_dir)
    assert len(written) == 1
    assert (out_dir / "S1" / "manifest.json").exists()
    import json
    data = json.loads((out_dir / "S1" / "manifest.json").read_text())
    assert data["block_id"] == "S1"
