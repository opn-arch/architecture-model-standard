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

from architecture_model.monitoring import monitored
from architecture_model.core.types import ArchitectureModel
from architecture_model.manifest.recursive import (
    generate_recursive_manifests,
    write_recursive_manifests,
)
from architecture_model.manifest.types import RecursiveManifest
from architecture_model.orchestration.decompose import decompose_model, write_sub_models
from architecture_model.orchestration.deep_decompose import DecomposeResult

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of running the full decomposition pipeline."""
    manifests: dict[str, RecursiveManifest] = field(default_factory=dict)
    sub_models: dict[str, ArchitectureModel] = field(default_factory=dict)
    deep_decompositions: dict[str, DecomposeResult] = field(default_factory=dict)
    written_paths: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@monitored(
    module="orchestration.pipeline",
    inputs=lambda a, kw: {"deep": kw.get("deep", False)},
    outputs=lambda r: {"blocks_scanned": len(r.manifests), "blocks_decomposed": len(r.deep_decompositions), "errors": len(r.errors)},
)
def run_pipeline(
    project_root: Path,
    *,
    parent_model: str = ".architecture-model.yaml",
    model_file: str | None = None,
    output_dir: str = ".architecture-models",
    deep: bool = False,
) -> PipelineResult:
    """Run the full decomposition pipeline.

    1. Generate recursive manifests (per-block AST scan + dependency analysis)
    2. Decompose parent model into sub-models (relationship tracing)
    3. Write all artifacts to output_dir/<block_id>/

    Args:
        project_root: Root directory with .architecture-model.yaml
        parent_model: Config filename with functional_blocks (default: .architecture-model.yaml)
        model_file: Model filename with entities/relationships. If None, auto-detects:
                    tries parent_model first, then .architecture-model-extracted.yaml
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

    # Step 1.5: Deep decompose blocks (if deep=True)
    if deep:
        from architecture_model.orchestration.deep_decompose import iterative_decompose
        logger.info("Step 1.5: Iterative deep decomposition...")
        for block_id, rm in manifests.items():
            decomps = iterative_decompose(
                rm.manifest, block_id=block_id, block_name=rm.block_name
            )
            if decomps:
                result.deep_decompositions[block_id] = decomps[-1]
                total_leaves = sum(len(d.sub_components) for d in decomps)
                logger.info("  %s: %d rounds, %d total sub-components",
                           block_id, len(decomps), total_leaves)

    # Step 2: Decompose parent model (requires entities section)
    # Auto-detect model file
    if model_file is not None:
        actual_model = project_root / model_file
    else:
        # Try parent_model first, fall back to extracted variant
        actual_model = project_root / parent_model
        # Check if it actually has entities (not just config)
        try:
            from architecture_model.core.parser import load_model
            test_model = load_model(actual_model)
            if not test_model.entities.components:
                raise ValueError("No components")
        except Exception:
            # Try extracted model
            extracted = project_root / ".architecture-model-extracted.yaml"
            if extracted.exists():
                actual_model = extracted
            else:
                actual_model = None

    if actual_model and actual_model.exists():
        logger.info("Step 2: Decomposing model (%s) into sub-models...", actual_model.name)
        try:
            sub_models = decompose_model(project_root, model_path=actual_model)
            result.sub_models = sub_models
            if sub_models:
                paths = write_sub_models(sub_models, out)
                result.written_paths.extend(paths)
                logger.info("  Generated %d sub-models", len(sub_models))
            else:
                logger.warning("  No sub-models generated (no matching components)")
        except Exception as exc:
            msg = f"Decomposition skipped: {exc}"
            result.errors.append(msg)
            logger.warning(msg)
    else:
        logger.info("Step 2: Skipped (no model with entities found)")

    return result
