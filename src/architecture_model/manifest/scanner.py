"""AST helpers and file scanning for the reality manifest.

Functions for parsing Python source files, extracting metadata (docstrings,
function signatures, imports), and assembling per-file scan results.
"""

from __future__ import annotations

import ast
import logging
import re
import warnings
from pathlib import Path
from typing import Any

from architecture_model.manifest.types import (
    ClassInfo,
    DecoratedFunction,
    FunctionInfo,
    ImportDetail,
    ModuleInfo,
    ModuleStatus,
)
from architecture_model.utils.discovery import collect_py_files as _discovery_collect

logger = logging.getLogger(__name__)


def _count_files(root: Path, directory: str, pattern: str) -> int:
    """Count files matching pattern in a directory relative to root."""
    target = root / directory
    if not target.is_dir():
        return 0
    return len(list(target.glob(pattern)))


def _collect_py_files(root: Path, directory: str) -> list[Path]:
    """Collect all .py files in a directory (recursive), excluding __pycache__.

    .. deprecated::
        Use :func:`architecture_model.utils.discovery.collect_py_files` instead.
    """
    warnings.warn(
        "_collect_py_files is deprecated, use utils.discovery.collect_py_files",
        DeprecationWarning,
        stacklevel=2,
    )
    return _discovery_collect(root / directory)


def _parse_file_ast(filepath: Path) -> ast.Module | None:
    """Parse a Python file's AST, returning None on failure."""
    try:
        source = filepath.read_text(encoding="utf-8")
        return ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError, OSError) as exc:
        logger.warning("Parse error in %s: %s", filepath, exc)
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


