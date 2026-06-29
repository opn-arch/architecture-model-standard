"""Configuration loader for the Architecture Model Standard.

Loads project configuration from .architecture-model.yaml or auto-discovers
project structure when no config file exists.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .schema import (
    ProjectConfig,
    OutputConfig,
    LayerConfig,
    FunctionalBlockConfig,
    MetricConfig,
)


CONFIG_FILENAME = ".architecture-model.yaml"


def load_config(root: Path) -> ProjectConfig:
    """Load project configuration from .architecture-model.yaml.

    Args:
        root: Project root directory containing the config file.

    Returns:
        ProjectConfig loaded from file.

    Raises:
        FileNotFoundError: If config file doesn't exist.
    """
    config_path = root / CONFIG_FILENAME
    if not config_path.exists():
        raise FileNotFoundError(
            f"No {CONFIG_FILENAME} found in {root}. "
            f"Run `architecture-model init` to generate one, or use get_config() for auto-discovery."
        )

    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not data:
        data = {}

    return ProjectConfig.from_dict(data, root=root)


def discover_config(root: Path) -> ProjectConfig:
    """Auto-discover project configuration by scanning filesystem.

    Inspects the directory structure to infer layers, functional blocks,
    and metrics without requiring a config file. Useful for first-time
    setup or projects that haven't created a config yet.

    Args:
        root: Project root directory to scan.

    Returns:
        ProjectConfig with best-guess values.
    """
    name = root.name

    # Discover layers from common directory patterns
    layers = _discover_layers(root)

    # Discover metrics from what directories exist
    metrics = _discover_metrics(root)

    # Functional blocks require manual definition — return empty
    # (the package will fall back to scanning all Python files)
    functional_blocks: list[FunctionalBlockConfig] = []

    return ProjectConfig(
        name=name,
        system=name,
        output=OutputConfig(),
        layers=layers,
        functional_blocks=functional_blocks,
        metrics=metrics,
        root=root,
    )


def get_config(root: Path) -> ProjectConfig:
    """Load config from file if it exists, otherwise auto-discover.

    This is the recommended entry point — it always returns a valid config.

    Args:
        root: Project root directory.

    Returns:
        ProjectConfig (from file or auto-discovered).
    """
    config_path = root / CONFIG_FILENAME
    if config_path.exists():
        return load_config(root)
    return discover_config(root)


# ---------------------------------------------------------------------------
# Auto-discovery heuristics
# ---------------------------------------------------------------------------

# Common layer patterns for Python web projects
_LAYER_HEURISTICS: list[tuple[str, list[str]]] = [
    ("web-layer", ["app/routers", "app/views", "app/api", "src/api", "api/"]),
    ("services-layer", ["app/services", "src/services", "services/"]),
    ("data-layer", ["app/models", "src/models", "models/", "alembic"]),
    ("pipeline-layer", ["scripts", "pipeline", "src/pipeline", "jobs/"]),
    ("scheduling-layer", ["app/tasks", "tasks/", "celery/"]),
]

# Common metric patterns
_METRIC_HEURISTICS: list[dict[str, Any]] = [
    {
        "label": "routers",
        "paths": ["app/routers", "app/api", "src/api"],
        "pattern": "*.py",
        "exclude": ["__init__.py"],
    },
    {
        "label": "models",
        "paths": ["app/models", "src/models"],
        "pattern": "*.py",
        "exclude": ["__init__.py", "base.py"],
    },
    {
        "label": "migrations",
        "paths": ["alembic/versions", "migrations"],
        "pattern": "*.py",
        "exclude": [],
    },
    {
        "label": "templates",
        "paths": ["app/templates", "templates"],
        "pattern": "**/*.html",
        "exclude": [],
        "recursive": True,
    },
]


def _discover_layers(root: Path) -> list[LayerConfig]:
    """Discover architecture layers from directory structure."""
    layers: list[LayerConfig] = []

    for layer_id, candidate_dirs in _LAYER_HEURISTICS:
        found_dirs = [d for d in candidate_dirs if (root / d).is_dir()]
        if found_dirs:
            layers.append(LayerConfig(id=layer_id, dirs=found_dirs))

    return layers


def _discover_metrics(root: Path) -> list[MetricConfig]:
    """Discover countable metrics from directory structure."""
    metrics: list[MetricConfig] = []

    for heuristic in _METRIC_HEURISTICS:
        for path in heuristic["paths"]:
            if (root / path).is_dir():
                metrics.append(
                    MetricConfig(
                        label=heuristic["label"],
                        path=path,
                        pattern=heuristic["pattern"],
                        exclude=heuristic["exclude"],
                        recursive=heuristic.get("recursive", False),
                    )
                )
                break  # Use first match per label

    return metrics
