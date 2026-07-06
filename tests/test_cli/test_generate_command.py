"""Tests for the 'generate' CLI command."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from architecture_model.cli.generate import (
    _cmd_generate,
    _detect_package_name,
    register_generate_command,
)
from architecture_model.cli.main import main


class TestRegisterGenerateCommand:
    """Test that the generate subcommand is properly registered."""

    def test_generate_subcommand_recognized(self):
        """Parser should recognize 'generate' as a valid subcommand."""
        result = main(["generate", "--test-guided", "/tmp/fake-repo"])
        # It will fail (dir doesn't exist), but it shouldn't fail on arg parsing
        # The command itself is recognized and dispatched
        assert result == 1  # repo doesn't exist, so returns 1

    def test_generate_subcommand_in_parser(self):
        """'generate' should be a registered subcommand in the parser."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        register_generate_command(subparsers)

        args = parser.parse_args(["generate", "--test-guided", "/some/path"])
        assert args.command == "generate"
        assert args.test_guided is True
        assert args.repo_path == "/some/path"


class TestArgumentParsing:
    """Test argument parsing for the generate command."""

    def _parse(self, argv: list[str]) -> argparse.Namespace:
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        register_generate_command(subparsers)
        return parser.parse_args(["generate"] + argv)

    def test_repo_path_positional(self):
        args = self._parse(["--test-guided", "/path/to/repo"])
        assert args.repo_path == "/path/to/repo"

    def test_test_guided_flag(self):
        args = self._parse(["--test-guided", "/path/to/repo"])
        assert args.test_guided is True

    def test_test_guided_default_false(self):
        args = self._parse(["/path/to/repo"])
        assert args.test_guided is False

    def test_max_retries_default(self):
        args = self._parse(["--test-guided", "/path/to/repo"])
        assert args.max_retries == 10

    def test_max_retries_custom(self):
        args = self._parse(["--test-guided", "/path/to/repo", "--max-retries", "20"])
        assert args.max_retries == 20

    def test_model_default(self):
        args = self._parse(["--test-guided", "/path/to/repo"])
        assert args.model == "qwen2.5:7b"

    def test_model_custom(self):
        args = self._parse(["--test-guided", "/path/to/repo", "--model", "llama3:8b"])
        assert args.model == "llama3:8b"

    def test_output_default_none(self):
        args = self._parse(["--test-guided", "/path/to/repo"])
        assert args.output is None

    def test_output_custom(self):
        args = self._parse(["--test-guided", "/path/to/repo", "--output", "/tmp/out"])
        assert args.output == "/tmp/out"

    def test_output_short_flag(self):
        args = self._parse(["--test-guided", "/path/to/repo", "-o", "/tmp/out"])
        assert args.output == "/tmp/out"

    def test_convergence_threshold_default(self):
        args = self._parse(["--test-guided", "/path/to/repo"])
        assert args.convergence_threshold == 3

    def test_convergence_threshold_custom(self):
        args = self._parse([
            "--test-guided", "/path/to/repo", "--convergence-threshold", "5"
        ])
        assert args.convergence_threshold == 5


class TestNoTestGuidedFlag:
    """Test that without --test-guided, an error is printed."""

    def test_without_test_guided_returns_error(self, capsys):
        """Without --test-guided, handler should print error and return 1."""
        args = argparse.Namespace(
            command="generate",
            repo_path="/tmp/fake",
            test_guided=False,
            max_retries=10,
            model="qwen2.5:7b",
            output=None,
            convergence_threshold=3,
        )
        result = _cmd_generate(args)
        assert result == 1

        captured = capsys.readouterr()
        assert "Only --test-guided mode is currently supported" in captured.out


