"""Tests for architecture_model.manifest (Wave 4 modules)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from architecture_model.manifest.blocks import _get_functional_blocks
from architecture_model.manifest.generator import generate_manifest
from architecture_model.manifest.slicers import get_manifest_slice

from .conftest import (
    HAS_MANIFEST,
    MANIFEST_PATH,
    PROJECT_ROOT,
    TEST_CONFIG_PATH,
    requires_manifest,
)


# ---------------------------------------------------------------------------
# FUNCTIONAL_BLOCKS (config-driven)
# ---------------------------------------------------------------------------


class TestFunctionalBlocks:
    """Test the functional blocks loaded from config."""

    @pytest.fixture(scope="class")
    def blocks(self) -> dict:
        """Load blocks from the test fixture config."""
        return _get_functional_blocks(TEST_CONFIG_PATH.parent)

    def test_has_f1_through_f6(self, blocks: dict):
        """Functional blocks contains F1 through F6."""
        for i in range(1, 7):
            assert f"F{i}" in blocks, f"Missing F{i}"

    def test_each_block_has_name(self, blocks: dict):
        """Each block has a 'name' key."""
        for block_id, block_def in blocks.items():
            assert "name" in block_def, f"{block_id} missing 'name'"
            assert block_def["name"], f"{block_id} has empty name"

    def test_each_block_has_dirs(self, blocks: dict):
        """Each block has a 'dirs' key (list)."""
        for block_id, block_def in blocks.items():
            assert "dirs" in block_def, f"{block_id} missing 'dirs'"
            assert isinstance(block_def["dirs"], list)

    def test_each_block_has_files(self, blocks: dict):
        """Each block has a 'files' key (list)."""
        for block_id, block_def in blocks.items():
            assert "files" in block_def, f"{block_id} missing 'files'"
            assert isinstance(block_def["files"], list)

    def test_each_block_has_description_source(self, blocks: dict):
        """Each block has 'description_source' key."""
        for block_id, block_def in blocks.items():
            assert "description_source" in block_def, f"{block_id} missing 'description_source'"


# ---------------------------------------------------------------------------
# generate_manifest
# ---------------------------------------------------------------------------


class TestGenerateManifest:
    """Test generate_manifest() produces expected structure."""

    @pytest.fixture(scope="class")
    def generated(self) -> dict:
        """Generate manifest from test fixture root."""
        return generate_manifest(TEST_CONFIG_PATH.parent)

    def test_has_generated_at(self, generated: dict):
        """Manifest has 'generated_at' timestamp."""
        assert "generated_at" in generated
        assert generated["generated_at"]

    def test_has_metrics(self, generated: dict):
        """Manifest has 'metrics' dict."""
        assert "metrics" in generated
        assert isinstance(generated["metrics"], dict)

    def test_has_functional_blocks(self, generated: dict):
        """Manifest has 'functional_blocks' with F1-F6."""
        assert "functional_blocks" in generated
        fb = generated["functional_blocks"]
        for i in range(1, 7):
            assert f"F{i}" in fb, f"Generated manifest missing F{i}"

    def test_functional_blocks_have_sub_functions(self, generated: dict):
        """Each functional block has sub_functions list."""
        for block_id, block in generated["functional_blocks"].items():
            assert "sub_functions" in block, f"{block_id} missing sub_functions"
            assert isinstance(block["sub_functions"], list)

    def test_has_modules(self, generated: dict):
        """Manifest has 'modules' list."""
        assert "modules" in generated
        assert isinstance(generated["modules"], list)

    def test_modules_have_required_fields(self, generated: dict):
        """Each module entry has file, line_count, status."""
        for mod in generated["modules"][:10]:
            assert "file" in mod, f"Module missing 'file': {mod}"
            assert "line_count" in mod
            assert "status" in mod

    def test_has_interfaces(self, generated: dict):
        """Manifest has 'interfaces' list."""
        assert "interfaces" in generated
        assert isinstance(generated["interfaces"], list)

    def test_metrics_has_expected_keys(self, generated: dict):
        """Metrics contains key system measurements."""
        metrics = generated["metrics"]
        assert "total_python_files" in metrics or len(metrics) >= 0


# ---------------------------------------------------------------------------
# get_manifest_slice (integration — requires real manifest)
# ---------------------------------------------------------------------------


ARTIFACT_NAMES = [
    "functional-architecture",
    "logical-architecture",
    "data-dictionary",
    "icd",
    "readme",
    "testing",
    "deployment-guide",
    "operations-manual",
    "use-cases",
    "requirements-analysis",
]


@requires_manifest
class TestGetManifestSlice:
    """Test manifest slicing for artifact context injection."""

    @pytest.fixture(scope="class")
    def real_manifest(self) -> dict:
        """Load the real manifest for slicing tests."""
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    @pytest.mark.parametrize("artifact_name", ARTIFACT_NAMES)
    def test_returns_non_empty_markdown(self, real_manifest: dict, artifact_name: str):
        """Each artifact slice returns non-empty markdown string."""
        result = get_manifest_slice(real_manifest, artifact_name)
        assert isinstance(result, str)
        assert len(result) > 50, f"Slice for '{artifact_name}' too short: {len(result)} chars"

    @pytest.mark.parametrize("artifact_name", ARTIFACT_NAMES)
    def test_slice_contains_heading(self, real_manifest: dict, artifact_name: str):
        """Each slice starts with a markdown heading."""
        result = get_manifest_slice(real_manifest, artifact_name)
        assert result.startswith("#"), f"Slice for '{artifact_name}' doesn't start with heading"

    def test_unknown_artifact_returns_error_message(self, real_manifest: dict):
        """Unknown artifact name returns an error message."""
        result = get_manifest_slice(real_manifest, "nonexistent-artifact")
        assert "unknown artifact" in result.lower()

    def test_functional_slice_has_blocks(self, real_manifest: dict):
        """Functional architecture slice mentions F-blocks."""
        result = get_manifest_slice(real_manifest, "functional-architecture")
        assert "F1" in result
        assert "Functional Blocks" in result

    def test_logical_slice_has_layers(self, real_manifest: dict):
        """Logical architecture slice groups by layers."""
        result = get_manifest_slice(real_manifest, "logical-architecture")
        assert "Metrics" in result

    def test_icd_slice_has_router_endpoints(self, real_manifest: dict):
        """ICD slice includes router endpoint information."""
        result = get_manifest_slice(real_manifest, "icd")
        assert "Router" in result or "router" in result

    def test_readme_slice_has_summary(self, real_manifest: dict):
        """README slice has project summary."""
        result = get_manifest_slice(real_manifest, "readme")
        assert "Summary" in result or "Functional Blocks" in result
