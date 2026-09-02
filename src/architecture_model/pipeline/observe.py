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
            # Scoped mode: only scan the specified files (may be relative to repo_path)
            py_files = []
            for f in ctx.scope_files:
                abs_f = f if f.is_absolute() else ctx.repo_path / f
                if abs_f.suffix == ".py" and abs_f.exists():
                    py_files.append(abs_f)
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
                diagnostics.append(
                    Diagnostic(
                        severity="warning",
                        code="parse-failed",
                        message=f"Parse failed: {py_file.relative_to(ctx.repo_path)}: {e}",
                    )
                )

        scope_paths = _scope_paths(ctx)

        # Routes
        routes = _detect_routes(ctx.repo_path)
        if scope_paths is not None:
            routes = [route for route in routes if _in_scope(route.file, scope_paths, ctx.repo_path)]

        # Constraints
        constraints = _detect_constraints(ctx.repo_path)
        if scope_paths is not None:
            constraints = [
                constraint for constraint in constraints
                if _in_scope(Path(constraint.source), scope_paths, ctx.repo_path)
            ]

        # Test files
        test_files = _find_test_files(py_files, ctx.repo_path)

        # In scoped mode, also discover test files from common test directories
        # that target the scoped source files (flat test layouts like tests/test_ansi.py)
        if ctx.scope_files and not test_files:
            test_files = _find_tests_for_scope(ctx.repo_path, py_files)

        # Docs
        docs = _find_docs(ctx.repo_path)
        if scope_paths is not None:
            docs = [doc for doc in docs if _in_scope(doc.path, scope_paths, ctx.repo_path)]

        # Resolve import edges from module imports
        edges = _resolve_import_edges(modules)

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

        total_symbols = sum(len(m.functions) + len(m.classes) + len(m.constants) for m in modules)
        symbol_density = (total_symbols / parsed) if parsed > 0 else 0.0

        # Code quality scoring — per-module with component_scores
        code_quality_avg = 0.0
        module_scores: dict[str, QualityMetrics] = {}
        try:
            from architecture_model.quality.code_review import analyze_source
            for mod in modules:
                try:
                    mod_path = mod.path if mod.path.is_absolute() else ctx.repo_path / mod.path
                    if mod_path.exists():
                        analysis = analyze_source(mod_path.read_text(), filename=str(mod_path))
                        mod.quality_score = analysis.score
                        fn_count = max(len(analysis.functions), 1)
                        module_scores[str(mod.path)] = QualityMetrics(
                            score=analysis.score,
                            sub_scores={
                                "complexity_avg": sum(f.complexity for f in analysis.functions) / fn_count,
                                "docstring_coverage": sum(1 for f in analysis.functions if f.has_docstring) / fn_count * 100,
                                "type_hint_coverage": sum(1 for f in analysis.functions if f.has_type_hints) / fn_count * 100,
                                "issue_count": float(len(analysis.issues)),
                            },
                        )
                    else:
                        import logging as _logging
                        _logging.getLogger(__name__).debug(
                            "quality: path not found: %s (resolved: %s)", mod.path, mod_path,
                        )
                except Exception as exc:
                    import logging as _logging
                    _logging.getLogger(__name__).debug(
                        "quality: analyze_source failed for %s: %s", mod.path, exc,
                    )
            if module_scores:
                code_quality_avg = sum(qm.score for qm in module_scores.values()) / len(module_scores)
        except ImportError:
            pass

        quality = QualityMetrics(
            score=int(parse_rate),
            sub_scores={
                "parse_success_rate": parse_rate,
                "symbol_density": symbol_density,
                "file_count": float(total_files),
                "code_quality_avg": code_quality_avg,
            },
            thresholds={"parse_success_rate": 90.0},
            component_scores=module_scores,
        )

        duration_ms = int((time.time() - start) * 1000)

        code_quality_note = f" Code quality: {code_quality_avg:.0f}/100 avg." if code_quality_avg > 0 else ""

        return StageResult(
            output=inventory,
            quality=quality,
            diagnostics=diagnostics,
            uncertainties=uncertainties,
            input_hash=str(len(py_files)),
            duration_ms=duration_ms,
            version="1.0",
            summary=f"Observed {len(modules)} modules with {len(edges)} import edges from {total_files} files.{code_quality_note}",
        )


def _is_excluded(path: Path, root: Path) -> bool:
    """Exclude common non-source directories and gitignored paths."""
    rel = path.relative_to(root)
    parts = rel.parts
    excluded = {
        ".git",
        "__pycache__",
        "node_modules",
        ".tox",
        "dist",
        "build",
        ".eggs",
        "results",
        ".architecture-archive",
        ".worktrees",
        "projects",
    }
    if excluded.intersection(parts):
        return True
    # Exclude any venv-like directories (venv, .venv, .venv-1, etc.)
    for part in parts:
        if part == "venv" or part.startswith(".venv"):
            return True
    # Respect .gitignore top-level directory entries
    gitignore = root / ".gitignore"
    if gitignore.exists():
        try:
            _load_gitignore_dirs(root)
            if _gitignore_dirs_cache.get(root) and _gitignore_dirs_cache[root].intersection(parts):
                return True
        except Exception:
            pass
    return False


