"""Tests for TestGuidedGenerator retry loop controller."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from architecture_model.training.test_guided_generator import (
    GenerationAttempt,
    TestGuidedGenerator,
    TestGuidedResult,
)


class TestGenerationAttemptDataclass:
    """Tests for GenerationAttempt dataclass."""

    __test__ = True  # This is a real test class

    def test_creation(self):
        attempt = GenerationAttempt(
            iteration=1,
            code="def hello(): pass",
            pass_rate=0.8,
            failures=MagicMock(),
            time_seconds=1.5,
            components_regenerated=["core"],
        )
        assert attempt.iteration == 1
        assert attempt.pass_rate == 0.8
        assert attempt.time_seconds == 1.5
        assert attempt.components_regenerated == ["core"]

    def test_default_components_list(self):
        attempt = GenerationAttempt(
            iteration=0,
            code="",
            pass_rate=0.0,
            failures=MagicMock(),
            time_seconds=0.0,
            components_regenerated=[],
        )
        assert attempt.components_regenerated == []


class TestTestGuidedResultDataclass:
    """Tests for TestGuidedResult dataclass."""

    __test__ = True

    def test_creation(self):
        result = TestGuidedResult(
            final_code="code",
            final_pass_rate=0.95,
            iterations=3,
            attempts=[],
            converged=True,
            structural_score=0.85,
        )
        assert result.final_code == "code"
        assert result.final_pass_rate == 0.95
        assert result.iterations == 3
        assert result.converged is True
        assert result.structural_score == 0.85

    def test_structural_score_optional(self):
        result = TestGuidedResult(
            final_code="code",
            final_pass_rate=1.0,
            iterations=1,
            attempts=[],
            converged=True,
            structural_score=None,
        )
        assert result.structural_score is None


class TestGuidedGeneratorInit:
    """Tests for TestGuidedGenerator.__init__."""

    __test__ = True

    def _make_generator(self, max_retries=10, convergence_threshold=3):
        surrogate = MagicMock()
        test_runner = MagicMock()
        contract_miner = MagicMock()
        prompt_builder = MagicMock()
        code_writer = MagicMock()
        failure_parser = MagicMock()
        return TestGuidedGenerator(
            surrogate=surrogate,
            test_runner=test_runner,
            contract_miner=contract_miner,
            prompt_builder=prompt_builder,
            code_writer=code_writer,
            failure_parser=failure_parser,
            max_retries=max_retries,
            convergence_threshold=convergence_threshold,
        )

    def test_stores_dependencies(self):
        surrogate = MagicMock()
        test_runner = MagicMock()
        contract_miner = MagicMock()
        prompt_builder = MagicMock()
        code_writer = MagicMock()
        failure_parser = MagicMock()
        gen = TestGuidedGenerator(
            surrogate=surrogate,
            test_runner=test_runner,
            contract_miner=contract_miner,
            prompt_builder=prompt_builder,
            code_writer=code_writer,
            failure_parser=failure_parser,
        )
        assert gen._surrogate is surrogate
        assert gen._test_runner is test_runner
        assert gen._contract_miner is contract_miner
        assert gen._prompt_builder is prompt_builder
        assert gen._code_writer is code_writer
        assert gen._failure_parser is failure_parser

    def test_default_max_retries(self):
        gen = self._make_generator()
        assert gen._max_retries == 10

    def test_custom_max_retries(self):
        gen = self._make_generator(max_retries=5)
        assert gen._max_retries == 5

    def test_default_convergence_threshold(self):
        gen = self._make_generator()
        assert gen._convergence_threshold == 3

    def test_custom_convergence_threshold(self):
        gen = self._make_generator(convergence_threshold=5)
        assert gen._convergence_threshold == 5


class TestCheckConvergence:
    """Tests for TestGuidedGenerator._check_convergence."""

    __test__ = True

    def _make_generator(self, convergence_threshold=3):
        return TestGuidedGenerator(
            surrogate=MagicMock(),
            test_runner=MagicMock(),
            contract_miner=MagicMock(),
            prompt_builder=MagicMock(),
            code_writer=MagicMock(),
            failure_parser=MagicMock(),
            convergence_threshold=convergence_threshold,
        )

    def _make_attempt(self, pass_rate: float) -> GenerationAttempt:
        return GenerationAttempt(
            iteration=0,
            code="",
            pass_rate=pass_rate,
            failures=MagicMock(),
            time_seconds=0.0,
            components_regenerated=[],
        )

    def test_returns_false_when_fewer_attempts_than_threshold(self):
        gen = self._make_generator(convergence_threshold=3)
        attempts = [self._make_attempt(0.5), self._make_attempt(0.5)]
        assert gen._check_convergence(attempts) is False

    def test_returns_true_when_last_n_same_pass_rate(self):
        gen = self._make_generator(convergence_threshold=3)
        attempts = [
            self._make_attempt(0.5),
            self._make_attempt(0.5),
            self._make_attempt(0.5),
        ]
        assert gen._check_convergence(attempts) is True

    def test_returns_true_when_last_n_decreasing(self):
        """Converged if last N show no improvement (decreasing counts)."""
        gen = self._make_generator(convergence_threshold=3)
        attempts = [
            self._make_attempt(0.8),
            self._make_attempt(0.7),
            self._make_attempt(0.6),
        ]
        assert gen._check_convergence(attempts) is True

    def test_returns_false_when_improvement_in_last_n(self):
        gen = self._make_generator(convergence_threshold=3)
        attempts = [
            self._make_attempt(0.5),
            self._make_attempt(0.6),
            self._make_attempt(0.7),
        ]
        assert gen._check_convergence(attempts) is False

    def test_returns_false_when_last_attempt_improves(self):
        gen = self._make_generator(convergence_threshold=3)
        attempts = [
            self._make_attempt(0.5),
            self._make_attempt(0.5),
            self._make_attempt(0.6),
        ]
        assert gen._check_convergence(attempts) is False

    def test_empty_attempts_returns_false(self):
        gen = self._make_generator(convergence_threshold=3)
        assert gen._check_convergence([]) is False

    def test_convergence_threshold_4(self):
        gen = self._make_generator(convergence_threshold=4)
        attempts = [
            self._make_attempt(0.5),
            self._make_attempt(0.5),
            self._make_attempt(0.5),
        ]
        # Only 3 attempts but threshold is 4
        assert gen._check_convergence(attempts) is False

        attempts.append(self._make_attempt(0.5))
        assert gen._check_convergence(attempts) is True


class TestInitialGeneration:
    """Tests for TestGuidedGenerator._initial_generation."""

    __test__ = True

    @pytest.fixture
    def generator(self):
        surrogate = MagicMock()
        surrogate.generate_with_prompt = AsyncMock(return_value="class Core: pass")
        return TestGuidedGenerator(
            surrogate=surrogate,
            test_runner=MagicMock(),
            contract_miner=MagicMock(),
            prompt_builder=MagicMock(),
            code_writer=MagicMock(),
            failure_parser=MagicMock(),
        )

    def test_calls_prompt_builder_and_surrogate(self, generator):
        model_yaml = "meta:\n  project: test\n"
        contracts = MagicMock()
        contracts.summary_for_prompt.return_value = "- target: does X"

        generator._prompt_builder.build_generation_prompt.return_value = (
            "system prompt",
            "user content",
        )

        result = asyncio.run(
            generator._initial_generation(model_yaml, contracts)
        )

        generator._prompt_builder.build_generation_prompt.assert_called_once_with(
            model_yaml, "- target: does X", None
        )
        generator._surrogate.generate_with_prompt.assert_called_once_with(
            "system prompt", "user content"
        )
        assert result == "class Core: pass"


class TestRetryComponent:
    """Tests for TestGuidedGenerator._retry_component."""

    __test__ = True

    @pytest.fixture
    def generator(self):
        surrogate = MagicMock()
        surrogate.generate_with_prompt = AsyncMock(return_value="class Fixed: pass")
        prompt_builder = MagicMock()
        prompt_builder.build_retry_prompt.return_value = (
            "retry system",
            "retry user",
        )
        return TestGuidedGenerator(
            surrogate=surrogate,
            test_runner=MagicMock(),
            contract_miner=MagicMock(),
            prompt_builder=prompt_builder,
            code_writer=MagicMock(),
            failure_parser=MagicMock(),
        )

    def test_builds_retry_prompt_and_calls_surrogate(self, generator):
        failures = MagicMock()
        failures.format_for_retry_prompt.return_value = "failure text"
        contracts = MagicMock()
        contracts.summary_for_prompt.return_value = "contract text"

        result = asyncio.run(
            generator._retry_component(
                component="core",
                model_yaml="model yaml",
                previous_code="old code",
                failures=failures,
                contracts=contracts,
            )
        )

        failures.format_for_retry_prompt.assert_called_once_with("core")
        generator._prompt_builder.build_retry_prompt.assert_called_once_with(
            "model yaml", "old code", "failure text", "core"
        )
        generator._surrogate.generate_with_prompt.assert_called_once_with(
            "retry system", "retry user"
        )
        assert result == "class Fixed: pass"


class TestGenerateFullPipeline:
    """Tests for the full generate() pipeline."""

    __test__ = True

    def _setup_mocks(self, test_pass_rate=1.0, pytest_output="1 passed in 0.1s"):
        """Create a generator with mocked dependencies for pipeline tests."""
        surrogate = MagicMock()
        surrogate.generate_with_prompt = AsyncMock(return_value="# core.py\nclass Core: pass")

        test_runner = MagicMock()

        contract_miner = MagicMock()
        contracts = MagicMock()
        contracts.summary_for_prompt.return_value = "contract text"
        contract_miner.mine.return_value = contracts

        prompt_builder = MagicMock()
        prompt_builder.build_generation_prompt.return_value = ("sys", "usr")
        prompt_builder.build_retry_prompt.return_value = ("retry_sys", "retry_usr")

        code_writer = MagicMock()
        package = MagicMock()
        package.package_dir = Path("/tmp/test_pkg")
        code_writer.materialize.return_value = package

        failure_parser = MagicMock()

        gen = TestGuidedGenerator(
            surrogate=surrogate,
            test_runner=test_runner,
            contract_miner=contract_miner,
            prompt_builder=prompt_builder,
            code_writer=code_writer,
            failure_parser=failure_parser,
            max_retries=5,
            convergence_threshold=3,
        )
        return gen, {
            "surrogate": surrogate,
            "test_runner": test_runner,
            "contract_miner": contract_miner,
            "prompt_builder": prompt_builder,
            "code_writer": code_writer,
            "failure_parser": failure_parser,
            "package": package,
            "contracts": contracts,
        }

    @patch("architecture_model.training.test_guided_generator.enrich_from_manifest")
    @patch("architecture_model.training.test_guided_generator.compact_for_generation")
    @patch("architecture_model.training.test_guided_generator.dump_model")
    @patch("architecture_model.training.test_guided_generator.tempfile")
    def test_all_tests_pass_on_initial_generation(
        self, mock_tempfile, mock_dump, mock_compact, mock_enrich
    ):
        """When initial generation passes all tests, no retries needed."""
        from architecture_model.training.failure_parser import FailureReport

        gen, mocks = self._setup_mocks()

        # Setup model enrichment
        mock_enrich.return_value = MagicMock(model=MagicMock())
        mock_compact.return_value = MagicMock()
        mock_dump.return_value = {"meta": {"project": "test"}}
        mock_tempfile.mkdtemp.return_value = "/tmp/tgg_test"

        # Setup test run: all tests pass
        failure_report = FailureReport(
            failures=[],
            total_passed=10,
            total_failed=0,
            total_collected=10,
            pass_rate=1.0,
        )
        mocks["failure_parser"].parse.return_value = failure_report

        # Mock _run_tests to return passing output
        gen._run_tests = MagicMock(return_value="10 passed in 0.5s")

        model = MagicMock()
        manifest = {"modules": []}

        result = asyncio.run(
            gen.generate(model, manifest, Path("/tmp/repo"), "mypackage")
        )

        assert result.final_pass_rate == 1.0
        assert result.converged is True
        assert result.iterations == 1
        assert len(result.attempts) == 1
        # Should NOT have done retries
        mocks["prompt_builder"].build_retry_prompt.assert_not_called()

    @patch("architecture_model.training.test_guided_generator.enrich_from_manifest")
    @patch("architecture_model.training.test_guided_generator.compact_for_generation")
    @patch("architecture_model.training.test_guided_generator.dump_model")
    @patch("architecture_model.training.test_guided_generator.tempfile")
    def test_retries_on_failures_then_converges(
        self, mock_tempfile, mock_dump, mock_compact, mock_enrich
    ):
        """Retry loop improves then converges."""
        from architecture_model.training.failure_parser import FailureReport, TestFailure

        gen, mocks = self._setup_mocks()

        mock_enrich.return_value = MagicMock(model=MagicMock())
        mock_compact.return_value = MagicMock()
        mock_dump.return_value = {"meta": {"project": "test"}}
        mock_tempfile.mkdtemp.return_value = "/tmp/tgg_test"

        # First run: 50% pass rate, then 70%, then 70%, then 70% (converges)
        failure_reports = [
            FailureReport(
                failures=[TestFailure(
                    test_name="test_x", test_file="tests/test_core.py",
                    error_type="AssertionError", error_message="x != y",
                    relevant_component="core",
                )],
                total_passed=5, total_failed=5, total_collected=10,
                pass_rate=0.5,
                by_component={"core": [TestFailure(
                    test_name="test_x", test_file="tests/test_core.py",
                    error_type="AssertionError", error_message="x != y",
                    relevant_component="core",
                )]},
            ),
            FailureReport(
                failures=[TestFailure(
                    test_name="test_x", test_file="tests/test_core.py",
                    error_type="AssertionError", error_message="x != y",
                    relevant_component="core",
                )],
                total_passed=7, total_failed=3, total_collected=10,
                pass_rate=0.7,
                by_component={"core": [TestFailure(
                    test_name="test_x", test_file="tests/test_core.py",
                    error_type="AssertionError", error_message="x != y",
                    relevant_component="core",
                )]},
            ),
            FailureReport(
                failures=[TestFailure(
                    test_name="test_x", test_file="tests/test_core.py",
                    error_type="AssertionError", error_message="x != y",
                    relevant_component="core",
                )],
                total_passed=7, total_failed=3, total_collected=10,
                pass_rate=0.7,
                by_component={"core": [TestFailure(
                    test_name="test_x", test_file="tests/test_core.py",
                    error_type="AssertionError", error_message="x != y",
                    relevant_component="core",
                )]},
            ),
            FailureReport(
                failures=[TestFailure(
                    test_name="test_x", test_file="tests/test_core.py",
                    error_type="AssertionError", error_message="x != y",
                    relevant_component="core",
                )],
                total_passed=7, total_failed=3, total_collected=10,
                pass_rate=0.7,
                by_component={"core": [TestFailure(
                    test_name="test_x", test_file="tests/test_core.py",
                    error_type="AssertionError", error_message="x != y",
                    relevant_component="core",
                )]},
            ),
        ]
        mocks["failure_parser"].parse.side_effect = failure_reports
        gen._run_tests = MagicMock(return_value="5 passed, 5 failed in 1.0s")

        model = MagicMock()
        manifest = {"modules": []}

        result = asyncio.run(
            gen.generate(model, manifest, Path("/tmp/repo"), "mypackage")
        )

        assert result.converged is True
        assert result.final_pass_rate == 0.7
        # Should have initial + retries (convergence after 3 same values)
        assert result.iterations >= 2

    @patch("architecture_model.training.test_guided_generator.enrich_from_manifest")
    @patch("architecture_model.training.test_guided_generator.compact_for_generation")
    @patch("architecture_model.training.test_guided_generator.dump_model")
    @patch("architecture_model.training.test_guided_generator.tempfile")
    def test_max_retries_hit(
        self, mock_tempfile, mock_dump, mock_compact, mock_enrich
    ):
        """Stops when max_retries exhausted without convergence."""
        from architecture_model.training.failure_parser import FailureReport, TestFailure

        gen, mocks = self._setup_mocks()
        gen._max_retries = 3  # Low limit for test speed

        mock_enrich.return_value = MagicMock(model=MagicMock())
        mock_compact.return_value = MagicMock()
        mock_dump.return_value = {"meta": {"project": "test"}}
        mock_tempfile.mkdtemp.return_value = "/tmp/tgg_test"

        # Each iteration has different pass_rate (never converges)
        call_count = [0]

        def make_report(*args, **kwargs):
            call_count[0] += 1
            rate = 0.1 * call_count[0]  # 0.1, 0.2, 0.3, 0.4
            return FailureReport(
                failures=[TestFailure(
                    test_name="test_x", test_file="tests/test_core.py",
                    error_type="AssertionError", error_message="x != y",
                    relevant_component="core",
                )],
                total_passed=int(rate * 10), total_failed=10 - int(rate * 10),
                total_collected=10,
                pass_rate=rate,
                by_component={"core": [TestFailure(
                    test_name="test_x", test_file="tests/test_core.py",
                    error_type="AssertionError", error_message="x != y",
                    relevant_component="core",
                )]},
            )

        mocks["failure_parser"].parse.side_effect = make_report
        gen._run_tests = MagicMock(return_value="5 passed, 5 failed in 1.0s")

        model = MagicMock()
        manifest = {"modules": []}

        result = asyncio.run(
            gen.generate(model, manifest, Path("/tmp/repo"), "mypackage")
        )

        assert result.converged is False
        # initial + max_retries
        assert result.iterations <= gen._max_retries + 1

    @patch("architecture_model.training.test_guided_generator.enrich_from_manifest")
    @patch("architecture_model.training.test_guided_generator.compact_for_generation")
    @patch("architecture_model.training.test_guided_generator.dump_model")
    @patch("architecture_model.training.test_guided_generator.tempfile")
    def test_cleanup_called_on_completion(
        self, mock_tempfile, mock_dump, mock_compact, mock_enrich
    ):
        """CodeWriter.cleanup is called after generation completes."""
        from architecture_model.training.failure_parser import FailureReport

        gen, mocks = self._setup_mocks()

        mock_enrich.return_value = MagicMock(model=MagicMock())
        mock_compact.return_value = MagicMock()
        mock_dump.return_value = {"meta": {"project": "test"}}
        mock_tempfile.mkdtemp.return_value = "/tmp/tgg_test"

        failure_report = FailureReport(
            failures=[], total_passed=10, total_failed=0,
            total_collected=10, pass_rate=1.0,
        )
        mocks["failure_parser"].parse.return_value = failure_report
        gen._run_tests = MagicMock(return_value="10 passed in 0.5s")

        model = MagicMock()
        manifest = {"modules": []}

        asyncio.run(gen.generate(model, manifest, Path("/tmp/repo"), "mypackage"))

        mocks["code_writer"].cleanup.assert_called()

    @patch("architecture_model.training.test_guided_generator.enrich_from_manifest")
    @patch("architecture_model.training.test_guided_generator.compact_for_generation")
    @patch("architecture_model.training.test_guided_generator.dump_model")
    @patch("architecture_model.training.test_guided_generator.tempfile")
    def test_mines_contracts(
        self, mock_tempfile, mock_dump, mock_compact, mock_enrich
    ):
        """Contract miner is invoked with correct arguments."""
        from architecture_model.training.failure_parser import FailureReport

        gen, mocks = self._setup_mocks()

        mock_enrich.return_value = MagicMock(model=MagicMock())
        mock_compact.return_value = MagicMock()
        mock_dump.return_value = {"meta": {"project": "test"}}
        mock_tempfile.mkdtemp.return_value = "/tmp/tgg_test"

        failure_report = FailureReport(
            failures=[], total_passed=10, total_failed=0,
            total_collected=10, pass_rate=1.0,
        )
        mocks["failure_parser"].parse.return_value = failure_report
        gen._run_tests = MagicMock(return_value="10 passed in 0.5s")

        model = MagicMock()
        manifest = {"modules": []}
        repo_path = Path("/tmp/repo")

        asyncio.run(gen.generate(model, manifest, repo_path, "mypackage"))

        mocks["contract_miner"].mine.assert_called_once_with(repo_path, "mypackage")


class TestGenerateWithPromptOnSurrogate:
    """Tests for Surrogate.generate_with_prompt method."""

    __test__ = True

    def test_strips_python_fences(self):
        from architecture_model.training.surrogate import Surrogate

        surrogate = Surrogate(model_name="test:latest")

        # Mock _chat to return code in fences
        async def mock_chat(messages):
            return {"message": {"content": "```python\nclass Foo: pass\n```"}}

        surrogate._chat = mock_chat

        result = asyncio.run(surrogate.generate_with_prompt("system", "user"))
        assert result == "class Foo: pass"

    def test_strips_generic_fences(self):
        from architecture_model.training.surrogate import Surrogate

        surrogate = Surrogate(model_name="test:latest")

        async def mock_chat(messages):
            return {"message": {"content": "```\nclass Bar: pass\n```"}}

        surrogate._chat = mock_chat

        result = asyncio.run(surrogate.generate_with_prompt("system", "user"))
        assert result == "class Bar: pass"

    def test_no_fences_returns_raw(self):
        from architecture_model.training.surrogate import Surrogate

        surrogate = Surrogate(model_name="test:latest")

        async def mock_chat(messages):
            return {"message": {"content": "class Baz: pass"}}

        surrogate._chat = mock_chat

        result = asyncio.run(surrogate.generate_with_prompt("system", "user"))
        assert result == "class Baz: pass"

    def test_passes_correct_messages(self):
        from architecture_model.training.surrogate import Surrogate

        surrogate = Surrogate(model_name="test:latest")
        captured_messages = []

        async def mock_chat(messages):
            captured_messages.append(messages)
            return {"message": {"content": "output"}}

        surrogate._chat = mock_chat

        asyncio.run(surrogate.generate_with_prompt("my system", "my user"))
        assert len(captured_messages) == 1
        assert captured_messages[0] == [
            {"role": "system", "content": "my system"},
            {"role": "user", "content": "my user"},
        ]


class TestExtractComponentCode:
    """Tests for TestGuidedGenerator._extract_component_code."""

    __test__ = True

    def _make_generator(self):
        return TestGuidedGenerator(
            surrogate=MagicMock(),
            test_runner=MagicMock(),
            contract_miner=MagicMock(),
            prompt_builder=MagicMock(),
            code_writer=MagicMock(),
            failure_parser=MagicMock(),
        )

    def test_extracts_correct_component_from_multi_module(self):
        """Extracts the right component from multi-module code."""
        gen = self._make_generator()
        full_code = (
            "# core.py\n"
            "class Core:\n"
            "    pass\n"
            "# utils.py\n"
            "def helper():\n"
            "    return 42\n"
        )
        result = gen._extract_component_code(full_code, "core")
        assert "class Core:" in result
        assert "def helper" not in result

    def test_extracts_last_component(self):
        """Extracts the last component in multi-module code."""
        gen = self._make_generator()
        full_code = (
            "# core.py\n"
            "class Core:\n"
            "    pass\n"
            "# utils.py\n"
            "def helper():\n"
            "    return 42\n"
        )
        result = gen._extract_component_code(full_code, "utils")
        assert "def helper" in result
        assert "class Core" not in result

    def test_returns_full_code_when_component_not_found(self):
        """Fallback: returns all code if component not found."""
        gen = self._make_generator()
        full_code = "# core.py\nclass Core:\n    pass\n"
        result = gen._extract_component_code(full_code, "nonexistent")
        assert result == full_code

    def test_handles_single_module_code(self):
        """When code has only one module header, extracts that module."""
        gen = self._make_generator()
        full_code = "# main.py\ndef main():\n    print('hello')\n"
        result = gen._extract_component_code(full_code, "main")
        assert "def main():" in result
        assert "# main.py" not in result


class TestSpliceComponent:
    """Tests for TestGuidedGenerator._splice_component."""

    __test__ = True

    def _make_generator(self):
        return TestGuidedGenerator(
            surrogate=MagicMock(),
            test_runner=MagicMock(),
            contract_miner=MagicMock(),
            prompt_builder=MagicMock(),
            code_writer=MagicMock(),
            failure_parser=MagicMock(),
        )

    def test_replaces_existing_component(self):
        """Replaces code for an existing component."""
        gen = self._make_generator()
        full_code = (
            "# core.py\n"
            "class Core:\n"
            "    pass\n"
            "# utils.py\n"
            "def helper():\n"
            "    return 42\n"
        )
        new_code = "class CoreV2:\n    value = True"
        result = gen._splice_component(full_code, "core", new_code)
        assert "class CoreV2:" in result
        assert "class Core:" not in result
        # utils should still be there
        assert "# utils.py" in result
        assert "def helper" in result

    def test_appends_component_when_not_found(self):
        """Appends a new component when the target doesn't exist."""
        gen = self._make_generator()
        full_code = "# core.py\nclass Core:\n    pass\n"
        new_code = "def new_func():\n    return True"
        result = gen._splice_component(full_code, "extras", new_code)
        # Original preserved
        assert "# core.py" in result
        assert "class Core:" in result
        # New component appended
        assert "# extras.py" in result
        assert "def new_func" in result

    def test_preserves_other_components_unchanged(self):
        """Replacing one component doesn't affect others."""
        gen = self._make_generator()
        full_code = (
            "# alpha.py\n"
            "class Alpha:\n"
            "    x = 1\n"
            "# beta.py\n"
            "class Beta:\n"
            "    y = 2\n"
            "# gamma.py\n"
            "class Gamma:\n"
            "    z = 3\n"
        )
        new_code = "class BetaFixed:\n    y = 99"
        result = gen._splice_component(full_code, "beta", new_code)
        # Alpha untouched
        assert "class Alpha:" in result
        assert "x = 1" in result
        # Beta replaced
        assert "class BetaFixed:" in result
        assert "class Beta:" not in result
        # Gamma untouched
        assert "class Gamma:" in result
        assert "z = 3" in result


