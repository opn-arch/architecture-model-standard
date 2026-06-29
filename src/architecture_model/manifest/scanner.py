"""AST helpers and file scanning for the reality manifest.

Functions for parsing Python source files, extracting metadata (docstrings,
function signatures, imports), and assembling per-file scan results.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any


def _count_files(root: Path, directory: str, pattern: str) -> int:
    """Count files matching pattern in a directory relative to root."""
    target = root / directory
    if not target.is_dir():
        return 0
    return len(list(target.glob(pattern)))


def _collect_py_files(root: Path, directory: str) -> list[Path]:
    """Collect all .py files in a directory (recursive), excluding __pycache__."""
    target = root / directory
    if not target.is_dir():
        return []
    return sorted(
        p for p in target.rglob("*.py") if "__pycache__" not in str(p) and p.name != "__init__.py"
    )


def _parse_file_ast(filepath: Path) -> ast.Module | None:
    """Parse a Python file's AST, returning None on failure."""
    try:
        source = filepath.read_text(encoding="utf-8")
        return ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return None


def _get_module_docstring(tree: ast.Module) -> str | None:
    """Extract the module-level docstring."""
    return ast.get_docstring(tree)


def _format_annotation(node: ast.expr | None) -> str:
    """Best-effort unparse of a type annotation node."""
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return "..."


def _extract_public_functions(tree: ast.Module) -> list[dict[str, str]]:
    """Extract public function/method signatures from module-level definitions."""
    functions: list[dict[str, str]] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            sig = _build_signature(node)
            functions.append({"name": node.name, "signature": sig})
    return functions


def _build_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Build a human-readable function signature string."""
    args_parts: list[str] = []
    all_args = node.args

    # Positional args (skip 'self'/'cls')
    for i, arg in enumerate(all_args.args):
        if arg.arg in ("self", "cls"):
            continue
        ann = _format_annotation(arg.annotation)
        part = f"{arg.arg}: {ann}" if ann else arg.arg
        args_parts.append(part)

    # *args
    if all_args.vararg:
        ann = _format_annotation(all_args.vararg.annotation)
        part = f"*{all_args.vararg.arg}: {ann}" if ann else f"*{all_args.vararg.arg}"
        args_parts.append(part)

    # keyword-only
    for arg in all_args.kwonlyargs:
        ann = _format_annotation(arg.annotation)
        part = f"{arg.arg}: {ann}" if ann else arg.arg
        args_parts.append(part)

    # **kwargs
    if all_args.kwarg:
        ann = _format_annotation(all_args.kwarg.annotation)
        part = f"**{all_args.kwarg.arg}: {ann}" if ann else f"**{all_args.kwarg.arg}"
        args_parts.append(part)

    ret = _format_annotation(node.returns)
    ret_str = f" -> {ret}" if ret else ""
    return f"{node.name}({', '.join(args_parts)}){ret_str}"


def _derive_name_from_docstring(docstring: str | None, filepath: Path) -> str:
    """Derive a sub-function name from docstring or filename."""
    if docstring:
        # First sentence or first line
        first_line = docstring.strip().split("\n")[0]
        # Take up to first period or dash
        sentence = re.split(r"[.\-]", first_line)[0].strip()
        if 3 < len(sentence) < 80:
            return sentence
    # Fallback: humanize file stem
    stem = filepath.stem
    # Remove leading underscore and common prefixes
    stem = re.sub(r"^_pipeline_", "", stem)
    stem = re.sub(r"^_", "", stem)
    return stem.replace("_", " ").title()


def _extract_imports(tree: ast.Module) -> list[str]:
    """Extract all imported module names from a file's AST."""
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _file_line_count(filepath: Path) -> int:
    """Count lines in a file."""
    try:
        return len(filepath.read_text(encoding="utf-8").splitlines())
    except OSError:
        return 0


def _determine_status(filepath: Path, line_count: int) -> str:
    """Determine if a file is active or dormant."""
    if not filepath.exists():
        return "missing"
    if line_count > 50:
        return "active"
    return "dormant"


def _scan_file(root: Path, filepath: Path) -> dict[str, Any]:
    """Scan a single Python file and return its metadata."""
    rel_path = str(filepath.relative_to(root))
    line_count = _file_line_count(filepath)
    status = _determine_status(filepath, line_count)

    tree = _parse_file_ast(filepath)
    docstring = None
    functions: list[dict[str, str]] = []
    imports: list[str] = []

    if tree is not None:
        docstring = _get_module_docstring(tree)
        functions = _extract_public_functions(tree)
        imports = _extract_imports(tree)

    name = _derive_name_from_docstring(docstring, filepath)

    return {
        "file": rel_path,
        "name": name,
        "docstring": docstring,
        "functions": [f["signature"] for f in functions],
        "imports": imports,
        "line_count": line_count,
        "status": status,
    }
