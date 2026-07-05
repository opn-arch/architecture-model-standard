"""
Code structure extraction via Python AST parsing.

Parses Python source code into a normalized StructuralGraph that captures
the architectural skeleton: classes, functions, imports, and module structure.
Used for round-trip evaluation (code → model → code → compare).
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field


@dataclass
class ClassInfo:
    """A class found in the source code."""
    name: str
    methods: list[str] = field(default_factory=list)
    bases: list[str] = field(default_factory=list)
    module: str = ""


@dataclass
class FunctionInfo:
    """A top-level function found in the source code."""
    name: str
    args: list[str] = field(default_factory=list)
    module: str = ""


@dataclass
class ImportEdge:
    """An import relationship between modules."""
    from_module: str
    to_module: str


@dataclass
class StructuralGraph:
    """Normalized structural representation of Python code."""
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    imports: list[ImportEdge] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)

    @property
    def class_names(self) -> set[str]:
        return {c.name for c in self.classes}

    @property
    def method_names(self) -> set[str]:
        methods = set()
        for c in self.classes:
            for m in c.methods:
                methods.add(f"{c.name}.{m}")
        return methods

    @property
    def function_names(self) -> set[str]:
        return {f.name for f in self.functions}

    @property
    def import_modules(self) -> set[str]:
        return {e.to_module for e in self.imports}


def _is_kept_method(name: str) -> bool:
    """Return True if method should be kept in the structural graph.

    Keeps __init__ and public methods. Skips other dunders and private methods.
    """
    if name == "__init__":
        return True
    if name.startswith("_"):
        return False
    return True


def parse_code_structure(code: str, module_name: str = "module") -> StructuralGraph:
    """Parse Python source into a StructuralGraph via AST.

    Handles:
    - Class definitions (with methods, base classes)
    - Top-level functions (with argument names)
    - Import statements (import X, from X import Y)

    Gracefully handles syntax errors by returning partial results.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return StructuralGraph()

    classes: list[ClassInfo] = []
    functions: list[FunctionInfo] = []
    imports: list[ImportEdge] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            methods = [
                n.name
                for n in ast.iter_child_nodes(node)
                if isinstance(n, ast.FunctionDef) and _is_kept_method(n.name)
            ]
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(ast.unparse(base))
            classes.append(ClassInfo(
                name=node.name,
                methods=methods,
                bases=bases,
                module=module_name,
            ))

        elif isinstance(node, ast.FunctionDef):
            args = [
                a.arg for a in node.args.args
                if a.arg != "self"
            ]
            functions.append(FunctionInfo(
                name=node.name,
                args=args,
                module=module_name,
            ))

        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(ImportEdge(
                    from_module=module_name,
                    to_module=alias.name,
                ))

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(ImportEdge(
                    from_module=module_name,
                    to_module=node.module,
                ))

    return StructuralGraph(
        classes=classes,
        functions=functions,
        imports=imports,
    )


# Pattern matching lines like "# src/auth/service.py" or "# app.py"
_FILE_MARKER_RE = re.compile(r"^#\s+(\S+\.py)\s*$")


def _path_to_module_name(path: str) -> str:
    """Convert a file path to a dotted module name.

    Examples:
        src/auth/service.py → auth.service
        src/mypackage/utils/helpers.py → mypackage.utils.helpers
        app.py → app
    """
    # Remove .py extension
    path = re.sub(r"\.py$", "", path)
    # Split into parts
    parts = path.replace("\\", "/").split("/")
    # Strip leading 'src' directory if present
    if parts and parts[0] == "src":
        parts = parts[1:]
    # Remove __init__ from module path
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else "module"


def parse_multi_file_code(code: str) -> StructuralGraph:
    """Parse code that contains multiple files separated by '# path/to/file.py' markers.

    The format is what _read_code_context() in pipeline.py produces:
    # path/to/module.py
    <code>

    # path/to/other.py
    <code>
    """
    if not code.strip():
        return StructuralGraph()

    # Split into file chunks
    chunks: list[tuple[str, str]] = []  # (module_name, code)
    lines = code.split("\n")

    current_module: str | None = None
    current_lines: list[str] = []

    for line in lines:
        match = _FILE_MARKER_RE.match(line)
        if match:
            # Save previous chunk
            if current_module is not None:
                chunks.append((current_module, "\n".join(current_lines)))
            current_module = _path_to_module_name(match.group(1))
            current_lines = []
        else:
            current_lines.append(line)

    # Save last chunk
    if current_module is not None:
        chunks.append((current_module, "\n".join(current_lines)))
    elif current_lines:
        # No markers found — treat as single module
        chunks.append(("module", "\n".join(current_lines)))

    # Parse each chunk and merge
    merged = StructuralGraph()
    modules: list[str] = []

    for module_name, chunk_code in chunks:
        modules.append(module_name)
        graph = parse_code_structure(chunk_code, module_name=module_name)
        merged.classes.extend(graph.classes)
        merged.functions.extend(graph.functions)
        merged.imports.extend(graph.imports)

    merged.modules = modules
    return merged
