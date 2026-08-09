"""Observe pipeline stage — produces a factual Inventory from source code.

Wraps existing manifest generation, route detection, and constraint detection
into the unified Stage protocol. Zero inference — only observable facts.
"""
from __future__ import annotations

import ast
import time
from pathlib import Path
from typing import Any

from .observe_types import (
    ClassRecord,
    ConstantRecord,
    ConstraintRecord,
    DocRecord,
    FunctionRecord,
    ImportEdge,
    Inventory,
    ModuleRecord,
    RouteRecord,
    TestFileRecord,
)
from .protocol import (
    Diagnostic,
    Evidence,
    PipelineContext,
    QualityMetrics,
    StageResult,
    Uncertainty,
)


class ObserveStage:
    """Scans a codebase and produces a raw Inventory."""

    name: str = "observe"
    requires: list[str] = []

    def run(self, ctx: PipelineContext) -> StageResult[Inventory]:
        start = time.time()
        diagnostics: list[Diagnostic] = []
        uncertainties: list[Uncertainty] = []

        # Collect Python files
        if ctx.scope_files:
            # Scoped mode: only scan the specified files
            py_files = [f for f in ctx.scope_files if f.suffix == ".py" and f.exists()]
        else:
            py_files = list(ctx.repo_path.rglob("*.py"))
            py_files = [f for f in py_files if not _is_excluded(f, ctx.repo_path)]

        modules: list[ModuleRecord] = []
        edges: list[ImportEdge] = []
        parse_failures = 0

        for py_file in py_files:
            try:
                mod, mod_edges, mod_uncertainties = _scan_module(py_file, ctx.repo_path)
                modules.append(mod)
                edges.extend(mod_edges)
                uncertainties.extend(mod_uncertainties)
            except SyntaxError as e:
                parse_failures += 1
                diagnostics.append(Diagnostic(
                    level="warning",
                    message=f"Parse failed: {py_file.relative_to(ctx.repo_path)}: {e}",
                    source="observe",
                ))

        # Routes
        routes = _detect_routes(ctx.repo_path)

        # Constraints
        constraints = _detect_constraints(ctx.repo_path)

        # Test files
        test_files = _find_test_files(py_files, ctx.repo_path)

        # Docs
        docs = _find_docs(ctx.repo_path)

        inventory = Inventory(
            modules=modules,
            edges=edges,
            routes=routes,
            constraints=constraints,
            test_files=test_files,
            docs=docs,
        )

        # Quality metrics
        total_files = len(py_files)
        parsed = total_files - parse_failures
        parse_rate = (parsed / total_files * 100) if total_files > 0 else 100.0

        total_symbols = sum(
            len(m.functions) + len(m.classes) + len(m.constants)
            for m in modules
        )
        symbol_density = (total_symbols / parsed) if parsed > 0 else 0.0

        quality = QualityMetrics(
            score=int(parse_rate),
            sub_scores={
                "parse_success_rate": parse_rate,
                "symbol_density": symbol_density,
                "file_count": float(total_files),
            },
            thresholds={"parse_success_rate": 90.0},
        )

        duration_ms = int((time.time() - start) * 1000)

        return StageResult(
            output=inventory,
            quality=quality,
            diagnostics=diagnostics,
            uncertainties=uncertainties,
            input_hash=str(len(py_files)),
            duration_ms=duration_ms,
            version="1.0",
        )


def _is_excluded(path: Path, root: Path) -> bool:
    """Exclude common non-source directories."""
    rel = path.relative_to(root)
    parts = rel.parts
    excluded = {".git", "__pycache__", ".venv", "venv", "node_modules", ".tox", "dist", "build", ".eggs"}
    return bool(excluded.intersection(parts))


def _scan_module(
    py_file: Path, root: Path
) -> tuple[ModuleRecord, list[ImportEdge], list[Uncertainty]]:
    """Scan a single Python file into a ModuleRecord."""
    source = py_file.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(source, filename=str(py_file))

    functions: list[FunctionRecord] = []
    classes: list[ClassRecord] = []
    constants: list[ConstantRecord] = []
    imports: list[str] = []
    uncertainties: list[Uncertainty] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(_extract_function(node, source))
        elif isinstance(node, ast.ClassDef):
            classes.append(_extract_class(node, source))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.extend(_extract_imports(node))
            # Check for dynamic imports
        elif isinstance(node, ast.Assign):
            for const in _extract_constants(node, source):
                constants.append(const)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            # Check for importlib usage
            if _is_dynamic_import(node.value):
                uncertainties.append(Uncertainty(
                    category="dynamic_import",
                    description=f"Dynamic import in {py_file.relative_to(root)}:{node.lineno}",
                    suggested_fallback="search",
                    priority="informational",
                ))

    # Check body for dynamic imports in any statement
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_dynamic_import(node):
            if not any(u.category == "dynamic_import" for u in uncertainties):
                uncertainties.append(Uncertainty(
                    category="dynamic_import",
                    description=f"Dynamic import in {py_file.relative_to(root)}:{node.lineno}",
                    suggested_fallback="search",
                    priority="informational",
                ))

    # Module docstring
    docstring = ast.get_docstring(tree)

    mod = ModuleRecord(
        path=py_file.relative_to(root),
        functions=functions,
        classes=classes,
        constants=constants,
        imports=imports,
        line_count=len(source.splitlines()),
        docstring=docstring,
    )

    return mod, [], uncertainties