def _scope_paths(ctx: PipelineContext) -> set[Path] | None:
    """Return normalized scoped and explicitly shared file paths."""
    if not ctx.scope_files:
        return None
    shared = ctx.config.get("shared_scope_files", [])
    return {
        (path if path.is_absolute() else ctx.repo_path / path).resolve()
        for path in [*ctx.scope_files, *(Path(item) for item in shared)]
    }


def _in_scope(path: Path, scope_paths: set[Path], root: Path) -> bool:
    candidate = path if path.is_absolute() else root / path
    return candidate.resolve() in scope_paths


_gitignore_dirs_cache: dict[Path, set[str]] = {}


def _load_gitignore_dirs(root: Path) -> None:
    """Parse .gitignore for directory exclusions (cached)."""
    if root in _gitignore_dirs_cache:
        return
    dirs: set[str] = set()
    try:
        for line in (root / ".gitignore").read_text().splitlines():
            line = line.strip().rstrip("/")
            if line and not line.startswith("#") and "/" not in line:
                candidate = root / line
                if candidate.is_dir():
                    dirs.add(line)
    except Exception:
        pass
    _gitignore_dirs_cache[root] = dirs


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
                uncertainties.append(
                    Uncertainty(
                        category="dynamic_import",
                        description=f"Dynamic import in {py_file.relative_to(root)}:{node.lineno}",
                        suggested_fallback="search",
                        priority="informational",
                    )
                )

    # Check body for dynamic imports in any statement
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_dynamic_import(node):
            if not any(u.category == "dynamic_import" for u in uncertainties):
                uncertainties.append(
                    Uncertainty(
                        category="dynamic_import",
                        description=f"Dynamic import in {py_file.relative_to(root)}:{node.lineno}",
                        suggested_fallback="search",
                        priority="informational",
                    )
                )

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


def _resolve_import_edges(modules: list[ModuleRecord]) -> list[ImportEdge]:
    """Resolve import strings into ImportEdge objects linking in-project modules.

    Builds a mapping of qualified module names to file paths, then checks each
    module's imports list against the map to produce edges.
    """
    # Build qualified name → Path mapping
    # e.g. "architecture_model.core.parser" → Path("src/architecture_model/core/parser.py")
    name_to_path: dict[str, Path] = {}
    for mod in modules:
        # Convert path to qualified name: src/foo/bar.py → foo.bar
        parts = list(mod.path.with_suffix("").parts)
        # Try various prefixes (handle src-layout)
        for start in range(len(parts)):
            qualified = ".".join(parts[start:])
            name_to_path[qualified] = mod.path
        # Also register __init__ as the package name
        if parts and parts[-1] == "__init__":
            pkg_parts = parts[:-1]
            for start in range(len(pkg_parts)):
                qualified = ".".join(pkg_parts[start:])
                name_to_path[qualified] = mod.path

    edges: list[ImportEdge] = []
    seen: set[tuple[str, str]] = set()  # (source, target) dedup

    for mod in modules:
        source_path = mod.path
        for imp in mod.imports:
            # Try exact match and prefix matches
            target_path = _resolve_import(imp, name_to_path)
            if target_path and target_path != source_path:
                key = (str(source_path), str(target_path))
                if key not in seen:
                    seen.add(key)
                    # Extract symbol from "from X import Y" style
                    symbols = []
                    if "." in imp:
                        symbols = [imp.rsplit(".", 1)[-1]]
                    edges.append(
                        ImportEdge(
                            source=source_path,
                            target=target_path,
                            symbols=symbols,
                        )
                    )

    return edges


def _resolve_import(imp: str, name_to_path: dict[str, Path]) -> Path | None:
    """Resolve an import string to a project module path."""
    # Direct match
    if imp in name_to_path:
        return name_to_path[imp]
    # Try as package (from X import Y — X might be a package)
    parts = imp.split(".")
    for i in range(len(parts), 0, -1):
        prefix = ".".join(parts[:i])
        if prefix in name_to_path:
            return name_to_path[prefix]
    return None


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
                value=str(getattr(c, "description", "")),
                source="config",
                constraint_type=str(getattr(c, "constraint_type", "")),
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


def _find_tests_for_scope(
    root: Path, scope_files: list[Path],
) -> list[TestFileRecord]:
    """Discover test files targeting scoped source stems in flat test layouts.

    Scans common test directories (tests/, test/) for files matching
    test_<stem>.py or <stem>_test.py where <stem> is a scoped source file.
    """
    results: list[TestFileRecord] = []
    scope_modules = {
        ".".join(path.relative_to(root).with_suffix("").parts)
        for path in scope_files if path.suffix == ".py"
    }
    for test_dir_name in ("tests", "test"):
        test_dir = root / test_dir_name
        if not test_dir.is_dir():
            continue
        for tf in test_dir.rglob("*.py"):
            name = tf.stem
            target = name.removeprefix("test_").removesuffix("_test")
            imports_scope = bool(_test_imports(tf) & scope_modules)
            path_context = any(
                tuple(tf.relative_to(test_dir).parts[:-1]) == tuple(module.split(".")[:-1])
                for module in scope_modules
            )
            stem_matches = any(target == module.rsplit(".", 1)[-1] for module in scope_modules)
            if target and target != name and stem_matches and (imports_scope or path_context):
                rel = tf.relative_to(root)
                results.append(TestFileRecord(path=rel, targets=[target]))
    return results


def _test_imports(path: Path) -> set[str]:
    """Return concrete module names imported by a Python test file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return set()
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
            imports.update(f"{node.module}.{alias.name}" for alias in node.names)
    return imports


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
