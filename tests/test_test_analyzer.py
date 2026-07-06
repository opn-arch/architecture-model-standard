"""Tests for the test_analyzer module — behavioral contract extraction from test files."""

import textwrap
import tempfile
from pathlib import Path

import pytest

from architecture_model.manifest.test_analyzer import (
    TestAnalysisResult,
    analyze_test_file,
    extract_constants_from_contracts,
)
from architecture_model.core.types import Constant, TestContract


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def unittest_file(tmp_path: Path) -> Path:
    """A minimal unittest-style test file."""
    code = textwrap.dedent("""\
        import unittest
        from mypackage.colors import Fore, Back

        class TestColors(unittest.TestCase):
            def test_fore_black(self):
                self.assertEqual(Fore.BLACK, '\\033[30m')

            def test_fore_red(self):
                self.assertEqual(Fore.RED, '\\033[31m')

            def test_raises_on_invalid(self):
                with self.assertRaises(ValueError):
                    Fore.invalid_color()

            def test_is_string(self):
                self.assertIsInstance(Fore.BLACK, str)

            def test_true_condition(self):
                self.assertTrue(Fore.BLACK.startswith('\\033'))
    """)
    f = tmp_path / "test_colors.py"
    f.write_text(code)
    return f


@pytest.fixture
def pytest_file(tmp_path: Path) -> Path:
    """A minimal pytest-style test file."""
    code = textwrap.dedent("""\
        import pytest
        from mypackage.colors import Fore

        def test_fore_black():
            assert Fore.BLACK == '\\033[30m'

        def test_fore_red():
            assert Fore.RED == '\\033[31m'

        def test_raises_value_error():
            with pytest.raises(ValueError):
                Fore.invalid_color()

        def test_isinstance_check():
            assert isinstance(Fore.BLACK, str)
    """)
    f = tmp_path / "test_colors_pytest.py"
    f.write_text(code)
    return f


# ---------------------------------------------------------------------------
# Test: TestAnalysisResult structure
# ---------------------------------------------------------------------------


class TestAnalysisResultStructure:
    def test_result_has_expected_fields(self, unittest_file: Path):
        result = analyze_test_file(unittest_file)
        assert isinstance(result, TestAnalysisResult)
        assert result.test_file == "test_colors.py"
        assert isinstance(result.contracts, list)
        assert isinstance(result.constants, list)
        assert isinstance(result.required_imports, list)
        assert isinstance(result.test_count, int)


# ---------------------------------------------------------------------------
# Test: unittest assertEqual extraction
# ---------------------------------------------------------------------------


class TestUnittestAssertEqual:
    def test_extracts_value_equality_contracts(self, unittest_file: Path):
        result = analyze_test_file(unittest_file)
        value_contracts = [c for c in result.contracts if c.contract_type == "value_equality"]
        assert len(value_contracts) >= 2
        # Should capture Fore.BLACK == '\033[30m'
        assertions = [c.assertion for c in value_contracts]
        assert any("BLACK" in a and "30m" in a for a in assertions)
        assert any("RED" in a and "31m" in a for a in assertions)

    def test_assertEqual_produces_test_contract(self, unittest_file: Path):
        result = analyze_test_file(unittest_file)
        value_contracts = [c for c in result.contracts if c.contract_type == "value_equality"]
        for c in value_contracts:
            assert isinstance(c, TestContract)
            assert c.test_file == "test_colors.py"
            assert c.test_method != ""

    def test_extracts_assertRaises(self, unittest_file: Path):
        result = analyze_test_file(unittest_file)
        raises_contracts = [c for c in result.contracts if c.contract_type == "raises"]
        assert len(raises_contracts) >= 1
        assert any("ValueError" in c.assertion for c in raises_contracts)

    def test_extracts_assertIsInstance(self, unittest_file: Path):
        result = analyze_test_file(unittest_file)
        type_contracts = [c for c in result.contracts if c.contract_type == "type_check"]
        assert len(type_contracts) >= 1
        assert any("str" in c.assertion for c in type_contracts)

    def test_extracts_assertTrue(self, unittest_file: Path):
        result = analyze_test_file(unittest_file)
        # assertTrue should produce some contract (state_change or general)
        all_methods = [c.test_method for c in result.contracts]
        assert "test_true_condition" in all_methods


# ---------------------------------------------------------------------------
# Test: pytest-style assertion extraction
# ---------------------------------------------------------------------------


class TestPytestAssertions:
    def test_extracts_assert_eq(self, pytest_file: Path):
        result = analyze_test_file(pytest_file)
        value_contracts = [c for c in result.contracts if c.contract_type == "value_equality"]
        assert len(value_contracts) >= 2
        assertions = [c.assertion for c in value_contracts]
        assert any("BLACK" in a for a in assertions)

    def test_extracts_pytest_raises(self, pytest_file: Path):
        result = analyze_test_file(pytest_file)
        raises_contracts = [c for c in result.contracts if c.contract_type == "raises"]
        assert len(raises_contracts) >= 1
        assert any("ValueError" in c.assertion for c in raises_contracts)

    def test_extracts_assert_isinstance(self, pytest_file: Path):
        result = analyze_test_file(pytest_file)
        type_contracts = [c for c in result.contracts if c.contract_type == "type_check"]
        assert len(type_contracts) >= 1
        assert any("str" in c.assertion for c in type_contracts)

    def test_test_count(self, pytest_file: Path):
        result = analyze_test_file(pytest_file)
        assert result.test_count == 4


