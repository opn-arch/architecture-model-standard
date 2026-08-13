"""Infer pipeline stage — derives capabilities, actors, and behaviors from Inventory.

Capability-driven: clusters by purpose (routes, domain modules, test patterns),
not by import structure. Import affinity is a secondary signal only.
"""
from __future__ import annotations

import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from .infer_types import (
    InferenceResult,
    InferredActor,
    InferredBehavior,
    InferredCapability,
)
from .observe_types import Inventory, ModuleRecord, RouteRecord
from .protocol import (
    Diagnostic,
    Evidence,
    PipelineContext,
    QualityMetrics,
    StageResult,
    Uncertainty,
)
from .corrections import get_corrections_for_stage


_LARGE_REPO_MODULE_THRESHOLD = 50


class InferStage:
    """Infers capabilities, actors, and behaviors from observed Inventory."""

    name: str = "infer"
    requires: list[str] = ["observe"]

    def run(self, ctx: PipelineContext) -> StageResult[InferenceResult]:
        start = time.time()
        diagnostics: list[Diagnostic] = []
        uncertainties: list[Uncertainty] = []

        # Get observe output
        observe_result = ctx.get("observe")
        if observe_result is None:
            raise RuntimeError("infer requires observe to have run first")
        inventory: Inventory = observe_result.output

        capabilities: list[InferredCapability] = []
        actors: list[InferredActor] = []
        behaviors: list[InferredBehavior] = []

        cap_counter = 0

        # --- Strategy 1: Routes → capabilities grouped by URL prefix ---
        if inventory.routes:
            # For large repos, consolidate routes into a single capability
            source_count = sum(
                1 for m in inventory.modules
                if not _is_non_source_module(m)
                and m.path.stem not in ("utils", "helpers", "common", "base",
                                        "constants", "types", "config")
            )
            if source_count > _LARGE_REPO_MODULE_THRESHOLD:
                # Single "Web Routes" capability for all routes
                cap_counter += 1
                capabilities.append(InferredCapability(
                    id=f"CAP-{cap_counter}",
                    name="Web Routes",
                    description=f"HTTP routing ({len(inventory.routes)} endpoints)",
                    evidence_source="routes",
                ))
                # Still infer actors from routes
                has_auth = any(r.is_authenticated for r in inventory.routes)
                actors.append(InferredActor(
                    id="ACT-1",
                    name="API Consumer",
                    actor_type="system" if not has_auth else "human",
                    evidence_source="routes",
                ))
            else:
                route_caps, route_actors = _infer_from_routes(inventory.routes)
                for cap in route_caps:
                    cap_counter += 1
                    cap.id = f"CAP-{cap_counter}"
                    capabilities.append(cap)
                actors.extend(route_actors)

        # --- Strategy 2: Domain modules → capabilities ---
        is_scoped = bool(ctx.scope_files)
        domain_caps = _infer_from_domain_modules(inventory.modules, capabilities, scoped=is_scoped)
        for cap in domain_caps:
            cap_counter += 1
            cap.id = f"CAP-{cap_counter}"
            capabilities.append(cap)

        # --- Strategy 3: CLI/commands → capabilities ---
        cli_caps = _infer_from_cli(inventory.modules)
        for cap in cli_caps:
            cap_counter += 1
            cap.id = f"CAP-{cap_counter}"
            capabilities.append(cap)

        # --- Actors: infer from auth patterns, CLI entry points ---
        if not actors:
            actors = _infer_default_actors(inventory)

        # --- Behaviors: from trigger chains (route → function → calls) ---
        behaviors = _infer_behaviors(inventory, capabilities, actors)

        # --- Uncertainties for ambiguous modules ---
        for mod in inventory.modules:
            if not _module_has_clear_purpose(mod, capabilities):
                uncertainties.append(Uncertainty(
                    category="ambiguous_module",
                    description=f"{mod.path} has no clear capability affiliation",
                    suggested_fallback="llm_analysis",
                    priority="informational",
                ))

        result = InferenceResult(
            capabilities=capabilities,
            actors=actors,
            behaviors=behaviors,
        )

        # --- Apply prior corrections ---
        for correction in get_corrections_for_stage(ctx, "infer"):
            if correction.correction_type == "rename" and correction.entity_id.startswith("CAP-"):
                for cap in result.capabilities:
                    if cap.id == correction.entity_id:
                        old_name = correction.before.get("name")
                        new_name = correction.after.get("name")
                        if new_name and (old_name is None or cap.name == old_name):
                            cap.name = new_name
                            diagnostics.append(Diagnostic(
                                severity="info",
                                code="correction_applied",
                                message=f"Renamed {cap.id} to '{new_name}' (prior correction)",
                            ))
                        break

        # Quality
        total_modules = len(inventory.modules)
        covered = sum(1 for m in inventory.modules if _module_has_clear_purpose(m, capabilities))
        coverage = (covered / total_modules * 100) if total_modules > 0 else 100.0

        quality = QualityMetrics(
            score=int(coverage),
            sub_scores={
                "capability_coverage": coverage,
                "actor_completeness": 100.0 if actors else 0.0,
                "capability_count": float(len(capabilities)),
            },
            thresholds={"capability_coverage": 60.0},
        )

        duration_ms = int((time.time() - start) * 1000)

        return StageResult(
            output=result,
            quality=quality,
            diagnostics=diagnostics,
            uncertainties=uncertainties,
            input_hash=str(len(inventory.modules)),
            duration_ms=duration_ms,
            version="1.0",
        )


