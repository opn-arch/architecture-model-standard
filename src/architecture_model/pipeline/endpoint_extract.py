"""Endpoint extractors (Phase 4-A Tasks 8-10).

Deterministic AST-based extraction of CLI commands (Click + argparse),
HTTP routes (FastAPI/Flask/starlette — Task 9), and plugin hooks
(entry_points — Task 10). Each extractor returns a list of
:class:`~architecture_model.pipeline.endpoint_types.Endpoint` sorted by
``(file, lineno)``.

Design goals
------------
1. Pure-AST — no import execution, safe on untrusted sources.
2. Deterministic — repeated runs on the same input produce byte-identical
   output. Extractors sort by ``(file, lineno)``.
3. Best-effort — unknown decorator shapes are ignored rather than
   raising; the pipeline is expected to be resilient to third-party
   framework variations.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable

from architecture_model.pipeline.endpoint_types import Endpoint, EndpointArg

__all__ = ["extract_cli_endpoints"]


# ---------------------------------------------------------------------------
# Click / argparse helpers
# ---------------------------------------------------------------------------


def _literal_or_none(node: ast.AST | None) -> object | None:
    """Return ``ast.literal_eval(node)`` or ``None`` on failure/absence."""
    if node is None:
        return None
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return None


def _decorator_attr_chain(dec: ast.expr) -> list[str]:
    """Return the dotted-attribute chain of a decorator.

    ``@click.command()`` → ``["click", "command"]``.
    ``@cli.command("x")`` → ``["cli", "command"]``.
    ``@app.route("/")`` → ``["app", "route"]``.
    """
    if isinstance(dec, ast.Call):
        return _decorator_attr_chain(dec.func)
    if isinstance(dec, ast.Attribute):
        head = _decorator_attr_chain(dec.value)
        return head + [dec.attr]
    if isinstance(dec, ast.Name):
        return [dec.id]
    return []


def _decorator_call(dec: ast.expr) -> ast.Call | None:
    """Return the underlying ``ast.Call`` if ``dec`` is a called decorator."""
    return dec if isinstance(dec, ast.Call) else None


def _click_command_name(dec: ast.expr, fallback: str) -> str | None:
    """If ``dec`` is a Click command/group decorator, return its name.

    Returns ``None`` when ``dec`` is not a Click command declaration.
    """
    chain = _decorator_attr_chain(dec)
    if not chain:
        return None
    last = chain[-1]
    if last not in {"command", "group"}:
        return None
    # We accept ``click.command`` / ``click.group`` (chain length 2) OR
    # ``<var>.command`` / ``<var>.group`` where ``<var>`` is presumed to
    # be a Click group instance. This heuristic catches both the entry
    # decorator and nested subcommands.
    call = _decorator_call(dec)
    if call is not None:
        # First positional string is the command name, else name= kwarg.
        for arg in call.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value
        for kw in call.keywords:
            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                value = kw.value.value
                if isinstance(value, str):
                    return value
    return fallback


def _click_arg_from_decorator(dec: ast.expr) -> EndpointArg | None:
    """Parse ``@click.option(...)`` / ``@click.argument(...)`` into an arg.

    Returns ``None`` when ``dec`` is not a click.option/argument call.
    """
    call = _decorator_call(dec)
    if call is None:
        return None
    chain = _decorator_attr_chain(dec)
    if not chain or chain[-1] not in {"option", "argument"}:
        return None
    is_option = chain[-1] == "option"
    # First positional string is the flag / argument name.
    if not call.args:
        return None
    first = call.args[0]
    if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
        return None
    name = first.value
    # Type kwarg — best-effort stringify.
    type_str = ""
    default: object = None
    required = not is_option  # click options default optional, args required
    for kw in call.keywords:
        if kw.arg == "type" and isinstance(kw.value, (ast.Name, ast.Attribute)):
            type_str = _decorator_attr_chain(kw.value)[-1]
        elif kw.arg == "default":
            default = _literal_or_none(kw.value)
            if default is not None:
                required = False
        elif kw.arg == "required" and isinstance(kw.value, ast.Constant):
            if isinstance(kw.value.value, bool):
                required = kw.value.value
    return EndpointArg(name=name, type=type_str, required=required, default=default)


# ---------------------------------------------------------------------------
# Click extraction
# ---------------------------------------------------------------------------


def _extract_click_from_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef, file: str
) -> Endpoint | None:
    """Return an Endpoint if ``node`` is a Click command; else None."""
    command_decorator: ast.expr | None = None
    command_name: str | None = None
    args: list[EndpointArg] = []
    for dec in node.decorator_list:
        name = _click_command_name(dec, fallback=node.name)
        if name is not None and command_decorator is None:
            command_decorator = dec
            command_name = name
            continue
        arg = _click_arg_from_decorator(dec)
        if arg is not None:
            args.append(arg)
    if command_decorator is None or command_name is None:
        return None
    return Endpoint(
        kind="cli_command",
        name=command_name,
        file=file,
        lineno=command_decorator.lineno,
        args=tuple(args),
        metadata={"framework": "click"},
    )


# ---------------------------------------------------------------------------
# argparse extraction
# ---------------------------------------------------------------------------


def _extract_argparse_from_call(call: ast.Call, file: str) -> Endpoint | None:
    """Return an Endpoint if ``call`` is ``<parser>.add_parser("name", ...)``."""
    if not isinstance(call.func, ast.Attribute):
        return None
    if call.func.attr != "add_parser":
        return None
    if not call.args:
        return None
    first = call.args[0]
    if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
        return None
    return Endpoint(
        kind="cli_command",
        name=first.value,
        file=file,
        lineno=call.lineno,
        metadata={"framework": "argparse"},
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _parse_source(path: Path) -> ast.Module | None:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    try:
        return ast.parse(source, filename=str(path))
    except SyntaxError:
        return None


def extract_cli_endpoints(source_files: Iterable[Path]) -> list[Endpoint]:
    """AST-scan the given Python files for CLI command declarations.

    Handles Click (``@click.command``, ``@click.group``,
    ``@<group>.command``) and argparse (``.add_parser("name")``).
    Output is sorted by ``(file, lineno)`` for stable downstream use.
    """
    endpoints: list[Endpoint] = []
    for path in source_files:
        tree = _parse_source(path)
        if tree is None:
            continue
        file = str(path)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                ep = _extract_click_from_function(node, file)
                if ep is not None:
                    endpoints.append(ep)
            elif isinstance(node, ast.Call):
                ep = _extract_argparse_from_call(node, file)
                if ep is not None:
                    endpoints.append(ep)
    endpoints.sort(key=lambda e: (e.file, e.lineno, e.name))
    return endpoints
