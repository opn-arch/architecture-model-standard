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

__all__ = [
    "extract_cli_endpoints",
    "extract_http_endpoints",
    "extract_plugin_hook_endpoints",
]


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


# ---------------------------------------------------------------------------
# HTTP route extraction (Task 9)
# ---------------------------------------------------------------------------


_HTTP_METHOD_DECORATORS = {"get", "post", "put", "delete", "patch", "options", "head"}


def _path_param_names(path: str) -> list[str]:
    """Extract path-parameter names from ``"/items/{item_id}"``-style paths."""
    names: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in path:
        if ch == "{":
            depth += 1
            current = []
        elif ch == "}":
            if depth > 0:
                names.append("".join(current).split(":", 1)[0])
                depth -= 1
        elif depth > 0:
            current.append(ch)
    return names


def _path_args_from_signature(
    fn: ast.FunctionDef | ast.AsyncFunctionDef, path: str
) -> tuple[EndpointArg, ...]:
    """Match path params to function signature args to produce EndpointArgs."""
    param_names = _path_param_names(path)
    if not param_names:
        return ()
    sig_args: dict[str, ast.arg] = {a.arg: a for a in fn.args.args}
    out: list[EndpointArg] = []
    for name in param_names:
        arg = sig_args.get(name)
        type_str = ""
        if arg is not None and arg.annotation is not None:
            chain = _decorator_attr_chain(arg.annotation)
            if chain:
                type_str = chain[-1]
        out.append(EndpointArg(name=name, type=type_str, required=True))
    return tuple(out)


def _http_route_from_function(
    fn: ast.FunctionDef | ast.AsyncFunctionDef, file: str
) -> list[Endpoint]:
    """Return zero-or-more HTTP-route endpoints for a decorated function.

    Supports FastAPI-style method decorators (``@app.get("/")``, ...) and
    Flask's ``@app.route("/", methods=[...])`` which may expand to
    multiple endpoints.
    """
    out: list[Endpoint] = []
    for dec in fn.decorator_list:
        call = _decorator_call(dec)
        if call is None:
            continue
        chain = _decorator_attr_chain(dec)
        if len(chain) < 2:
            continue
        method_attr = chain[-1].lower()
        # First positional string is the path.
        path: str | None = None
        for arg in call.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                path = arg.value
                break
        if path is None:
            continue
        if method_attr in _HTTP_METHOD_DECORATORS:
            # FastAPI / APIRouter — single HTTP method per decorator.
            args = _path_args_from_signature(fn, path)
            out.append(
                Endpoint(
                    kind="http_route",
                    name=fn.name,
                    file=file,
                    lineno=dec.lineno,
                    args=args,
                    metadata={
                        "framework": "fastapi",
                        "http_method": method_attr.upper(),
                        "path": path,
                    },
                )
            )
        elif method_attr == "route":
            # Flask-style: methods=[...] kwarg lists HTTP methods.
            methods: list[str] = []
            for kw in call.keywords:
                if kw.arg == "methods":
                    value = _literal_or_none(kw.value)
                    if isinstance(value, (list, tuple)):
                        methods = [str(m).upper() for m in value]
            if not methods:
                methods = ["GET"]
            args = _path_args_from_signature(fn, path)
            for method in methods:
                out.append(
                    Endpoint(
                        kind="http_route",
                        name=fn.name,
                        file=file,
                        lineno=dec.lineno,
                        args=args,
                        metadata={
                            "framework": "flask",
                            "http_method": method,
                            "path": path,
                        },
                    )
                )
    return out


def _starlette_route_from_call(call: ast.Call, file: str) -> list[Endpoint]:
    """Return endpoints for a ``Route("/path", ..., methods=[...])`` call."""
    if not isinstance(call.func, ast.Name) or call.func.id != "Route":
        return []
    if not call.args:
        return []
    first = call.args[0]
    if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
        return []
    path = first.value
    methods: list[str] = []
    for kw in call.keywords:
        if kw.arg == "methods":
            value = _literal_or_none(kw.value)
            if isinstance(value, (list, tuple)):
                methods = [str(m).upper() for m in value]
    if not methods:
        methods = ["GET"]
    param_names = _path_param_names(path)
    args = tuple(EndpointArg(name=n, required=True) for n in param_names)
    return [
        Endpoint(
            kind="http_route",
            name=path,
            file=file,
            lineno=call.lineno,
            args=args,
            metadata={
                "framework": "starlette",
                "http_method": m,
                "path": path,
            },
        )
        for m in methods
    ]


