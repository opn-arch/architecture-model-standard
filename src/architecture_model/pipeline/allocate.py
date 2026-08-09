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
from .infer_types import InferenceResult, InferredCapability
from .observe_types import ImportEdge, Inventory, ModuleRecord
from .protocol import (
    Diagnostic,
    PipelineContext,
    QualityMetrics,
    StageResult,
    Uncertainty,
)


# Thresholds
MAX_COMPONENT_FILES = 15
MIN_COMPONENT_FILES = 2


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

        # All source modules (exclude tests, __init__)
        source_modules = [
            m for m in inventory.modules
            if not m.path.stem.startswith("test_")
            and m.path.stem != "conftest"
        ]

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
            components.append(ComponentAllocation(
                id=f"COMP-{len(components) + 1}",
                name="Infrastructure",
                files=still_unallocated,
                layer="infra",
            ))

        # Step 4: Split oversized components
        components = _split_oversized(components)

        # Step 5: Merge undersized components
        components = _merge_undersized(components)

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


def _seed_from_capabilities(
    capabilities: list[InferredCapability], modules: list[ModuleRecord]
) -> list[ComponentAllocation]:
    """Create one component per capability, seed files by name matching.

    Each file is assigned to at most one component (first match wins).
    """
    components = []
    assigned: set[Path] = set()

    for i, cap in enumerate(capabilities, 1):
        # Match modules whose name relates to the capability
        cap_words = set(cap.name.lower().replace(" management", "").replace("cli ", "").split())
        matched_files = []

        for mod in modules:
            if mod.path in assigned:
                continue
            mod_name = mod.path.stem.lower()
            # Direct name match
            if any(w in mod_name for w in cap_words if len(w) > 2):
                matched_files.append(mod.path)
            # Path-based match (e.g., "api/users.py" for "User" capability)
            elif any(w in str(mod.path).lower() for w in cap_words if len(w) > 2):
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


def _split_oversized(components: list[ComponentAllocation]) -> list[ComponentAllocation]:
    """Split components exceeding MAX_COMPONENT_FILES."""
    result = []
    for comp in components:
        if len(comp.files) > MAX_COMPONENT_FILES:
            # Split by subdirectory
            by_dir: dict[str, list[Path]] = defaultdict(list)
            for f in comp.files:
                by_dir[str(f.parent)].append(f)

            if len(by_dir) > 1:
                for i, (dir_name, files) in enumerate(by_dir.items()):
                    sub_name = Path(dir_name).stem if dir_name != "." else "core"
                    result.append(ComponentAllocation(
                        id=f"{comp.id}-{i + 1}",
                        name=f"{comp.name} ({sub_name})",
                        capability_id=comp.capability_id,
                        files=files,
                        layer=comp.layer,
                    ))
            else:
                result.append(comp)
        else:
            result.append(comp)
    return result


def _merge_undersized(components: list[ComponentAllocation]) -> list[ComponentAllocation]:
    """Merge components with fewer than MIN_COMPONENT_FILES into nearest neighbor."""
    if len(components) <= 1:
        return components

    large = [c for c in components if len(c.files) >= MIN_COMPONENT_FILES]
    small = [c for c in components if len(c.files) < MIN_COMPONENT_FILES]

    if not large:
        return components  # All small, nothing to merge into

    for s in small:
        # Merge into the first large component (simplistic — could use affinity)
        large[0].files.extend(s.files)

    return large


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
