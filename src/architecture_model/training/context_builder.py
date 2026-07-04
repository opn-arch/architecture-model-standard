"""
ContextBuilder: AST-guided smart context selection for architecture extraction.

Scans a repository using AST analysis to identify architecturally significant
code and produces structured context slices for multi-pass extraction.
"""

from __future__ import annotations

import ast
import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ContextSlices:
    """Structured code context for multi-pass extraction.

    Each slice is optimized for a specific extraction pass:
    - structure: directory tree, package structure, entry points
    - boundaries: API endpoints, external interfaces, actor touchpoints
    - behavior: tasks, event handlers, workflows, processing pipelines
    - relationships: import graph, dependency hotspots, cross-module calls
    - constraints: configs, decorators enforcing rules, settings
    """
    structure: str
    boundaries: str
    behavior: str
    relationships: str
    constraints: str

    def combined(self) -> str:
        """Return all slices combined into a single context string."""
        return "\n\n".join([
            self.structure, self.boundaries, self.behavior,
            self.relationships, self.constraints,
        ])


# Decorator patterns that signal architectural significance
_ARCH_DECORATORS = {
    # Task/worker patterns
    "shared_task", "task", "instrumented_task", "periodic_task",
    # API patterns
    "api_view", "action", "route", "endpoint",
    # Silo/deployment patterns
    "control_silo_endpoint", "region_silo_endpoint", "cell_silo_endpoint",
    # Django patterns
    "receiver", "csrf_exempt",
}

# Base classes that signal architectural boundaries
_ARCH_BASE_CLASSES = {
    # DRF
    "APIView", "ViewSet", "ModelViewSet", "GenericAPIView",
    # Django
    "Model", "View", "TemplateView",
    # Celery
    "Task",
    # Kafka/Stream
    "ProcessingStrategy", "ProcessingStrategyFactory", "StreamProcessor",
    # Custom service patterns
    "Service", "BaseService", "IntegrationInstallation",
}

# Config keys that reveal infrastructure
_INFRA_PATTERNS = [
    "DATABASES", "CACHES", "BROKER_URL", "CELERY_",
    "KAFKA_", "REDIS_", "ELASTICSEARCH_", "CLICKHOUSE_",
    "SENTRY_", "SECRET_KEY", "ALLOWED_HOSTS",
]


