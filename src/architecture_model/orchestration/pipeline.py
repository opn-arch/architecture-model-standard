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
from architecture_model.core.types import ArchitectureModel, ModelMeta
from architecture_model.manifest.recursive import (
    generate_recursive_manifests,
    write_recursive_manifests,
)
from architecture_model.manifest.types import RecursiveManifest
from architecture_model.orchestration.decompose import decompose_model, write_sub_models
from architecture_model.orchestration.deep_decompose import DecomposeResult
from architecture_model.orchestration.auto_enrich import enrich_from_manifest

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of running the full decomposition pipeline."""
    manifests: dict[str, RecursiveManifest] = field(default_factory=dict)
    sub_models: dict[str, ArchitectureModel] = field(default_factory=dict)
    deep_decompositions: dict[str, DecomposeResult] = field(default_factory=dict)
    written_paths: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    fblock_config: dict = field(default_factory=dict)


@monitored(
    module="orchestration.pipeline",
    inputs=lambda a, kw: {"deep": kw.get("deep", False), "from_scratch": kw.get("from_scratch", False)},
    outputs=lambda r: {"blocks_scanned": len(r.manifests), "blocks_decomposed": len(r.deep_decompositions), "errors": len(r.errors)},
)
def run_pipeline(
    project_root: Path,
    *,
    parent_model: str = ".architecture-model.yaml",
    model_file: str | None = None,
    output_dir: str = ".architecture-models",
    deep: bool = False,
    compact: bool = False,
    from_scratch: bool = False,
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
        deep: Enable iterative deep decomposition of blocks
        compact: Compact root model after decomposition
        from_scratch: If True and no model exists, bootstrap one from manifest
                      using module grouping and auto-enrichment

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

    # Step 1.8: Auto-enrich model from manifest (if model available)
    if actual_model and actual_model.exists():
        try:
            from architecture_model.core.parser import load_model as _load_model
            from architecture_model.manifest.generator import generate_manifest

            _enrichment_model = _load_model(actual_model)
            _flat_manifest = generate_manifest(project_root)
            enrich_from_manifest(_enrichment_model, _flat_manifest)
            logger.info("Step 1.8: Auto-enriched model components from manifest")
        except Exception as exc:
            logger.debug("Auto-enrichment skipped: %s", exc)

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

            # Step 3: Compact root model (if compact=True and sub-models exist)
            if compact and sub_models:
                from architecture_model.orchestration.decompose import compact_root_model
                from architecture_model.core.parser import load_model as _load, save_model

                block_ids = list(sub_models.keys())
                root = _load(actual_model)
                compact_root_model(root, block_ids=block_ids)
                save_model(root, actual_model)
                logger.info("  Compacted root model (stripped %d blocks)", len(block_ids))

        except Exception as exc:
            msg = f"Decomposition skipped: {exc}"
            result.errors.append(msg)
            logger.warning(msg)
    else:
        if from_scratch:
            logger.info("Step 2: Bootstrapping model from scratch via module grouping...")
            try:
                from architecture_model.manifest.generator import generate_manifest
                from architecture_model.manifest.grouping import (
                    auto_fblocks, create_components_from_manifest, group_modules,
                )
                from architecture_model.core.parser import save_model
                from architecture_model.core.types import ArchitectureModel, Entities
                from architecture_model.manifest.chains import build_block_chains
                from architecture_model.core.representativeness import compute_representativeness

                flat_manifest = generate_manifest(project_root)
                components = create_components_from_manifest(flat_manifest)
                model = ArchitectureModel(
                    meta=ModelMeta(project=project_root.name, schema_version="1.3"),
                    entities=Entities(components=components),
                    relationships=[],
                )
                enrich_from_manifest(model, flat_manifest)

                # Build event chains for behavioral enrichment
                try:
                    groups = group_modules(flat_manifest.modules, flat_manifest.interfaces)
                    chains = build_block_chains(flat_manifest, groups, block_id="root")
                    logger.info("  Built %d event chains", len(chains))
                except Exception as exc:
                    logger.debug("Chain building skipped: %s", exc)

                # Generate F-block config for hierarchical decomposition
                try:
                    if not groups:
                        groups = group_modules(flat_manifest.modules, flat_manifest.interfaces)
                    fblock_config = auto_fblocks(groups, threshold=3)
                    if fblock_config:
                        logger.info("  Generated %d F-blocks from module groups", len(fblock_config))
                        result.fblock_config = fblock_config

                        # Generate per-block recursive manifests using auto-F-blocks
                        block_manifests = generate_recursive_manifests(
                            project_root, fblock_override=fblock_config
                        )
                        result.manifests = block_manifests
                        paths = write_recursive_manifests(block_manifests, out)
                        result.written_paths.extend(paths)
                        logger.info("  Generated %d block manifests from auto-F-blocks", len(block_manifests))
                except Exception as exc:
                    logger.debug("Auto F-block generation skipped: %s", exc)

                # Verify representativeness
                _rep = None
                try:
                    _rep = compute_representativeness(model, flat_manifest.modules, flat_manifest.interfaces)
                    logger.info("  Representativeness: %.1f%% (file=%.1f%%, rel=%.1f%%, coh=%.1f%%)",
                               _rep.overall, _rep.file_coverage, _rep.relationship_accuracy, _rep.boundary_coherence)
                except Exception as exc:
                    logger.debug("Representativeness check skipped: %s", exc)

                # Save the bootstrapped model
                model_path = project_root / ".architecture-model-extracted.yaml"
                save_model(model, model_path)
                result.written_paths.append(model_path)

                # Persist full project bundle
                from architecture_model.persistence.store import save_project as _save_project
                _save_project(
                    project_root, model, flat_manifest,
                    representativeness=_rep,
                )
                logger.info("  Bootstrapped model with %d components → %s", len(components), model_path.name)
            except Exception as exc:
                msg = f"From-scratch bootstrap failed: {exc}"
                result.errors.append(msg)
                logger.error(msg)
        else:
            logger.info("Step 2: Skipped (no model with entities found)")

    return result
