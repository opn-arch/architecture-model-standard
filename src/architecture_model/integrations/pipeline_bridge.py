"""
Pipeline Bridge: Connect the Architecture Model to the artifact generation pipeline.

This module provides the interface between:
- The existing _pipeline_manifest.py (code-grounded reality)
- The architecture model (structural + semantic truth)
- The artifact generation pipeline (_pipeline_artifacts.py, _pipeline_templates.py)

It replaces raw manifest slices with model-enriched context for LLM artifact generation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ..core.parser import load_model, save_model
from ..core.merger import merge_manifest
from ..core.slicer import slice_by_fblock, slice_for_artifact
from ..core.validator import validate_model
from ..core.types import ArchitectureModel
from ..integrations.llm_context import (
    format_model_context,
    format_fblock_context,
    format_artifact_context,
)


# ---------------------------------------------------------------------------
# Configuration — loaded from .architecture-model.yaml
# ---------------------------------------------------------------------------


def _get_default_paths(project_root: Path) -> tuple[Path, Path, Path]:
    """Resolve output paths from config."""
    try:
        from ..config.loader import get_config

        config = get_config(project_root)
        resolved = config.resolved_output()
        return resolved.model, resolved.manifest, resolved.artifacts
    except Exception:
        # Fallback for backward compatibility
        name = project_root.name
        return (
            project_root / f"output/{name}/architecture-model.yaml",
            project_root / f"output/{name}/reality-manifest.json",
            project_root / f"output/{name}/artifacts/stage2",
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_model(
    project_root: str | Path,
    force_refresh: bool = False,
) -> ArchitectureModel:
    """
    Load or generate the architecture model for the project.

    If the model YAML exists and isn't stale, loads it.
    If missing or force_refresh=True, re-extracts from artifacts and merges manifest.

    Args:
        project_root: Path to project root directory.
        force_refresh: Force re-extraction even if model exists.

    Returns:
        Loaded and validated ArchitectureModel.
    """
    project_root = Path(project_root)
    model_path, manifest_path, artifact_dir = _get_default_paths(project_root)

    if model_path.exists() and not force_refresh:
        return load_model(model_path)

    # Re-extract
    from ..extract.from_artifacts import extract_from_artifacts

    model = extract_from_artifacts(artifact_dir)

    if manifest_path.exists():
        merge_manifest(model, manifest_path)

    save_model(model, model_path)
    return model


def get_artifact_context(
    project_root: str | Path,
    artifact_name: str,
    max_tokens: int = 3000,
) -> str:
    """
    Get model-based context for artifact generation/regeneration.

    This REPLACES the raw manifest slice with structured architectural context.
    The returned string is injected into the LLM system prompt alongside the
    manifest metrics (which are kept for ground-truth file counts).

    Args:
        project_root: Project root path.
        artifact_name: Which artifact needs context.
        max_tokens: Token budget for the context block.

    Returns:
        Formatted model context string for LLM prompt injection.
    """
    model = get_model(project_root)
    return format_artifact_context(model, artifact_name, max_tokens=max_tokens)


def get_fblock_context(
    project_root: str | Path,
    f_block: str,
    max_tokens: int = 2000,
) -> str:
    """
    Get model-based context for a single F-block (for section regeneration).

    Args:
        project_root: Project root path.
        f_block: F-block ID (e.g., "F3").
        max_tokens: Token budget.

    Returns:
        Formatted F-block context string.
    """
    model = get_model(project_root)
    return format_fblock_context(model, f_block, max_tokens=max_tokens)


def get_model_summary(project_root: str | Path) -> dict[str, Any]:
    """
    Get a summary dict of the model for injection into pipeline metadata.

    Returns dict with entity_count, relationship_count, validation score, etc.
    """
    model = get_model(project_root)
    result = validate_model(model)

    return {
        "entity_count": model.entity_count,
        "relationship_count": model.relationship_count,
        "validation_score": result.score,
        "entities": {
            "actors": len(model.entities.actors),
            "capabilities": len(model.entities.capabilities),
            "behaviors": len(model.entities.behaviors),
            "interfaces": len(model.entities.interfaces),
            "constraints": len(model.entities.constraints),
            "layers": len(model.entities.layers),
            "components": len(model.entities.components),
        },
        "schema_version": model.meta.schema_version,
        "manifest_hash": model.meta.manifest_hash,
    }


def enrich_manifest_slice(
    manifest_slice: str,
    project_root: str | Path,
    artifact_name: str,
    max_model_tokens: int = 2000,
) -> str:
    """
    Enrich an existing manifest slice with architecture model context.

    This is the BACKWARD-COMPATIBLE integration point. The existing pipeline
    generates manifest slices via _pipeline_manifest.py — this function
    prepends model context to that slice, giving the LLM both:
    1. Architectural structure (from model) — WHAT things mean, how they relate
    2. Code-grounded metrics (from manifest) — WHAT actually exists

    Args:
        manifest_slice: Raw manifest slice text (from _pipeline_manifest.py).
        project_root: Project root path.
        artifact_name: Which artifact this slice is for.
        max_model_tokens: Token budget for model context portion.

    Returns:
        Combined context: model context + separator + manifest metrics.
    """
    try:
        model_context = get_artifact_context(
            project_root, artifact_name, max_tokens=max_model_tokens
        )
    except Exception:
        # If model loading fails, fall back to manifest-only
        return manifest_slice

    return (
        f"=== ARCHITECTURE MODEL CONTEXT ===\n"
        f"{model_context}\n"
        f"\n"
        f"=== CODE-GROUNDED MANIFEST (verified metrics) ===\n"
        f"{manifest_slice}"
    )
