import pytest
from pathlib import Path

from architecture_model.utils.discovery import (
    collect_py_files,
    discover_source_files,
    discover_test_files,
    is_excluded_dir,
    EXCLUDED_DIRS,
)


def test_excluded_dirs_contains_common_patterns():
    for d in ("__pycache__", ".git", "venv", ".venv", "node_modules", ".tox", ".eggs"):
        assert d in EXCLUDED_DIRS


def test_collect_py_files_excludes_pycache(tmp_path):
    (tmp_path / "good.py").write_text("x = 1")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "bad.cpython-311.pyc").write_text("")
    result = collect_py_files(tmp_path)
    assert len(result) == 1
    assert result[0].name == "good.py"


def test_collect_py_files_recursive(tmp_path):
    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / "mod.py").write_text("x = 1")
    (tmp_path / "top.py").write_text("x = 1")
    result = collect_py_files(tmp_path, recursive=True)
    assert len(result) == 2


def test_collect_py_files_non_recursive(tmp_path):
    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / "mod.py").write_text("x = 1")
    (tmp_path / "top.py").write_text("x = 1")
    result = collect_py_files(tmp_path, recursive=False)
    assert len(result) == 1
    assert result[0].name == "top.py"


def test_collect_py_files_exclude_init(tmp_path):
    (tmp_path / "__init__.py").write_text("")
    (tmp_path / "mod.py").write_text("x = 1")
    result = collect_py_files(tmp_path, exclude_init=True)
    assert len(result) == 1
    assert result[0].name == "mod.py"


def test_collect_py_files_nonexistent_dir(tmp_path):
    result = collect_py_files(tmp_path / "nonexistent")
    assert result == []


def test_is_excluded_dir():
    assert is_excluded_dir(Path("__pycache__")) is True
    assert is_excluded_dir(Path(".git")) is True
    assert is_excluded_dir(Path(".hidden")) is True
    assert is_excluded_dir(Path("mypackage")) is False


def test_discover_source_files_skips_tests(tmp_path):
    src = tmp_path / "src" / "pkg"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("")
    (src / "mod.py").write_text("x = 1")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_mod.py").write_text("x = 1")
    result = discover_source_files(tmp_path)
    assert all("test_" not in f.name for f in result)


def test_discover_test_files(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_mod.py").write_text("x = 1")
    (tests / "helper.py").write_text("x = 1")
    result = discover_test_files(tmp_path)
    # Both files are in tests/ dir, so both are considered test files
    assert len(result) == 2
    names = {f.name for f in result}
    assert "test_mod.py" in names
    assert "helper.py" in names


def test_discover_test_files_by_name(tmp_path):
    (tmp_path / "test_something.py").write_text("x = 1")
    (tmp_path / "something_test.py").write_text("x = 1")
    (tmp_path / "normal.py").write_text("x = 1")
    result = discover_test_files(tmp_path)
    assert len(result) == 2
