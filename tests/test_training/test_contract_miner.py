"""Tests for TestContractMiner - behavioral contract extraction from test suites."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from architecture_model.training.test_contract_miner import (
    MethodContract,
    TestContractMiner,
    TestContracts,
)


@pytest.fixture
def miner():
    return TestContractMiner()


@pytest.fixture
def make_test_file(tmp_path):
    """Helper to create a test file with given content."""

    def _make(filename: str, content: str) -> Path:
        test_dir = tmp_path / "tests"
        test_dir.mkdir(exist_ok=True)
        f = test_dir / filename
        f.write_text(textwrap.dedent(content))
        return f

    return _make


class TestExtractsPublicApi:
    """Test extraction of public API symbols from imports."""

    def test_extracts_public_api_from_imports(self, miner, tmp_path):
        """from click import Command, Group → public_api contains both."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_basic.py").write_text(
            textwrap.dedent("""\
            from click import Command, Group

            def test_command_works():
                cmd = Command("hello")
                assert cmd.name == "hello"

            def test_group_works():
                grp = Group("grp")
                assert grp.name == "grp"
        """)
        )
        result = miner.mine(tmp_path, "click")
        assert "Command" in result.public_api
        assert "Group" in result.public_api


class TestExtractsAssertions:
    """Test assertion description extraction."""

    def test_extracts_assertion_equals(self, miner, tmp_path):
        """assert result == 42 → assertion 'result equals 42'."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_math.py").write_text(
            textwrap.dedent("""\
            from mylib import compute

            def test_compute_value():
                result = compute()
                assert result == 42
        """)
        )
        result = miner.mine(tmp_path, "mylib")
        assert result.contracts
        assertions = result.contracts[0].assertions
        assert any("equals" in a and "42" in a for a in assertions)

    def test_extracts_assertion_contains(self, miner, tmp_path):
        """assert 'foo' in output → assertion "'foo' in output"."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_output.py").write_text(
            textwrap.dedent("""\
            from mylib import render

            def test_output_has_foo():
                output = render()
                assert "foo" in output
        """)
        )
        result = miner.mine(tmp_path, "mylib")
        assert result.contracts
        assertions = result.contracts[0].assertions
        assert any("in" in a and "foo" in a for a in assertions)

    def test_extracts_assertion_not(self, miner, tmp_path):
        """assert not result.exception → assertion 'not result.exception'."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_clean.py").write_text(
            textwrap.dedent("""\
            from mylib import run

            def test_no_exception():
                result = run()
                assert not result.exception
        """)
        )
        result = miner.mine(tmp_path, "mylib")
        assert result.contracts
        assertions = result.contracts[0].assertions
        assert any("not" in a and "exception" in a for a in assertions)


class TestExtractsRaises:
    """Test exception extraction from pytest.raises."""

    def test_extracts_raises_contract(self, miner, tmp_path):
        """with pytest.raises(ValueError) → raises=['ValueError']."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_validation.py").write_text(
            textwrap.dedent("""\
            import pytest
            from mylib import validate

            def test_invalid_input_raises():
                with pytest.raises(ValueError):
                    validate("")
        """)
        )
        result = miner.mine(tmp_path, "mylib")
        assert result.contracts
        assert "ValueError" in result.contracts[0].raises