def _extract_function(node: ast.FunctionDef | ast.AsyncFunctionDef, source: str) -> FunctionRecord:
    """Extract function info from AST node."""
    sig = _build_signature(node)
    body_hint = _build_body_hint(node, source)
    calls = _extract_calls(node)
    decorators = [_decorator_name(d) for d in node.decorator_list]
    docstring = ast.get_docstring(node)

    return FunctionRecord(
        name=node.name,
        signature=sig,
        body_hint=body_hint,
        calls=calls,
        decorators=decorators,
        docstring=docstring,
        line_number=node.lineno,
    )


def _extract_class(node: ast.ClassDef, source: str) -> ClassRecord:
    """Extract class info from AST node."""
    bases = [ast.unparse(b) for b in node.bases]
    methods = []
    method_details = []
    attributes: dict[str, str] = {}
    decorators = [_decorator_name(d) for d in node.decorator_list]

    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(item.name)
            method_details.append(_extract_function(item, source))
        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    try:
                        attributes[target.id] = ast.unparse(item.value)
                    except Exception:
                        attributes[target.id] = "..."

    is_abstract = any("ABC" in b or "Abstract" in b for b in bases)

    return ClassRecord(
        name=node.name,
        bases=bases,
        methods=methods,
        method_details=method_details,
        attributes=attributes,
        decorators=decorators,
        is_abstract=is_abstract,
    )


def _extract_constants(node: ast.Assign, source: str) -> list[ConstantRecord]:
    """Extract module-level constants (UPPER_CASE assignments)."""
    results = []
    for target in node.targets:
        if isinstance(target, ast.Name) and target.id.isupper():
            try:
                value = ast.unparse(node.value)
            except Exception:
                value = "..."
            results.append(ConstantRecord(name=target.id, value=value))
    return results


def _extract_imports(node: ast.Import | ast.ImportFrom) -> list[str]:
    """Extract import strings."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    elif isinstance(node, ast.ImportFrom) and node.module:
        return [node.module]
    return []


def _is_dynamic_import(node: ast.Call) -> bool:
    """Check if a call is importlib.import_module or __import__."""
    if isinstance(node.func, ast.Attribute):
        return node.func.attr == "import_module"
    if isinstance(node.func, ast.Name):
        return node.func.id == "__import__"
    return False


def _build_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Build function signature string."""
    args = ast.unparse(node.args) if node.args.args else ""
    ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    return f"{prefix}def {node.name}({args}){ret}"


def _build_body_hint(node: ast.FunctionDef | ast.AsyncFunctionDef, source: str) -> str:
    """Generate a body hint — full body for trivial functions, summary for complex."""
    body = node.body
    # Skip docstring
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]

    if not body:
        return "pass"

    # Trivial: single return/assignment
    if len(body) == 1:
        return ast.unparse(body[0])

    # Short: 2-3 lines
    if len(body) <= 3:
        return "; ".join(ast.unparse(s) for s in body)

    # Complex: summarize
    return f"[{len(body)} statements]"


def _extract_calls(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Extract function/method calls from body."""
    calls = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                calls.append(child.func.id)
            elif isinstance(child.func, ast.Attribute):
                calls.append(child.func.attr)
    return list(dict.fromkeys(calls))  # deduplicate preserving order


def _decorator_name(node: ast.expr) -> str:
    """Get decorator name as string."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return ast.unparse(node)
    elif isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ast.unparse(node)


def _detect_routes(root: Path) -> list[RouteRecord]:
    """Detect routes using the extract module."""
    try:
        from architecture_model.extract.route_detector import detect_routes, RouteInfo
        routes = detect_routes(root)
        return [
            RouteRecord(
                method=r.method,
                path=r.path,
                function_name=r.function_name,
                file=Path(r.file),
                docstring=r.docstring,
                is_authenticated=r.is_authenticated,
                framework=r.framework,
            )
            for r in routes
        ]
    except Exception:
        return []


def _detect_constraints(root: Path) -> list[ConstraintRecord]:
    """Detect constraints using the extract module."""
    try:
        from architecture_model.extract.constraint_detector import detect_constraints
        constraints = detect_constraints(root)
        return [
            ConstraintRecord(
                name=c.name,
                value=str(getattr(c, 'description', '')),
                source="config",
                constraint_type=str(getattr(c, 'constraint_type', '')),
            )
            for c in constraints
        ]
    except Exception:
        return []


def _find_test_files(py_files: list[Path], root: Path) -> list[TestFileRecord]:
    """Identify test files and their likely targets."""
    test_files = []
    for f in py_files:
        rel = f.relative_to(root)
        name = f.stem
        if name.startswith("test_") or name.endswith("_test") or "tests" in rel.parts:
            # Guess target module from test name
            target = name.removeprefix("test_").removesuffix("_test")
            test_files.append(TestFileRecord(path=rel, targets=[target] if target else []))
    return test_files


def _find_docs(root: Path) -> list[DocRecord]:
    """Find documentation files."""
    docs = []
    for pattern in ("*.md", "*.rst", "docs/**/*.md", "docs/**/*.rst"):
        for f in root.glob(pattern):
            if _is_excluded(f, root):
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                lines = content.splitlines()
                title = lines[0].lstrip("#").strip() if lines else ""
                docs.append(DocRecord(path=f.relative_to(root), title=title))
            except Exception:
                pass
    return docs
