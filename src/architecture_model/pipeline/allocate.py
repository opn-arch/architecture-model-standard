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
from .corrections import get_corrections_for_stage, get_resolutions_for_stage


# Thresholds
MAX_COMPONENT_FILES = 12
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

        project_type = _detect_project_type(source_modules)
        is_scoped = bool(ctx.scope_files)

        # Scoped small context: one component per substantive file
        if is_scoped and len(source_modules) <= _SCOPED_FILE_LIMIT:
            components = _allocate_per_file(source_modules, inference.capabilities, project_type=project_type)
        else:
            # Step 1: Seed components from capabilities
            components = _seed_from_capabilities(inference.capabilities, source_modules, project_type=project_type)

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

        _apply_allocation_resolutions(ctx, components, source_modules, project_type, diagnostics)

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

        # Per-component quality aggregation from observe's per-module scores
        comp_quality: dict[str, QualityMetrics] = {}
        module_quality = observe_result.quality.component_scores if observe_result else {}
        if module_quality:
            for comp in components:
                comp_mod_scores: list[float] = []
                comp_mod_details: dict[str, QualityMetrics] = {}
                for f in comp.files:
                    key = str(f)
                    if key in module_quality:
                        comp_mod_scores.append(module_quality[key].score)
                        comp_mod_details[key] = module_quality[key]
                if comp_mod_scores:
                    comp_quality[comp.id] = QualityMetrics(
                        score=sum(comp_mod_scores) / len(comp_mod_scores),
                        sub_scores={
                            "module_count": float(len(comp.files)),
                            "worst_module": min(comp_mod_scores),
                            "best_module": max(comp_mod_scores),
                        },
                        component_scores=comp_mod_details,
                    )

        quality = QualityMetrics(
            score=int((file_coverage + boundary_coherence) / 2),
            sub_scores={
                "file_coverage": file_coverage,
                "boundary_coherence": boundary_coherence,
                "component_count": float(len(components)),
            },
            thresholds={"file_coverage": 95.0, "boundary_coherence": 50.0},
            component_scores=comp_quality,
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
            summary=f"Allocated {allocated_count} files to {len(components)} components ({file_coverage:.0f}% coverage).",
        )


def _allocate_per_file(
    modules: list[ModuleRecord], capabilities: list[InferredCapability],
    project_type: str = "library",
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
                layer=_infer_layer([mod.path], project_type=project_type),
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
    capabilities: list[InferredCapability], modules: list[ModuleRecord],
    project_type: str = "library",
) -> list[ComponentAllocation]:
    """Create one component per capability, seed files by name matching.

    Each file is assigned to at most one primary component. Stable source-file
    evidence wins; name affinity is only a fallback for legacy capabilities.
    """
    components = []
    assigned: set[Path] = set()
    reserved_exact = {
        Path(path): capability.id
        for capability in capabilities
        for path in capability.source_files
    }

    for i, cap in enumerate(capabilities, 1):
        matched_files = []

        exact_sources = {Path(path) for path in cap.source_files}
        for mod in modules:
            if mod.path not in assigned and mod.path in exact_sources:
                matched_files.append(mod.path)

        if not matched_files and cap.evidence_source == "package_group":
            # Match files whose path contains this package directory
            pkg_name = cap.source_key
            for mod in modules:
                if mod.path in assigned:
                    continue
                if reserved_exact.get(mod.path) not in (None, cap.id):
                    continue
                # Check if any parent directory matches the package name
                parts = [p.lower() for p in mod.path.parts[:-1]]  # exclude filename
                if pkg_name in parts:
                    matched_files.append(mod.path)
        elif not matched_files:
            # Original stem-matching logic for route/domain/cli caps
            cap_words = set(cap.name.lower().replace(" management", "").replace("cli ", "").split())
            cap_slug = "_".join(
                cap.name.lower().replace(" management", "").replace("cli ", "").split()
            )

            for mod in modules:
                if mod.path in assigned:
                    continue
                if reserved_exact.get(mod.path) not in (None, cap.id):
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
            layer=_infer_layer(matched_files, project_type=project_type),
        )
        components.append(comp)

    return components


