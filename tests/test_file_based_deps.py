"""Tests that compute_block_dependencies resolves file-based F-blocks."""
from pathlib import Path

from architecture_model.manifest.recursive import (
    generate_recursive_manifests,
    compute_block_dependencies,
)


def test_file_based_blocks_resolve_dependencies(tmp_path):
    """F-blocks defined with files: (not dirs:) are found in dependency resolution."""
    pkg = tmp_path / "myapp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text(
        '"""Core module."""\nclass EventBus:\n    pass\n' + "\n" * 60
    )
    (pkg / "config.py").write_text(
        '"""Config."""\nfrom myapp.core import EventBus\n\nclass ConfigEntry:\n    pass\n' + "\n" * 60
    )
    (pkg / "helpers.py").write_text(
        '"""Helpers."""\nimport myapp.core\nimport myapp.config\n\ndef helper(): pass\n' + "\n" * 60
    )

    config_yaml = tmp_path / ".architecture-model.yaml"
    config_yaml.write_text(
        "functional_blocks:\n"
        "  F1:\n"
        "    name: Core\n"
        "    dirs: []\n"
        "    files:\n"
        "      - myapp/core.py\n"
        "  F2:\n"
        "    name: Config\n"
        "    dirs: []\n"
        "    files:\n"
        "      - myapp/config.py\n"
        "  F3:\n"
        "    name: Helpers\n"
        "    dirs: []\n"
        "    files:\n"
        "      - myapp/helpers.py\n"
    )

    manifests = generate_recursive_manifests(tmp_path)
    # Pass config=None to test that it reconstructs from manifests
    deps = compute_block_dependencies(manifests, None)

    assert "F1" in deps.get("F2", []), f"F2 should depend on F1, got: {deps}"
    assert "F1" in deps.get("F3", []), f"F3 should depend on F1, got: {deps}"
    assert "F2" in deps.get("F3", []), f"F3 should depend on F2, got: {deps}"
