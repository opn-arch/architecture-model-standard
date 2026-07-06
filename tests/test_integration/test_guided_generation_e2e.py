"""End-to-end integration test for test-guided generation pipeline.

Mocks: Surrogate (no Ollama), subprocess (no real pytest runs)
Real: TestContractMiner, FailureParser, PromptBuilder, CodeWriter, TestGuidedGenerator
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    ComponentKind,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
    Symbol,
    SymbolKind,
)
from architecture_model.training.code_writer import CodeWriter
from architecture_model.training.failure_parser import FailureParser
from architecture_model.training.prompt_builder import PromptBuilder
from architecture_model.training.surrogate import Surrogate
from architecture_model.training.test_contract_miner import TestContractMiner
from architecture_model.training.test_guided_generator import (
    TestGuidedGenerator,
    TestGuidedResult,
)
from architecture_model.training.test_runner import TestRunner


# ---------------------------------------------------------------------------
# Synthetic repo fixture
# ---------------------------------------------------------------------------

CORE_PY = """\
\"\"\"Core module with main functionality.\"\"\"


class Calculator:
    \"\"\"A simple calculator class.\"\"\"

    def add(self, a: int, b: int) -> int:
        \"\"\"Add two numbers.\"\"\"
        return a + b

    def subtract(self, a: int, b: int) -> int:
        \"\"\"Subtract b from a.\"\"\"
        return a - b

    def multiply(self, a: int, b: int) -> int:
        \"\"\"Multiply two numbers.\"\"\"
        return a * b

    def divide(self, a: int, b: int) -> float:
        \"\"\"Divide a by b. Raises ValueError on zero division.\"\"\"
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
"""

UTILS_PY = """\
\"\"\"Utility functions.\"\"\"


def format_result(value: float, precision: int = 2) -> str:
    \"\"\"Format a numeric result with given precision.\"\"\"
    return f"{value:.{precision}f}"


def validate_input(value) -> bool:
    \"\"\"Validate that input is numeric.\"\"\"
    return isinstance(value, (int, float))
"""

TEST_CORE_PY = """\
\"\"\"Tests for core module.\"\"\"
import pytest
from mypackage.core import Calculator


@pytest.fixture
def calc():
    \"\"\"Create a Calculator instance.\"\"\"
    return Calculator()


def test_add(calc):
    assert calc.add(2, 3) == 5


def test_subtract(calc):
    assert calc.subtract(10, 4) == 6


@pytest.mark.parametrize("a,b,expected", [
    (2, 3, 6),
    (0, 5, 0),
    (-1, 3, -3),
])
def test_multiply(calc, a, b, expected):
    assert calc.multiply(a, b) == expected


def test_divide(calc):
    assert calc.divide(10, 2) == 5.0


def test_divide_by_zero(calc):
    with pytest.raises(ValueError):
        calc.divide(10, 0)
"""

TEST_UTILS_PY = """\
\"\"\"Tests for utils module.\"\"\"
import pytest
from mypackage.utils import format_result, validate_input


def test_format_result_default_precision():
    assert format_result(3.14159) == "3.14"


def test_format_result_custom_precision():
    assert format_result(3.14159, 4) == "3.1416"


def test_validate_input_int():
    assert validate_input(42) is True


def test_validate_input_float():
    assert validate_input(3.14) is True


def test_validate_input_string():
    assert validate_input("hello") is False
"""

PYPROJECT_TOML = """\
[project]
name = "mypackage"
version = "0.1.0"

[build-system]
requires = ["setuptools"]
build-backend = "setuptools.backends._legacy:_Backend"
"""


@pytest.fixture
def synthetic_repo(tmp_path):
    """Create a synthetic repo with 2 modules and simple tests."""
    repo = tmp_path / "mypackage_repo"
    src = repo / "src" / "mypackage"
    tests = repo / "tests"

    src.mkdir(parents=True)
    tests.mkdir(parents=True)

    (src / "__init__.py").write_text("")
    (src / "core.py").write_text(CORE_PY)
    (src / "utils.py").write_text(UTILS_PY)
    (tests / "test_core.py").write_text(TEST_CORE_PY)
    (tests / "test_utils.py").write_text(TEST_UTILS_PY)
    (repo / "pyproject.toml").write_text(PYPROJECT_TOML)

    return repo


@pytest.fixture
def synthetic_model():
    """Create an ArchitectureModel matching the synthetic repo."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.2", project="mypackage"),
        entities=Entities(
            components=[
                Component(
                    id="comp-core",
                    name="core",
                    status=Status.ACTIVE,
                    kind=ComponentKind.LIBRARY,
                    symbols=[
                        Symbol(
                            name="Calculator",
                            kind=SymbolKind.CLASS,
                            members=["add", "subtract", "multiply", "divide"],
                        ),
                    ],
                ),
                Component(
                    id="comp-utils",
                    name="utils",
                    status=Status.ACTIVE,
                    kind=ComponentKind.LIBRARY,
                    functions=["format_result", "validate_input"],
                ),
            ],
        ),
        relationships=[
            Relationship(
                type=RelationType.DEPENDS_ON,
                from_id="comp-core",
                to_id="comp-utils",
            ),
        ],
    )


