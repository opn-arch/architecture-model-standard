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

    # Combined config+model file
    (tmp_path / ".architecture-model.yaml").write_text(textwrap.dedent("""\
        meta:
          project: test-pipeline
          schema_version: '2.0'
        entities:
          components:
            - id: COMP-CORE
              name: Core
              status: ACTIVE
              source_block: S1
              files:
                - src/myapp/core/bus.py
            - id: COMP-API
              name: API
              status: ACTIVE
              source_block: S2
              files:
                - src/myapp/api/handler.py
          capabilities:
            - id: CAP-EVENTS
              name: Event System
              source_block: S1
              status: ACTIVE
        relationships:
          - from: COMP-CORE
            to: CAP-EVENTS
            type: realizes
          - from: COMP-API
            to: COMP-CORE
            type: depends-on
        functional_blocks:
          S1:
            name: Core
            dirs:
              - src/myapp/core
            files: []
          S2:
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
    assert "S1" in result.manifests
    assert "S2" in result.manifests
    assert "S1" in result.sub_models
    assert any(c.id == "COMP-CORE" for c in result.sub_models["S1"].entities.components)


def test_run_pipeline_writes_artifacts(tmp_path):
    """Pipeline writes manifests and sub-models to .architecture-models/."""
    root = _setup_project(tmp_path)
    result = run_pipeline(root)

    out = root / ".architecture-models"
    assert (out / "S1" / "manifest.json").exists()
    assert (out / "S2" / "manifest.json").exists()
    assert (out / "S1" / ".architecture-model.yaml").exists()


def test_run_pipeline_computes_dependencies(tmp_path):
    """Pipeline computes cross-block dependencies."""
    root = _setup_project(tmp_path)
    result = run_pipeline(root)

    f2_deps = result.manifests["S2"].block_dependencies
    assert "S1" in f2_deps


def test_run_pipeline_deep_decompose(tmp_path):
    """Pipeline with deep=True produces sub-components for large blocks."""
    pkg = tmp_path / "bigpkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for i in range(20):
        imports = f"from bigpkg.mod{max(0,i-1)} import something\n" if i > 0 else ""
        (pkg / f"mod{i}.py").write_text(
            f'"""Module {i}."""\n{imports}class Cls{i}:\n    pass\n' + "\n" * 50
        )

    (tmp_path / ".architecture-model.yaml").write_text(
        "functional_blocks:\n"
        "  S1:\n"
        "    name: BigPackage\n"
        "    dirs:\n"
        "      - bigpkg\n"
        "    files: []\n"
    )

    result = run_pipeline(tmp_path, deep=True)
    assert "S1" in result.deep_decompositions
    decomp = result.deep_decompositions["S1"]
    assert len(decomp.sub_components) >= 2


def test_run_pipeline_config_only(tmp_path):
    """Pipeline works with config-only file (no model entities) — skips decompose."""
    pkg = tmp_path / "myapp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text('"""Core."""\nclass X:\n    pass\n' + "\n" * 60)

    (tmp_path / ".architecture-model.yaml").write_text(
        "functional_blocks:\n"
        "  S1:\n"
        "    name: Core\n"
        "    dirs:\n"
        "      - myapp\n"
        "    files: []\n"
    )

    result = run_pipeline(tmp_path)
    assert "S1" in result.manifests
    assert len(result.sub_models) == 0  # No model to decompose
