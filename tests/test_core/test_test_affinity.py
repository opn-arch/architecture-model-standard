"""Tests for test-affinity decomposition strategy."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from architecture_model.core.decomposer import (
    Subsystem,
    test_affinity_decompose as decompose,
)


@pytest.fixture
def repo_with_tests(tmp_path: Path) -> Path:
    """Create a minimal repo with source and test files that import from source."""
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "alpha.py").write_text("class Alpha: pass\n")
    (pkg / "beta.py").write_text(
        textwrap.dedent("""\
        from mypkg.alpha import Alpha

        class Beta:
            def use_alpha(self):
                return Alpha()
        """)
    )
    (pkg / "gamma.py").write_text("def gamma_func(): pass\n")

    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("")
    (tests / "test_alpha.py").write_text(
        textwrap.dedent("""\
        from mypkg.alpha import Alpha

        def test_alpha():
            assert Alpha()
        """)
    )
    (tests / "test_beta.py").write_text(
        textwrap.dedent("""\
        from mypkg.beta import Beta

        def test_beta():
            assert Beta()
        """)
    )
    return tmp_path


@pytest.fixture
def repo_with_suffix_tests(tmp_path: Path) -> Path:
    """Create a repo using *_test.py naming convention (like colorama)."""
    pkg = tmp_path / "colorama"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "ansi.py").write_text("class Fore: pass\nclass Back: pass\n")
    (pkg / "winterm.py").write_text("class WinTerm: pass\n")
    (pkg / "win32.py").write_text(
        textwrap.dedent("""\
        from .winterm import WinTerm

        class Win32: pass
        """)
    )

    tests = pkg / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("")
    (tests / "ansi_test.py").write_text(
        textwrap.dedent("""\
        from colorama.ansi import Fore, Back

        def test_fore():
            assert Fore
        """)
    )
    (tests / "winterm_test.py").write_text(
        textwrap.dedent("""\
        from colorama.winterm import WinTerm
        from colorama.win32 import Win32

        def test_winterm():
            assert WinTerm
        """)
    )
    return tmp_path


@pytest.fixture
def repo_no_tests(tmp_path: Path) -> Path:
    """Repo with no test files — all source goes to root subsystem."""
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "main.py").write_text("def main(): pass\n")
    (pkg / "utils.py").write_text("def helper(): pass\n")
    return tmp_path


class TestDiscoverTestFiles:
    """Verify that both test_*.py and *_test.py patterns are discovered."""

    def test_discovers_test_prefix_files(self, repo_with_tests: Path):
        result = decompose(repo_with_tests)
        all_test_files = []
        for sub in result:
            all_test_files.extend(sub.test_files)
        test_names = {f.name for f in all_test_files}
        assert "test_alpha.py" in test_names
        assert "test_beta.py" in test_names

    def test_discovers_test_suffix_files(self, repo_with_suffix_tests: Path):
        result = decompose(repo_with_suffix_tests)
        all_test_files = []
        for sub in result:
            all_test_files.extend(sub.test_files)
        test_names = {f.name for f in all_test_files}
        assert "ansi_test.py" in test_names
        assert "winterm_test.py" in test_names

    def test_init_files_not_counted_as_tests(self, repo_with_tests: Path):
        result = decompose(repo_with_tests)
        all_test_files = []
        for sub in result:
            all_test_files.extend(sub.test_files)
        test_names = {f.name for f in all_test_files}
        assert "__init__.py" not in test_names


class TestTestToSourceMapping:
    """Verify test files are correctly mapped to source modules via imports."""

    def test_maps_test_to_source_via_import(self, repo_with_tests: Path):
        result = decompose(repo_with_tests)
        # Find the subsystem containing alpha.py
        alpha_sub = None
        for sub in result:
            src_names = {f.name for f in sub.source_files}
            if "alpha.py" in src_names:
                alpha_sub = sub
                break
        assert alpha_sub is not None
        test_names = {f.name for f in alpha_sub.test_files}
        assert "test_alpha.py" in test_names

    def test_maps_suffix_test_to_source(self, repo_with_suffix_tests: Path):
        result = decompose(repo_with_suffix_tests)
        # Find subsystem containing ansi.py
        ansi_sub = None
        for sub in result:
            src_names = {f.name for f in sub.source_files}
            if "ansi.py" in src_names:
                ansi_sub = sub
                break
        assert ansi_sub is not None
        test_names = {f.name for f in ansi_sub.test_files}
        assert "ansi_test.py" in test_names

    def test_test_importing_multiple_sources_groups_them(
        self, repo_with_suffix_tests: Path
    ):
        """winterm_test.py imports both winterm and win32 → same subsystem."""
        result = decompose(repo_with_suffix_tests)
        winterm_sub = None
        for sub in result:
            src_names = {f.name for f in sub.source_files}
            if "winterm.py" in src_names:
                winterm_sub = sub
                break
        assert winterm_sub is not None
        src_names = {f.name for f in winterm_sub.source_files}
        assert "win32.py" in src_names
        assert "winterm.py" in src_names


class TestSubsystemGrouping:
    """Verify correct grouping into subsystems."""

    def test_untested_modules_go_to_root(self, repo_with_tests: Path):
        """gamma.py has no dedicated test → root subsystem."""
        result = decompose(repo_with_tests)
        root_sub = None
        for sub in result:
            if sub.name == "root":
                root_sub = sub
                break
        assert root_sub is not None
        src_names = {f.name for f in root_sub.source_files}
        assert "gamma.py" in src_names

    def test_no_tests_all_in_root(self, repo_no_tests: Path):
        """When no test files exist, all source goes to root."""
        result = decompose(repo_no_tests)
        assert len(result) == 1
        assert result[0].name == "root"
        src_names = {f.name for f in result[0].source_files}
        assert "main.py" in src_names
        assert "utils.py" in src_names

    def test_init_in_root_subsystem(self, repo_with_tests: Path):
        """__init__.py should go to root unless it has a dedicated test."""
        result = decompose(repo_with_tests)
        root_sub = None
        for sub in result:
            if sub.name == "root":
                root_sub = sub
                break
        assert root_sub is not None
        src_names = {f.name for f in root_sub.source_files}
        assert "__init__.py" in src_names

    def test_subsystem_name_derived_from_test_file(self, repo_with_tests: Path):
        """Subsystem names come from test file (strip test_ prefix / _test suffix)."""
        result = decompose(repo_with_tests)
        names = {sub.name for sub in result}
        assert "alpha" in names
        assert "beta" in names

    def test_number_of_subsystems(self, repo_with_tests: Path):
        """alpha, beta, and root → 3 subsystems."""
        result = decompose(repo_with_tests)
        assert len(result) == 3


class TestDependencyDetection:
    """Verify inter-subsystem dependencies are detected from source imports."""

    def test_detects_cross_subsystem_dependency(self, repo_with_tests: Path):
        """beta.py imports from alpha → beta subsystem depends on alpha."""
        result = decompose(repo_with_tests)
        beta_sub = None
        for sub in result:
            if sub.name == "beta":
                beta_sub = sub
                break
        assert beta_sub is not None
        assert "alpha" in beta_sub.dependencies

    def test_no_self_dependency(self, repo_with_tests: Path):
        """A subsystem should not list itself as a dependency."""
        result = decompose(repo_with_tests)
        for sub in result:
            assert sub.name not in sub.dependencies


class TestTopologicalSort:
    """Verify output is sorted topologically (leaves first)."""

    def test_leaves_come_first(self, repo_with_tests: Path):
        """alpha has no deps → should come before beta which depends on alpha."""
        result = decompose(repo_with_tests)
        names = [sub.name for sub in result]
        alpha_idx = names.index("alpha")
        beta_idx = names.index("beta")
        assert alpha_idx < beta_idx

    def test_root_ordering(self, repo_with_tests: Path):
        """Root subsystem (no deps) should be among the first."""
        result = decompose(repo_with_tests)
        # root has no dependencies, so it should be early
        root_sub = next(sub for sub in result if sub.name == "root")
        assert root_sub.dependencies == []


class TestSubsystemDataclass:
    """Verify Subsystem dataclass structure."""

    def test_subsystem_fields(self, repo_with_tests: Path):
        result = decompose(repo_with_tests)
        for sub in result:
            assert isinstance(sub, Subsystem)
            assert isinstance(sub.name, str)
            assert isinstance(sub.source_files, list)
            assert isinstance(sub.test_files, list)
            assert isinstance(sub.dependencies, list)
            for f in sub.source_files:
                assert isinstance(f, Path)
            for f in sub.test_files:
                assert isinstance(f, Path)


class TestColoramaStructure:
    """Integration test: works on colorama-like structure."""

    @pytest.fixture
    def colorama_repo(self, tmp_path: Path) -> Path:
        """Simulate colorama's directory layout."""
        pkg = tmp_path / "colorama"
        pkg.mkdir()
        (pkg / "__init__.py").write_text(
            "from .initialise import init\nfrom .ansi import Fore, Back, Style\n"
        )
        (pkg / "ansi.py").write_text("class Fore: pass\nclass Back: pass\nclass Style: pass\n")
        (pkg / "ansitowin32.py").write_text(
            textwrap.dedent("""\
            from .ansi import Fore
            from .winterm import WinTerm

            class AnsiToWin32: pass
            """)
        )
        (pkg / "initialise.py").write_text(
            textwrap.dedent("""\
            from .ansitowin32 import AnsiToWin32

            def init(): pass
            """)
        )
        (pkg / "win32.py").write_text("class Win32: pass\n")
        (pkg / "winterm.py").write_text(
            textwrap.dedent("""\
            from .win32 import Win32

            class WinTerm: pass
            """)
        )

        tests = pkg / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("")
        (tests / "ansi_test.py").write_text(
            textwrap.dedent("""\
            from colorama.ansi import Fore, Back, Style

            def test_fore(): pass
            """)
        )
        (tests / "ansitowin32_test.py").write_text(
            textwrap.dedent("""\
            from colorama.ansitowin32 import AnsiToWin32

            def test_ansitowin32(): pass
            """)
        )
        (tests / "initialise_test.py").write_text(
            textwrap.dedent("""\
            from colorama.initialise import init

            def test_init(): pass
            """)
        )
        (tests / "winterm_test.py").write_text(
            textwrap.dedent("""\
            from colorama.winterm import WinTerm
            from colorama.win32 import Win32

            def test_winterm(): pass
            """)
        )

        return tmp_path

    def test_colorama_produces_expected_subsystems(self, colorama_repo: Path):
        result = decompose(colorama_repo)
        names = {sub.name for sub in result}
        # Expected: ansi, ansitowin32, initialise, winterm, root
        assert "ansi" in names
        assert "ansitowin32" in names
        assert "initialise" in names
        assert "winterm" in names
        assert "root" in names

    def test_colorama_subsystem_count(self, colorama_repo: Path):
        result = decompose(colorama_repo)
        assert len(result) == 5

    def test_colorama_winterm_groups_win32(self, colorama_repo: Path):
        """win32.py is imported by winterm_test.py → grouped with winterm."""
        result = decompose(colorama_repo)
        winterm_sub = next(sub for sub in result if sub.name == "winterm")
        src_names = {f.name for f in winterm_sub.source_files}
        assert "winterm.py" in src_names
        assert "win32.py" in src_names

    def test_colorama_ansitowin32_depends_on_ansi_and_winterm(self, colorama_repo: Path):
        """ansitowin32.py imports from ansi and winterm → has those as deps."""
        result = decompose(colorama_repo)
        a2w_sub = next(sub for sub in result if sub.name == "ansitowin32")
        assert "ansi" in a2w_sub.dependencies
        assert "winterm" in a2w_sub.dependencies

    def test_colorama_topological_order(self, colorama_repo: Path):
        """ansi (no deps) should come before ansitowin32 (depends on ansi)."""
        result = decompose(colorama_repo)
        names = [sub.name for sub in result]
        ansi_idx = names.index("ansi")
        a2w_idx = names.index("ansitowin32")
        assert ansi_idx < a2w_idx
