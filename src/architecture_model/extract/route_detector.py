"""
AST-based route handler detection for Python web frameworks.

Scans Python source files and extracts decorated route handlers for
FastAPI, Flask, and Django projects.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RouteInfo:
    """Information about a detected route handler."""

    method: str  # GET, POST, PUT, DELETE, PATCH
    path: str  # "/articles/{slug}"
    function_name: str  # "get_article"
    docstring: str  # First line of function docstring
    file: str  # Relative path to the file
    is_authenticated: bool  # True if has auth dependency/decorator
    framework: str  # "fastapi", "flask", "django"


# HTTP methods recognized from decorator attribute names (FastAPI/Flask style).
_HTTP_METHODS = frozenset({"get", "post", "put", "delete", "patch", "options", "head"})


def detect_routes(
    project_root: Path, web_layer_dirs: list[str] | None = None
) -> list[RouteInfo]:
    """Scan Python files for route handler declarations.

    Args:
        project_root: Root directory of the project.
        web_layer_dirs: Optional list of directories to restrict scanning
                       (e.g., ["app/api"]). If None, scans all .py files.

    Returns:
        List of RouteInfo for each detected route handler.
    """
    root = Path(project_root)
    py_files = _collect_python_files(root, web_layer_dirs)
    routes: list[RouteInfo] = []

    for py_file in py_files:
        tree = _parse_file(py_file)
        if tree is None:
            continue
        rel_path = str(py_file.relative_to(root))
        routes.extend(_extract_fastapi_routes(tree, rel_path))
        routes.extend(_extract_flask_routes(tree, rel_path))
        if py_file.name == "urls.py":
            routes.extend(_extract_django_routes(tree, rel_path))

    return routes


# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------


def _collect_python_files(
    root: Path, web_layer_dirs: list[str] | None
) -> list[Path]:
    """Collect Python files to scan, optionally restricted to given dirs."""
    if web_layer_dirs:
        files: list[Path] = []
        for dir_name in web_layer_dirs:
            target = root / dir_name
            if target.is_dir():
                files.extend(sorted(target.rglob("*.py")))
        return files
    return sorted(root.rglob("*.py"))


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _parse_file(path: Path) -> ast.Module | None:
    """Parse a Python file, returning None on failure."""
    try:
        source = path.read_text(encoding="utf-8")
        return ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError, OSError) as exc:
        print(f"route_detector: skipping {path} ({exc})", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# FastAPI extraction
# ---------------------------------------------------------------------------


def _extract_fastapi_routes(tree: ast.Module, rel_path: str) -> list[RouteInfo]:
    """Extract routes from FastAPI-style decorators."""
    routes: list[RouteInfo] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            info = _parse_fastapi_decorator(decorator)
            if info is None:
                continue
            method, path = info
            routes.append(
                RouteInfo(
                    method=method.upper(),
                    path=path,
                    function_name=node.name,
                    docstring=_get_docstring(node),
                    file=rel_path,
                    is_authenticated=_has_auth_dependency(node),
                    framework="fastapi",
                )
            )
    return routes


def _parse_fastapi_decorator(node: ast.expr) -> tuple[str, str] | None:
    """Return (method, path) if the decorator is a FastAPI route call."""
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if not isinstance(func, ast.Attribute):
        return None
    if func.attr not in _HTTP_METHODS:
        return None
    # First positional arg is the path
    path = _get_first_string_arg(node)
    if path is None:
        path = ""
    return func.attr, path


def _has_auth_dependency(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a function has auth-related Depends() or Security() parameters."""
    for arg in _all_function_args(node):
        if arg.annotation is None:
            continue
        if _is_auth_annotation(arg.annotation):
            return True
        # Check default values
    # Also check defaults
    defaults = _collect_defaults(node)
    for default in defaults:
        if _is_auth_call(default):
            return True
    # Check route decorator dependencies=[Depends(...)] kwarg
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call):
            for kw in decorator.keywords:
                if kw.arg == "dependencies" and isinstance(kw.value, ast.List):
                    for elt in kw.value.elts:
                        if _is_auth_call(elt):
                            return True
    return False


def _all_function_args(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.arg]:
    """Get all arguments from a function definition."""
    args = node.args
    return args.posonlyargs + args.args + args.kwonlyargs


def _collect_defaults(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.expr]:
    """Collect all default values from function arguments."""
    args = node.args
    return list(args.defaults) + list(args.kw_defaults)


def _is_auth_annotation(ann: ast.expr) -> bool:
    """Check if an annotation references auth (e.g., Depends(get_current_user))."""
    if isinstance(ann, ast.Call):
        return _is_auth_call(ann)
    return False


