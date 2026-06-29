"""Shared fixtures for architecture model tests.

Integration tests (those needing real project output files) are automatically
skipped when the consumer project data is not available.  Set the environment
variable ARCHITECTURE_MODEL_PROJECT_ROOT to point at the consumer project
(e.g. logs-db) to enable integration tests.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from architecture_model.core.parser import load_model
from architecture_model.core.types import ArchitectureModel

# ---------------------------------------------------------------------------
# Path resolution — prefer env var, fallback to sibling project assumption
# ---------------------------------------------------------------------------

_env_root = os.environ.get("ARCHITECTURE_MODEL_PROJECT_ROOT")
if _env_root:
    PROJECT_ROOT = Path(_env_root).resolve()
else:
    # Default: assume logs-db is a sibling directory
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = PROJECT_ROOT / "output" / "logs-db" / "architecture-model.yaml"
MANIFEST_PATH = PROJECT_ROOT / "output" / "logs-db" / "reality-manifest.json"
ARTIFACTS_DIR = PROJECT_ROOT / "output" / "logs-db" / "artifacts" / "stage2"

# Test-local fixtures path
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
TEST_CONFIG_PATH = FIXTURES_DIR / ".architecture-model.yaml"

# Flags for skipping integration tests
HAS_MODEL = MODEL_PATH.exists()
HAS_MANIFEST = MANIFEST_PATH.exists()
HAS_ARTIFACTS = ARTIFACTS_DIR.exists()

requires_model = pytest.mark.skipif(not HAS_MODEL, reason=f"Model file not found: {MODEL_PATH}")
requires_manifest = pytest.mark.skipif(
    not HAS_MANIFEST, reason=f"Manifest file not found: {MANIFEST_PATH}"
)
requires_artifacts = pytest.mark.skipif(
    not HAS_ARTIFACTS, reason=f"Artifacts dir not found: {ARTIFACTS_DIR}"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def model() -> ArchitectureModel:
    """Load the real architecture model (session-scoped for speed)."""
    if not HAS_MODEL:
        pytest.skip(f"Model file not found: {MODEL_PATH}")
    return load_model(MODEL_PATH)


@pytest.fixture(scope="session")
def manifest() -> dict:
    """Load the real reality manifest (session-scoped for speed)."""
    if not HAS_MANIFEST:
        pytest.skip(f"Manifest file not found: {MANIFEST_PATH}")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def artifacts_dir() -> Path:
    """Return path to stage2 artifacts directory."""
    if not HAS_ARTIFACTS:
        pytest.skip(f"Artifacts dir not found: {ARTIFACTS_DIR}")
    return ARTIFACTS_DIR
