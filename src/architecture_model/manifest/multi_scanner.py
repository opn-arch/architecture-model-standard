"""Multi-language scanner that merges SourceGraphs from all detected languages.

Detects languages by file extension, runs appropriate scanners,
and merges results into a single unified SourceGraph.
"""
from __future__ import annotations

from pathlib import Path

from architecture_model.manifest.protocol import (
    DependencyEdge, SourceGraph, SourceUnit,
)


def scan_all_languages(root: Path) -> SourceGraph:
    """Scan repository for all supported languages, return merged SourceGraph.

    Language detection by file extension:
    - .py  → Python (via generate_manifest → SourceGraph.from_manifest)
    - .kt  → Kotlin (via scan_kotlin, tree-sitter)
    - .java → Java (via scan_java, tree-sitter)
    - .ts/.tsx/.js/.jsx → TypeScript (via regex fallback)

    Cross-language edges are NOT detected (would require API contract analysis).
    """
    graphs: list[SourceGraph] = []

    # Python
    py_files = list(root.rglob("*.py"))
    if py_files:
        try:
            from architecture_model.manifest.generator import generate_manifest
            manifest = generate_manifest(root)
            graphs.append(SourceGraph.from_manifest(manifest))
        except Exception:
            pass  # manifest generation can fail on non-Python repos

    # Kotlin
    kt_files = [
        f for f in root.rglob("*.kt")
        if not any(part in _JVM_EXCLUDE for part in f.parts)
    ]
    if kt_files:
        try:
            from architecture_model.manifest.kt_scanner import scan_kotlin
            kt_root = _find_jvm_source_root(root, kt_files)
            graphs.append(scan_kotlin(kt_root))
        except ImportError:
            pass  # tree-sitter not installed

    # Java (only if .java files outside build dirs)
    java_files = [
        f for f in root.rglob("*.java")
        if not any(part in _JVM_EXCLUDE for part in f.parts)
    ]
    if java_files:
        try:
            from architecture_model.manifest.kt_scanner import scan_java
            java_root = _find_jvm_source_root(root, java_files)
            graphs.append(scan_java(java_root))
        except ImportError:
            pass

    # TypeScript (regex fallback)
    ts_files = list(root.rglob("*.ts")) + list(root.rglob("*.tsx"))
    ts_files = [f for f in ts_files if "node_modules" not in f.parts]
    if ts_files:
        try:
            from architecture_model.manifest.ts_scanner import scan_typescript_fallback
            ts_data = scan_typescript_fallback(root)
            graphs.append(SourceGraph.from_json(ts_data))
        except Exception:
            pass

    return _merge_graphs(graphs)


_JVM_EXCLUDE = frozenset({
    "build", ".gradle", ".idea", "generated", "ksp", "kspCaches",
    "__pycache__", ".git", "node_modules",
})


def _find_jvm_source_root(repo_root: Path, source_files: list[Path]) -> Path:
    """Find the best source root for JVM files.

    For Android projects, this is typically app/src/main/.
    Falls back to the common parent of all source files.
    """
    # Check Android-style layouts in subdirectories
    for child in repo_root.iterdir():
        if child.is_dir():
            main = child / "app" / "src" / "main"
            if main.exists():
                return main

    # Standard Maven/Gradle layouts
    for candidate in [
        repo_root / "app" / "src" / "main",
        repo_root / "src" / "main" / "kotlin",
        repo_root / "src" / "main" / "java",
        repo_root / "src" / "main",
    ]:
        if candidate.exists():
            return candidate

    # Fall back to common parent of source files
    if source_files:
        parents = [f.parent for f in source_files]
        # Find the shortest common prefix
        common = parents[0]
        for p in parents[1:]:
            while not str(p).startswith(str(common)):
                common = common.parent
        return common

    return repo_root


def _merge_graphs(graphs: list[SourceGraph]) -> SourceGraph:
    """Merge multiple SourceGraphs into one."""
    if not graphs:
        return SourceGraph()
    if len(graphs) == 1:
        return graphs[0]

    all_units: list[SourceUnit] = []
    all_edges: list[DependencyEdge] = []
    languages: set[str] = set()

    for g in graphs:
        all_units.extend(g.units)
        all_edges.extend(g.edges)
        if g.language:
            languages.add(g.language)

    lang = "+".join(sorted(languages)) if len(languages) > 1 else (
        languages.pop() if languages else ""
    )

    return SourceGraph(
        units=all_units,
        edges=all_edges,
        root=graphs[0].root,
        language=lang,
    )
