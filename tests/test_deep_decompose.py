"""Tests for recursive deep decomposition."""
from pathlib import Path

from architecture_model.orchestration.deep_decompose import (
    deep_decompose_block,
    DecomposeResult,
)
from architecture_model.manifest.recursive import generate_block_manifest


def _create_block_with_modules(tmp_path, n_modules=20, n_groups=4):
    """Create a block with n_modules arranged in n_groups of import clusters."""
    pkg = tmp_path / "myapp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")

    group_size = n_modules // n_groups
    for g in range(n_groups):
        subpkg = pkg / f"group{g}"
        subpkg.mkdir()
        (subpkg / "__init__.py").write_text("")
        for i in range(group_size):
            imports = f"from myapp.group{g}.mod{max(0,i-1)} import something\n" if i > 0 else ""
            content = f'"""Module {g}_{i}."""\n{imports}class Class{g}_{i}:\n    pass\n' + "\n" * 50
            (subpkg / f"mod{i}.py").write_text(content)

    # Cross-group: each group's first module imports from group0
    for g in range(1, n_groups):
        existing = (pkg / f"group{g}" / "mod0.py").read_text()
        (pkg / f"group{g}" / "mod0.py").write_text(
            f"from myapp.group0.mod0 import Class0_0\n" + existing
        )

    return pkg


def test_deep_decompose_produces_sub_components(tmp_path):
    """Deep decomposition breaks a large block into sub-components."""
    pkg = _create_block_with_modules(tmp_path, n_modules=20, n_groups=4)
    block_def = {"name": "MyBlock", "dirs": ["myapp"], "files": []}
    manifest = generate_block_manifest(tmp_path, "S1", block_def)

    result = deep_decompose_block(manifest, block_id="S1", block_name="MyBlock")

    assert isinstance(result, DecomposeResult)
    assert len(result.sub_components) >= 2
    assert len(result.sub_components) <= 8
    # All non-init modules accounted for
    all_files = set()
    for sc in result.sub_components:
        all_files.update(sc.files)
    manifest_files = {m.file for m in manifest.modules if "__init__" not in m.file}
    assert manifest_files.issubset(all_files)


def test_deep_decompose_skips_small_blocks(tmp_path):
    """Blocks with few modules don't get decomposed."""
    pkg = tmp_path / "small"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for i in range(5):
        (pkg / f"mod{i}.py").write_text(f'"""M{i}."""\nclass C{i}: pass\n' + "\n" * 50)

    block_def = {"name": "Small", "dirs": ["small"], "files": []}
    manifest = generate_block_manifest(tmp_path, "S1", block_def)

    result = deep_decompose_block(manifest, block_id="S1", block_name="Small")
    assert result.sub_components == []


def test_deep_decompose_produces_relationships(tmp_path):
    """Sub-components have dependency relationships between them."""
    pkg = _create_block_with_modules(tmp_path, n_modules=20, n_groups=4)
    block_def = {"name": "MyBlock", "dirs": ["myapp"], "files": []}
    manifest = generate_block_manifest(tmp_path, "S1", block_def)

    result = deep_decompose_block(manifest, block_id="S1", block_name="MyBlock")
    assert len(result.internal_relationships) > 0
