"""Tests for architecture_model.config.loader F-block naming."""

from __future__ import annotations

from pathlib import Path

import pytest

from architecture_model.config.loader import _discover_functional_blocks


def test_source_block_naming_from_imports(tmp_path):
    """F-blocks with common import patterns should get semantic names."""
    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")

    api_dir = pkg / "api"
    api_dir.mkdir()
    (api_dir / "__init__.py").write_text("")
    (api_dir / "routes.py").write_text("from fastapi import APIRouter\nrouter = APIRouter()\n")

    db_dir = pkg / "db"
    db_dir.mkdir()
    (db_dir / "__init__.py").write_text("")
    (db_dir / "models.py").write_text("from sqlalchemy import Column, Integer\n")

    blocks = _discover_functional_blocks(tmp_path)
    names = {b.name for b in blocks}
    # Should NOT be raw title-cased dir names
    assert "Api" not in names, f"Got raw name 'Api' in {names}"
    assert "Db" not in names, f"Got raw name 'Db' in {names}"
    # api/ dir with fastapi imports should get "REST API Endpoints" (dir name contains "api")
    assert "REST API Endpoints" in names, f"Expected 'REST API Endpoints' in {names}"
    # db/ dir with sqlalchemy imports should get "Database Access" (dir name is "db", not "models")
    assert "Database Access" in names, f"Expected 'Database Access' in {names}"


def test_source_block_naming_fallback_when_no_characteristic_imports(tmp_path):
    """F-blocks without recognizable imports should fall back to title-cased dir name."""
    pkg = tmp_path / "mylib"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")

    utils_dir = pkg / "utils"
    utils_dir.mkdir()
    (utils_dir / "__init__.py").write_text("")
    (utils_dir / "helpers.py").write_text("import os\nimport sys\n")

    blocks = _discover_functional_blocks(tmp_path)
    names = {b.name for b in blocks}
    # Should fall back to title-cased dir name
    assert "Utils" in names, f"Expected 'Utils' fallback in {names}"
