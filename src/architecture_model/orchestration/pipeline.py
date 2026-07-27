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
    generate_recursive_manifests,
    write_recursive_manifests,
)
from architecture_model.manifest.types import RecursiveManifest
from architecture_model.orchestration.decompose import decompose_model, write_sub_models

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of running the full decomposition pipeline."""
    manifests: dict[str, RecursiveManifest] = field(default_factory=dict)
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
        project_root: Root directory with .architecture-model.yaml
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

    # Step 2: Decompose parent model (requires entities section)
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
            # Decomposition failure is non-fatal (config-only files, etc.)
            msg = f"Decomposition skipped: {exc}"
            result.errors.append(msg)
            logger.warning(msg)
    else:
        logger.info("Step 2: Skipped (no parent model at %s)", model_path)

    return result