class TestDetectPackageName:
    """Test package name detection logic."""

    def test_from_directory_name(self, tmp_path):
        repo = tmp_path / "my-project"
        repo.mkdir()
        assert _detect_package_name(repo) == "my_project"

    def test_from_pyproject_toml(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        pyproject = repo / "pyproject.toml"
        pyproject.write_text('[project]\nname = "cool-package"\n')
        assert _detect_package_name(repo) == "cool_package"

    def test_pyproject_with_quotes(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        pyproject = repo / "pyproject.toml"
        pyproject.write_text("[project]\nname = 'single-quoted'\n")
        assert _detect_package_name(repo) == "single_quoted"

    def test_fallback_on_missing_pyproject(self, tmp_path):
        repo = tmp_path / "fallback-name"
        repo.mkdir()
        assert _detect_package_name(repo) == "fallback_name"

    def test_fallback_on_invalid_pyproject(self, tmp_path):
        repo = tmp_path / "bad-toml"
        repo.mkdir()
        pyproject = repo / "pyproject.toml"
        pyproject.write_text("this is not valid toml at all\n")
        # Should fallback to directory name
        assert _detect_package_name(repo) == "bad_toml"


class TestCmdGenerateHandler:
    """Test the handler with mocked dependencies."""

    @pytest.fixture
    def mock_args(self, tmp_path):
        """Create a valid args namespace pointing to a real directory."""
        repo = tmp_path / "test-repo"
        repo.mkdir()
        (repo / "pyproject.toml").write_text('[project]\nname = "test-pkg"\n')
        return argparse.Namespace(
            command="generate",
            repo_path=str(repo),
            test_guided=True,
            max_retries=5,
            model="qwen2.5:7b",
            output=None,
            convergence_threshold=3,
        )

    @patch("architecture_model.manifest.generator.generate_manifest")
    @patch("architecture_model.extract.from_code.extract_from_code")
    @patch("architecture_model.training.test_guided_generator.TestGuidedGenerator")
    @patch("architecture_model.training.surrogate.Surrogate")
    @patch("architecture_model.training.test_runner.TestRunner")
    @patch("architecture_model.training.test_contract_miner.TestContractMiner")
    @patch("architecture_model.training.prompt_builder.PromptBuilder")
    @patch("architecture_model.training.code_writer.CodeWriter")
    @patch("architecture_model.training.failure_parser.FailureParser")
    def test_handler_creates_generator_and_runs(
        self,
        mock_failure_parser_cls,
        mock_code_writer_cls,
        mock_prompt_builder_cls,
        mock_contract_miner_cls,
        mock_test_runner_cls,
        mock_surrogate_cls,
        mock_generator_cls,
        mock_extract,
        mock_manifest,
        mock_args,
        capsys,
    ):
        """Handler should wire up dependencies and call generator.generate()."""
        # Setup mocks
        mock_manifest.return_value = {"modules": [], "interfaces": []}
        mock_model = MagicMock()
        mock_extract.return_value = mock_model

        mock_result = MagicMock()
        mock_result.final_pass_rate = 0.85
        mock_result.iterations = 3
        mock_result.converged = True
        mock_result.structural_score = None
        mock_result.final_code = "# generated code"

        mock_gen_instance = MagicMock()
        mock_gen_instance.generate = AsyncMock(return_value=mock_result)
        mock_generator_cls.return_value = mock_gen_instance

        # Run
        result = _cmd_generate(mock_args)

        # Verify
        assert result == 0
        mock_manifest.assert_called_once()
        mock_extract.assert_called_once()
        mock_generator_cls.assert_called_once()
        mock_gen_instance.generate.assert_called_once()

        # Check output
        captured = capsys.readouterr()
        assert "85.0%" in captured.out
        assert "3" in captured.out
        assert "True" in captured.out

    @patch("architecture_model.manifest.generator.generate_manifest")
    @patch("architecture_model.extract.from_code.extract_from_code")
    @patch("architecture_model.training.test_guided_generator.TestGuidedGenerator")
    @patch("architecture_model.training.surrogate.Surrogate")
    @patch("architecture_model.training.test_runner.TestRunner")
    @patch("architecture_model.training.test_contract_miner.TestContractMiner")
    @patch("architecture_model.training.prompt_builder.PromptBuilder")
    @patch("architecture_model.training.code_writer.CodeWriter")
    @patch("architecture_model.training.failure_parser.FailureParser")
    def test_handler_writes_output_to_dir(
        self,
        mock_failure_parser_cls,
        mock_code_writer_cls,
        mock_prompt_builder_cls,
        mock_contract_miner_cls,
        mock_test_runner_cls,
        mock_surrogate_cls,
        mock_generator_cls,
        mock_extract,
        mock_manifest,
        mock_args,
        tmp_path,
    ):
        """When --output is provided, should write generated code to file."""
        output_dir = tmp_path / "output"
        mock_args.output = str(output_dir)

        mock_manifest.return_value = {"modules": []}
        mock_extract.return_value = MagicMock()

        mock_result = MagicMock()
        mock_result.final_pass_rate = 1.0
        mock_result.iterations = 1
        mock_result.converged = True
        mock_result.structural_score = None
        mock_result.final_code = "# perfect code\npass\n"

        mock_gen_instance = MagicMock()
        mock_gen_instance.generate = AsyncMock(return_value=mock_result)
        mock_generator_cls.return_value = mock_gen_instance

        result = _cmd_generate(mock_args)

        assert result == 0
        output_file = output_dir / "test_pkg_generated.py"
        assert output_file.exists()
        assert output_file.read_text() == "# perfect code\npass\n"

    def test_handler_invalid_repo_path(self, capsys):
        """Handler should return 1 for non-existent repo path."""
        args = argparse.Namespace(
            command="generate",
            repo_path="/nonexistent/path/to/repo",
            test_guided=True,
            max_retries=10,
            model="qwen2.5:7b",
            output=None,
            convergence_threshold=3,
        )
        result = _cmd_generate(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "not a directory" in captured.out

    def test_handler_missing_training_deps(self, mock_args, capsys):
        """Handler should print install hint when training deps are missing."""
        with patch(
            "architecture_model.cli.generate._check_training_deps", return_value=False
        ):
            result = _cmd_generate(mock_args)
            assert result == 1
            captured = capsys.readouterr()
            assert "Training dependencies required" in captured.out
            assert "pip install" in captured.out

    @patch("architecture_model.manifest.generator.generate_manifest")
    @patch("architecture_model.extract.from_code.extract_from_code")
    @patch("architecture_model.training.test_guided_generator.TestGuidedGenerator")
    @patch("architecture_model.training.surrogate.Surrogate")
    @patch("architecture_model.training.test_runner.TestRunner")
    @patch("architecture_model.training.test_contract_miner.TestContractMiner")
    @patch("architecture_model.training.prompt_builder.PromptBuilder")
    @patch("architecture_model.training.code_writer.CodeWriter")
    @patch("architecture_model.training.failure_parser.FailureParser")
    def test_handler_passes_correct_params_to_generator(
        self,
        mock_failure_parser_cls,
        mock_code_writer_cls,
        mock_prompt_builder_cls,
        mock_contract_miner_cls,
        mock_test_runner_cls,
        mock_surrogate_cls,
        mock_generator_cls,
        mock_extract,
        mock_manifest,
        mock_args,
    ):
        """Handler should pass max_retries and convergence_threshold to generator."""
        mock_args.max_retries = 15
        mock_args.convergence_threshold = 7

        mock_manifest.return_value = {"modules": []}
        mock_extract.return_value = MagicMock()

        mock_result = MagicMock()
        mock_result.final_pass_rate = 0.5
        mock_result.iterations = 15
        mock_result.converged = False
        mock_result.structural_score = None
        mock_result.final_code = ""

        mock_gen_instance = MagicMock()
        mock_gen_instance.generate = AsyncMock(return_value=mock_result)
        mock_generator_cls.return_value = mock_gen_instance

        _cmd_generate(mock_args)

        # Verify constructor args
        call_kwargs = mock_generator_cls.call_args[1]
        assert call_kwargs["max_retries"] == 15
        assert call_kwargs["convergence_threshold"] == 7

    @patch("architecture_model.manifest.generator.generate_manifest")
    @patch("architecture_model.extract.from_code.extract_from_code")
    @patch("architecture_model.training.test_guided_generator.TestGuidedGenerator")
    @patch("architecture_model.training.surrogate.Surrogate")
    @patch("architecture_model.training.test_runner.TestRunner")
    @patch("architecture_model.training.test_contract_miner.TestContractMiner")
    @patch("architecture_model.training.prompt_builder.PromptBuilder")
    @patch("architecture_model.training.code_writer.CodeWriter")
    @patch("architecture_model.training.failure_parser.FailureParser")
    def test_handler_passes_model_to_surrogate(
        self,
        mock_failure_parser_cls,
        mock_code_writer_cls,
        mock_prompt_builder_cls,
        mock_contract_miner_cls,
        mock_test_runner_cls,
        mock_surrogate_cls,
        mock_generator_cls,
        mock_extract,
        mock_manifest,
        mock_args,
    ):
        """Handler should pass model name to Surrogate constructor."""
        mock_args.model = "llama3:70b"

        mock_manifest.return_value = {"modules": []}
        mock_extract.return_value = MagicMock()

        mock_result = MagicMock()
        mock_result.final_pass_rate = 0.0
        mock_result.iterations = 1
        mock_result.converged = False
        mock_result.structural_score = None
        mock_result.final_code = ""

        mock_gen_instance = MagicMock()
        mock_gen_instance.generate = AsyncMock(return_value=mock_result)
        mock_generator_cls.return_value = mock_gen_instance

        _cmd_generate(mock_args)

        mock_surrogate_cls.assert_called_once_with(model_name="llama3:70b")
