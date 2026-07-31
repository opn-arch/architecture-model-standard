"""Behavioral extraction from function AST nodes.

Extracts call_order, control_flow, and guards from function bodies.
These are lightweight structural signals — no type inference or inter-procedural analysis.
"""
from __future__ import annotations

import ast
from typing import Union

# Builtins to exclude from call_order
_BUILTINS = frozenset({
    "print", "len", "str", "int", "float", "bool", "list", "dict", "set",
    "tuple", "range", "enumerate", "zip", "map", "filter", "sorted", "reversed",
    "min", "max", "sum", "abs", "round", "isinstance", "issubclass", "hasattr",
    "getattr", "setattr", "delattr", "type", "id", "repr", "hash", "iter",
    "next", "super", "object", "property", "staticmethod", "classmethod",
    "vars", "dir", "any", "all", "ord", "chr", "hex", "oct", "bin",
    "format", "input", "open",
})


def extract_call_order(func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> list[str]:
    """Extract ordered call sequence from function body.
    
    Walks body in execution order (top-to-bottom, depth-first into expressions).
    For nested calls like save(transform(x)), yields innermost first (evaluation order).
    """
    calls: list[str] = []
    _walk_body_for_calls(func_node.body, calls)
    return calls


def _walk_body_for_calls(stmts: list[ast.stmt], calls: list[str]) -> None:
    """Walk statements in execution order, extracting calls."""
    for stmt in stmts:
        if isinstance(stmt, ast.Expr):
            _extract_calls_from_expr(stmt.value, calls)
        elif isinstance(stmt, ast.Assign):
            _extract_calls_from_expr(stmt.value, calls)
        elif isinstance(stmt, ast.Return):
            if stmt.value:
                _extract_calls_from_expr(stmt.value, calls)
        elif isinstance(stmt, ast.If):
            # Walk both branches in order
            _walk_body_for_calls(stmt.body, calls)
            _walk_body_for_calls(stmt.orelse, calls)
        elif isinstance(stmt, (ast.For, ast.AsyncFor)):
            _extract_calls_from_expr(stmt.iter, calls)
            _walk_body_for_calls(stmt.body, calls)
        elif isinstance(stmt, (ast.While,)):
            _walk_body_for_calls(stmt.body, calls)
        elif isinstance(stmt, ast.Try):
            _walk_body_for_calls(stmt.body, calls)
            for handler in stmt.handlers:
                _walk_body_for_calls(handler.body, calls)
            _walk_body_for_calls(stmt.orelse, calls)
            _walk_body_for_calls(stmt.finalbody, calls)
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            _walk_body_for_calls(stmt.body, calls)
        elif isinstance(stmt, ast.AugAssign):
            _extract_calls_from_expr(stmt.value, calls)
        elif isinstance(stmt, ast.AnnAssign) and stmt.value:
            _extract_calls_from_expr(stmt.value, calls)
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Descend into nested functions (closures/decorators)
            _walk_body_for_calls(stmt.body, calls)
        # TryStar (3.11+)
        elif hasattr(ast, 'TryStar') and isinstance(stmt, ast.TryStar):
            _walk_body_for_calls(stmt.body, calls)
            for handler in stmt.handlers:
                _walk_body_for_calls(handler.body, calls)


def _extract_calls_from_expr(node: ast.expr, calls: list[str]) -> None:
    """Extract calls from an expression, innermost first (evaluation order)."""
    if isinstance(node, ast.Call):
        # Process arguments first (they evaluate before the outer call)
        for arg in node.args:
            _extract_calls_from_expr(arg, calls)
        for kw in node.keywords:
            _extract_calls_from_expr(kw.value, calls)
        # If func is itself an expression (chained calls), recurse into it
        if isinstance(node.func, ast.Call):
            _extract_calls_from_expr(node.func, calls)
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Call):
            # e.g. foo().bar() — extract the inner call too
            _extract_calls_from_expr(node.func.value, calls)
        # Then the call itself
        name = _call_name(node)
        if name and name not in _BUILTINS:
            calls.append(name)
    elif isinstance(node, ast.BoolOp):
        for val in node.values:
            _extract_calls_from_expr(val, calls)
    elif isinstance(node, ast.BinOp):
        _extract_calls_from_expr(node.left, calls)
        _extract_calls_from_expr(node.right, calls)
    elif isinstance(node, ast.UnaryOp):
        _extract_calls_from_expr(node.operand, calls)
    elif isinstance(node, ast.IfExp):
        _extract_calls_from_expr(node.body, calls)
        _extract_calls_from_expr(node.orelse, calls)
    elif isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
        _extract_calls_from_expr(node.elt, calls)
        for gen in node.generators:
            _extract_calls_from_expr(gen.iter, calls)
            for if_clause in gen.ifs:
                _extract_calls_from_expr(if_clause, calls)
    elif isinstance(node, ast.DictComp):
        _extract_calls_from_expr(node.key, calls)
        _extract_calls_from_expr(node.value, calls)
        for gen in node.generators:
            _extract_calls_from_expr(gen.iter, calls)
            for if_clause in gen.ifs:
                _extract_calls_from_expr(if_clause, calls)
    elif isinstance(node, ast.Await):
        _extract_calls_from_expr(node.value, calls)
    elif isinstance(node, ast.Yield):
        if node.value:
            _extract_calls_from_expr(node.value, calls)
    elif isinstance(node, ast.YieldFrom):
        _extract_calls_from_expr(node.value, calls)
    elif isinstance(node, ast.Starred):
        _extract_calls_from_expr(node.value, calls)
    elif isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        for elt in node.elts:
            _extract_calls_from_expr(elt, calls)
    elif isinstance(node, ast.Dict):
        for key in node.keys:
            if key:
                _extract_calls_from_expr(key, calls)
        for val in node.values:
            _extract_calls_from_expr(val, calls)
    elif isinstance(node, ast.Subscript):
        _extract_calls_from_expr(node.value, calls)
    elif isinstance(node, ast.FormattedValue):
        _extract_calls_from_expr(node.value, calls)
    elif isinstance(node, ast.JoinedStr):
        for val in node.values:
            _extract_calls_from_expr(val, calls)
    elif isinstance(node, ast.Compare):
        _extract_calls_from_expr(node.left, calls)
        for comp in node.comparators:
            _extract_calls_from_expr(comp, calls)
    elif isinstance(node, ast.Lambda):
        _extract_calls_from_expr(node.body, calls)


