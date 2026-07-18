"""Tests for typed BlockManifest returns from blocks.py."""

from pathlib import Path

from architecture_model.manifest.types import BlockManifest, SubFunctionEntry


def test_process_block_returns_block_manifest(tmp_path):
    pkg = tmp_path / "mymod"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text('"""Core logic."""\ndef compute(x: int) -> int:\n    return x * 2\n')

    from architecture_model.manifest.blocks import process_block

    block_def = {"name": "MyBlock", "dirs": ["mymod"], "files": [], "description_source": "test"}
    result = process_block(tmp_path, "F1", block_def)
    assert isinstance(result, BlockManifest)
    assert result.name == "MyBlock"
    assert len(result.sub_functions) >= 1
    assert all(isinstance(sf, SubFunctionEntry) for sf in result.sub_functions)


def test_process_block_backward_compat(tmp_path):
    pkg = tmp_path / "mod"
    pkg.mkdir()
    (pkg / "a.py").write_text("x = 1\n")

    from architecture_model.manifest.blocks import process_block

    block_def = {"name": "Test", "dirs": ["mod"], "files": [], "description_source": "test"}
    d = process_block(tmp_path, "F1", block_def).to_dict()
    assert "name" in d
    assert "sub_functions" in d
    assert isinstance(d["sub_functions"], list)


def test_deprecated_process_block_returns_dict(tmp_path):
    """_process_block still returns a dict for backward compat."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "mod.py").write_text("def hello(): pass\n")

    from architecture_model.manifest.blocks import _process_block

    block_def = {"name": "Pkg", "dirs": ["pkg"], "files": [], "description_source": "test"}
    result = _process_block(tmp_path, "F1", block_def)
    assert isinstance(result, dict)
    assert result["name"] == "Pkg"


def test_sub_function_entry_has_signature_strings(tmp_path):
    """functions field should contain signature strings, not FunctionInfo objects."""
    pkg = tmp_path / "mymod"
    pkg.mkdir()
    (pkg / "core.py").write_text("def foo(x: int) -> str:\n    return str(x)\n")

    from architecture_model.manifest.blocks import process_block

    block_def = {"name": "M", "dirs": ["mymod"], "files": [], "description_source": "t"}
    result = process_block(tmp_path, "F1", block_def)
    for sf in result.sub_functions:
        for f in sf.functions:
            assert isinstance(f, str), f"Expected str, got {type(f)}"