class TestExtractsParametrize:
    """Test parametrize input extraction."""

    def test_extracts_parametrize_cases(self, miner, tmp_path):
        """@pytest.mark.parametrize(...) → inputs populated."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_params.py").write_text(
            textwrap.dedent("""\
            import pytest
            from mylib import double

            @pytest.mark.parametrize("val,expected", [(1, 2), (3, 6), (5, 10)])
            def test_double(val, expected):
                assert double(val) == expected
        """)
        )
        result = miner.mine(tmp_path, "mylib")
        assert result.contracts
        assert result.contracts[0].inputs  # Should have extracted parametrize data


class TestIdentifiesTarget:
    """Test target identification from test code."""

    def test_identifies_target_from_method_call(self, miner, tmp_path):
        """runner.invoke(cli) → target contains 'invoke'."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_cli.py").write_text(
            textwrap.dedent("""\
            from click.testing import CliRunner
            from myapp import cli

            def test_hello_command():
                runner = CliRunner()
                result = runner.invoke(cli)
                assert result.exit_code == 0
        """)
        )
        result = miner.mine(tmp_path, "myapp")
        assert result.contracts
        # The target should reference invoke or the imported symbol
        target = result.contracts[0].target
        assert "invoke" in target or "cli" in target

    def test_identifies_target_from_test_name(self, miner, tmp_path):
        """def test_basic_functionality → target='basic_functionality' as fallback."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_misc.py").write_text(
            textwrap.dedent("""\
            def test_basic_functionality():
                x = 1 + 1
                assert x == 2
        """)
        )
        result = miner.mine(tmp_path, "somelib")
        assert result.contracts
        assert result.contracts[0].target == "basic_functionality"


class TestGroupsByComponent:
    """Test component grouping from imports."""

    def test_groups_by_component(self, miner, tmp_path):
        """Imports from two modules → contracts have correct component."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_multi.py").write_text(
            textwrap.dedent("""\
            from mylib.core import Parser
            from mylib.utils import helper

            def test_parser():
                p = Parser()
                assert p is not None

            def test_helper():
                result = helper()
                assert result == "ok"
        """)
        )
        result = miner.mine(tmp_path, "mylib")
        components = {c.component for c in result.contracts}
        assert "core" in components
        assert "utils" in components


class TestSummaryForPrompt:
    """Test prompt summary generation."""

    def test_summary_for_prompt_respects_max_tokens(self):
        """Output truncated at limit."""
        contracts = TestContracts(
            contracts=[
                MethodContract(
                    component="core",
                    target=f"function_{i}",
                    test_source=f"test.py::test_{i}",
                    assertions=[f"result equals {i}" * 10],
                )
                for i in range(50)
            ],
            total_tests=50,
            total_assertions=50,
        )
        summary = contracts.summary_for_prompt("core", max_tokens=50)
        # 50 tokens * 4 chars = 200 char limit
        assert len(summary) <= 200


class TestForComponentFilters:
    """Test component filtering."""

    def test_for_component_filters(self):
        """for_component returns only matching contracts."""
        contracts = TestContracts(
            contracts=[
                MethodContract(
                    component="core",
                    target="parse",
                    test_source="test.py::test_parse",
                ),
                MethodContract(
                    component="utils",
                    target="format",
                    test_source="test.py::test_format",
                ),
                MethodContract(
                    component="core",
                    target="validate",
                    test_source="test.py::test_validate",
                ),
            ]
        )
        core_contracts = contracts.for_component("core")
        assert len(core_contracts) == 2
        assert all(c.component == "core" for c in core_contracts)
        utils_contracts = contracts.for_component("utils")
        assert len(utils_contracts) == 1
        assert utils_contracts[0].target == "format"


class TestHandlesEdgeCases:
    """Test edge case handling."""

    def test_handles_empty_test_dir(self, miner, tmp_path):
        """No test files → empty TestContracts."""
        result = miner.mine(tmp_path, "somelib")
        assert result.contracts == []
        assert result.public_api == []
        assert result.total_tests == 0

    def test_handles_syntax_error_in_test_file(self, miner, tmp_path):
        """Malformed test file is skipped gracefully."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_broken.py").write_text("def test_x(:\n    pass\n")
        result = miner.mine(tmp_path, "somelib")
        assert result.contracts == []


class TestMinesRealClickTests:
    """Integration test against real click test suite."""

    @pytest.mark.skipif(
        not Path("/tmp/test-repos/click/tests").exists(),
        reason="click test repo not available",
    )
    def test_mines_real_click_tests(self, miner):
        """Mine the click test suite and verify meaningful extraction."""
        result = miner.mine(Path("/tmp/test-repos/click"), "click")
        # Should find a significant number of tests
        assert result.total_tests > 50
        # Should extract contracts
        assert len(result.contracts) > 20
        # Should identify public API
        assert len(result.public_api) > 5
        # Should have assertions
        assert result.total_assertions > 30
