"""Project metrics computation from filesystem scanning.

Loads metric definitions from .architecture-model.yaml config.
Falls back to heuristic discovery if no config exists.
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import Any, Optional

from architecture_model.manifest.types import MetricsResult
from architecture_model.utils.discovery import EXCLUDED_DIRS

logger = logging.getLogger(__name__)


def compute_metrics(root: Path, config: Optional[Any] = None) -> MetricsResult:
    """Compute verified project metrics from filesystem.

    Args:
        root: Project root directory.
        config: Optional ProjectConfig. If None, loaded from .architecture-model.yaml.

    Returns:
        MetricsResult with metric values.
    """
    if config is None:
        from architecture_model.config.loader import get_config

        config = get_config(root)

    result: dict[str, int] = {}

    for metric in config.metrics:
        metric_path = root / metric.path
        if not metric_path.is_dir():
            result[f"{metric.label}_count"] = 0
            continue

        if metric.recursive:
            files = list(metric_path.rglob(metric.pattern))
        else:
            files = list(metric_path.glob(metric.pattern))

        # Apply exclusions
        if metric.exclude:
            files = [
                f for f in files if f.name not in metric.exclude
                and not any(part in EXCLUDED_DIRS for part in f.parts)
            ]
        else:
            files = [f for f in files if not any(part in EXCLUDED_DIRS for part in f.parts)]

        result[f"{metric.label}_count"] = len(files)

    # Always include total Python files (not configurable — universal metric)
    total_python = len(
        [
            p
            for p in root.rglob("*.py")
            if not any(part in EXCLUDED_DIRS for part in p.parts)
        ]
    )
    result["total_python_files"] = total_python

    logger.debug("Computed %d metrics for %s: %s", len(result), root, result)

    return MetricsResult(values=result)


def _compute_metrics(root: Path, config: Optional[Any] = None) -> dict[str, int]:
    """Compute verified project metrics from filesystem.

    .. deprecated::
        Use :func:`compute_metrics` instead, which returns a :class:`MetricsResult`.
    """
    warnings.warn(
        "_compute_metrics is deprecated, use compute_metrics() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return compute_metrics(root, config).to_dict()
