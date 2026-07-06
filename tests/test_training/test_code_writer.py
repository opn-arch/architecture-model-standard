import pytest
from pathlib import Path
from architecture_model.training.code_writer import CodeWriter, MaterializedPackage


class TestCodeWriter:
    def setup_method(self):
        self.writer = CodeWriter()

    def test_splits_by_module_headers(self, tmp_path):
        """Code with '# module.py' headers splits into separate files."""
        code = """# core.py
class Context:
    def invoke(self): pass

# utils.py
def echo(msg):
    print(msg)
"""
        pkg = self.writer.materialize(code, "mypackage", tmp_path)
        assert "core.py" in pkg.modules
        assert "utils.py" in pkg.modules
        assert (tmp_path / "mypackage" / "core.py").exists()
        assert (tmp_path / "mypackage" / "utils.py").exists()

    def test_writes_correct_content(self, tmp_path):
        """Each file contains its module's code."""
        code = """# core.py
class Context:
    pass

# utils.py
def echo():
    pass
"""
        pkg = self.writer.materialize(code, "mypackage", tmp_path)
        core_content = (tmp_path / "mypackage" / "core.py").read_text()
        assert "class Context:" in core_content
        assert "def echo" not in core_content

    def test_generates_init_py(self, tmp_path):
        """Creates __init__.py with imports when not in generated code."""
        code = """# core.py
class Context:
    pass

def main():
    pass
"""
        pkg = self.writer.materialize(code, "mypackage", tmp_path)
        assert pkg.init_written
        init_content = (tmp_path / "mypackage" / "__init__.py").read_text()
        assert "from .core import Context" in init_content

    def test_preserves_existing_init(self, tmp_path):
        """If generated code includes __init__.py, uses that instead."""
        code = """# __init__.py
from .core import Context
__version__ = "1.0"

# core.py
class Context:
    pass
"""
        pkg = self.writer.materialize(code, "mypackage", tmp_path)
        init_content = (tmp_path / "mypackage" / "__init__.py").read_text()
        assert "__version__" in init_content

    def test_normalizes_module_paths(self, tmp_path):
        """Strips package name prefix from module paths."""
        code = """# mypackage/core.py
class Context:
    pass

# src/mypackage/utils.py
def echo():
    pass
"""
        pkg = self.writer.materialize(code, "mypackage", tmp_path)
        assert "core.py" in pkg.modules
        assert "utils.py" in pkg.modules

    def test_handles_single_module(self, tmp_path):
        """Code without module headers becomes a single module."""
        code = "class App:\n    pass\n"
        pkg = self.writer.materialize(code, "mypackage", tmp_path)
        assert len(pkg.modules) >= 1  # At least the single module + __init__

    def test_skips_empty_modules(self, tmp_path):
        """Empty module sections are not written."""
        code = """# core.py
class Context:
    pass

# empty.py

# utils.py
def echo():
    pass
"""
        pkg = self.writer.materialize(code, "mypackage", tmp_path)
        assert "core.py" in pkg.modules
        assert "utils.py" in pkg.modules

    def test_package_is_importable(self, tmp_path):
        """Written package can be imported."""
        code = """# core.py
class Context:
    def invoke(self):
        return 42
"""
        pkg = self.writer.materialize(code, "testpkg", tmp_path)

        import sys
        sys.path.insert(0, str(tmp_path))
        try:
            import importlib
            mod = importlib.import_module("testpkg.core")
            assert hasattr(mod, "Context")
            assert mod.Context().invoke() == 42
        finally:
            sys.path.remove(str(tmp_path))
            # Clean up imported modules
            for key in list(sys.modules.keys()):
                if key.startswith("testpkg"):
                    del sys.modules[key]

    def test_patch_for_testing_copies_tests(self, tmp_path):
        """patch_for_testing copies the test directory."""
        # Setup: create a mock "original repo" with tests
        orig_repo = tmp_path / "original"
        orig_repo.mkdir()
        (orig_repo / "tests").mkdir()
        (orig_repo / "tests" / "test_core.py").write_text("def test_x(): pass")
        (orig_repo / "conftest.py").write_text("import pytest")

        # Create package
        output = tmp_path / "generated"
        output.mkdir()
        code = "# core.py\nclass X: pass\n"
        pkg = self.writer.materialize(code, "mypkg", output)

        # Patch
        self.writer.patch_for_testing(pkg, orig_repo)

        assert (output / "tests" / "test_core.py").exists()
        assert (output / "conftest.py").exists()

    def test_patch_generates_pyproject_if_missing(self, tmp_path):
        """Creates minimal pyproject.toml when original doesn't have one."""
        orig_repo = tmp_path / "original"
        orig_repo.mkdir()
        (orig_repo / "tests").mkdir()

        output = tmp_path / "generated"
        output.mkdir()
        pkg = self.writer.materialize("# m.py\nx=1\n", "mypkg", output)

        self.writer.patch_for_testing(pkg, orig_repo)

        pyproject = output / "pyproject.toml"
        assert pyproject.exists()
        assert "mypkg" in pyproject.read_text()

    def test_materialized_package_fields(self, tmp_path):
        """MaterializedPackage has correct metadata."""
        code = "# a.py\nx=1\n\n# b.py\ny=2\n"
        pkg = self.writer.materialize(code, "testpkg", tmp_path)

        assert pkg.package_name == "testpkg"
        assert pkg.package_dir == tmp_path
        assert pkg.source_dir == tmp_path / "testpkg"
        assert "a.py" in pkg.modules
        assert "b.py" in pkg.modules

    def test_cleanup_removes_directory(self, tmp_path):
        """cleanup removes the materialized package."""
        code = "# a.py\nx=1\n"
        output = tmp_path / "toclean"
        output.mkdir()
        pkg = self.writer.materialize(code, "testpkg", output)
        assert pkg.source_dir.exists()

        self.writer.cleanup(pkg)
        assert not output.exists()