@pytest.fixture
def synthetic_manifest():
    """Build a minimal manifest for the synthetic repo."""
    return {
        "modules": [
            {
                "file": "src/mypackage/core.py",
                "classes": [
                    {
                        "name": "Calculator",
                        "methods": ["add", "subtract", "multiply", "divide"],
                    }
                ],
                "functions": [],
                "imports": [],
            },
            {
                "file": "src/mypackage/utils.py",
                "classes": [],
                "functions": ["format_result", "validate_input"],
                "imports": [],
            },
        ],
        "interfaces": [],
    }


# ---------------------------------------------------------------------------
# Canned LLM outputs
# ---------------------------------------------------------------------------

GENERATED_CODE_PASSING = """\
# core.py
class Calculator:
    \"\"\"A simple calculator class.\"\"\"

    def add(self, a: int, b: int) -> int:
        return a + b

    def subtract(self, a: int, b: int) -> int:
        return a - b

    def multiply(self, a: int, b: int) -> int:
        return a * b

    def divide(self, a: int, b: int) -> float:
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b

# utils.py
def format_result(value: float, precision: int = 2) -> str:
    return f"{value:.{precision}f}"

def validate_input(value) -> bool:
    return isinstance(value, (int, float))
"""

GENERATED_CODE_FAILING = """\
# core.py
class Calculator:
    \"\"\"A simple calculator class.\"\"\"

    def add(self, a: int, b: int) -> int:
        return a + b

    def subtract(self, a: int, b: int) -> int:
        return a - b

    def multiply(self, a: int, b: int) -> int:
        return 0  # Bug: always returns 0

    def divide(self, a: int, b: int) -> float:
        return a / b  # Bug: no zero check

# utils.py
def format_result(value: float, precision: int = 2) -> str:
    return str(value)  # Bug: wrong formatting

def validate_input(value) -> bool:
    return isinstance(value, (int, float))
"""

GENERATED_CODE_STAGNANT = """\
# core.py
class Calculator:
    \"\"\"A simple calculator class.\"\"\"

    def add(self, a: int, b: int) -> int:
        return a + b

    def subtract(self, a: int, b: int) -> int:
        return a - b

    def multiply(self, a: int, b: int) -> int:
        return 0  # Still wrong

    def divide(self, a: int, b: int) -> float:
        return a / b  # Still no zero check

# utils.py
def format_result(value: float, precision: int = 2) -> str:
    return str(value)  # Still wrong

def validate_input(value) -> bool:
    return isinstance(value, (int, float))
"""

# Pytest output strings
PYTEST_ALL_PASS = """\
collected 10 items

tests/test_core.py::test_add PASSED
tests/test_core.py::test_subtract PASSED
tests/test_core.py::test_multiply[2-3-6] PASSED
tests/test_core.py::test_multiply[0-5-0] PASSED
tests/test_core.py::test_multiply[-1-3--3] PASSED
tests/test_core.py::test_divide PASSED
tests/test_core.py::test_divide_by_zero PASSED
tests/test_utils.py::test_format_result_default_precision PASSED
tests/test_utils.py::test_format_result_custom_precision PASSED
tests/test_utils.py::test_validate_input_int PASSED
tests/test_utils.py::test_validate_input_float PASSED
tests/test_utils.py::test_validate_input_string PASSED

======================== 10 passed in 0.5s ========================
"""

