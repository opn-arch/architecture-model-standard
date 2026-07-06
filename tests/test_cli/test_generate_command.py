"""Tests for the 'generate' CLI command (stub — moved to arch-agent)."""

from __future__ import annotations

import argparse

from architecture_model.cli.generate import (
    _cmd_generate,
    register_generate_command,
)
from architecture_model.cli.main import main


class TestGenerateStub:
    """Test that the generate stub command works correctly."""

    def test_generate_subcommand_recognized(self):
        """Parser should recognize 'generate' as a valid subcommand."""
        result = main(["generate"])
        assert result == 1  # stub always returns 1

    def test_generate_prints_migration_message(self, capsys):
        """Generate stub should tell users to install arch-agent."""
        args = argparse.Namespace(command="generate", repo_path=None)
        result = _cmd_generate(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "arch-agent" in captured.out
        assert "pip install arch-agent" in captured.out

    def test_register_generate_command(self):
        """'generate' should be a registered subcommand in the parser."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        register_generate_command(subparsers)

        args = parser.parse_args(["generate", "/some/path"])
        assert args.command == "generate"
        assert args.repo_path == "/some/path"
