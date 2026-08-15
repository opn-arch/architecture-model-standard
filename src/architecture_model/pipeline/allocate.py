"""Allocate pipeline stage — assigns files to components seeded by capabilities.

Strategy:
1. Seed: one component per capability (files matched by name/content)
2. Assign: remaining files by import affinity to seeded components
3. Split: oversized components (>15 files) by sub-clustering
4. Merge: undersized components (<2 files) into nearest neighbor
"""

from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from .allocate_types import AllocationResult, ComponentAllocation
from .infer import _is_non_source_module
from .infer_types import InferenceResult, InferredCapability
from .observe_types import ImportEdge, Inventory, ModuleRecord
from .protocol import (
    Diagnostic,
    PipelineContext,
    QualityMetrics,
    StageResult,
    Uncertainty,
)
from .corrections import get_corrections_for_stage


# Thresholds
MAX_COMPONENT_FILES = 15
MIN_COMPONENT_FILES = 2
_SCOPED_FILE_LIMIT = 15  # use per-file strategy when scoped context has <= this many files


class AllocateStage:
    """Assigns files to architecture components based on capability affinity."""

    name: str = "allocate"
    requires: list[str] = ["observe", "infer"]

    def run(self, ctx: PipelineContext) -> StageResult[AllocationResult]:
        start = time.time()
        diagnostics: list[Diagnostic] = []
        uncertainties: list[Uncertainty] = []

        observe_result = ctx.get("observe")
        infer_result = ctx.get("infer")
        if observe_result is None or infer_result is None:
            raise RuntimeError("allocate requires observe and infer")

        inventory: Inventory = observe_result.output
        inference: InferenceResult = infer_result.output

        # All source modules (exclude tests, examples, benchmarks, etc.)
        source_modules = [m for m in inventory.modules if not _is_non_source_module(m)]

        is_scoped = bool(ctx.scope_files)

        # Scoped small context: one component per substantive file
        if is_scoped and len(source_modules) <= _SCOPED_FILE_LIMIT:
            components = _allocate_per_file(source_modules, inference.capabilities)
        else:
            # Step 1: Seed components from capabilities
            components = _seed_from_capabilities(inference.capabilities, source_modules)

            # Step 2: Assign unallocated files by import affinity
            allocated_files = {f for c in components for f in c.files}
            unallocated = [m for m in source_modules if m.path not in allocated_files]

            if unallocated and components:
                _assign_by_import_affinity(unallocated, components, inventory.edges)
                allocated_files = {f for c in components for f in c.files}
                unallocated = [m for m in source_modules if m.path not in allocated_files]

            # Step 3: Remaining unallocated → "Infrastructure" component
            still_unallocated = [m.path for m in unallocated]
            if still_unallocated:
                components.append(
                    ComponentAllocation(
                        id=f"COMP-{len(components) + 1}",
                        name="Infrastructure",
                        files=still_unallocated,
                        layer="infra",
                    )
                )

            # Step 4: Split oversized components
            components = _split_oversized(components)

            # Step 5: Merge undersized components
            components = _merge_undersized(components)

        # --- Apply prior corrections ---
        comp_by_id = {c.id: c for c in components}
        for correction in get_corrections_for_stage(ctx, "allocate"):
            if correction.correction_type == "split" and correction.entity_id.startswith("COMP-"):
                if correction.entity_id in comp_by_id:
                    diagnostics.append(
                        Diagnostic(
                            severity="warning",
                            code="split_suggested",
                            message=(
                                f"Prior correction suggests splitting {correction.entity_id}: "
                                f"{correction.reason}"
                            ),
                            context={"entity_id": correction.entity_id, "after": correction.after},
                        )
                    )
            elif correction.correction_type == "reassign" and correction.entity_id.startswith(
                "COMP-"
            ):
                src_id = correction.entity_id
                dst_id = correction.after.get("component_id", "")
                files_to_move = [Path(f) for f in correction.after.get("files", [])]
                src = comp_by_id.get(src_id)
                dst = comp_by_id.get(dst_id)
                if src and dst and files_to_move:
                    moved = []
                    for f in files_to_move:
                        if f in src.files:
                            src.files.remove(f)
                            dst.files.append(f)
                            moved.append(str(f))
                    if moved:
                        diagnostics.append(
                            Diagnostic(
                                severity="info",
                                code="correction_applied",
                                message=(
                                    f"Reassigned {len(moved)} file(s) from {src_id} to {dst_id} "
                                    f"(prior correction)"
                                ),
                            )
                        )

        # Ensure component files are sorted for deterministic output
        for comp in components:
            comp.files = sorted(comp.files, key=str)

        # Compute metrics
        total_files = len(source_modules)
        allocated_count = sum(len(c.files) for c in components)
        file_coverage = (allocated_count / total_files * 100) if total_files > 0 else 100.0
        boundary_coherence = _compute_boundary_coherence(components, inventory.edges)

        result = AllocationResult(
            components=components,
            unallocated=[],  # all assigned after infra catch-all
            file_coverage=file_coverage,
            boundary_coherence=boundary_coherence,
        )

        quality = QualityMetrics(
            score=int((file_coverage + boundary_coherence) / 2),
            sub_scores={
                "file_coverage": file_coverage,
                "boundary_coherence": boundary_coherence,
                "component_count": float(len(components)),
            },
            thresholds={"file_coverage": 95.0, "boundary_coherence": 50.0},
        )

        duration_ms = int((time.time() - start) * 1000)

        return StageResult(
            output=result,
            quality=quality,
            diagnostics=diagnostics,
            uncertainties=uncertainties,
            input_hash=str(total_files),
            duration_ms=duration_ms,
            version="1.0",
        )


