"""Tests for CLI train subcommand: argument parsing, help text, dispatch."""

import pytest
from unittest.mock import patch, MagicMock

from architecture_model.cli.main import main


# ---------------------------------------------------------------------------
# Argument parsing tests
# ---------------------------------------------------------------------------


class TestTrainFetch:
    def test_parses_default_args(self):
        """train fetch with no args uses defaults."""
        with patch("architecture_model.cli.train._cmd_train_fetch", return_value=0) as mock:
            result = main(["train", "fetch"])
        assert result == 0
        args = mock.call_args[0][0]
        assert args.n == 50
        assert args.min_stars == 100
        assert args.clone_dir == "./repos"

    def test_parses_custom_args(self):
        """train fetch accepts --n, --min-stars, --clone-dir."""
        with patch("architecture_model.cli.train._cmd_train_fetch", return_value=0) as mock:
            result = main(["train", "fetch", "--n", "20", "--min-stars", "500", "--clone-dir", "/tmp/clones"])
        assert result == 0
        args = mock.call_args[0][0]
        assert args.n == 20
        assert args.min_stars == 500
        assert args.clone_dir == "/tmp/clones"


class TestTrainRun:
    def test_parses_default_args(self):
        """train run with no args uses defaults."""
        with patch("architecture_model.cli.train._cmd_train_run", return_value=0) as mock:
            result = main(["train", "run"])
        assert result == 0
        args = mock.call_args[0][0]
        assert args.n_repos == 50
        assert args.db == "training.db"

    def test_parses_custom_args(self):
        """train run accepts --n-repos, --db."""
        with patch("architecture_model.cli.train._cmd_train_run", return_value=0) as mock:
            result = main(["train", "run", "--n-repos", "10", "--db", "custom.db"])
        assert result == 0
        args = mock.call_args[0][0]
        assert args.n_repos == 10
        assert args.db == "custom.db"


class TestTrainFit:
    def test_parses_default_args(self):
        """train fit with no args uses defaults."""
        with patch("architecture_model.cli.train._cmd_train_fit", return_value=0) as mock:
            result = main(["train", "fit"])
        assert result == 0
        args = mock.call_args[0][0]
        assert args.db == "training.db"
        assert args.base_model == "codellama:13b"
        assert args.epochs == 3

    def test_parses_custom_args(self):
        """train fit accepts --db, --base-model, --epochs."""
        with patch("architecture_model.cli.train._cmd_train_fit", return_value=0) as mock:
            result = main(["train", "fit", "--db", "my.db", "--base-model", "llama2:7b", "--epochs", "5"])
        assert result == 0
        args = mock.call_args[0][0]
        assert args.db == "my.db"
        assert args.base_model == "llama2:7b"
        assert args.epochs == 5


class TestTrainSwap:
    def test_parses_default_args(self):
        """train swap with no args uses default model name."""
        with patch("architecture_model.cli.train._cmd_train_swap", return_value=0) as mock:
            result = main(["train", "swap"])
        assert result == 0
        args = mock.call_args[0][0]
        assert args.model_name == "arch-model-v1"

    def test_parses_custom_model_name(self):
        """train swap accepts --model-name."""
        with patch("architecture_model.cli.train._cmd_train_swap", return_value=0) as mock:
            result = main(["train", "swap", "--model-name", "my-custom-model"])
        assert result == 0
        args = mock.call_args[0][0]
        assert args.model_name == "my-custom-model"


class TestTrainLoop:
    def test_parses_default_args(self):
        """train loop with no args uses defaults."""
        with patch("architecture_model.cli.train._cmd_train_loop", return_value=0) as mock:
            result = main(["train", "loop"])
        assert result == 0
        args = mock.call_args[0][0]
        assert args.max_iterations == 100
        assert args.budget == 100000

    def test_parses_custom_args(self):
        """train loop accepts --max-iterations, --budget."""
        with patch("architecture_model.cli.train._cmd_train_loop", return_value=0) as mock:
            result = main(["train", "loop", "--max-iterations", "50", "--budget", "5000"])
        assert result == 0
        args = mock.call_args[0][0]
        assert args.max_iterations == 50
        assert args.budget == 5000


class TestTrainStatus:
    def test_parses_default_args(self):
        """train status with no args uses default db."""
        with patch("architecture_model.cli.train._cmd_train_status", return_value=0) as mock:
            result = main(["train", "status"])
        assert result == 0
        args = mock.call_args[0][0]
        assert args.db == "training.db"

    def test_parses_custom_db(self):
        """train status accepts --db."""
        with patch("architecture_model.cli.train._cmd_train_status", return_value=0) as mock:
            result = main(["train", "status", "--db", "other.db"])
        assert result == 0
        args = mock.call_args[0][0]
        assert args.db == "other.db"


# ---------------------------------------------------------------------------
# Dispatch / error handling tests
# ---------------------------------------------------------------------------


class TestTrainDispatch:
    def test_train_no_subcommand_returns_error(self, capsys):
        """train with no subcommand prints help and returns 1."""
        result = main(["train"])
        assert result == 1
        captured = capsys.readouterr()
        assert "train" in captured.out.lower() or "usage" in captured.out.lower()

    def test_train_invalid_subcommand_exits(self):
        """train with invalid subcommand causes SystemExit (argparse error)."""
        with pytest.raises(SystemExit):
            main(["train", "nonexistent"])


# ---------------------------------------------------------------------------
# Help text tests
# ---------------------------------------------------------------------------


class TestTrainHelpText:
    def test_train_help_mentions_subcommands(self, capsys):
        """train --help lists available subcommands."""
        with pytest.raises(SystemExit) as exc_info:
            main(["train", "--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        for cmd in ("fetch", "run", "fit", "swap", "loop", "status"):
            assert cmd in captured.out

    def test_fetch_help_mentions_options(self, capsys):
        """train fetch --help mentions key options."""
        with pytest.raises(SystemExit) as exc_info:
            main(["train", "fetch", "--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "--n" in captured.out
        assert "--min-stars" in captured.out
        assert "--clone-dir" in captured.out

    def test_fit_help_mentions_options(self, capsys):
        """train fit --help mentions key options."""
        with pytest.raises(SystemExit) as exc_info:
            main(["train", "fit", "--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "--base-model" in captured.out
        assert "--epochs" in captured.out
        assert "--db" in captured.out
