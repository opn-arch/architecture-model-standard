"""Configuration subpackage for the Architecture Model Standard.

Provides project descriptor loading and auto-discovery so the package
works with any project — not just logs-db.
"""

from .schema import (
    ProjectConfig,
    OutputConfig,
    LayerConfig,
    FunctionalBlockConfig,
    MetricConfig,
)
from .loader import load_config, discover_config, get_config

__all__ = [
    "ProjectConfig",
    "OutputConfig",
    "LayerConfig",
    "FunctionalBlockConfig",
    "MetricConfig",
    "load_config",
    "discover_config",
    "get_config",
]
