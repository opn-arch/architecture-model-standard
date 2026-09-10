"""CLI endpoint extraction (Click + argparse) — Phase 4-A Task 8.

AST-scans Python sources for CLI command declarations. Deterministic
output sorted by (file, lineno). Both Click decorators
(``@click.command``, ``@click.group``, ``@<group>.command``) and
argparse (``add_subparsers().add_parser("name")``) are supported.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from architecture_model.pipeline.endpoint_extract import extract_cli_endpoints
from architecture_model.pipeline.endpoint_types import Endpoint, EndpointArg


@pytest.fixture
def cli_source(tmp_path: Path) -> Path:
    src = tmp_path / "mycli.py"
    src.write_text(
        dedent(
            """
            import click
            import argparse

            @click.group()
            def cli():
                pass

            @cli.command("hello")
            @click.option("--name", default="world", help="Who to greet")
            @click.argument("target")
            def hello_cmd(name, target):
                pass

            @click.command()
            def standalone():
                pass

            def build_argparse():
                parser = argparse.ArgumentParser()
                sub = parser.add_subparsers()
                sub.add_parser("sync", help="Sync things")
                return parser
            """
        ).lstrip()
    )
    return src


def test_extract_cli_endpoints_finds_click_group_and_subcommand(cli_source):
    endpoints = extract_cli_endpoints([cli_source])
    names = {e.name for e in endpoints}
    assert "cli" in names  # @click.group
    assert "hello" in names  # @cli.command("hello")
    assert "standalone" in names  # @click.command() → falls back to func name


def test_extract_cli_endpoints_captures_click_args(cli_source):
    endpoints = extract_cli_endpoints([cli_source])
    hello = next(e for e in endpoints if e.name == "hello")
    arg_names = {a.name for a in hello.args}
    assert "--name" in arg_names or "name" in arg_names
    assert "target" in arg_names
    name_arg = next(a for a in hello.args if a.name in {"--name", "name"})
    assert name_arg.default == "world"
    assert name_arg.required is False
    target_arg = next(a for a in hello.args if a.name == "target")
    assert target_arg.required is True


def test_extract_cli_endpoints_detects_argparse(cli_source):
    endpoints = extract_cli_endpoints([cli_source])
    argparse_endpoints = [e for e in endpoints if e.name == "sync"]
    assert len(argparse_endpoints) == 1
    assert argparse_endpoints[0].kind == "cli_command"
    assert argparse_endpoints[0].metadata.get("framework") == "argparse"


def test_extract_cli_endpoints_deterministic_order(cli_source):
    a = extract_cli_endpoints([cli_source])
    b = extract_cli_endpoints([cli_source])
    assert [(e.file, e.lineno, e.name) for e in a] == [
        (e.file, e.lineno, e.name) for e in b
    ]
    # Sorted by (file, lineno) ascending
    linenos = [e.lineno for e in a]
    assert linenos == sorted(linenos)


def test_extract_cli_endpoints_all_kind_is_cli_command(cli_source):
    endpoints = extract_cli_endpoints([cli_source])
    assert all(e.kind == "cli_command" for e in endpoints)


def test_endpoint_and_endpoint_arg_are_frozen():
    ep = Endpoint(kind="cli_command", name="x", file="f.py", lineno=1)
    with pytest.raises((AttributeError, TypeError)):
        ep.name = "y"  # type: ignore[misc]
    arg = EndpointArg(name="a", type="str", required=True, default=None)
    with pytest.raises((AttributeError, TypeError)):
        arg.name = "b"  # type: ignore[misc]