def _is_auth_call(node: ast.expr) -> bool:
    """Check if a Call node is Depends(auth...) or Security(...)."""
    if not isinstance(node, ast.Call):
        return False
    func_name = _get_call_name(node)
    if func_name == "Security":
        return True
    if func_name == "Depends":
        if node.args:
            arg = node.args[0]
            # Direct name: Depends(get_current_user)
            arg_name = _get_node_name(arg)
            if arg_name and _is_auth_name(arg_name):
                return True
            # Factory call: Depends(get_current_user_authorizer())
            if isinstance(arg, ast.Call):
                call_name = _get_call_name(arg)
                if call_name and _is_auth_name(call_name):
                    return True
    return False


def _is_auth_name(name: str) -> bool:
    """Check if a name looks auth-related."""
    lower = name.lower()
    return (
        "auth" in lower
        or "current_user" in lower
        or "permission" in lower
        or "login_required" in lower
    )


def _get_call_name(node: ast.Call) -> str:
    """Get the simple name of a Call's function."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _get_node_name(node: ast.expr) -> str:
    """Get the name string from a Name or Attribute node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


# ---------------------------------------------------------------------------
# Flask extraction
# ---------------------------------------------------------------------------


def _extract_flask_routes(tree: ast.Module, rel_path: str) -> list[RouteInfo]:
    """Extract routes from Flask-style @app.route() decorators."""
    routes: list[RouteInfo] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            info = _parse_flask_decorator(decorator)
            if info is None:
                continue
            methods, path = info
            for method in methods:
                routes.append(
                    RouteInfo(
                        method=method.upper(),
                        path=path,
                        function_name=node.name,
                        docstring=_get_docstring(node),
                        file=rel_path,
                        is_authenticated=_has_flask_auth_decorator(node),
                        framework="flask",
                    )
                )
    return routes


def _parse_flask_decorator(node: ast.expr) -> tuple[list[str], str] | None:
    """Return (methods, path) if the decorator is a Flask route call."""
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if not isinstance(func, ast.Attribute):
        return None
    if func.attr != "route":
        return None
    path = _get_first_string_arg(node)
    if path is None:
        return None
    methods = _get_flask_methods(node)
    return methods, path


def _get_flask_methods(node: ast.Call) -> list[str]:
    """Extract the methods= keyword from a Flask route decorator."""
    for kw in node.keywords:
        if kw.arg == "methods":
            if isinstance(kw.value, ast.List):
                methods: list[str] = []
                for elt in kw.value.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        methods.append(elt.value)
                if methods:
                    return methods
    return ["GET"]


def _has_flask_auth_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a Flask handler has login_required or similar auth decorator."""
    for decorator in node.decorator_list:
        name = ""
        if isinstance(decorator, ast.Name):
            name = decorator.id
        elif isinstance(decorator, ast.Attribute):
            name = decorator.attr
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                name = decorator.func.id
            elif isinstance(decorator.func, ast.Attribute):
                name = decorator.func.attr
        if _is_auth_name(name):
            return True
    return False


# ---------------------------------------------------------------------------
# Django extraction
# ---------------------------------------------------------------------------


def _extract_django_routes(tree: ast.Module, rel_path: str) -> list[RouteInfo]:
    """Extract routes from Django urlpatterns assignments."""
    routes: list[RouteInfo] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        # Look for: urlpatterns = [...]
        if not any(
            isinstance(t, ast.Name) and t.id == "urlpatterns" for t in node.targets
        ):
            continue
        if not isinstance(node.value, ast.List):
            continue
        for elt in node.value.elts:
            info = _parse_django_path_call(elt)
            if info:
                routes.append(
                    RouteInfo(
                        method="GET",
                        path=info[0],
                        function_name=info[1],
                        docstring="",
                        file=rel_path,
                        is_authenticated=False,
                        framework="django",
                    )
                )
    return routes


def _parse_django_path_call(node: ast.expr) -> tuple[str, str] | None:
    """Parse a path() or re_path() call in urlpatterns."""
    if not isinstance(node, ast.Call):
        return None
    func_name = _get_call_name(node)
    if func_name not in ("path", "re_path"):
        return None
    if len(node.args) < 2:
        return None
    # First arg is the route string
    route_arg = node.args[0]
    if not isinstance(route_arg, ast.Constant) or not isinstance(
        route_arg.value, str
    ):
        return None
    route = route_arg.value
    # Second arg is the view function
    view_name = _get_node_name(node.args[1])
    if not view_name:
        # Try dotted access e.g., views.article_list
        if isinstance(node.args[1], ast.Attribute):
            view_name = node.args[1].attr
    return route, view_name


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _get_first_string_arg(node: ast.Call) -> str | None:
    """Get the first positional string argument from a Call node."""
    if node.args:
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return first.value
    return None


def _get_docstring(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Get the first line of a function's docstring, or empty string."""
    ds = ast.get_docstring(node)
    if ds:
        return ds.split("\n")[0].strip()
    return ""
