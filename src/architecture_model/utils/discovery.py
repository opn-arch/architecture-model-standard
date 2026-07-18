"""Shared file discovery and exclusion logic.

Consolidates duplicated file-discovery patterns from manifest/scanner,
config/loader, core/merger, and core/decomposer.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

EXCLUDED_DIRS: frozenset[str] = frozenset({
    "__pycache__", ".git", ".hg", ".svn",
    "venv", ".venv", "env", ".env",
    "node_modules",
    ".eggs", ".tox", ".nox", ".mypy_cache", ".pytest_cache",
    "htmlcov", "build", "dist", ".build",
    "alembic",
})


def is_excluded_dir(path: Path) -> bool:
    """Check if a directory path should be excluded from scanning."""
    name = path.name
    return name in EXCLUDED_DIRS or name.startswith(".")


def collect_py_files(
    directory: Path,
    recursive: bool = True,
    exclude_init: bool = False,
) -> list[Path]:
    """Collect Python files from a directory."""
    if not directory.is_dir():
        logger.debug("Directory does not exist: %s", directory)
        return []

    glob_fn = directory.rglob if recursive else directory.glob
    files = sorted(
        p for p in glob_fn("*.py")
        if not any(part in EXCLUDED_DIRS for part in p.parts)
        and (not exclude_init or p.name != "__init__.py")
    )
    logger.debug("Collected %d .py files from %s (recursive=%s)", len(files), directory, recursive)
    return files


def discover_source_files(project_root: Path) -> list[Path]:
    """Discover all source (non-test) Python files in a project."""
    all_py = collect_py_files(project_root, recursive=True)
    sources = [f for f in all_py if not _is_test_file(f, project_root)]
    logger.info("Discovered %d source files (of %d total .py)", len(sources), len(all_py))
    return sources


def discover_test_files(project_root: Path) -> list[Path]:
    """Discover all test Python files in a project."""
    all_py = collect_py_files(project_root, recursive=True)
    tests = [f for f in all_py if _is_test_file(f, project_root)]
    logger.info("Discovered %d test files", len(tests))
    return tests


def _is_test_file(path: Path, project_root: Path) -> bool:
    """Check if a file is a test file by name or location."""
    rel = path.relative_to(project_root)
    parts = rel.parts
    if any(p in ("tests", "test") for p in parts):
        return True
    return path.name.startswith("test_") or path.name.endswith("_test.py")
