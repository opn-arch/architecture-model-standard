"""AST-based body hint extraction for function implementations.

Classifies functions by body complexity and produces tiered hints:
- TRIVIAL (1 statement after docstring): exact body text
- SHORT (2-5 statements): semicolon-joined body lines
- COMPLEX (6+ statements): structural summary
"""
from __future__ import annotations

import ast
from enum import Enum
from pathlib import Path

from architecture_model.core.types import FunctionSignature


class BodyComplexity(Enum):
    """Classification of function body complexity."""
    TRIVIAL = "trivial"
    SHORT = "short"
    COMPLEX = "complex"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _find_function(
    tree: ast.Module, func_name: str, class_name: str | None = None
) -> ast.FunctionDef | ast.AsyncFunctionDef:
    """Locate an AST FunctionDef node by name, optionally within a class."""
    if class_name:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if item.name == func_name:
                            return item
        raise ValueError(
            f"Function '{func_name}' not found in class '{class_name}'"
        )

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == func_name:
                return node
    raise ValueError(f"Function '{func_name}' not found")


def _strip_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    """Remove leading docstring Expr from body list."""
    if not body:
        return body
    first = body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, (ast.Constant,))
        and isinstance(first.value.value, str)
    ):
        return body[1:]
    return body


def _summarize_complex_body(body: list[ast.stmt]) -> str:
    """Produce a structural summary for COMPLEX bodies.

    Walks top-level statements and produces condensed representations.
    """
    parts: list[str] = []
    for stmt in body:
        if isinstance(stmt, ast.For):
            target = ast.unparse(stmt.target)
            iter_expr = ast.unparse(stmt.iter)
            parts.append(f"for {target} in {iter_expr}: ...")
        elif isinstance(stmt, ast.While):
            test = ast.unparse(stmt.test)
            parts.append(f"while {test}: ...")
        elif isinstance(stmt, ast.If):
            test = ast.unparse(stmt.test)
            parts.append(f"if {test}: ...")
        elif isinstance(stmt, ast.Return):
            if stmt.value:
                parts.append(f"return {ast.unparse(stmt.value)}")
            else:
                parts.append("return")
        elif isinstance(stmt, ast.Assign):
            target = ast.unparse(stmt.targets[0])
            value = ast.unparse(stmt.value)
            if len(value) > 60:
                value = value[:57] + "..."
            parts.append(f"{target} = {value}")
        elif isinstance(stmt, ast.AugAssign):
            target = ast.unparse(stmt.target)
            # Map operator to string
            op_map = {
                ast.Add: "+=", ast.Sub: "-=", ast.Mult: "*=",
                ast.Div: "/=", ast.Mod: "%=", ast.Pow: "**=",
                ast.BitOr: "|=", ast.BitAnd: "&=", ast.BitXor: "^=",
                ast.LShift: "<<=", ast.RShift: ">>=", ast.FloorDiv: "//=",
            }
            op_str = op_map.get(type(stmt.op), "?=")
            value = ast.unparse(stmt.value)
            if len(value) > 60:
                value = value[:57] + "..."
            parts.append(f"{target} {op_str} {value}")
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            parts.append(ast.unparse(stmt.value))
        elif isinstance(stmt, ast.With):
            parts.append("with ...: ...")
        elif isinstance(stmt, (ast.Try, ast.TryStar)):
            parts.append("try/except: ...")
        else:
            # Fallback: just unparse it, truncated
            text = ast.unparse(stmt)
            if len(text) > 60:
                text = text[:57] + "..."
            parts.append(text)
    return "; ".join(parts)


def _node_to_signature(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    source: str,
    class_name: str | None = None,
) -> FunctionSignature:
    """Convert an AST FunctionDef to a FunctionSignature with body_hint."""
    # Extract params
    params: list[str] = []
    args = node.args

    # Positional args (skip self/cls)
    for arg in args.args:
        if arg.arg in ("self", "cls"):
            continue
        if arg.annotation:
            params.append(f"{arg.arg}: {ast.unparse(arg.annotation)}")
        else:
            params.append(arg.arg)

    # *args
    if args.vararg:
        if args.vararg.annotation:
            params.append(f"*{args.vararg.arg}: {ast.unparse(args.vararg.annotation)}")
        else:
            params.append(f"*{args.vararg.arg}")

    # keyword-only args
    for arg in args.kwonlyargs:
        if arg.annotation:
            params.append(f"{arg.arg}: {ast.unparse(arg.annotation)}")
        else:
            params.append(arg.arg)

    # **kwargs
    if args.kwarg:
        if args.kwarg.annotation:
            params.append(f"**{args.kwarg.arg}: {ast.unparse(args.kwarg.annotation)}")
        else:
            params.append(f"**{args.kwarg.arg}")

    # Returns
    returns = ast.unparse(node.returns) if node.returns else ""

    # Decorators
    decorators = [ast.unparse(dec) for dec in node.decorator_list]

    # Body hint
    body = _strip_docstring(node.body)
    stmt_count = len(body)

    if stmt_count <= 1:
        body_hint = ast.unparse(body[0]) if body else ""
    elif stmt_count <= 5:
        body_hint = "; ".join(ast.unparse(s) for s in body)
    else:
        body_hint = _summarize_complex_body(body)

    return FunctionSignature(
        name=node.name,
        params=params,
        returns=returns,
        decorators=decorators,
        body_hint=body_hint,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_function(source: str, func_name: str) -> BodyComplexity:
    """Classify a function's body complexity.

    Parses source, finds function by name, counts body statements
    (excluding leading docstring). 1=TRIVIAL, 2-5=SHORT, 6+=COMPLEX.
    """
    tree = ast.parse(source)
    node = _find_function(tree, func_name)
    body = _strip_docstring(node.body)
    count = len(body)

    if count <= 1:
        return BodyComplexity.TRIVIAL
    elif count <= 5:
        return BodyComplexity.SHORT
    else:
        return BodyComplexity.COMPLEX


def extract_body_hint(
    source: str, func_name: str, class_name: str | None = None
) -> str:
    """Produce a tiered body hint for a function.

    - Trivial: exact single statement text
    - Short: semicolon-joined statements
    - Complex: structural summary
    """
    tree = ast.parse(source)
    node = _find_function(tree, func_name, class_name)
    body = _strip_docstring(node.body)
    count = len(body)

    if count <= 1:
        return ast.unparse(body[0]) if body else ""
    elif count <= 5:
        return "; ".join(ast.unparse(s) for s in body)
    else:
        return _summarize_complex_body(body)


def extract_file_hints(
    filepath: Path, include_private: bool = False
) -> list[FunctionSignature]:
    """Scan an entire file and produce FunctionSignature objects with body hints.

    Excludes private functions (starting with '_') EXCEPT '__init__'.
    Includes class methods. When include_private=True, includes all functions.
    """
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))

    results: list[FunctionSignature] = []

    def _should_include(name: str) -> bool:
        if include_private:
            return True
        if name == "__init__":
            return True
        if name.startswith("_"):
            return False
        return True

    # Top-level functions
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _should_include(node.name):
                results.append(_node_to_signature(node, source))
        elif isinstance(node, ast.ClassDef):
            # Class methods — use qualified name (ClassName.method)
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if _should_include(item.name):
                        sig = _node_to_signature(item, source, class_name=node.name)
                        # Qualify name to avoid collisions between classes
                        sig.name = f"{node.name}.{item.name}"
                        results.append(sig)

    return results
