"""Tests for __init__.py re-export tracing in test-to-source mapping."""
import ast
import tempfile
from pathlib import Path

import pytest

from architecture_model.core.merger import _map_tests_to_sources


@pytest.fixture
def package_repo(tmp_path):
    """Create a repo with package-level imports (like tqdm)."""
    pkg = tmp_path / "mylib"
    pkg.mkdir()

    # __init__.py re-exports from submodules
    (pkg / "__init__.py").write_text(
        "from .core import MyClass, helper\n"
        "from .utils import format_value\n"
        "__all__ = ['MyClass', 'helper', 'format_value']\n"
    )
    (pkg / "core.py").write_text(
        "class MyClass:\n    pass\n\ndef helper():\n    return 1\n"
    )
    (pkg / "utils.py").write_text(
        "def format_value(x):\n    return str(x)\n"
    )

    # Test file imports from package level
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_mylib.py").write_text(
        "from mylib import MyClass, helper, format_value\n\n"
        "def test_my_class():\n    assert MyClass() is not None\n"
    )

    return tmp_path


def test_package_import_traces_to_submodules(package_repo):
    """from mylib import X should map to core.py and utils.py, not just __init__."""
    test_files = list((package_repo / "tests").glob("test_*.py"))
    source_stems = {"__init__", "core", "utils"}

    mapping = _map_tests_to_sources(test_files, source_stems, package_repo)

    # Should map to both core and utils (the actual implementation files)
    assert "core" in mapping, "Should trace re-export to core.py"
    assert "utils" in mapping, "Should trace re-export to utils.py"


def test_subpackage_import_traces_through_init(tmp_path):
    """from mylib.sub import X should trace sub/__init__.py re-exports."""
    pkg = tmp_path / "mylib"
    sub = pkg / "sub"
    sub.mkdir(parents=True)

    (pkg / "__init__.py").write_text("")
    (sub / "__init__.py").write_text("from .impl import do_thing\n")
    (sub / "impl.py").write_text("def do_thing(): pass\n")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_sub.py").write_text(
        "from mylib.sub import do_thing\n\n"
        "def test_do_thing():\n    assert do_thing() is None\n"
    )

    test_files = [tests_dir / "test_sub.py"]
    source_stems = {"__init__", "impl"}

    mapping = _map_tests_to_sources(test_files, source_stems, tmp_path)

    assert "impl" in mapping, "Should trace sub/__init__.py re-export to impl.py"


def test_direct_submodule_import_still_works(tmp_path):
    """from mylib.core import X should still directly map to core.py."""
    pkg = tmp_path / "mylib"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text("class Foo: pass\n")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_core.py").write_text(
        "from mylib.core import Foo\n\n"
        "def test_foo():\n    assert Foo()\n"
    )

    test_files = [tests_dir / "test_core.py"]
    source_stems = {"__init__", "core"}

    mapping = _map_tests_to_sources(test_files, source_stems, tmp_path)

    assert "core" in mapping


def test_no_false_positives_from_stdlib(tmp_path):
    """Importing 'os.path' should NOT map to a local 'path.py'."""
    pkg = tmp_path / "mylib"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "path.py").write_text("def resolve(): pass\n")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_path.py").write_text(
        "import os.path\n"
        "from mylib.path import resolve\n\n"
        "def test_resolve():\n    assert resolve() is None\n"
    )

    test_files = [tests_dir / "test_path.py"]
    source_stems = {"__init__", "path"}

    mapping = _map_tests_to_sources(test_files, source_stems, tmp_path)

    # 'path' should be mapped (from mylib.path import), but the test
    # should not double-map from 'os.path'
    assert "path" in mapping
    # Only one test file should be in the mapping for 'path'
    assert len(mapping["path"]) == 1
