"""Multi-signal module grouping for architecture model generation.

Groups modules into logical components using three signals:
1. Subdirectory affinity — files in the same subdirectory
2. Name-prefix affinity — underscore-prefixed files in the same directory
3. Import affinity — files with high mutual import counts

Trivial files (__init__.py with no code, __version__.py, etc.) are filtered out.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from architecture_model.manifest.types import InterfaceEdge, ModuleInfo, Manifest
from architecture_model.manifest.protocol import DependencyEdge, SourceGraph, SourceUnit
from architecture_model.core.types import Component


@dataclass
class ModuleGroup:
    """A logical group of related modules."""

    name: str
    modules: list[str]  # file paths
    primary_file: str  # largest file by line count

    def __repr__(self) -> str:
        return f"ModuleGroup({self.name!r}, {len(self.modules)} files)"


# ---------------------------------------------------------------------------
# Trivial-file filter
# ---------------------------------------------------------------------------

_TRIVIAL_NAMES = {"__version__", "__main__"}


def _is_trivial(mod: ModuleInfo) -> bool:
    """Check if a module is trivial (should be excluded from grouping)."""
    stem = PurePosixPath(mod.file).stem

    # __version__.py, __main__.py — always trivial
    if stem in _TRIVIAL_NAMES:
        return True

    # __init__.py with <=5 lines and no functions/classes
    if stem == "__init__" and mod.line_count <= 5 and not mod.functions and not mod.classes:
        return True

    # Modules with 0 functions and 0 classes
    if not mod.functions and not mod.classes:
        return True

    # Vendor directories — third-party code, not project architecture
    parts = PurePosixPath(mod.file).parts
    if "vendor" in parts or "_vendor" in parts or "vendored" in parts:
        return True

    return False


# ---------------------------------------------------------------------------
# Grouping
# ---------------------------------------------------------------------------


def group_modules(
    modules: list[ModuleInfo],
    interfaces: list[InterfaceEdge],
    *,
    target_groups: int | None = None,
    min_group_size: int = 1,
) -> list[ModuleGroup]:
    """Group modules into logical components using multi-signal affinity.

    Args:
        modules: List of modules to group.
        interfaces: Import edges between modules.
        target_groups: Desired number of groups. None = auto-calculate.
        min_group_size: Minimum modules per group (after merging).

    Returns:
        List of ModuleGroup objects.
    """
    # Step 0: Filter trivial modules
    kept = [m for m in modules if not _is_trivial(m)]
    if not kept:
        return []

    # Build lookup: file -> ModuleInfo
    mod_by_file: dict[str, ModuleInfo] = {m.file: m for m in kept}

    # Step 1: Subdirectory grouping (always group files in same subdir)
    dir_groups: dict[str, list[str]] = defaultdict(list)
    for m in kept:
        parent = str(PurePosixPath(m.file).parent)
        dir_groups[parent].append(m.file)

    # Step 2: Within each directory, handle grouping
    # Each group is (name, files, locked) where locked=True means don't merge
    initial_groups: list[tuple[str, list[str], bool]] = []
    for dir_path, files in dir_groups.items():
        # Files with underscore prefix (but not __init__ etc.)
        underscore_files = [
            f for f in files
            if PurePosixPath(f).stem.startswith("_") and PurePosixPath(f).stem not in ("__init__",)
        ]
        normal_files = [f for f in files if f not in underscore_files]

        # Determine if this is a subdirectory (nested package within another scanned dir)
        is_subdir = _is_subdirectory_group(dir_path, dir_groups)

        # Subdirectories with multiple files: always keep grouped (locked)
        if is_subdir and len(files) > 1:
            dir_name = PurePosixPath(dir_path).name
            initial_groups.append((dir_name.lstrip("_").title(), files, True))
        elif len(underscore_files) >= 2 and normal_files:
            # Underscore files grouped as internals (locked)
            dir_name = PurePosixPath(dir_path).name
            initial_groups.append((f"{dir_name.title()}Internals", underscore_files, True))
            for f in normal_files:
                name = PurePosixPath(f).stem.replace("_", " ").title().replace(" ", "")
                initial_groups.append((name, [f], False))
        else:
            # Default: each file gets its own group
            for f in files:
                stem = PurePosixPath(f).stem
                name = stem.lstrip("_").replace("_", " ").title().replace(" ", "")
                initial_groups.append((name, [f], False))

    # Step 3: Calculate target
    if target_groups is None:
        n_unlocked = sum(1 for _, _, locked in initial_groups if not locked)
        n_locked = sum(1 for _, _, locked in initial_groups if locked)
        # Aggressive merging: aim for 5-15 total groups regardless of module count
        if n_unlocked <= 10:
            target_unlocked = max(n_unlocked, 3)
        else:
            # sqrt scaling: 100 modules → ~10 groups, 400 → ~20
            import math
            target_unlocked = max(5, min(15, int(math.sqrt(n_unlocked) * 1.2)))
        target_groups = target_unlocked + n_locked
        # Hard cap: never exceed 20 total groups (agents can't reason about more)
        target_groups = min(target_groups, 20)

    # Step 4: Import-affinity merging (only unlocked groups)
    locked = [(n, f) for n, f, lk in initial_groups if lk]
    unlocked = [(n, f) for n, f, lk in initial_groups if not lk]
    
    target_unlocked = target_groups - len(locked)
    if len(unlocked) > target_unlocked and target_unlocked > 0:
        unlocked = _merge_by_import_affinity(unlocked, interfaces, target_unlocked)
    
    merged_groups = locked + unlocked

    # Step 5: Build ModuleGroup objects
    result: list[ModuleGroup] = []
    for name, files in merged_groups:
        if not files:
            continue
        # Find primary file (largest by line count)
        primary = max(files, key=lambda f: mod_by_file[f].line_count if f in mod_by_file else 0)
        result.append(ModuleGroup(name=name, modules=files, primary_file=primary))

    return result


def _is_subdirectory_group(dir_path: str, all_dirs: dict[str, list[str]]) -> bool:
    """Check if dir_path is a subdirectory of another directory in the groups."""
    parts = PurePosixPath(dir_path).parts
    # If this dir has more path parts than some other dir, it's a subdirectory
    for other_dir in all_dirs:
        if other_dir == dir_path:
            continue
        other_parts = PurePosixPath(other_dir).parts
        if len(parts) > len(other_parts) and parts[: len(other_parts)] == other_parts:
            return True
    return False


def _merge_by_import_affinity(
    groups: list[tuple[str, list[str]]],
    interfaces: list[InterfaceEdge],
    target: int,
) -> list[tuple[str, list[str]]]:
    """Iteratively merge groups with highest import affinity until at target."""
    # Build edge count between file pairs
    edge_count: dict[tuple[str, str], int] = defaultdict(int)
    for iface in interfaces:
        key = (min(iface.source, iface.target), max(iface.source, iface.target))
        edge_count[key] += 1

    groups = list(groups)  # copy

    while len(groups) > target:
        # Find the pair of groups with highest cross-edge count
        best_score = -1
        best_pair = (0, 1)

        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                score = _cross_edge_count(groups[i][1], groups[j][1], edge_count)
                if score > best_score:
                    best_score = score
                    best_pair = (i, j)

        # If no import affinity exists, merge smallest groups
        if best_score <= 0:
            # Find two smallest groups
            sizes = [(len(g[1]), idx) for idx, g in enumerate(groups)]
            sizes.sort()
            best_pair = (sizes[0][1], sizes[1][1])

        i, j = best_pair
        # Merge j into i
        merged_name = groups[i][0]  # keep the larger group's name
        if len(groups[j][1]) > len(groups[i][1]):
            merged_name = groups[j][0]
        merged_files = groups[i][1] + groups[j][1]
        groups[i] = (merged_name, merged_files)
        groups.pop(j)

    return groups


def _cross_edge_count(
    files_a: list[str], files_b: list[str], edge_count: dict[tuple[str, str], int]
) -> int:
    """Count import edges between two sets of files."""
    total = 0
    for a in files_a:
        for b in files_b:
            key = (min(a, b), max(a, b))
            total += edge_count.get(key, 0)
    return total


# ---------------------------------------------------------------------------
# Component creation
# ---------------------------------------------------------------------------


def create_components_from_manifest(
    manifest: Manifest,
    *,
    block_id: str = "F1",
    target_groups: int | None = None,
) -> list[Component]:
    """Create architecture components from a manifest using smart grouping.

    Groups modules using multi-signal affinity, then creates one Component
    per group with appropriate metadata.

    Args:
        manifest: The manifest to create components from.
        block_id: F-block ID to assign to all components.
        target_groups: Desired number of components (None = auto).

    Returns:
        List of Component objects.
    """
    groups = group_modules(
        manifest.modules,
        manifest.interfaces if hasattr(manifest, "interfaces") else [],
        target_groups=target_groups,
    )

    components: list[Component] = []
    for idx, group in enumerate(groups, 1):
        comp = Component(
            id=f"COMP-{idx}",
            name=group.name,
            status="ACTIVE",
            files=group.modules,
            f_block=block_id,
        )
        components.append(comp)

    return components


# ---------------------------------------------------------------------------
# Auto F-block generation
# ---------------------------------------------------------------------------


def auto_fblocks(groups: list[ModuleGroup], threshold: int = 3) -> dict:
    """Generate F-block config from flat module groups.

    Groups with >= threshold files become individual F-blocks.
    Smaller groups are merged into a 'Shared' F-block.

    Args:
        groups: Module groups from group_modules()
        threshold: Minimum files to become a standalone F-block (default: 3)

    Returns:
        Dict of F-block definitions suitable for config:
        {
            "F1": {"name": "Auth", "dirs": ["src/auth"], "files": ["auth/login.py", ...]},
            "F2": {"name": "API", "dirs": ["src/api"], "files": [...]},
            "F0": {"name": "Shared", "dirs": [], "files": [...]},  # small groups merged
        }
    """
    fblocks: dict[str, dict] = {}
    shared_files: list[str] = []
    block_num = 1

    for group in groups:
        files = group.modules
        file_count = len(files)

        if file_count >= threshold:
            # Find common directory prefix for this group's files
            if files:
                parts_list = [PurePosixPath(f).parts for f in files]
                common_parts: list[str] = []
                if parts_list:
                    for parts in zip(*parts_list):
                        if len(set(parts)) == 1:
                            common_parts.append(parts[0])
                        else:
                            break
                common_dir = str(PurePosixPath(*common_parts)) if common_parts else ""
            else:
                common_dir = ""

            fblocks[f"F{block_num}"] = {
                "name": group.name,
                "dirs": [common_dir] if common_dir else [],
                "files": list(files),
            }
            block_num += 1
        else:
            shared_files.extend(files)

    # Flat-repo fallback: if no F-blocks were created (all groups below threshold),
    # promote each group to its own F-block instead of collapsing to F0
    if not fblocks and len(groups) >= 2:
        for i, g in enumerate(groups, 1):
            if g.modules:
                fblocks[f"F{i}"] = {
                    "name": g.name,
                    "dirs": [],
                    "files": list(g.modules),
                }
        return fblocks

    # Merge small groups into Shared block
    if shared_files:
        fblocks["F0"] = {
            "name": "Shared",
            "dirs": [],
            "files": shared_files,
        }

    return fblocks


# ---------------------------------------------------------------------------
# SourceGraph-based grouping (language-agnostic)
# ---------------------------------------------------------------------------


def group_source_graph(
    graph: SourceGraph,
    *,
    target_groups: int | None = None,
    min_group_size: int = 1,
) -> list[ModuleGroup]:
    """Group source units using multi-signal affinity (language-agnostic).

    This is the SourceGraph equivalent of group_modules(). It converts
    SourceUnits into lightweight ModuleInfo-compatible objects and delegates
    to the existing grouping algorithm.

    Args:
        graph: A SourceGraph instance (from any language scanner or JSON).
        target_groups: Desired number of groups. None = auto-calculate.
        min_group_size: Minimum modules per group (after merging).

    Returns:
        List of ModuleGroup objects.
    """
    from architecture_model.manifest.types import FunctionInfo, ClassInfo, ModuleStatus

    # Convert SourceUnits to ModuleInfo for reuse of existing algorithm
    modules: list[ModuleInfo] = []
    for unit in graph.units:
        functions = []
        classes = []
        for exp in unit.exports:
            if exp.kind == "class":
                classes.append(ClassInfo(name=exp.name))
            else:
                functions.append(FunctionInfo(name=exp.name, signature=exp.signature))

        modules.append(ModuleInfo(
            file=unit.file,
            name=PurePosixPath(unit.file).stem,
            docstring=None,
            functions=functions,
            imports=[],
            line_count=1 if unit.has_content else 0,
            status=ModuleStatus.ACTIVE,
            classes=classes,
        ))

    # Convert DependencyEdges to InterfaceEdges
    interfaces: list[InterfaceEdge] = [
        InterfaceEdge(source=e.source, target=e.target, import_path="")
        for e in graph.edges
    ]

    return group_modules(
        modules, interfaces, target_groups=target_groups, min_group_size=min_group_size
    )
