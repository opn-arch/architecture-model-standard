"""
CLI command for test-guided code generation — moved to arch-agent package.

The test-guided generation pipeline now lives in the arch-agent package.
This stub remains for backward compatibility.
"""

from __future__ import annotations

import argparse


def register_generate_command(subparsers: argparse._SubParsersAction) -> None:
    """Register the 'generate' subcommand (stub — see arch-agent package)."""
    p_generate = subparsers.add_parser(
        "generate",
        help="Generate code from architecture model (moved to arch-agent)",
        description="Test-guided code generation has moved to the arch-agent package.",
    )
    p_generate.add_argument(
        "repo_path",
        nargs="?",
        help="Path to the target repository",
    )


def _cmd_generate(args: argparse.Namespace) -> int:
    """Handle the 'generate' command (stub)."""
    print("Test-guided code generation has moved to the arch-agent package.")
    print("Install: pip install arch-agent")
    print("Run: arch-agent generate --help")
    return 1