PYTEST_SOME_FAIL = """\
collected 10 items

tests/test_core.py::test_add PASSED
tests/test_core.py::test_subtract PASSED
tests/test_core.py::test_multiply[2-3-6] FAILED
tests/test_core.py::test_multiply[0-5-0] PASSED
tests/test_core.py::test_multiply[-1-3--3] FAILED
tests/test_core.py::test_divide PASSED
tests/test_core.py::test_divide_by_zero FAILED
tests/test_utils.py::test_format_result_default_precision FAILED
tests/test_utils.py::test_format_result_custom_precision FAILED
tests/test_utils.py::test_validate_input_int PASSED
tests/test_utils.py::test_validate_input_float PASSED
tests/test_utils.py::test_validate_input_string PASSED

=========================== FAILURES ===========================
___________________________ test_multiply[2-3-6] ___________________________

    def test_multiply(calc, a, b, expected):
>       assert calc.multiply(a, b) == expected
E       assert 0 == 6

___________________________ test_multiply[-1-3--3] ___________________________

    def test_multiply(calc, a, b, expected):
>       assert calc.multiply(a, b) == expected
E       assert 0 == -3

___________________________ test_divide_by_zero ___________________________

    def test_divide_by_zero(calc):
>       with pytest.raises(ValueError):
E       Failed: DID NOT RAISE <class 'ValueError'>

___________________________ test_format_result_default_precision ___________________________

    def test_format_result_default_precision():
>       assert format_result(3.14159) == "3.14"
E       AssertionError: assert '3.14159' == '3.14'

___________________________ test_format_result_custom_precision ___________________________

    def test_format_result_custom_precision():
>       assert format_result(3.14159, 4) == "3.1416"
E       AssertionError: assert '3.14159' == '3.1416'

=========================== short test summary info ===========================
FAILED tests/test_core.py::test_multiply[2-3-6] - AssertionError: assert 0 == 6
FAILED tests/test_core.py::test_multiply[-1-3--3] - AssertionError: assert 0 == -3
FAILED tests/test_core.py::test_divide_by_zero - Failed: DID NOT RAISE <class 'ValueError'>
FAILED tests/test_utils.py::test_format_result_default_precision - AssertionError: assert '3.14159' == '3.14'
FAILED tests/test_utils.py::test_format_result_custom_precision - AssertionError: assert '3.14159' == '3.1416'
======================== 5 failed, 5 passed in 0.8s ========================
"""


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_subprocess_result(stdout: str, returncode: int = 0):
    """Create a mock subprocess.CompletedProcess."""
    mock_result = MagicMock()
    mock_result.stdout = stdout
    mock_result.stderr = ""
    mock_result.returncode = returncode
    return mock_result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFullPipelineInitialPass:
    """Test: Surrogate generates code, mocked pytest returns all-pass."""

    @pytest.mark.asyncio
    async def test_full_pipeline_initial_pass(
        self, synthetic_repo, synthetic_model, synthetic_manifest
    ):
        """All tests pass on first try → pass_rate=1.0, iterations=1, converged=True."""
        # Mock surrogate
        surrogate = MagicMock(spec=Surrogate)
        surrogate.generate_with_prompt = AsyncMock(return_value=GENERATED_CODE_PASSING)

        # Real components
        test_runner = TestRunner()
        contract_miner = TestContractMiner()
        prompt_builder = PromptBuilder()
        code_writer = CodeWriter()
        failure_parser = FailureParser()

        generator = TestGuidedGenerator(
            surrogate=surrogate,
            test_runner=test_runner,
            contract_miner=contract_miner,
            prompt_builder=prompt_builder,
            code_writer=code_writer,
            failure_parser=failure_parser,
            max_retries=5,
            convergence_threshold=3,
        )

        # Mock subprocess to return all-pass pytest output
        with patch(
            "architecture_model.training.test_guided_generator.subprocess.run"
        ) as mock_run:
            mock_run.return_value = _make_subprocess_result(PYTEST_ALL_PASS)

            result = await generator.generate(
                model=synthetic_model,
                manifest=synthetic_manifest,
                repo_path=synthetic_repo,
                package_name="mypackage",
            )

        assert result.final_pass_rate == 1.0
        assert result.iterations == 1
        assert result.converged is True
        assert len(result.attempts) == 1
        assert result.attempts[0].pass_rate == 1.0


