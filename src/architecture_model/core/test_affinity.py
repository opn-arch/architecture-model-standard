"""Test-affinity-based repository decomposition.

Groups source files into subsystems based on which test files import them.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from architecture_model.utils.discovery import (
    EXCLUDED_DIRS,
    discover_source_files as _discover_source_files,
    discover_test_files as _discover_test_files,
)


@dataclass
class Subsystem:
    """A subsystem identified from test file affinity analysis."""
    name: str                          # e.g., "ansi"
    source_files: list[Path]           # modules in this subsystem
    test_files: list[Path]             # tests that validate this subsystem
    dependencies: list[str] = field(default_factory=list)  # other subsystem names


def _is_excluded(path: Path, repo_path: Path) -> bool:
    """Check if a path should be excluded from scanning."""
    parts = path.relative_to(repo_path).parts
    for part in parts:
        if part in EXCLUDED_DIRS or part.endswith(".egg-info"):
            return True
    return False


def _extract_imports(file_path: Path) -> list[str]:
    """Extract all imported module names from a Python file using AST.

    Returns a flat list of top-level module/package names imported.
    E.g., 'from colorama.ansi import Fore' -> ['colorama.ansi']
          'import os' -> ['os']
          'from .winterm import WinTerm' -> ['.winterm']
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError):
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                prefix = "." * (node.level or 0)
                imports.append(f"{prefix}{node.module}")
            elif node.level:
                # from . import something → relative import with no module
                for alias in node.names:
                    imports.append(f"{'.' * node.level}{alias.name}")
    return imports


def _resolve_import_to_source(
    import_name: str,
    source_files: list[Path],
    repo_path: Path,
) -> Path | None:
    """Resolve an import string to a source file path.

    Handles:
    - Direct package imports: 'colorama.ansi' → colorama/ansi.py
    - Relative imports: '.winterm' → winterm.py (in same package)
    - Simple module names: 'ansi' → ansi.py
    - Sub-module imports: 'structlog._config' → src/structlog/_config.py
    """
    # Strip leading dots for relative imports
    stripped = import_name.lstrip(".")

    # Try matching against source file module paths
    for src_file in source_files:
        rel = src_file.relative_to(repo_path)
        # Convert path to dotted module: colorama/ansi.py → colorama.ansi
        # Also handle src-layout: src/structlog/_config.py → structlog._config
        if rel.name == "__init__.py":
            module_path = ".".join(rel.parent.parts)
        else:
            module_path = ".".join(rel.with_suffix("").parts)

        # Strip 'src.' prefix for src-layout repos
        module_path_no_src = module_path
        if module_path.startswith("src."):
            module_path_no_src = module_path[4:]

        # Exact match: 'colorama.ansi' == 'colorama.ansi'
        if module_path == stripped or module_path_no_src == stripped:
            return src_file

        # Suffix match: import 'colorama.ansi' matches module 'ansi'
        # (when import is fully qualified)
        parts = stripped.split(".")
        stem = rel.stem if rel.name != "__init__.py" else rel.parent.name
        if parts[-1] == stem and len(parts) > 1:
            # Verify the package part matches
            pkg_parts = parts[:-1]
            path_parts = list(rel.parent.parts) if rel.name != "__init__.py" else list(rel.parent.parent.parts)
            # Check if package parts align (at least the last part should match)
            if pkg_parts == list(rel.parent.parts)[:len(pkg_parts)]:
                return src_file
            # Also check without 'src' prefix in path
            path_no_src = [p for p in path_parts if p != "src"]
            if pkg_parts == path_no_src[:len(pkg_parts)]:
                return src_file

        # Simple name match: 'ansi' → ansi.py
        if stripped == stem and "." not in stripped:
            return src_file

    return None


def _subsystem_name_from_test(test_file: Path) -> str:
    """Derive subsystem name from test file name.

    test_alpha.py → 'alpha'
    ansi_test.py → 'ansi'
    tests_alpha.py → 'alpha'
    """
    name = test_file.stem
    if name.startswith("test_"):
        return name[5:]  # strip 'test_'
    elif name.startswith("tests_"):
        return name[6:]  # strip 'tests_'
    elif name.endswith("_test"):
        return name[:-5]  # strip '_test'
    return name