def extract_http_endpoints(source_files: Iterable[Path]) -> list[Endpoint]:
    """AST-scan the given Python files for HTTP route declarations.

    Handles FastAPI / APIRouter method decorators, Flask
    ``@app.route(..., methods=[...])``, and starlette ``Route(...)``
    call sites. Output is sorted by ``(file, lineno, name)``.
    """
    endpoints: list[Endpoint] = []
    for path in source_files:
        tree = _parse_source(path)
        if tree is None:
            continue
        file = str(path)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                endpoints.extend(_http_route_from_function(node, file))
            elif isinstance(node, ast.Call):
                endpoints.extend(_starlette_route_from_call(node, file))
    endpoints.sort(key=lambda e: (e.file, e.lineno, e.name))
    return endpoints


# ---------------------------------------------------------------------------
# Plugin hook extraction (Task 10)
# ---------------------------------------------------------------------------


def _extract_from_pyproject(path: Path) -> list[Endpoint]:
    """Read ``pyproject.toml`` entry_points + scripts tables."""
    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError:  # pragma: no cover - py<3.11 fallback
        import tomli as tomllib  # type: ignore[no-redef]
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return []
    project = data.get("project") or {}
    out: list[Endpoint] = []
    file = str(path)
    # [project.entry-points."<group>"]
    entry_points = project.get("entry-points") or {}
    if isinstance(entry_points, dict):
        for group_name in sorted(entry_points):
            group = entry_points[group_name]
            if not isinstance(group, dict):
                continue
            for name in sorted(group):
                target = group[name]
                if not isinstance(target, str):
                    continue
                out.append(
                    Endpoint(
                        kind="plugin_hook",
                        name=name,
                        file=file,
                        lineno=1,
                        metadata={
                            "entry_point_group": group_name,
                            "target": target,
                            "source": "pyproject",
                        },
                    )
                )
    # [project.scripts] — console-script style, surface as plugin_hooks
    # under the ``console_scripts`` group for consistency with setup.py.
    scripts = project.get("scripts") or {}
    if isinstance(scripts, dict):
        for name in sorted(scripts):
            target = scripts[name]
            if not isinstance(target, str):
                continue
            out.append(
                Endpoint(
                    kind="plugin_hook",
                    name=name,
                    file=file,
                    lineno=1,
                    metadata={
                        "entry_point_group": "console_scripts",
                        "target": target,
                        "source": "pyproject",
                    },
                )
            )
    return out


def _extract_from_setup_py(path: Path) -> list[Endpoint]:
    """AST-parse ``setup.py`` for ``entry_points={...}`` kwarg to setup()."""
    tree = _parse_source(path)
    if tree is None:
        return []
    file = str(path)
    out: list[Endpoint] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func_chain = _decorator_attr_chain(node.func)
        if not func_chain or func_chain[-1] != "setup":
            continue
        for kw in node.keywords:
            if kw.arg != "entry_points":
                continue
            value = _literal_or_none(kw.value)
            if not isinstance(value, dict):
                continue
            for group_name in sorted(value):
                entries = value[group_name]
                if not isinstance(entries, (list, tuple)):
                    continue
                for entry in entries:
                    if not isinstance(entry, str):
                        continue
                    # Format: "name = target[:extras]"
                    if "=" not in entry:
                        continue
                    name_part, target_part = entry.split("=", 1)
                    name = name_part.strip()
                    target = target_part.strip()
                    if not name or not target:
                        continue
                    out.append(
                        Endpoint(
                            kind="plugin_hook",
                            name=name,
                            file=file,
                            lineno=node.lineno,
                            metadata={
                                "entry_point_group": group_name,
                                "target": target,
                                "source": "setup.py",
                            },
                        )
                    )
    return out


def extract_plugin_hook_endpoints(repo_root: Path) -> list[Endpoint]:
    """Scan ``repo_root`` for plugin-hook declarations.

    Reads ``pyproject.toml`` (``[project.entry-points]`` and
    ``[project.scripts]``) and ``setup.py`` (``entry_points={...}``
    kwarg to ``setup()``). Output is sorted by
    ``(entry_point_group, name)`` for stable downstream use.
    """
    endpoints: list[Endpoint] = []
    pyproject = repo_root / "pyproject.toml"
    if pyproject.is_file():
        endpoints.extend(_extract_from_pyproject(pyproject))
    setup_py = repo_root / "setup.py"
    if setup_py.is_file():
        endpoints.extend(_extract_from_setup_py(setup_py))
    endpoints.sort(
        key=lambda e: (
            e.metadata.get("entry_point_group", ""),
            e.name,
            e.file,
        )
    )
    return endpoints