# ---------------------------------------------------------------------------
# Test: Import extraction
# ---------------------------------------------------------------------------


class TestImportExtraction:
    def test_unittest_imports(self, unittest_file: Path):
        result = analyze_test_file(unittest_file)
        assert "Fore" in result.required_imports
        assert "Back" in result.required_imports

    def test_pytest_imports(self, pytest_file: Path):
        result = analyze_test_file(pytest_file)
        assert "Fore" in result.required_imports

    def test_ignores_stdlib_imports(self, unittest_file: Path):
        """Should not include 'unittest' or 'pytest' as required imports."""
        result = analyze_test_file(unittest_file)
        assert "unittest" not in result.required_imports
        assert "TestCase" not in result.required_imports


# ---------------------------------------------------------------------------
# Test: Constant extraction from contracts
# ---------------------------------------------------------------------------


class TestConstantExtraction:
    def test_extracts_constants_from_escape_codes(self, unittest_file: Path):
        result = analyze_test_file(unittest_file)
        constants = result.constants
        assert len(constants) >= 2
        names = [c.name for c in constants]
        assert "BLACK" in names
        assert "RED" in names

    def test_constant_values_are_numeric_codes(self, unittest_file: Path):
        result = analyze_test_file(unittest_file)
        black = next(c for c in result.constants if c.name == "BLACK")
        assert black.value == "30"
        red = next(c for c in result.constants if c.name == "RED")
        assert red.value == "31"

    def test_constant_context_includes_parent(self, unittest_file: Path):
        result = analyze_test_file(unittest_file)
        black = next(c for c in result.constants if c.name == "BLACK")
        assert "Fore" in black.context

    def test_extract_constants_from_contracts_standalone(self):
        """Test the standalone helper function."""
        contracts = [
            TestContract(
                test_file="test.py",
                test_method="test_x",
                assertion="Fore.BLACK == '\\033[30m'",
                contract_type="value_equality",
            ),
            TestContract(
                test_file="test.py",
                test_method="test_y",
                assertion="Back.RED == '\\033[41m'",
                contract_type="value_equality",
            ),
        ]
        constants = extract_constants_from_contracts(contracts)
        assert len(constants) == 2
        names = [c.name for c in constants]
        assert "BLACK" in names
        assert "RED" in names
        black = next(c for c in constants if c.name == "BLACK")
        assert black.value == "30"
        red = next(c for c in constants if c.name == "RED")
        assert red.value == "41"


# ---------------------------------------------------------------------------
# Test: Real-world colorama ansi_test.py (conditional)
# ---------------------------------------------------------------------------


COLORAMA_TEST = Path("/tmp/test-repos/colorama/colorama/tests/ansi_test.py")


@pytest.mark.skipif(
    not COLORAMA_TEST.exists(),
    reason="colorama test repo not available at /tmp/test-repos/colorama",
)
class TestColoramaAnsiTest:
    def test_parses_without_error(self):
        result = analyze_test_file(COLORAMA_TEST)
        assert result is not None
        assert result.test_count >= 3  # at least 3 test methods

    def test_extracts_fore_constants(self):
        result = analyze_test_file(COLORAMA_TEST)
        names = [c.name for c in result.constants]
        assert "BLACK" in names
        assert "RED" in names
        assert "GREEN" in names
        assert "RESET" in names

    def test_fore_black_value(self):
        result = analyze_test_file(COLORAMA_TEST)
        black = next(c for c in result.constants if c.name == "BLACK" and "Fore" in c.context)
        assert black.value == "30"

    def test_fore_reset_value(self):
        result = analyze_test_file(COLORAMA_TEST)
        resets = [c for c in result.constants if c.name == "RESET" and "Fore" in c.context]
        assert len(resets) >= 1
        assert resets[0].value == "39"

    def test_back_constants(self):
        result = analyze_test_file(COLORAMA_TEST)
        back_constants = [c for c in result.constants if "Back" in c.context]
        assert len(back_constants) >= 8  # BLACK through WHITE + RESET

    def test_style_constants(self):
        result = analyze_test_file(COLORAMA_TEST)
        style_constants = [c for c in result.constants if "Style" in c.context]
        assert len(style_constants) >= 3  # DIM, NORMAL, BRIGHT

    def test_required_imports(self):
        result = analyze_test_file(COLORAMA_TEST)
        assert "Fore" in result.required_imports
        assert "Back" in result.required_imports
        assert "Style" in result.required_imports

    def test_contract_count(self):
        """colorama ansi_test has many assertEqual calls."""
        result = analyze_test_file(COLORAMA_TEST)
        assert len(result.contracts) >= 20  # lots of assertions