class TestFullPipelineRetryImproves:
    """Test: First run fails, retry generates improved code that passes."""

    @pytest.mark.asyncio
    async def test_full_pipeline_retry_improves(
        self, synthetic_repo, synthetic_model, synthetic_manifest
    ):
        """Fails first, passes on retry → iterations=2."""
        # Mock surrogate: first call returns failing code,
        # subsequent calls return fixed component code (one per failing component).
        # The targeted retry calls generate_with_prompt once per failing component.
        fixed_core = (
            'class Calculator:\n'
            '    def add(self, a, b): return a + b\n'
            '    def subtract(self, a, b): return a - b\n'
            '    def multiply(self, a, b): return a * b\n'
            '    def divide(self, a, b):\n'
            '        if b == 0: raise ValueError("Cannot divide by zero")\n'
            '        return a / b\n'
        )
        fixed_utils = (
            'def format_result(value, precision=2): return f"{value:.{precision}f}"\n'
            'def validate_input(value): return isinstance(value, (int, float))\n'
        )
        surrogate = MagicMock(spec=Surrogate)
        surrogate.generate_with_prompt = AsyncMock(
            side_effect=[GENERATED_CODE_FAILING, fixed_core, fixed_utils]
        )

        test_runner = TestRunner()
        contract_miner = TestContractMiner()
        prompt_builder = PromptBuilder()
        code_writer = CodeWriter()
        failure_parser = FailureParser()

        generator = TestGuidedGenerator(
            surrogate=surrogate,
            test_runner=test_runner,
            contract_miner=contract_miner,
            prompt_builder=prompt_builder,
            code_writer=code_writer,
            failure_parser=failure_parser,
            max_retries=5,
            convergence_threshold=3,
        )

        # Mock subprocess: first run fails, second run passes
        with patch(
            "architecture_model.training.test_guided_generator.subprocess.run"
        ) as mock_run:
            mock_run.side_effect = [
                _make_subprocess_result(PYTEST_SOME_FAIL, returncode=1),
                _make_subprocess_result(PYTEST_ALL_PASS, returncode=0),
            ]

            result = await generator.generate(
                model=synthetic_model,
                manifest=synthetic_manifest,
                repo_path=synthetic_repo,
                package_name="mypackage",
            )

        assert result.iterations == 2
        assert result.final_pass_rate == 1.0
        assert result.converged is True
        assert len(result.attempts) == 2
        assert result.attempts[0].pass_rate < 1.0
        assert result.attempts[1].pass_rate == 1.0


class TestFullPipelineConvergenceStops:
    """Test: Surrogate keeps generating same quality, convergence detected."""

    @pytest.mark.asyncio
    async def test_full_pipeline_convergence_stops(
        self, synthetic_repo, synthetic_model, synthetic_manifest
    ):
        """Pass rate doesn't improve → converged=True, iterations <= max_retries."""
        # Mock surrogate: always returns stagnant code
        surrogate = MagicMock(spec=Surrogate)
        surrogate.generate_with_prompt = AsyncMock(
            return_value=GENERATED_CODE_STAGNANT
        )

        test_runner = TestRunner()
        contract_miner = TestContractMiner()
        prompt_builder = PromptBuilder()
        code_writer = CodeWriter()
        failure_parser = FailureParser()

        max_retries = 10
        convergence_threshold = 3

        generator = TestGuidedGenerator(
            surrogate=surrogate,
            test_runner=test_runner,
            contract_miner=contract_miner,
            prompt_builder=prompt_builder,
            code_writer=code_writer,
            failure_parser=failure_parser,
            max_retries=max_retries,
            convergence_threshold=convergence_threshold,
        )

        # Mock subprocess: always returns same failures
        with patch(
            "architecture_model.training.test_guided_generator.subprocess.run"
        ) as mock_run:
            mock_run.return_value = _make_subprocess_result(
                PYTEST_SOME_FAIL, returncode=1
            )

            result = await generator.generate(
                model=synthetic_model,
                manifest=synthetic_manifest,
                repo_path=synthetic_repo,
                package_name="mypackage",
            )

        assert result.converged is True
        assert result.final_pass_rate < 1.0
        # Should stop early due to convergence (not exhaust all retries)
        assert result.iterations <= max_retries
        # Must have at least convergence_threshold attempts to detect convergence
        assert result.iterations >= convergence_threshold


class TestContractMiningFeedsIntoPrompt:
    """Test: Contracts mined from test fixtures appear in generation prompt."""

    @pytest.mark.asyncio
    async def test_contract_mining_feeds_into_prompt(
        self, synthetic_repo, synthetic_model, synthetic_manifest
    ):
        """Mined contracts are passed into PromptBuilder call."""
        # Mock surrogate to capture the prompt
        surrogate = MagicMock(spec=Surrogate)
        surrogate.generate_with_prompt = AsyncMock(return_value=GENERATED_CODE_PASSING)

        test_runner = TestRunner()
        contract_miner = TestContractMiner()
        prompt_builder = PromptBuilder()
        code_writer = CodeWriter()
        failure_parser = FailureParser()

        generator = TestGuidedGenerator(
            surrogate=surrogate,
            test_runner=test_runner,
            contract_miner=contract_miner,
            prompt_builder=prompt_builder,
            code_writer=code_writer,
            failure_parser=failure_parser,
            max_retries=5,
        )

        with patch(
            "architecture_model.training.test_guided_generator.subprocess.run"
        ) as mock_run:
            mock_run.return_value = _make_subprocess_result(PYTEST_ALL_PASS)

            await generator.generate(
                model=synthetic_model,
                manifest=synthetic_manifest,
                repo_path=synthetic_repo,
                package_name="mypackage",
            )

        # Verify surrogate was called with the prompt
        assert surrogate.generate_with_prompt.called
        call_args = surrogate.generate_with_prompt.call_args
        system_prompt = call_args[0][0] if call_args[0] else call_args[1].get("system", "")
        user_prompt = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("user", "")

        # The system prompt should contain behavioral contracts section
        assert "Behavioral Contracts" in system_prompt or "contracts" in system_prompt.lower()

        # Also verify that the contract miner actually found contracts from our test files
        contracts = contract_miner.mine(synthetic_repo, "mypackage")
        assert contracts.total_tests > 0
        assert len(contracts.contracts) > 0
        # Should find at least Calculator-related contracts
        component_names = {c.component for c in contracts.contracts}
        assert len(component_names) > 0