def _call_name(node: ast.Call) -> str | None:
    """Get the callable name from a Call node."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    elif isinstance(func, ast.Attribute):
        # self.method() -> "self.method", obj.method() -> "obj.method"
        if isinstance(func.value, ast.Name):
            return f"{func.value.id}.{func.attr}"
        return func.attr
    return None


def extract_control_flow(func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> list[str]:
    """Detect structural control flow patterns in a function.
    
    Returns deduplicated list of pattern names found.
    """
    patterns: set[str] = set()
    func_name = func_node.name

    for node in ast.walk(func_node):
        if isinstance(node, ast.Try):
            patterns.add("try_except")
        elif isinstance(node, ast.For):
            patterns.add("for_loop")
        elif isinstance(node, ast.AsyncFor):
            patterns.add("async_for")
        elif isinstance(node, ast.While):
            patterns.add("while_loop")
        elif isinstance(node, ast.With):
            patterns.add("with_context")
        elif isinstance(node, ast.AsyncWith):
            patterns.add("async_with")
        elif isinstance(node, (ast.Yield, ast.YieldFrom)):
            patterns.add("generator")
        elif isinstance(node, ast.If):
            # if_chain: 3+ branches (if/elif/elif...)
            if _count_if_branches(node) >= 3:
                patterns.add("if_chain")
        elif isinstance(node, ast.Call):
            # recursion: function calls itself
            name = _call_name(node)
            if name == func_name:
                patterns.add("recursion")
        # match_case (3.10+)
        elif hasattr(ast, 'Match') and isinstance(node, ast.Match):
            patterns.add("match_case")
        # TryStar (3.11+)
        elif hasattr(ast, 'TryStar') and isinstance(node, ast.TryStar):
            patterns.add("try_except")

    # Stable ordering for determinism
    order = [
        "try_except", "for_loop", "async_for", "while_loop",
        "if_chain", "with_context", "async_with", "generator",
        "match_case", "recursion",
    ]
    return [p for p in order if p in patterns]


def _count_if_branches(node: ast.If) -> int:
    """Count total branches in an if/elif chain."""
    count = 1  # the if itself
    if node.orelse:
        if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
            count += _count_if_branches(node.orelse[0])
        else:
            count += 1  # else branch
    return count


def extract_guards(func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> list[str]:
    """Extract precondition guards from the first 6 statements of a function body.
    
    Guards are: assert statements, raise-if patterns, early return-if patterns.
    """
    guards: list[str] = []
    first_stmts = func_node.body[:6]

    for stmt in first_stmts:
        if isinstance(stmt, ast.Assert):
            cond_text = ast.unparse(stmt.test)
            guards.append(f"assert {cond_text}")
        elif isinstance(stmt, ast.If):
            # Check if body is a single raise or return
            if len(stmt.body) == 1:
                inner = stmt.body[0]
                cond_text = ast.unparse(stmt.test)
                if isinstance(inner, ast.Raise):
                    exc = ast.unparse(inner.exc) if inner.exc else "Exception"
                    guards.append(f"raise {exc} if {cond_text}")
                elif isinstance(inner, ast.Return):
                    val = ast.unparse(inner.value) if inner.value else "None"
                    guards.append(f"return {val} if {cond_text}")

    return guards