def _allocate_per_file(
    modules: list[ModuleRecord], capabilities: list[InferredCapability]
) -> list[ComponentAllocation]:
    """One component per substantive file for small scoped contexts.

    Files with classes or public functions become their own component.
    ``__init__.py`` and helper-only files are grouped with the nearest
    sibling or placed in an Infrastructure component.
    """
    components: list[ComponentAllocation] = []
    infra_files: list[Path] = []
    cap_by_stem: dict[str, str] = {}

    # Build a stem → capability_id map for linking
    for cap in capabilities:
        slug = "_".join(cap.name.lower().split())
        cap_by_stem[slug] = cap.id
        for word in cap.name.lower().split():
            cap_by_stem[word] = cap.id

    comp_counter = 0
    for mod in modules:
        stem = mod.path.stem
        # __init__.py and trivial helpers → infra bucket
        if stem == "__init__" or (
            not mod.classes and not [f for f in mod.functions if not f.name.startswith("_")]
        ):
            infra_files.append(mod.path)
            continue

        comp_counter += 1
        cap_id = cap_by_stem.get(stem.lower().lstrip("_"), "")
        components.append(
            ComponentAllocation(
                id=f"COMP-{comp_counter}",
                name=stem.lstrip("_").replace("_", " ").title(),
                capability_id=cap_id,
                files=[mod.path],
                layer=_infer_layer([mod.path]),
            )
        )

    # Attach infra files to an Infrastructure component if any
    if infra_files:
        comp_counter += 1
        components.append(
            ComponentAllocation(
                id=f"COMP-{comp_counter}",
                name="Infrastructure",
                files=infra_files,
                layer="infra",
            )
        )

    return components


def _seed_from_capabilities(
    capabilities: list[InferredCapability], modules: list[ModuleRecord]
) -> list[ComponentAllocation]:
    """Create one component per capability, seed files by name matching.

    Each file is assigned to at most one component (first match wins).
    For package_group capabilities, matches by directory path.
    For other capabilities, uses exact stem match.
    """
    components = []
    assigned: set[Path] = set()

    for i, cap in enumerate(capabilities, 1):
        matched_files = []

        if cap.evidence_source == "package_group":
            # Match files whose path contains this package directory
            pkg_name = "_".join(cap.name.lower().split())
            for mod in modules:
                if mod.path in assigned:
                    continue
                # Check if any parent directory matches the package name
                parts = [p.lower() for p in mod.path.parts[:-1]]  # exclude filename
                if pkg_name in parts:
                    matched_files.append(mod.path)
        else:
            # Original stem-matching logic for route/domain/cli caps
            cap_words = set(cap.name.lower().replace(" management", "").replace("cli ", "").split())
            cap_slug = "_".join(
                cap.name.lower().replace(" management", "").replace("cli ", "").split()
            )

            for mod in modules:
                if mod.path in assigned:
                    continue
                mod_stem = mod.path.stem.lower().lstrip("_")
                if mod_stem == cap_slug or mod_stem in cap_words:
                    matched_files.append(mod.path)
                elif any(
                    mod_stem == w or mod_stem.startswith(w + "_") for w in cap_words if len(w) > 3
                ):
                    matched_files.append(mod.path)

        assigned.update(matched_files)
        comp = ComponentAllocation(
            id=f"COMP-{i}",
            name=cap.name.replace(" Management", ""),
            capability_id=cap.id,
            files=matched_files,
            layer=_infer_layer(matched_files),
        )
        components.append(comp)

    return components


