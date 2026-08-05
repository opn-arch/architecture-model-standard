"""Pipeline-scoped cache for scan_file results."""

from __future__ import annotations

import hashlib
from pathlib import Path

from architecture_model.manifest.types import ModuleInfo


class ScanCache:
    """Pipeline-scoped cache for scan_file results.

    Keyed on (absolute_path, content_hash) so modified files are re-scanned.
    """

    def __init__(self) -> None:
        self._cache: dict[str, ModuleInfo] = {}
        self._hits = 0
        self._misses = 0

    def get(self, filepath: Path) -> ModuleInfo | None:
        """Get cached scan result for a file."""
        key = self._key(filepath)
        if key is None:
            self._misses += 1
            return None
        result = self._cache.get(key)
        if result is not None:
            self._hits += 1
        else:
            self._misses += 1
        return result

    def put(self, filepath: Path, module: ModuleInfo) -> None:
        """Cache a scan result."""
        key = self._key(filepath)
        if key is not None:
            self._cache[key] = module

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    def _key(self, filepath: Path) -> str | None:
        """Generate cache key from (absolute_path, content_hash)."""
        try:
            abs_path = filepath.resolve()
            content = abs_path.read_bytes()
            content_hash = hashlib.md5(content).hexdigest()
            return f"{abs_path}:{content_hash}"
        except (OSError, IOError):
            return None