class TestTrainingSignalFromResult:
    """Test: record_test_guided_signal returns correct training signal."""

    @pytest.mark.asyncio
    async def test_training_signal_from_result(
        self, synthetic_repo, synthetic_model, synthetic_manifest
    ):
        """After generation, record_test_guided_signal returns correct dict."""
        from architecture_model.training.pipeline import TrainingPipeline
        from architecture_model.training.controller import MPCController
        from architecture_model.training.dataset import DatasetStore
        from architecture_model.training.evaluator import Evaluator

        # Targeted retry calls generate_with_prompt per failing component
        fixed_core = (
            'class Calculator:\n'
            '    def add(self, a, b): return a + b\n'
            '    def subtract(self, a, b): return a - b\n'
            '    def multiply(self, a, b): return a * b\n'
            '    def divide(self, a, b):\n'
            '        if b == 0: raise ValueError("Cannot divide by zero")\n'
            '        return a / b\n'
        )
        fixed_utils = (
            'def format_result(value, precision=2): return f"{value:.{precision}f}"\n'
            'def validate_input(value): return isinstance(value, (int, float))\n'
        )
        surrogate = MagicMock(spec=Surrogate)
        surrogate.generate_with_prompt = AsyncMock(
            side_effect=[GENERATED_CODE_FAILING, fixed_core, fixed_utils]
        )

        test_runner = TestRunner()
        contract_miner = TestContractMiner()
        prompt_builder = PromptBuilder()
        code_writer = CodeWriter()
        failure_parser = FailureParser()

        generator = TestGuidedGenerator(
            surrogate=surrogate,
            test_runner=test_runner,
            contract_miner=contract_miner,
            prompt_builder=prompt_builder,
            code_writer=code_writer,
            failure_parser=failure_parser,
            max_retries=5,
        )

        with patch(
            "architecture_model.training.test_guided_generator.subprocess.run"
        ) as mock_run:
            mock_run.side_effect = [
                _make_subprocess_result(PYTEST_SOME_FAIL, returncode=1),
                _make_subprocess_result(PYTEST_ALL_PASS, returncode=0),
            ]

            result = await generator.generate(
                model=synthetic_model,
                manifest=synthetic_manifest,
                repo_path=synthetic_repo,
                package_name="mypackage",
            )

        # Now test record_test_guided_signal via a mocked pipeline
        mock_oracle = MagicMock()
        mock_store = MagicMock(spec=DatasetStore)
        mock_store.save_preference = MagicMock()
        mock_evaluator = MagicMock(spec=Evaluator)
        mock_controller = MagicMock(spec=MPCController)
        mock_controller.state = MagicMock()
        mock_controller.state.iteration = 1
        mock_trainer = MagicMock()
        mock_repo_fetcher = MagicMock()

        pipeline = TrainingPipeline(
            surrogate=surrogate,
            oracle=mock_oracle,
            store=mock_store,
            evaluator=mock_evaluator,
            controller=mock_controller,
            trainer=mock_trainer,
            repo_fetcher=mock_repo_fetcher,
        )

        signal = pipeline.record_test_guided_signal(
            result=result,
            model_yaml="test model yaml",
            iteration=1,
        )

        assert "test_pass_rate" in signal
        assert signal["test_pass_rate"] == result.final_pass_rate
        assert "test_iterations" in signal
        assert signal["test_iterations"] == result.iterations
        assert "dpo_pairs_generated" in signal
        # With improvement from attempt 0 → attempt 1, should have at least 1 pair
        assert signal["dpo_pairs_generated"] >= 1