def _extract_function_docstring(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """Extract function docstring if present."""
    return ast.get_docstring(node)


def _extract_function_calls(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Extract direct function/method calls (depth-1) from function body."""
    calls: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                calls.append(child.func.id)
            elif isinstance(child.func, ast.Attribute):
                calls.append(child.func.attr)
    seen = set()
    unique = []
    for c in calls:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


def _extract_raises(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Extract exception types raised in function body."""
    raises: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Raise) and child.exc is not None:
            if isinstance(child.exc, ast.Call):
                if isinstance(child.exc.func, ast.Name):
                    raises.append(child.exc.func.id)
                elif isinstance(child.exc.func, ast.Attribute):
                    raises.append(child.exc.func.attr)
            elif isinstance(child.exc, ast.Name):
                raises.append(child.exc.id)
    return list(dict.fromkeys(raises))


def _extract_public_functions(tree: ast.Module) -> list[FunctionInfo]:
    """Extract public function/method signatures from module-level definitions."""
    functions: list[FunctionInfo] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            sig = _build_signature(node)
            functions.append(FunctionInfo(
                name=node.name,
                signature=sig,
                calls=_extract_function_calls(node),
                docstring=_extract_function_docstring(node),
                raises=_extract_raises(node),
            ))
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


def _extract_exports(tree: ast.Module, filepath: Path) -> list[str]:
    """Extract public API exports from __init__.py."""
    if filepath.name != "__init__.py":
        return []

    # Check for __all__
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        try:
                            return [
                                elt.value
                                for elt in node.value.elts
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                            ]
                        except (AttributeError, TypeError):
                            pass

    # Fallback: collect symbols from relative imports
    exports: list[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ImportFrom) and node.level > 0:
            for alias in node.names:
                if not alias.name.startswith("_"):
                    exports.append(alias.name)
    return exports


def _extract_class_attributes(cls_node: ast.ClassDef) -> dict[str, str]:
    """Extract class-level attribute assignments (name = literal_value).

    Returns dict mapping attribute name to repr of its value.
    Only captures simple assignments to literals (int, str, float, bool, bytes).
    Skips names starting with underscore.
    """
    attrs: dict[str, str] = {}
    for item in cls_node.body:
        if not isinstance(item, ast.Assign):
            continue
        for target in item.targets:
            if not isinstance(target, ast.Name):
                continue
            if target.id.startswith("_"):
                continue
            if isinstance(item.value, ast.Constant) and isinstance(
                item.value.value, (int, str, float, bool, bytes)
            ):
                attrs[target.id] = repr(item.value.value)
    return attrs


def _extract_module_constants(tree: ast.Module) -> dict[str, str]:
    """Extract module-level constants (UPPER_CASE names assigned to literals).

    A constant is: name is ALL_UPPER_CASE (allowing digits/underscores)
    and value is a literal (str, int, float, bytes, bool).
    Returns dict mapping name to repr of value.
    """
    consts: dict[str, str] = {}
    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            name = target.id
            if name.startswith("_"):
                continue
            if not re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
                continue
            if isinstance(node.value, ast.Constant) and isinstance(
                node.value.value, (int, str, float, bool, bytes)
            ):
                consts[name] = repr(node.value.value)
    return consts


def _extract_module_assignments(tree: ast.Module) -> dict[str, str]:
    """Extract module-level non-constant assignments (instance creation, calls, etc.).

    Captures: name = expr where:
    - name is NOT all-uppercase (those are constants)
    - name does NOT start with underscore or dunder
    - value is NOT a literal (those would be constants if uppercase)
    - value IS a non-literal expression (Call, Attribute, etc.)
    Returns dict mapping name to ast.unparse(value).
    """
    assigns: dict[str, str] = {}
    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            name = target.id
            if name.startswith("_"):
                continue
            if re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
                continue
            if isinstance(node.value, ast.Constant):
                continue
            try:
                assigns[name] = ast.unparse(node.value)
            except Exception:
                pass
    return assigns


def _extract_classes(tree: ast.Module) -> list[ClassInfo]:
    """Extract class definitions with inheritance and method info."""
    classes: list[ClassInfo] = []
    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name.startswith("_"):
            continue

        # Extract bases
        bases: list[str] = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(base.attr)
            else:
                try:
                    bases.append(ast.unparse(base))
                except Exception:
                    pass

        # Extract methods (public + __init__)
        methods: list[str] = []
        has_abstractmethod = False
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not item.name.startswith("_") or item.name == "__init__":
                    methods.append(item.name)
                for dec in item.decorator_list:
                    dec_name = None
                    if isinstance(dec, ast.Name):
                        dec_name = dec.id
                    elif isinstance(dec, ast.Attribute):
                        dec_name = dec.attr
                    if dec_name == "abstractmethod":
                        has_abstractmethod = True

        # Determine if abstract
        is_abstract = (
            has_abstractmethod
            or any(b in ("ABC", "Protocol") for b in bases)
            or any(node.name.startswith(p) for p in ("Base", "Abstract", "I")
                   if len(node.name) > len(p))
        )

        # Class decorators
        decorators: list[str] = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                decorators.append(dec.attr)
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    decorators.append(dec.func.id)
                elif isinstance(dec.func, ast.Attribute):
                    decorators.append(dec.func.attr)

        classes.append(ClassInfo(
            name=node.name,
            bases=bases,
            methods=methods,
            is_abstract=is_abstract,
            decorators=decorators,
            attributes=_extract_class_attributes(node),
        ))
    return classes


def _get_decorator_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Extract decorator names from a function node."""
    names: list[str] = []
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name):
            names.append(dec.id)
        elif isinstance(dec, ast.Attribute):
            names.append(dec.attr)
        elif isinstance(dec, ast.Call):
            if isinstance(dec.func, ast.Name):
                names.append(dec.func.id)
            elif isinstance(dec.func, ast.Attribute):
                names.append(dec.func.attr)
    # Filter trivial decorators
    trivial = {"property", "staticmethod", "classmethod", "cached_property", "override"}
    return [n for n in names if n not in trivial]


def _extract_decorated_functions_from_tree(tree: ast.Module) -> list[DecoratedFunction]:
    """Extract decorated functions (module-level and class methods)."""
    results: list[DecoratedFunction] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decs = _get_decorator_names(node)
            if decs:
                results.append(DecoratedFunction(
                    name=node.name,
                    decorators=decs,
                    is_method=False,
                    class_name=None,
                ))
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    decs = _get_decorator_names(item)
                    if decs and item.name != "__init__":
                        results.append(DecoratedFunction(
                            name=item.name,
                            decorators=decs,
                            is_method=True,
                            class_name=node.name,
                        ))
    return results


def _extract_imports_detailed(tree: ast.Module) -> list[ImportDetail]:
    """Extract imports with symbol-level detail."""
    imports: list[ImportDetail] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(ImportDetail(
                    module=alias.name,
                    symbols=[],
                    is_relative=False,
                ))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            symbols = [alias.name for alias in node.names] if node.names else []
            imports.append(ImportDetail(
                module=module,
                symbols=symbols,
                is_relative=node.level > 0,
            ))
    return imports


def _file_line_count(filepath: Path) -> int:
    """Count lines in a file."""
    try:
        return len(filepath.read_text(encoding="utf-8").splitlines())
    except OSError:
        return 0


def _determine_status(filepath: Path, line_count: int) -> ModuleStatus:
    """Determine if a file is active or dormant."""
    if not filepath.exists():
        return ModuleStatus.MISSING
    if line_count > 50:
        return ModuleStatus.ACTIVE
    return ModuleStatus.DORMANT


def scan_file(root: Path, filepath: Path) -> ModuleInfo:
    """Scan a single Python file and return typed metadata.

    Args:
        root: Project root directory.
        filepath: Absolute path to the Python file.

    Returns:
        ModuleInfo with all extracted metadata.
    """
    rel_path = str(filepath.relative_to(root))
    line_count = _file_line_count(filepath)
    status = _determine_status(filepath, line_count)

    tree = _parse_file_ast(filepath)
    docstring = None
    functions: list[FunctionInfo] = []
    imports: list[str] = []

    if tree is not None:
        docstring = _get_module_docstring(tree)
        functions = _extract_public_functions(tree)
        imports = _extract_imports(tree)
        classes = _extract_classes(tree)
        exports = _extract_exports(tree, filepath)
        decorated = _extract_decorated_functions_from_tree(tree)
        imports_detailed = _extract_imports_detailed(tree)
        constants = _extract_module_constants(tree)
        assignments = _extract_module_assignments(tree)
    else:
        classes = []
        exports = []
        decorated = []
        imports_detailed = []
        constants = {}
        assignments = {}
        status = ModuleStatus.MISSING

    name = _derive_name_from_docstring(docstring, filepath)

    logger.debug(
        "Scanned %s: %d funcs, %d classes, %d constants",
        rel_path, len(functions), len(classes), len(constants),
    )

    return ModuleInfo(
        file=rel_path,
        name=name,
        docstring=docstring,
        functions=functions,
        imports=imports,
        line_count=line_count,
        status=status,
        classes=classes,
        exports=exports,
        decorated_functions=decorated,
        imports_detailed=imports_detailed,
        module_constants=constants,
        module_assignments=assignments,
    )


def _scan_file(root: Path, filepath: Path) -> dict[str, Any]:
    """Scan a single Python file and return its metadata as a dict.

    .. deprecated::
        Use :func:`scan_file` instead, which returns a :class:`ModuleInfo`.
    """
    warnings.warn(
        "_scan_file is deprecated, use scan_file() which returns ModuleInfo",
        DeprecationWarning,
        stacklevel=2,
    )
    result = scan_file(root, filepath)
    d = result.to_dict()
    # Legacy format: functions is list of signature strings, not list of dicts
    d["functions"] = [f.signature for f in result.functions]
    return d