def _infer_from_routes(routes: list[RouteRecord]) -> tuple[list[InferredCapability], list[InferredActor]]:
    """Group routes by URL prefix → one capability per prefix."""
    prefix_groups: dict[str, list[RouteRecord]] = defaultdict(list)

    for route in routes:
        prefix = _extract_prefix(route.path)
        prefix_groups[prefix].append(route)

    capabilities = []
    for prefix, group in prefix_groups.items():
        name = _name_from_prefix(prefix)
        cap = InferredCapability(
            id="",  # assigned by caller
            name=f"{name} Management",
            description=f"CRUD operations for {name} ({len(group)} endpoints)",
            evidence_source="routes",
        )
        capabilities.append(cap)

    # If routes exist, infer API consumer actor
    actors = []
    if routes:
        has_auth = any(r.is_authenticated for r in routes)
        actors.append(InferredActor(
            id="ACT-1",
            name="API Consumer",
            actor_type="system" if not has_auth else "human",
            evidence_source="routes",
        ))

    return capabilities, actors


def _extract_prefix(path: str) -> str:
    """Extract first meaningful path segment: /users/{id} → users."""
    parts = [p for p in path.strip("/").split("/") if p and not p.startswith("{")]
    return parts[0] if parts else "root"


# Directories that contain non-source modules (tests, examples, docs, etc.)
_NON_SOURCE_DIRS = frozenset({
    "tests", "test", "testing", "examples", "example", "demos", "demo",
    "docs", "doc", "typing_tests", "benchmarks", "fixtures", "tools",
    "_unicode_data", "scripts", "contrib",
})


def _is_non_source_module(mod: ModuleRecord) -> bool:
    """Check if a module is in a non-source directory (tests, examples, etc.)."""
    name = mod.path.stem
    if name.startswith("test_") or name.endswith("_test"):
        return True
    if name in ("__init__", "conftest", "setup"):
        return True
    # Check if any parent directory is non-source
    parts = set(mod.path.parts[:-1])  # all dirs except filename
    return bool(parts & _NON_SOURCE_DIRS)


def _name_from_prefix(prefix: str) -> str:
    """Convert URL prefix to capability name."""
    # Singularize simple cases
    name = prefix.replace("-", " ").replace("_", " ").title()
    if name.endswith("s") and len(name) > 3:
        name = name[:-1]
    return name


def _infer_from_domain_modules(
    modules: list[ModuleRecord], existing: list[InferredCapability],
    *, scoped: bool = False,
) -> list[InferredCapability]:
    """Infer capabilities from domain-named modules not yet covered by routes.

    When *scoped* (recursive sub-pipeline), lower thresholds so each file with
    any public API surface becomes a capability — subsystems are small and every
    file is more likely to represent a distinct concern.
    """
    existing_names = {c.name.lower() for c in existing}
    capabilities = []

    # Filter source modules once for both paths
    source_modules = [
        mod for mod in modules
        if not _is_non_source_module(mod)
        and mod.path.stem not in ("utils", "helpers", "common", "base", "constants", "types", "config")
    ]

    # Large repos: group by package instead of one-cap-per-file
    if not scoped and len(source_modules) > _LARGE_REPO_MODULE_THRESHOLD:
        return _infer_capabilities_by_package(source_modules, existing_names)

    # In scoped contexts, each meaningful file is a capability
    min_funcs = 1 if scoped else 3
    min_classes = 1 if scoped else 2

    # Look for modules with domain-rich classes/functions (not utils, not tests)
    for mod in modules:
        if _is_non_source_module(mod):
            continue
        name = mod.path.stem
        if name in ("utils", "helpers", "common", "base", "constants", "types", "config"):
            continue

        # Module with public functions/classes = potential capability
        public_funcs = [f for f in mod.functions if not f.name.startswith("_")]
        if len(public_funcs) >= min_funcs or len(mod.classes) >= min_classes:
            cap_name = name.lstrip("_").replace("_", " ").title()
            if cap_name.lower() not in existing_names:
                capabilities.append(InferredCapability(
                    id="",
                    name=cap_name,
                    description=f"Domain logic in {mod.path}",
                    evidence_source="domain_module",
                ))
                existing_names.add(cap_name.lower())

    return capabilities


