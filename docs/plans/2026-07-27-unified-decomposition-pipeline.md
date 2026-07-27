# Unified Decomposition Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a single `run_pipeline(project_root)` function that chains: recursive manifests → decompose → write all artifacts, with proper support for file-based F-blocks.

**Architecture:** Add `orchestration/pipeline.py` as the unified entry point. Fix `compute_block_dependencies()` to handle file-based F-blocks (not just dir-prefix matching). The pipeline produces co-located artifacts in `.architecture-models/<block_id>/` (manifest.json + .architecture-model.yaml).

**Tech Stack:** Python 3.11+, architecture-model-standard internals, pytest

---

### Task 1: Fix `compute_block_dependencies()` for file-based F-blocks

The root cause: `_resolve_import_to_block()` in `manifest/recursive.py:168` only indexes `dirs` entries. F-blocks with `files:` (like HA's F1-F3) never get indexed, so imports to those files can't be resolved to blocks.

**Files:**
- Modify: `src/architecture_model/manifest/recursive.py:160-180`
- Test: `tests/test_file_based_deps.py`

**Step 1: Write the failing test**

```python
"""Tests that compute_block_dependencies resolves file-based F-blocks."""
import tempfile
from pathlib import Path

from architecture_model.manifest.recursive import (
    generate_recursive_manifests,
    compute_block_dependencies,
)


def test_file_based_blocks_resolve_dependencies(tmp_path):
    """F-blocks defined with files: (not dirs:) are found in dependency resolution."""
    # Create source files
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

    # Config with file-based F-blocks
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
    deps = compute_block_dependencies(manifests, None)

    # Config imports from Core
    assert "F1" in deps.get("F2", []), f"F2 should depend on F1, got: {deps}"
    # Helpers imports from both Core and Config
    assert "F1" in deps.get("F3", []), f"F3 should depend on F1, got: {deps}"
    assert "F2" in deps.get("F3", []), f"F3 should depend on F2, got: {deps}"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_file_based_deps.py -v`
Expected: FAIL — F2 deps will be empty because file-based blocks aren't indexed

**Step 3: Implement the fix**

In `manifest/recursive.py`, modify `compute_block_dependencies()` to also index `files:` entries:

```python
def compute_block_dependencies(
    manifests: dict[str, "RecursiveManifest"],
    config,
) -> dict[str, list[str]]:
    # If config is None, reconstruct from manifests
    if config is None:
        # Build a minimal config-like dict from what we have
        fblock_dict = {}
        for block_id, rm in manifests.items():
            fblock_dict[block_id] = {
                "name": rm.block_name,
                "dirs": [],
                "files": [m.file for m in rm.manifest.modules],
            }
    else:
        fblock_dict = config.fblock_dict

    # Build file -> block_id mapping from BOTH dirs and files
    file_to_block: dict[str, str] = {}
    dir_prefixes: dict[str, str] = {}  # dir prefix -> block_id
    
    for block_id, block_def in fblock_dict.items():
        for d in block_def.get("dirs", []):
            dir_prefixes[d.rstrip("/")] = block_id
        for f in block_def.get("files", []):
            # Index by module path (without .py extension, dots as separators)
            module_path = f.replace("/", ".").removesuffix(".py")
            file_to_block[module_path] = block_id
            # Also index the slash form
            file_to_block[f.removesuffix(".py")] = block_id

    def _resolve_import_to_block(import_path: str) -> str | None:
        """Map import path to block_id via dir prefix OR file matching."""
        # Try exact file match first
        if import_path in file_to_block:
            return file_to_block[import_path]
        # Try dot-form
        dot_form = import_path.replace("/", ".")
        if dot_form in file_to_block:
            return file_to_block[dot_form]
        # Try dir prefix matching
        for dir_prefix, bid in dir_prefixes.items():
            norm_prefix = dir_prefix.replace(".", "/").rstrip("/")
            if import_path.startswith(norm_prefix + "/") or import_path == norm_prefix:
                return bid
            if norm_prefix.startswith("src/"):
                stripped = norm_prefix[4:]
                if import_path.startswith(stripped + "/") or import_path == stripped:
                    return bid
        return None

    # ... rest of function unchanged (the loop over manifests)
```

**Step 4: Run tests**

Run: `pytest tests/test_file_based_deps.py tests/test_dependency_diff.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git commit -m "fix: compute_block_dependencies resolves file-based F-blocks"
```

---

### Task 2: Create unified pipeline function

**Files:**
- Create: `src/architecture_model/orchestration/pipeline.py`
- Test: `tests/test_pipeline.py`

**Step 1: Write the failing test**

```python
"""Tests for the unified decomposition pipeline."""
import textwrap
from pathlib import Path

from architecture_model.orchestration.pipeline import run_pipeline, PipelineResult


def _setup_project(tmp_path):
    """Minimal project with config + parent model + source."""
    pkg = tmp_path / "src" / "myapp"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    
    core = pkg / "core"
    core.mkdir()
    (core / "__init__.py").write_text("")
    (core / "bus.py").write_text(
        '"""Event bus."""\nclass EventBus:\n    def fire(self): pass\n' + "\n" * 60
    )
    
    api = pkg / "api"
    api.mkdir()
    (api / "__init__.py").write_text("")
    (api / "handler.py").write_text(
        '"""API handler."""\nfrom myapp.core.bus import EventBus\nclass Handler:\n    pass\n' + "\n" * 60
    )

    # Config
    (tmp_path / ".architecture-model.yaml").write_text(textwrap.dedent("""\
        meta:
          project: test-pipeline
          schema_version: '2.0'
        entities:
          components:
            - id: COMP-CORE
              name: Core
              status: ACTIVE
              f_block: F1
              files:
                - src/myapp/core/bus.py
            - id: COMP-API
              name: API
              status: ACTIVE
              f_block: F2
              files:
                - src/myapp/api/handler.py
          capabilities:
            - id: CAP-EVENTS
              name: Event System
              f_block: F1
              status: ACTIVE
        relationships:
          - from: COMP-CORE
            to: CAP-EVENTS
            type: realizes
          - from: COMP-API
            to: COMP-CORE
            type: depends-on
        functional_blocks:
          F1:
            name: Core
            dirs:
              - src/myapp/core
            files: []
          F2:
            name: API
            dirs:
              - src/myapp/api
            files: []
    """))

    return tmp_path


def test_run_pipeline_produces_manifests_and_sub_models(tmp_path):
    """Pipeline produces both recursive manifests and sub-models."""
    root = _setup_project(tmp_path)
    result = run_pipeline(root)

    assert isinstance(result, PipelineResult)
    assert "F1" in result.manifests
    assert "F2" in result.manifests
    assert "F1" in result.sub_models
    # F1 sub-model has the Core component
    assert any(c.id == "COMP-CORE" for c in result.sub_models["F1"].entities.components)


def test_run_pipeline_writes_artifacts(tmp_path):
    """Pipeline writes manifests and sub-models to .architecture-models/."""
    root = _setup_project(tmp_path)
    result = run_pipeline(root)

    out = root / ".architecture-models"
    assert (out / "F1" / "manifest.json").exists()
    assert (out / "F2" / "manifest.json").exists()
    assert (out / "F1" / ".architecture-model.yaml").exists()


def test_run_pipeline_computes_dependencies(tmp_path):
    """Pipeline computes cross-block dependencies."""
    root = _setup_project(tmp_path)
    result = run_pipeline(root)

    # API depends on Core
    f2_deps = result.manifests["F2"].block_dependencies
    assert "F1" in f2_deps
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL — `ImportError: cannot import name 'run_pipeline'`

**Step 3: Write minimal implementation**

```python
"""Unified decomposition pipeline.

Single entry point that chains:
1. Generate recursive manifests (per-block AST scan)
2. Decompose parent model into sub-models (relationship tracing)
3. Write all artifacts to .architecture-models/<block_id>/

Usage:
    from architecture_model.orchestration.pipeline import run_pipeline
    result = run_pipeline(Path("/path/to/repo"))
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from architecture_model.core.types import ArchitectureModel
from architecture_model.manifest.recursive import (
    RecursiveManifest,
    generate_recursive_manifests,
    write_recursive_manifests,
)
from architecture_model.manifest.types import RecursiveManifest as RecursiveManifestType
from architecture_model.orchestration.decompose import decompose_model, write_sub_models

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of running the full decomposition pipeline."""
    manifests: dict[str, RecursiveManifestType] = field(default_factory=dict)
    sub_models: dict[str, ArchitectureModel] = field(default_factory=dict)
    written_paths: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def run_pipeline(
    project_root: Path,
    *,
    parent_model: str = ".architecture-model.yaml",
    output_dir: str = ".architecture-models",
) -> PipelineResult:
    """Run the full decomposition pipeline.

    1. Generate recursive manifests (per-block AST scan + dependency analysis)
    2. Decompose parent model into sub-models (relationship tracing)
    3. Write all artifacts to output_dir/<block_id>/

    Args:
        project_root: Root directory with .architecture-model.yaml (config + model)
        parent_model: Filename of the parent model (default: .architecture-model.yaml)
        output_dir: Output directory name (default: .architecture-models)

    Returns:
        PipelineResult with manifests, sub_models, and written paths.
    """
    result = PipelineResult()
    out = project_root / output_dir

    # Step 1: Recursive manifests
    logger.info("Step 1: Generating recursive manifests...")
    try:
        manifests = generate_recursive_manifests(project_root, parent_model=parent_model)
        result.manifests = manifests
        paths = write_recursive_manifests(manifests, out)
        result.written_paths.extend(paths)
        logger.info("  Generated %d block manifests", len(manifests))
    except Exception as exc:
        result.errors.append(f"Manifest generation failed: {exc}")
        logger.error("Manifest generation failed: %s", exc)
        return result

    # Step 2: Decompose parent model
    model_path = project_root / parent_model
    if model_path.exists():
        logger.info("Step 2: Decomposing parent model into sub-models...")
        try:
            sub_models = decompose_model(project_root)
            result.sub_models = sub_models
            if sub_models:
                paths = write_sub_models(sub_models, out)
                result.written_paths.extend(paths)
                logger.info("  Generated %d sub-models", len(sub_models))
            else:
                logger.warning("  No sub-models generated (no matching components)")
        except Exception as exc:
            result.errors.append(f"Decomposition failed: {exc}")
            logger.error("Decomposition failed: %s", exc)
    else:
        logger.info("Step 2: Skipped (no parent model at %s)", model_path)

    return result
```

**Step 4: Run tests**

Run: `pytest tests/test_pipeline.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git commit -m "feat: unified decomposition pipeline (run_pipeline)"
```

---

### Task 3: Handle combined config+model YAML format

HA Core uses a single `.architecture-model.yaml` that has BOTH `functional_blocks:` (config) AND `entities:`/`relationships:` (model). The pipeline needs `decompose_model()` to load from the same file that may contain both.

Currently `decompose_model()` calls `load_model()` which expects a pure model file, and `get_config()` which expects a pure config file. When both are in one file, we need to handle this.

**Files:**
- Modify: `src/architecture_model/orchestration/decompose.py:232-233`
- Test: `tests/test_pipeline.py` (extend existing test)

**Step 1: Write failing test**

```python
def test_pipeline_handles_combined_config_model_file(tmp_path):
    """Pipeline works when .architecture-model.yaml has both config and model sections."""
    # This is how HA Core's file is structured: functional_blocks + entities + relationships
    pkg = tmp_path / "myapp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text('"""Core."""\nclass Core:\n    pass\n' + "\n" * 60)

    (tmp_path / ".architecture-model.yaml").write_text(textwrap.dedent("""\
        meta:
          project: combined
          schema_version: '2.0'
        functional_blocks:
          F1:
            name: Core
            dirs: []
            files:
              - myapp/core.py
        entities:
          components:
            - id: COMP-CORE
              name: Core
              status: ACTIVE
              f_block: F1
              files:
                - myapp/core.py
          capabilities:
            - id: CAP-CORE
              name: Core Capability
              status: ACTIVE
              f_block: F1
        relationships:
          - from: COMP-CORE
            to: CAP-CORE
            type: realizes
    """))

    result = run_pipeline(tmp_path)
    assert "F1" in result.manifests
    assert "F1" in result.sub_models
    assert len(result.errors) == 0
```

**Step 2: Run test — verify it fails (likely get_config can't parse combined file)**

**Step 3: Fix if needed — ensure config loader handles combined format**

**Step 4: Verify all tests pass**

**Step 5: Commit**

---

### Task 4: Export from `__init__.py` and verify full suite

**Files:**
- Modify: `src/architecture_model/__init__.py`
- Modify: `src/architecture_model/orchestration/__init__.py`

**Step 1: Add exports**

```python
# In orchestration/__init__.py
from architecture_model.orchestration.pipeline import run_pipeline, PipelineResult

# In top-level __init__.py
from architecture_model.orchestration.pipeline import run_pipeline
```

**Step 2: Run full test suite**

Run: `pytest tests/ --ignore=tests/test_config_loader.py -v`
Expected: All pass (506+ tests)

**Step 3: Commit**

```bash
git commit -m "feat: export run_pipeline from top-level package"
```

---

### Task 5: Validate pipeline on HA Core

**Manual verification (not automated test):**

```python
from pathlib import Path
from architecture_model.orchestration.pipeline import run_pipeline

result = run_pipeline(Path("/tmp/ha-core"))
print(f"Manifests: {len(result.manifests)}")
print(f"Sub-models: {len(result.sub_models)}")
print(f"Errors: {result.errors}")
for bid, sm in result.sub_models.items():
    print(f"  {bid}: {len(sm.entities.components)} comps, {len(sm.entities.capabilities)} caps")
```

Expected: 8 manifests, 8 sub-models (or close), no errors.

If sub-models are missing for some blocks, debug `_find_block_components()` with the HA model's component files vs config F-block dirs/files.

---

## Summary of Changes

| File | Action | Purpose |
|------|--------|---------|
| `src/architecture_model/manifest/recursive.py` | Modify | Fix `compute_block_dependencies` for file-based F-blocks |
| `src/architecture_model/orchestration/pipeline.py` | Create | Unified `run_pipeline()` entry point |
| `src/architecture_model/orchestration/__init__.py` | Modify | Export `run_pipeline` |
| `src/architecture_model/__init__.py` | Modify | Top-level export |
| `tests/test_file_based_deps.py` | Create | Test file-based dep resolution |
| `tests/test_pipeline.py` | Create | Test unified pipeline |

## Dependency Order

Task 1 → Task 2 → Task 3 → Task 4 → Task 5

Tasks 1 and 2 are the critical path. Task 3 may be unnecessary if the loader already handles combined files. Task 4 is bookkeeping. Task 5 is validation.
