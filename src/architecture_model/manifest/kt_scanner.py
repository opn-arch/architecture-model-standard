"""Tree-sitter based Kotlin scanner producing SourceGraph output.

Optional dependency: requires tree-sitter and tree-sitter-kotlin.
Install with: pip install architecture-model-standard[jvm]
"""
from __future__ import annotations

from pathlib import Path

from architecture_model.manifest.protocol import (
    DependencyEdge, ExportedSymbol, SourceGraph, SourceUnit,
)

# Lazy-loaded tree-sitter language
_KOTLIN_LANGUAGE = None

# Directories to exclude from scanning
EXCLUDE_DIRS = frozenset({
    "build", ".gradle", ".idea", "generated", "ksp", "kspCaches",
    "__pycache__", ".git", "node_modules",
})


def _get_kotlin_language():
    """Load tree-sitter Kotlin language (cached)."""
    global _KOTLIN_LANGUAGE
    if _KOTLIN_LANGUAGE is None:
        try:
            import tree_sitter_kotlin as tskotlin
            from tree_sitter import Language
            _KOTLIN_LANGUAGE = Language(tskotlin.language())
        except ImportError:
            raise ImportError(
                "tree-sitter-kotlin not installed. "
                "Install with: pip install tree-sitter tree-sitter-kotlin"
            )
    return _KOTLIN_LANGUAGE


def scan_kotlin(root: Path) -> SourceGraph:
    """Scan Kotlin files under root, produce SourceGraph.

    Extracts:
    - Class/data class/object declarations (public only)
    - Top-level functions (public only, skips internal/private)
    - Public methods inside classes
    - Import statements → dependency edges
    - Package declarations → for import resolution
    """
    from tree_sitter import Parser

    language = _get_kotlin_language()
    parser = Parser(language)

    units: list[SourceUnit] = []
    edges: list[DependencyEdge] = []
    package_to_file: dict[str, str] = {}  # "com.example.models" → "models/User.kt"

    # Collect .kt files, excluding build dirs
    kt_files = sorted(
        f for f in root.rglob("*.kt")
        if not any(part in EXCLUDE_DIRS for part in f.parts)
    )

    # First pass: index packages
    for filepath in kt_files:
        rel = str(filepath.relative_to(root))
        try:
            source = filepath.read_bytes()
        except Exception:
            continue
        tree = parser.parse(source)
        pkg = _extract_package(tree.root_node, source)
        if pkg:
            package_to_file[pkg] = rel

    # Second pass: extract symbols and imports
    for filepath in kt_files:
        rel = str(filepath.relative_to(root))
        try:
            source = filepath.read_bytes()
        except Exception:
            continue

        tree = parser.parse(source)
        exports = _extract_exports(tree.root_node, source)
        imports = _extract_imports(tree.root_node, source)

        units.append(SourceUnit(
            file=rel,
            has_content=bool(exports),
            exports=exports,
            language="kotlin",
        ))

        # Resolve imports to file edges
        for imp in imports:
            target = _resolve_import(imp, package_to_file, rel)
            if target and target != rel:
                edges.append(DependencyEdge(
                    source=rel,
                    target=target,
                    symbols=[imp.rsplit(".", 1)[-1]],
                ))

    return SourceGraph(units=units, edges=edges, root=str(root), language="kotlin")


# ---- AST helpers ----


def _extract_package(node, source: bytes) -> str:
    """Extract package declaration (e.g., 'com.example.models')."""
    for child in node.children:
        if child.type == "package_header":
            for c in child.children:
                if c.type == "qualified_identifier":
                    return source[c.start_byte:c.end_byte].decode()
    return ""


def _extract_exports(node, source: bytes) -> list[ExportedSymbol]:
    """Extract public classes, objects, and top-level functions."""
    exports: list[ExportedSymbol] = []
    for child in node.children:
        if child.type == "class_declaration":
            _extract_class(child, source, exports)
        elif child.type == "function_declaration":
            _extract_function(child, source, exports)
        elif child.type == "object_declaration":
            _extract_object(child, source, exports)
    return exports


def _has_visibility(node, source: bytes, *keywords: str) -> bool:
    """Check if node has given visibility modifier(s)."""
    for child in node.children:
        if child.type == "modifiers":
            for mod in child.children:
                if mod.type == "visibility_modifier":
                    text = source[mod.start_byte:mod.end_byte].decode().strip()
                    if text in keywords:
                        return True
    return False


def _extract_class(node, source: bytes, exports: list[ExportedSymbol]):
    """Extract class name and its public methods."""
    if _has_visibility(node, source, "private", "internal"):
        return

    name = _get_identifier(node, source)
    if not name:
        return

    # Constructor signature
    sig = ""
    for child in node.children:
        if child.type == "primary_constructor":
            sig = source[child.start_byte:child.end_byte].decode()
            break

    exports.append(ExportedSymbol(name=name, kind="class", signature=sig))

    # Extract public methods from class body
    for child in node.children:
        if child.type == "class_body":
            for member in child.children:
                if member.type == "function_declaration":
                    _extract_function(member, source, exports)


def _extract_function(node, source: bytes, exports: list[ExportedSymbol]):
    """Extract function if public."""
    if _has_visibility(node, source, "private", "internal"):
        return

    name = _get_identifier(node, source)
    if not name:
        return

    sig = ""
    for child in node.children:
        if child.type == "function_value_parameters":
            sig = source[child.start_byte:child.end_byte].decode()
            break

    exports.append(ExportedSymbol(name=name, kind="function", signature=sig))