def _assign_by_import_affinity(
    unallocated: list[ModuleRecord],
    components: list[ComponentAllocation],
    edges: list[ImportEdge],
) -> None:
    """Assign remaining files to components with most import connections."""
    for mod in unallocated:
        best_comp = None
        best_score = 0

        for comp in components:
            score = _import_affinity(mod, comp, edges)
            if score > best_score:
                best_score = score
                best_comp = comp

        if best_comp and best_score > 0:
            best_comp.files.append(mod.path)


def _import_affinity(mod: ModuleRecord, comp: ComponentAllocation, edges: list[ImportEdge]) -> int:
    """Count import connections between module and component files."""
    comp_files = set(comp.files)
    score = 0
    # Check if module imports anything from the component
    for imp in mod.imports:
        for cf in comp_files:
            if cf.stem in imp or cf.parent.stem in imp:
                score += 1
    return score


def _group_by_package_level(files: list[Path]) -> dict[str, list[Path]]:
    """Group files by the first directory level after their common prefix.

    For files like ``django/db/models/fields/a.py`` and ``django/db/backends/sqlite3/b.py``,
    the common prefix is ``django/db`` and the grouping keys are ``models`` and ``backends``.
    Files sitting directly at the prefix level go into a ``(root)`` group.
    """
    if not files:
        return {}

    # Find common prefix by iterating path parts until values diverge
    parts_list = [f.parent.parts for f in files]
    min_len = min(len(p) for p in parts_list)
    prefix_len = 0
    for i in range(min_len):
        if len({p[i] for p in parts_list}) == 1:
            prefix_len = i + 1
        else:
            break

    groups: dict[str, list[Path]] = defaultdict(list)
    for f in files:
        parent_parts = f.parent.parts
        if len(parent_parts) > prefix_len:
            key = parent_parts[prefix_len]
        else:
            key = "(root)"
        groups[key].append(f)
    return dict(groups)


def _split_oversized(components: list[ComponentAllocation]) -> list[ComponentAllocation]:
    """Split components exceeding MAX_COMPONENT_FILES."""
    result = []
    for comp in components:
        if len(comp.files) > MAX_COMPONENT_FILES:
            groups = _group_by_package_level(comp.files)

            if len(groups) > 1:
                for i, (pkg_name, files) in enumerate(groups.items()):
                    sub_name = pkg_name if pkg_name != "(root)" else "core"
                    result.append(
                        ComponentAllocation(
                            id=f"{comp.id}-{i + 1}",
                            name=f"{comp.name} ({sub_name})",
                            capability_id=comp.capability_id,
                            files=files,
                            layer=comp.layer,
                        )
                    )
            else:
                result.append(comp)
        else:
            result.append(comp)
    return result


def _merge_undersized(components: list[ComponentAllocation]) -> list[ComponentAllocation]:
    """Merge components with no files into nearest neighbor.

    Components with a capability_id are never merged (they're intentional).
    Only truly empty components (0 files, no capability) get merged.
    """
    if len(components) <= 1:
        return components

    # Keep all components that have files OR a backing capability
    keep = [c for c in components if c.files or c.capability_id]
    empty = [c for c in components if not c.files and not c.capability_id]

    if empty and keep:
        # Empty components with no capability — just drop them
        pass

    # Remove empty components with no capability
    return [c for c in components if c.files]


def _compute_boundary_coherence(
    components: list[ComponentAllocation], edges: list[ImportEdge]
) -> float:
    """Compute % of imports that stay within component boundaries."""
    if not edges:
        return 100.0

    # Build file→component map
    file_to_comp: dict[Path, str] = {}
    for comp in components:
        for f in comp.files:
            file_to_comp[f] = comp.id

    internal = 0
    total = 0
    for edge in edges:
        src_comp = file_to_comp.get(edge.source)
        tgt_comp = file_to_comp.get(edge.target)
        if src_comp and tgt_comp:
            total += 1
            if src_comp == tgt_comp:
                internal += 1

    return (internal / total * 100) if total > 0 else 100.0


def _infer_layer(files: list[Path]) -> str:
    """Guess architectural layer from file paths."""
    paths_str = " ".join(str(f) for f in files).lower()
    if any(w in paths_str for w in ("api", "route", "view", "handler", "endpoint")):
        return "web"
    if any(w in paths_str for w in ("model", "schema", "db", "repository", "migration")):
        return "data"
    if any(w in paths_str for w in ("service", "usecase", "domain", "logic")):
        return "service"
    return "infra"