class TestTargetedRetry:
    """Tests for TestGuidedGenerator._targeted_retry."""

    __test__ = True

    def _make_generator(self):
        surrogate = MagicMock()
        surrogate.generate_with_prompt = AsyncMock(return_value="class Fixed: pass")
        prompt_builder = MagicMock()
        prompt_builder.build_retry_prompt.return_value = ("sys", "usr")
        return TestGuidedGenerator(
            surrogate=surrogate,
            test_runner=MagicMock(),
            contract_miner=MagicMock(),
            prompt_builder=prompt_builder,
            code_writer=MagicMock(),
            failure_parser=MagicMock(),
        )

    def test_identifies_and_retries_failing_components(self):
        """Targeted retry identifies worst components and regenerates them."""
        from architecture_model.training.failure_parser import FailureReport, TestFailure

        gen = self._make_generator()

        failures = FailureReport(
            failures=[TestFailure(
                test_name="test_x", test_file="tests/test_core.py",
                error_type="AssertionError", error_message="x != y",
                relevant_component="core",
            )],
            total_passed=5, total_failed=5, total_collected=10,
            pass_rate=0.5,
            by_component={"core": [TestFailure(
                test_name="test_x", test_file="tests/test_core.py",
                error_type="AssertionError", error_message="x != y",
                relevant_component="core",
            )]},
        )
        contracts = MagicMock()
        contracts.summary_for_prompt.return_value = "contracts"

        current_code = "# core.py\nclass Core:\n    pass\n"
        model_yaml = "meta:\n  project: test\n"

        updated_code, regenerated = asyncio.run(
            gen._targeted_retry(
                failures=failures,
                model_yaml=model_yaml,
                contracts=contracts,
                current_code=current_code,
            )
        )

        # Should have regenerated the core component
        assert "core" in regenerated
        # Code should have been updated
        assert "class Fixed: pass" in updated_code

    def test_returns_updated_code_with_spliced_components(self):
        """Multiple failing components are each retried and spliced."""
        from architecture_model.training.failure_parser import FailureReport, TestFailure

        gen = self._make_generator()

        # Two failing components
        failures = FailureReport(
            failures=[
                TestFailure(
                    test_name="test_a", test_file="tests/test_core.py",
                    error_type="AssertionError", error_message="a",
                    relevant_component="core",
                ),
                TestFailure(
                    test_name="test_b", test_file="tests/test_utils.py",
                    error_type="TypeError", error_message="b",
                    relevant_component="utils",
                ),
            ],
            total_passed=3, total_failed=7, total_collected=10,
            pass_rate=0.3,
            by_component={
                "core": [TestFailure(
                    test_name="test_a", test_file="tests/test_core.py",
                    error_type="AssertionError", error_message="a",
                    relevant_component="core",
                )],
                "utils": [TestFailure(
                    test_name="test_b", test_file="tests/test_utils.py",
                    error_type="TypeError", error_message="b",
                    relevant_component="utils",
                )],
            },
        )
        contracts = MagicMock()
        contracts.summary_for_prompt.return_value = "contracts"

        current_code = (
            "# core.py\nclass Core:\n    pass\n"
            "# utils.py\ndef util():\n    pass\n"
        )
        model_yaml = "meta:\n  project: test\n"

        updated_code, regenerated = asyncio.run(
            gen._targeted_retry(
                failures=failures,
                model_yaml=model_yaml,
                contracts=contracts,
                current_code=current_code,
            )
        )

        # Both components regenerated
        assert "core" in regenerated
        assert "utils" in regenerated
        assert len(regenerated) == 2

    def test_returns_empty_list_when_no_failing_components(self):
        """When no components identified, returns code unchanged."""
        from architecture_model.training.failure_parser import FailureReport

        gen = self._make_generator()

        failures = FailureReport(
            failures=[],
            total_passed=10, total_failed=0, total_collected=10,
            pass_rate=1.0,
            by_component={},
        )
        contracts = MagicMock()
        current_code = "# core.py\nclass Core:\n    pass\n"

        updated_code, regenerated = asyncio.run(
            gen._targeted_retry(
                failures=failures,
                model_yaml="yaml",
                contracts=contracts,
                current_code=current_code,
            )
        )

        assert regenerated == []
        assert updated_code == current_code