class ContextBuilder:
    """Builds architecturally-rich code context from a repository."""

    def __init__(self, repo_path: Path, max_chars: int = 15000) -> None:
        self.repo_path = Path(repo_path)
        self._max_chars = max_chars
        self._per_slice = max_chars // 5  # Budget per slice

    def build(self) -> ContextSlices:
        """Scan the repo and return structured context slices."""
        return ContextSlices(
            structure=self._build_structure_slice(),
            boundaries=self._build_boundaries_slice(),
            behavior=self._build_behavior_slice(),
            relationships=self._build_relationships_slice(),
            constraints=self._build_constraints_slice(),
        )

    def _build_structure_slice(self) -> str:
        """Directory tree + package structure + entry points."""
        parts = []

        # Directory tree (top-level packages with file counts)
        parts.append("# PACKAGE STRUCTURE")
        for item in sorted(self.repo_path.iterdir()):
            if item.name.startswith((".", "__pycache__")):
                continue
            if item.is_dir():
                py_count = len(list(item.rglob("*.py")))
                parts.append(f"  {item.name}/ ({py_count} .py files)")
            elif item.suffix == ".py":
                parts.append(f"  {item.name}")

        # Entry points
        for name in ["wsgi.py", "asgi.py", "app.py", "main.py", "__main__.py"]:
            path = self.repo_path / name
            if path.exists():
                parts.append(f"\n# ENTRY POINT: {name}")
                parts.append(path.read_text()[:self._per_slice // 4])

        # Top-level __init__.py (often reveals architecture)
        init_path = self.repo_path / "__init__.py"
        if init_path.exists():
            content = init_path.read_text()
            if len(content) > 50:  # Skip empty inits
                parts.append(f"\n# __init__.py (package API)")
                parts.append(content[:self._per_slice // 4])

        return self._truncate("\n".join(parts))

    def _build_boundaries_slice(self) -> str:
        """API endpoints, external interfaces, actor touchpoints."""
        parts = ["# EXTERNAL BOUNDARIES (APIs, interfaces, integration points)"]

        # Find API/endpoint files
        api_files = self._find_files_matching(
            patterns=["api", "endpoint", "views", "urls", "routes"],
            extensions=[".py"],
        )

        for f in api_files[:10]:
            tree = self._parse_ast(f)
            if tree is None:
                continue
            classes = self._extract_classes_with_bases(tree, _ARCH_BASE_CLASSES)
            if classes:
                rel = f.relative_to(self.repo_path)
                parts.append(f"\n# {rel}")
                for cls_name, bases, methods in classes:
                    parts.append(f"class {cls_name}({', '.join(bases)}):")
                    for m in methods[:5]:
                        parts.append(f"    def {m}")

        # Integration/webhook files
        integ_files = self._find_files_matching(
            patterns=["integration", "webhook", "client"],
            extensions=[".py"],
        )
        for f in integ_files[:5]:
            rel = f.relative_to(self.repo_path)
            content = f.read_text()[:400]
            if "class " in content or "def " in content:
                parts.append(f"\n# {rel}")
                parts.append(content)

        return self._truncate("\n".join(parts))

    def _build_behavior_slice(self) -> str:
        """Tasks, event handlers, workflows, processing pipelines."""
        parts = ["# BEHAVIORS (tasks, event handlers, workflows)"]

        # Find decorated functions (tasks, signals, etc.)
        for py_file in self._iter_py_files(max_files=100):
            tree = self._parse_ast(py_file)
            if tree is None:
                continue
            decorated = self._extract_decorated_functions(tree, _ARCH_DECORATORS)
            if decorated:
                rel = py_file.relative_to(self.repo_path)
                parts.append(f"\n# {rel}")
                for name, decorators, args in decorated:
                    dec_str = ", ".join(f"@{d}" for d in decorators)
                    parts.append(f"  {dec_str}")
                    parts.append(f"  def {name}({args})")

        # Task/consumer __init__.py files
        for dirname in ["tasks", "consumers", "workers", "handlers", "processors"]:
            init = self.repo_path / dirname / "__init__.py"
            if init.exists():
                content = init.read_text()[:600]
                if content.strip():
                    parts.append(f"\n# {dirname}/__init__.py")
                    parts.append(content)

        return self._truncate("\n".join(parts))

    def _build_relationships_slice(self) -> str:
        """Import graph hotspots and cross-module dependencies."""
        parts = ["# RELATIONSHIPS (import graph, dependencies)"]

        # Build import frequency map
        import_counts: Counter = Counter()
        all_imports: dict[str, list[str]] = {}  # file -> imports

        for py_file in self._iter_py_files(max_files=200):
            tree = self._parse_ast(py_file)
            if tree is None:
                continue
            imports = self._extract_imports(tree)
            rel = str(py_file.relative_to(self.repo_path))
            all_imports[rel] = imports
            for imp in imports:
                import_counts[imp] += 1

        # Most-imported modules (architectural hotspots)
        parts.append("\n# MOST-IMPORTED MODULES (dependency hotspots)")
        for module, count in import_counts.most_common(20):
            parts.append(f"  {module}: imported by {count} files")

        # Key file dependencies
        parts.append("\n# KEY FILE IMPORTS")
        important_files = sorted(all_imports.keys())[:30]
        for f in important_files:
            if all_imports[f]:
                parts.append(f"  {f} → {', '.join(all_imports[f][:5])}")

        return self._truncate("\n".join(parts))

    def _build_constraints_slice(self) -> str:
        """Configs, decorator patterns enforcing rules, settings."""
        parts = ["# CONSTRAINTS (configs, settings, architectural rules)"]

        # Settings/config files
        config_files = self._find_files_matching(
            patterns=["settings", "config", "conf"],
            extensions=[".py"],
        )
        for f in config_files[:5]:
            content = f.read_text()
            # Extract lines matching infrastructure patterns
            infra_lines = []
            for line in content.splitlines():
                if any(pat in line for pat in _INFRA_PATTERNS):
                    infra_lines.append(line.strip())
            if infra_lines:
                rel = f.relative_to(self.repo_path)
                parts.append(f"\n# {rel}")
                parts.append("\n".join(infra_lines[:20]))

        # Decorator usage summary (constraints/rules)
        constraint_decorators = {"login_required", "permission_required",
                                 "rate_limit", "silo_mode", "csrf_exempt",
                                 "transaction", "atomic"}
        for py_file in self._iter_py_files(max_files=100):
            tree = self._parse_ast(py_file)
            if tree is None:
                continue
            decorated = self._extract_decorated_functions(tree, constraint_decorators)
            if decorated:
                rel = py_file.relative_to(self.repo_path)
                parts.append(f"\n# {rel}")
                for name, decs, _ in decorated[:3]:
                    parts.append(f"  @{', @'.join(decs)} → {name}")

        return self._truncate("\n".join(parts))

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _iter_py_files(self, max_files: int = 100) -> list[Path]:
        """Iterate Python files in repo, prioritizing shallow files."""
        files = []
        for py in sorted(self.repo_path.rglob("*.py")):
            if "__pycache__" in str(py):
                continue
            files.append(py)
            if len(files) >= max_files:
                break
        return files

    def _find_files_matching(self, patterns: list[str], extensions: list[str]) -> list[Path]:
        """Find files whose path contains any of the patterns."""
        results = []
        for py in self.repo_path.rglob("*"):
            if py.suffix not in extensions:
                continue
            if "__pycache__" in str(py):
                continue
            name_lower = py.name.lower()
            path_lower = str(py.relative_to(self.repo_path)).lower()
            if any(p in name_lower or p in path_lower for p in patterns):
                results.append(py)
        return sorted(results)[:20]

    def _parse_ast(self, filepath: Path) -> ast.Module | None:
        """Parse a Python file's AST, returning None on failure."""
        try:
            source = filepath.read_text(encoding="utf-8")
            return ast.parse(source, filename=str(filepath))
        except (SyntaxError, UnicodeDecodeError, OSError):
            return None

    def _extract_classes_with_bases(
        self, tree: ast.Module, target_bases: set[str]
    ) -> list[tuple[str, list[str], list[str]]]:
        """Extract classes inheriting from target base classes."""
        results = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(base.attr)
            if any(b in target_bases for b in bases):
                methods = [
                    n.name for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not n.name.startswith("_")
                ]
                results.append((node.name, bases, methods))
        return results

    def _extract_decorated_functions(
        self, tree: ast.Module, target_decorators: set[str]
    ) -> list[tuple[str, list[str], str]]:
        """Extract functions with specific decorators."""
        results = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            matched_decorators = []
            for dec in node.decorator_list:
                dec_name = None
                if isinstance(dec, ast.Name):
                    dec_name = dec.id
                elif isinstance(dec, ast.Attribute):
                    dec_name = dec.attr
                elif isinstance(dec, ast.Call):
                    if isinstance(dec.func, ast.Name):
                        dec_name = dec.func.id
                    elif isinstance(dec.func, ast.Attribute):
                        dec_name = dec.func.attr
                if dec_name and dec_name in target_decorators:
                    matched_decorators.append(dec_name)
            if matched_decorators:
                args = ", ".join(a.arg for a in node.args.args[:4])
                results.append((node.name, matched_decorators, args))
        return results

    def _extract_imports(self, tree: ast.Module) -> list[str]:
        """Extract top-level module imports."""
        imports = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    imports.append(top)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    imports.append(top)
        return list(set(imports))

    def _truncate(self, text: str) -> str:
        """Truncate text to per-slice budget."""
        if len(text) <= self._per_slice:
            return text
        return text[:self._per_slice] + "\n# ... (truncated)"