def _infer_capabilities_by_package(
    source_modules: list[ModuleRecord],
    existing_names: set[str],
) -> list[InferredCapability]:
    """Group modules by top-level package directory for large repos."""
    # Find common path prefix
    all_parts = [mod.path.parts for mod in source_modules]
    if not all_parts:
        return []
    prefix_len = 0
    for i in range(min(len(p) for p in all_parts)):
        values = {p[i] for p in all_parts}
        if len(values) == 1:
            prefix_len = i + 1
        else:
            break

    # Group by directory immediately after common prefix
    groups: dict[str, list[ModuleRecord]] = defaultdict(list)
    for mod in source_modules:
        parts = mod.path.parts
        if len(parts) > prefix_len:
            group_key = parts[prefix_len]
            # If it's a file (not a directory), put in root
            if group_key.endswith(".py"):
                group_key = "(root)"
        else:
            group_key = "(root)"
        groups[group_key].append(mod)

    capabilities = []
    for group_name, mods in groups.items():
        if group_name == "(root)" and len(mods) < 3:
            continue
        cap_name = group_name.replace("_", " ").title()
        if cap_name.lower() not in existing_names:
            capabilities.append(InferredCapability(
                id="",
                name=cap_name,
                description=f"Package group with {len(mods)} modules",
                evidence_source="package_group",
            ))
            existing_names.add(cap_name.lower())

    return capabilities


def _infer_from_cli(modules: list[ModuleRecord]) -> list[InferredCapability]:
    """Infer capabilities from CLI command modules."""
    capabilities = []
    for mod in modules:
        if _is_non_source_module(mod):
            continue
        # Check for click/typer/argparse patterns
        has_cli = any(
            "click" in imp or "typer" in imp or "argparse" in imp
            for imp in mod.imports
        )
        if has_cli and mod.path.stem not in ("__init__",):
            capabilities.append(InferredCapability(
                id="",
                name=f"CLI {mod.path.stem.replace('_', ' ').title()}",
                description=f"CLI commands in {mod.path}",
                evidence_source="cli_pattern",
            ))
    return capabilities


def _infer_default_actors(inventory: Inventory) -> list[InferredActor]:
    """Infer actors when no routes provide hints."""
    actors = []
    source_modules = [m for m in inventory.modules if not _is_non_source_module(m)]

    # Check for CLI entry points
    has_cli = any(
        any("click" in imp or "typer" in imp or "argparse" in imp for imp in m.imports)
        for m in source_modules
    )
    if has_cli:
        actors.append(InferredActor(
            id="ACT-1", name="CLI User", actor_type="human", evidence_source="cli_pattern"
        ))

    # Check for scheduled/timer patterns
    has_scheduler = any(
        any("schedule" in imp or "celery" in imp or "cron" in imp for imp in m.imports)
        for m in source_modules
    )
    if has_scheduler:
        actors.append(InferredActor(
            id=f"ACT-{len(actors) + 1}", name="Scheduler", actor_type="timer",
            evidence_source="scheduler_pattern",
        ))

    if not actors:
        actors.append(InferredActor(
            id="ACT-1", name="User", actor_type="human", evidence_source="default"
        ))

    return actors


def _infer_behaviors(
    inventory: Inventory,
    capabilities: list[InferredCapability],
    actors: list[InferredActor],
) -> list[InferredBehavior]:
    """Infer behaviors from route handlers and function call chains."""
    behaviors = []
    beh_counter = 0

    # One behavior per route
    for route in inventory.routes:
        beh_counter += 1
        actor_id = actors[0].id if actors else ""
        # Find matching capability
        prefix = _extract_prefix(route.path)
        cap_id = ""
        for cap in capabilities:
            if prefix.lower() in cap.name.lower():
                cap_id = cap.id
                break

        behaviors.append(InferredBehavior(
            id=f"BEH-{beh_counter}",
            name=f"{route.method} {route.path}",
            actor_id=actor_id,
            capability_id=cap_id,
            steps=[route.function_name],
        ))

    return behaviors


def _module_has_clear_purpose(mod: ModuleRecord, capabilities: list[InferredCapability]) -> bool:
    """Check if a module has a clear affiliation to any capability."""
    # Non-source modules are always "clear" (they don't need capabilities)
    if _is_non_source_module(mod):
        return True
    name = mod.path.stem
    # Utility/infra modules are fine without capability
    if name in ("__init__", "utils", "helpers", "common", "base", "constants", "types", "config", "conftest"):
        return True
    # Has capability mentioning it
    for cap in capabilities:
        if name.lower() in cap.name.lower() or name.lower() in cap.description.lower():
            return True
    return False
