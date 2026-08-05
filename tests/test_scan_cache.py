"""Tests for pipeline-scoped scan cache."""

import pytest
from pathlib import Path
from architecture_model.manifest.scan_cache import ScanCache
from architecture_model.manifest.scanner import scan_file


class TestScanCache:
    def test_same_file_twice_is_cache_hit(self, tmp_path):
        """Scanning same file twice with cache -> second call is a hit."""
        py_file = tmp_path / "mod.py"
        py_file.write_text("def hello(): pass")
        cache = ScanCache()

        result1 = scan_file(tmp_path, py_file, cache=cache)
        result2 = scan_file(tmp_path, py_file, cache=cache)

        assert cache.hits == 1
        assert cache.misses == 1
        assert result1.file == result2.file

    def test_modified_file_is_cache_miss(self, tmp_path):
        """If file content changes, cache should miss."""
        py_file = tmp_path / "mod.py"
        py_file.write_text("x = 1")
        cache = ScanCache()

        scan_file(tmp_path, py_file, cache=cache)
        py_file.write_text("x = 2")
        scan_file(tmp_path, py_file, cache=cache)

        assert cache.hits == 0
        assert cache.misses == 2

    def test_counters_correct(self, tmp_path):
        """Hits and misses counters are accurate."""
        f1 = tmp_path / "a.py"
        f1.write_text("a = 1")
        f2 = tmp_path / "b.py"
        f2.write_text("b = 2")
        cache = ScanCache()

        scan_file(tmp_path, f1, cache=cache)  # miss
        scan_file(tmp_path, f2, cache=cache)  # miss
        scan_file(tmp_path, f1, cache=cache)  # hit
        scan_file(tmp_path, f1, cache=cache)  # hit

        assert cache.misses == 2
        assert cache.hits == 2

    def test_scan_file_without_cache_still_works(self, tmp_path):
        """scan_file works fine without cache (backward compat)."""
        py_file = tmp_path / "mod.py"
        py_file.write_text("def foo(): pass")
        result = scan_file(tmp_path, py_file)
        assert result.file is not None
