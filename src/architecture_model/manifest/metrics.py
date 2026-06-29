"""Project metrics computation from filesystem scanning.

Loads metric definitions from .architecture-model.yaml config.
Falls back to heuristic discovery if no config exists.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


def _compute_metrics(root: Path, config: Optional[Any] = None) -> dict[str, int]:
    """Compute verified project metrics from filesystem.

    Args:
        root: Project root directory.
        config: Optional ProjectConfig. If None, loaded from .architecture-model.yaml.

    Returns:
        Dict mapping metric labels to counts.
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
                f for f in files if f.name not in metric.exclude and "__pycache__" not in str(f)
            ]
        else:
            files = [f for f in files if "__pycache__" not in str(f)]

        result[f"{metric.label}_count"] = len(files)

    # Always include total Python files (not configurable — universal metric)
    total_python = len(
        [
            p
            for p in root.rglob("*.py")
            if "__pycache__" not in str(p)
            and "venv" not in str(p)
            and ".venv" not in str(p)
            and "node_modules" not in str(p)
        ]
    )
    result["total_python_files"] = total_python

    return result
