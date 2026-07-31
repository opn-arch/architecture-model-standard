"""Persist architecture artifacts to .architecture/ directory.

Stores model, manifest, and metrics as a complete project snapshot.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProjectSnapshot:
    """Complete persisted state of an architecture extraction."""
    model: Any = None  # ArchitectureModel (lazy import to avoid cycles)
    manifest_dict: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    root: Path | None = None


def save_project(
    root: Path,
    model: Any,
    manifest: Any,
    representativeness: Any | None = None,
    telemetry: dict | None = None,
) -> Path:
    """Persist model + manifest + metrics to .architecture/ directory.

    Args:
        root: Repository root directory
        model: ArchitectureModel instance
        manifest: Manifest instance (has .to_dict())
        representativeness: RepresentativenessResult instance (has .to_dict())
        telemetry: Optional telemetry dict (token_budget, iterations, etc.)

    Returns:
        Path to the .architecture/ directory
    """
    arch_dir = root / ".architecture"
    arch_dir.mkdir(parents=True, exist_ok=True)

    # 1. Save model to root (standard location)
    from architecture_model.core.parser import save_model
    model_path = root / ".architecture-model.yaml"
    save_model(model, model_path)
    logger.info("Saved model to %s", model_path)

    # 2. Save manifest
    manifest_path = arch_dir / "manifest.json"
    manifest_dict = manifest.to_dict() if hasattr(manifest, 'to_dict') else manifest
    manifest_path.write_text(json.dumps(manifest_dict, indent=2, default=str))
    logger.info("Saved manifest to %s", manifest_path)

    # 3. Build and save metrics
    metrics: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    if representativeness is not None:
        metrics["representativeness"] = (
            representativeness.to_dict() if hasattr(representativeness, 'to_dict')
            else representativeness
        )

    if hasattr(manifest, 'metrics') and manifest.metrics is not None:
        m = manifest.metrics
        metrics["manifest_metrics"] = m.to_dict() if hasattr(m, 'to_dict') else m

    if telemetry:
        metrics["telemetry"] = telemetry

    metrics_path = arch_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, default=str))
    logger.info("Saved metrics to %s", metrics_path)

    return arch_dir


def save_block(
    root: Path,
    block_id: str,
    model: Any,
    manifest: Any,
    representativeness: Any | None = None,
) -> Path:
    """Persist a hierarchical block's artifacts to .architecture/<block_id>/.

    Args:
        root: Repository root directory
        block_id: F-block ID (e.g., "F1")
        model: ArchitectureModel for this block
        manifest: Manifest for this block
        representativeness: Optional RepresentativenessResult for this block

    Returns:
        Path to the block directory
    """
    block_dir = root / ".architecture" / block_id
    block_dir.mkdir(parents=True, exist_ok=True)

    # Save block model
    from architecture_model.core.parser import save_model
    save_model(model, block_dir / ".architecture-model.yaml")

    # Save block manifest
    manifest_dict = manifest.to_dict() if hasattr(manifest, 'to_dict') else manifest
    (block_dir / "manifest.json").write_text(
        json.dumps(manifest_dict, indent=2, default=str)
    )

    # Save block metrics
    if representativeness is not None:
        metrics = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "representativeness": (
                representativeness.to_dict() if hasattr(representativeness, 'to_dict')
                else representativeness
            ),
        }
        (block_dir / "metrics.json").write_text(
            json.dumps(metrics, indent=2, default=str)
        )

    return block_dir


def load_project(root: Path) -> ProjectSnapshot:
    """Load model + manifest + metrics from .architecture/ directory.

    Args:
        root: Repository root directory

    Returns:
        ProjectSnapshot with loaded data
    """
    snapshot = ProjectSnapshot(root=root)

    # Load model
    model_path = root / ".architecture-model.yaml"
    if model_path.exists():
        from architecture_model.core.parser import load_model
        snapshot.model = load_model(model_path)

    # Load manifest
    arch_dir = root / ".architecture"
    manifest_path = arch_dir / "manifest.json"
    if manifest_path.exists():
        snapshot.manifest_dict = json.loads(manifest_path.read_text())

    # Load metrics
    metrics_path = arch_dir / "metrics.json"
    if metrics_path.exists():
        snapshot.metrics = json.loads(metrics_path.read_text())

    return snapshot