def _apply_allocation_resolutions(
    ctx: PipelineContext,
    components: list[ComponentAllocation],
    modules: list[ModuleRecord],
    project_type: str,
    diagnostics: list[Diagnostic],
) -> None:
    """Apply explicit ambiguous-module file groups without parsing free text."""
    module_paths = {module.path for module in modules}
    for evidence in get_resolutions_for_stage(ctx, "allocate"):
        file_values = evidence.metadata.get("file_allocations") or evidence.metadata.get("files_sent", [])
        if isinstance(file_values, dict):
            file_values = [
                path
                for paths in file_values.values()
                for path in (paths if isinstance(paths, list) else [paths])
            ]
        files = [Path(path) for path in file_values]
        files = [path for path in files if path in module_paths]
        if not files:
            continue
        target_name = str(evidence.metadata.get("target_name", "")).strip()
        target_kind = str(evidence.metadata.get("target_kind", "component")).strip()
        if target_kind not in ("", "component"):
            continue
        for component in components:
            component.files = [path for path in component.files if path not in files]
        component = next(
            (item for item in components if target_name and item.name == target_name),
            None,
        )
        if component is None:
            component = ComponentAllocation(
                id=f"COMP-{len(components) + 1}",
                name=target_name or Path(files[0]).parent.name.replace("_", " ").title() or "Resolved Group",
                layer=_infer_layer(files, project_type),
            )
            components.append(component)
        component.files.extend(path for path in files if path not in component.files)
        component.evidence.append(evidence.raw)
        diagnostics.append(
            Diagnostic(
                severity="info",
                code="resolution_applied",
                message=f"Applied explicit allocation evidence to {component.id}",
                context={"files": [str(path) for path in files]},
            )
        )
    components[:] = [component for component in components if component.files]


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
    """Count import connections between module and component files using resolved edges."""
    comp_files = set(comp.files)
    score = 0
    for edge in edges:
        # Module imports something from this component
        if edge.source == mod.path and edge.target in comp_files:
            score += 1
        # Something in this component imports the module
        elif edge.target == mod.path and edge.source in comp_files:
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
    """Drop empty seeds; source overlap preserves their capability realization."""
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


_WEB_FRAMEWORKS = {"flask", "django", "fastapi", "starlette", "tornado", "aiohttp", "sanic", "bottle", "pyramid", "quart"}
_CLI_FRAMEWORKS = {"click", "typer"}


def _detect_project_type(modules: list[ModuleRecord]) -> str:
    """Detect whether the project is a web app, CLI tool, or library."""
    all_imports: set[str] = set()
    for mod in modules:
        for imp in mod.imports:
            root = imp.split(".")[0].lower()
            all_imports.add(root)
    if all_imports & _WEB_FRAMEWORKS:
        return "web_app"
    if all_imports & _CLI_FRAMEWORKS:
        return "cli_tool"
    return "library"


_LAYER_KEYWORDS: dict[str, list[str]] = {
    "web": ["route", "view", "handler", "endpoint", "controller", "server"],
    "data": ["model", "schema", "db", "repository", "migration"],
    "service": ["service", "usecase", "domain", "logic"],
    "core": ["core", "engine", "kernel"],
    "infra": ["util", "helper", "common", "compat"],
}


def _infer_layer(files: list[Path], project_type: str = "library") -> str:
    """Guess architectural layer from file paths using per-file majority voting."""
    default = "library" if project_type == "library" else "infra"
    if not files:
        return default

    votes: dict[str, int] = {}
    for f in files:
        path_str = str(f).lower()
        matched = False
        for layer, keywords in _LAYER_KEYWORDS.items():
            if any(kw in path_str for kw in keywords):
                votes[layer] = votes.get(layer, 0) + 1
                matched = True
                break
        if not matched:
            votes[default] = votes.get(default, 0) + 1

    if not votes:
        return default

    max_count = max(votes.values())
    for layer in _LAYER_KEYWORDS:
        if votes.get(layer, 0) == max_count:
            return layer
    return default
