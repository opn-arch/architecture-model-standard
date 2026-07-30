"""Pattern catalog loader."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_CATALOG_PATH = Path(__file__).parent / "data" / "patterns.yaml"
_cache: dict[str, Any] | None = None


def load_patterns() -> dict[str, Any]:
    """Load the pattern catalog. Cached after first call."""
    global _cache
    if _cache is None:
        with open(_CATALOG_PATH) as f:
            _cache = yaml.safe_load(f)
    return _cache


def get_pattern(name: str) -> dict[str, Any] | None:
    """Get a single pattern by name, or None if not found."""
    return load_patterns().get(name)