def _extract_object(node, source: bytes, exports: list[ExportedSymbol]):
    """Extract Kotlin object declaration."""
    if _has_visibility(node, source, "private", "internal"):
        return
    name = _get_identifier(node, source)
    if name:
        exports.append(ExportedSymbol(name=name, kind="class", signature="object"))


def _get_identifier(node, source: bytes) -> str | None:
    """Get the first identifier child (the declaration name)."""
    for child in node.children:
        if child.type == "identifier":
            return source[child.start_byte:child.end_byte].decode()
    return None


def _extract_imports(node, source: bytes) -> list[str]:
    """Extract import statements as qualified names."""
    imports: list[str] = []
    for child in node.children:
        if child.type == "import":
            for c in child.children:
                if c.type == "qualified_identifier":
                    imports.append(source[c.start_byte:c.end_byte].decode())
    return imports


def _resolve_import(
    imp: str, package_map: dict[str, str], current_file: str
) -> str | None:
    """Resolve an import to a file path using the package index.

    Tries exact match first, then parent package (for class imports).
    """
    if imp in package_map:
        return package_map[imp]
    # import com.example.models.User → try package com.example.models
    parent = imp.rsplit(".", 1)[0] if "." in imp else ""
    if parent and parent in package_map:
        return package_map[parent]
    return None


# ---- Java scanner ----

_JAVA_LANGUAGE = None


def _get_java_language():
    """Load tree-sitter Java language (cached)."""
    global _JAVA_LANGUAGE
    if _JAVA_LANGUAGE is None:
        try:
            import tree_sitter_java as tsjava
            from tree_sitter import Language
            _JAVA_LANGUAGE = Language(tsjava.language())
        except ImportError:
            raise ImportError(
                "tree-sitter-java not installed. "
                "Install with: pip install tree-sitter tree-sitter-java"
            )
    return _JAVA_LANGUAGE


def scan_java(root: Path) -> SourceGraph:
    """Scan Java files under root, produce SourceGraph.

    Extracts public classes and their public methods.
    """
    from tree_sitter import Parser

    language = _get_java_language()
    parser = Parser(language)

    units: list[SourceUnit] = []
    edges: list[DependencyEdge] = []
    package_to_file: dict[str, str] = {}

    java_files = sorted(
        f for f in root.rglob("*.java")
        if not any(part in EXCLUDE_DIRS for part in f.parts)
    )

    # First pass: index packages
    for filepath in java_files:
        rel = str(filepath.relative_to(root))
        try:
            source = filepath.read_bytes()
        except Exception:
            continue
        tree = parser.parse(source)
        pkg = _java_extract_package(tree.root_node, source)
        if pkg:
            package_to_file[pkg] = rel

    # Second pass: extract
    for filepath in java_files:
        rel = str(filepath.relative_to(root))
        try:
            source = filepath.read_bytes()
        except Exception:
            continue

        tree = parser.parse(source)
        exports = _java_extract_exports(tree.root_node, source)
        imports = _java_extract_imports(tree.root_node, source)

        units.append(SourceUnit(
            file=rel,
            has_content=bool(exports),
            exports=exports,
            language="java",
        ))

        for imp in imports:
            target = _resolve_import(imp, package_to_file, rel)
            if target and target != rel:
                edges.append(DependencyEdge(
                    source=rel,
                    target=target,
                    symbols=[imp.rsplit(".", 1)[-1]],
                ))

    return SourceGraph(units=units, edges=edges, root=str(root), language="java")


def _java_extract_package(node, source: bytes) -> str:
    """Extract Java package declaration."""
    for child in node.children:
        if child.type == "package_declaration":
            for c in child.children:
                if c.type in ("scoped_identifier", "identifier"):
                    return source[c.start_byte:c.end_byte].decode()
    return ""


def _java_extract_exports(node, source: bytes) -> list[ExportedSymbol]:
    """Extract public classes and methods from Java AST."""
    exports: list[ExportedSymbol] = []
    for child in node.children:
        if child.type == "class_declaration":
            _java_extract_class(child, source, exports)
    return exports


def _java_has_modifier(node, source: bytes, keyword: str) -> bool:
    """Check if Java declaration has a specific modifier."""
    for child in node.children:
        if child.type == "modifiers":
            text = source[child.start_byte:child.end_byte].decode()
            if keyword in text:
                return True
    return False


def _java_extract_class(node, source: bytes, exports: list[ExportedSymbol]):
    """Extract Java class if public (or package-private)."""
    if _java_has_modifier(node, source, "private"):
        return

    name = _get_identifier(node, source)
    if not name:
        return

    exports.append(ExportedSymbol(name=name, kind="class", signature=""))

    # Extract public methods
    for child in node.children:
        if child.type == "class_body":
            for member in child.children:
                if member.type == "method_declaration":
                    if not _java_has_modifier(member, source, "private"):
                        mname = _get_identifier(member, source)
                        if mname:
                            sig = ""
                            for c in member.children:
                                if c.type == "formal_parameters":
                                    sig = source[c.start_byte:c.end_byte].decode()
                                    break
                            exports.append(ExportedSymbol(
                                name=mname, kind="function", signature=sig,
                            ))


def _java_extract_imports(node, source: bytes) -> list[str]:
    """Extract Java import statements."""
    imports: list[str] = []
    for child in node.children:
        if child.type == "import_declaration":
            for c in child.children:
                if c.type in ("scoped_identifier", "identifier"):
                    imports.append(source[c.start_byte:c.end_byte].decode())
                    break
    return imports