def test_affinity_decompose(repo_path: Path) -> list[Subsystem]:
    """Decompose a repository into subsystems based on test file affinity.

    Algorithm:
    1. Discover all test files (*_test.py, test_*.py)
    2. Discover all source files (non-test .py files)
    3. For each test file, AST-parse its imports to identify which source modules it tests
    4. Group source modules by their primary test file (each source → exactly one subsystem)
    5. Determine dependencies between subsystems via import analysis
    6. Return subsystems sorted topologically (leaves first)

    Source modules with no test → assigned to 'root' subsystem
    """
    test_files = _discover_test_files(repo_path)
    source_files = _discover_source_files(repo_path)

    if not source_files:
        return []

    # Step 3: For each test file, find which source files it imports
    # Build: test_name → set of source files it imports
    test_to_sources: dict[str, set[Path]] = {}
    test_name_to_file: dict[str, Path] = {}

    for test_file in test_files:
        sub_name = _subsystem_name_from_test(test_file)
        imports = _extract_imports(test_file)

        matched_sources: set[Path] = set()
        for imp in imports:
            src = _resolve_import_to_source(imp, source_files, repo_path)
            if src is not None:
                matched_sources.add(src)

        if matched_sources:
            if sub_name not in test_to_sources:
                test_to_sources[sub_name] = set()
                test_name_to_file[sub_name] = test_file
            test_to_sources[sub_name].update(matched_sources)
            # If multiple test files map to same subsystem name, keep track
            # (unusual but handle gracefully)

    # Step 4: Primary assignment — each source file belongs to exactly one subsystem
    # Priority: assign to the subsystem whose name best matches the source file stem
    # Then: assign to the test that imports it exclusively
    # Finally: if claimed by multiple, prefer the name-matched test

    # Build: source → list of subsystems that claim it
    source_claimants: dict[Path, list[str]] = defaultdict(list)
    for sub_name, sources in test_to_sources.items():
        for src in sources:
            source_claimants[src].append(sub_name)

    # Assign each source to exactly one subsystem
    source_assignment: dict[Path, str] = {}
    for src_file, claimants in source_claimants.items():
        if len(claimants) == 1:
            source_assignment[src_file] = claimants[0]
        else:
            # Multiple tests import this source — pick the best match by name
            stem = src_file.stem
            best_match = None
            for c in claimants:
                if c == stem:
                    best_match = c
                    break
            if best_match is None:
                # No exact name match — assign to first alphabetically for determinism
                best_match = sorted(claimants)[0]
            source_assignment[src_file] = best_match

    # Step: Build subsystem_sources and assign unclaimed to 'root'
    subsystem_sources: dict[str, set[Path]] = defaultdict(set)
    subsystem_tests: dict[str, set[Path]] = defaultdict(set)

    for src_file, sub_name in source_assignment.items():
        subsystem_sources[sub_name].add(src_file)

    # Record test files for each subsystem
    for sub_name, test_file in test_name_to_file.items():
        if sub_name in subsystem_sources:
            subsystem_tests[sub_name].add(test_file)

    # Also collect ALL test files for a subsystem (handle multiple test files
    # mapping to same name, e.g., via directory structures)
    for test_file in test_files:
        sub_name = _subsystem_name_from_test(test_file)
        if sub_name in subsystem_sources:
            subsystem_tests[sub_name].add(test_file)

    # Assign unclaimed source files to 'root'
    for src_file in source_files:
        if src_file not in source_assignment:
            subsystem_sources["root"].add(src_file)

    # Ensure 'root' exists even if empty
    if "root" not in subsystem_sources:
        subsystem_sources["root"] = set()

    # Build source→subsystem mapping for dependency detection
    source_to_subsystem: dict[Path, str] = {}
    for sub_name, sources in subsystem_sources.items():
        for src in sources:
            source_to_subsystem[src] = sub_name

    # Step 5: Determine dependencies between subsystems
    subsystem_deps: dict[str, set[str]] = defaultdict(set)
    for sub_name, sources in subsystem_sources.items():
        for src_file in sources:
            imports = _extract_imports(src_file)
            for imp in imports:
                target = _resolve_import_to_source(imp, source_files, repo_path)
                if target is not None:
                    target_sub = source_to_subsystem.get(target)
                    if target_sub and target_sub != sub_name:
                        subsystem_deps[sub_name].add(target_sub)

    # Step 6: Topological sort (leaves first = Kahn's algorithm)
    all_names = set(subsystem_sources.keys())
    # Remove empty root if it has no files
    if not subsystem_sources.get("root"):
        all_names.discard("root")

    # Topological sort: A depends on B means B comes before A
    # in_degree[A] = number of subsystems A depends on (that exist in graph)
    in_degree: dict[str, int] = {}
    for name in all_names:
        deps_in_graph = subsystem_deps.get(name, set()) & all_names
        in_degree[name] = len(deps_in_graph)

    # Kahn's algorithm
    queue = sorted([n for n in all_names if in_degree[n] == 0])
    sorted_names: list[str] = []
    while queue:
        node = queue.pop(0)
        sorted_names.append(node)
        # Find nodes that depend on this node and reduce their in-degree
        for sub_name in all_names:
            if node in (subsystem_deps.get(sub_name, set()) & all_names):
                in_degree[sub_name] -= 1
                if in_degree[sub_name] == 0:
                    queue.append(sub_name)
        queue.sort()  # deterministic ordering

    # Any remaining (cycles) — append in alphabetical order
    remaining = sorted(all_names - set(sorted_names))
    sorted_names.extend(remaining)

    # Build result
    result: list[Subsystem] = []
    for sub_name in sorted_names:
        sources = sorted(subsystem_sources.get(sub_name, set()))
        tests = sorted(subsystem_tests.get(sub_name, set()))
        deps = sorted(subsystem_deps.get(sub_name, set()) & all_names)
        result.append(Subsystem(
            name=sub_name,
            source_files=sources,
            test_files=tests,
            dependencies=deps,
        ))

    return result
