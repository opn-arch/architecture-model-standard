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


def _infer_fallback_capabilities(modules: list, existing: list) -> list:
    """Fallback: if no capabilities found, treat packages with >3 public functions as capabilities."""
    if existing:
        return []

    from architecture_model.pipeline.infer_types import InferredCapability

    # Group by top-level package
    package_functions: dict[str, int] = {}
    for mod in modules:
        # Get top-level package from module path
        parts = getattr(mod, "file", "") if isinstance(mod, str) else str(getattr(mod, "file", ""))
        path_parts = parts.replace("\\", "/").split("/")
        # Find src-relative package name
        pkg = None
        for i, p in enumerate(path_parts):
            if p == "src" and i + 1 < len(path_parts):
                pkg = path_parts[i + 1] if i + 2 < len(path_parts) else path_parts[i + 1]
                if i + 2 < len(path_parts):
                    pkg = path_parts[i + 2]
                break
        if not pkg or pkg.startswith("_"):
            continue

        # Count public functions
        funcs = getattr(mod, "functions", [])
        public = [
            f
            for f in funcs
            if not (getattr(f, "name", "") or f if isinstance(f, str) else "").startswith("_")
        ]
        package_functions[pkg] = package_functions.get(pkg, 0) + len(public)

    # Create capability per package with >3 public functions
    caps = []
    for pkg, count in sorted(package_functions.items(), key=lambda x: -x[1]):
        if count > 3:
            cap_id = f"CAP-{pkg.replace('_', '-')}"
            caps.append(
                InferredCapability(
                    id=cap_id,
                    name=f"Provide {pkg.replace('_', ' ').title()} functionality",
                    description=f"Package '{pkg}' exposes {count} public functions",
                    evidence_source=f"fallback:package:{pkg}",
                )
            )

    return caps


class InferStage:
    """Infers capabilities, actors, and behaviors from observed Inventory."""

    name: str = "infer"
    requires: list[str] = ["observe"]

    @staticmethod
    def _get_large_repo_threshold(ctx: PipelineContext) -> int:
        """Get large repo threshold, checking global heuristics first."""
        if ctx.global_learning:
            rules = ctx.global_learning.get_heuristics(stage="infer")
            for rule in rules:
                if rule.threshold.get("parameter") == "LARGE_REPO_MODULE_THRESHOLD":
                    return int(rule.threshold["value"])
        return _LARGE_REPO_MODULE_THRESHOLD

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
                1
                for m in inventory.modules
                if not _is_non_source_module(m)
                and m.path.stem
                not in ("utils", "helpers", "common", "base", "constants", "types", "config")
            )
            if source_count > self._get_large_repo_threshold(ctx):
                # Single "Web Routes" capability for all routes
                cap_counter += 1
                capabilities.append(
                    InferredCapability(
                        id=f"CAP-{cap_counter}",
                        name="Web Routes",
                        description=f"HTTP routing ({len(inventory.routes)} endpoints)",
                        evidence_source="routes",
                    )
                )
                # Still infer actors from routes
                has_auth = any(r.is_authenticated for r in inventory.routes)
                actors.append(
                    InferredActor(
                        id="ACT-1",
                        name="API Consumer",
                        actor_type="system" if not has_auth else "human",
                        evidence_source="routes",
                    )
                )
            else:
                route_caps, route_actors = _infer_from_routes(inventory.routes)
                for cap in route_caps:
                    cap_counter += 1
                    cap.id = f"CAP-{cap_counter}"
                    capabilities.append(cap)
                actors.extend(route_actors)

        # --- Strategy 1b: WebSocket, gRPC, scheduled task triggers ---
        trigger_caps = _infer_from_triggers(inventory.modules)
        for cap in trigger_caps:
            cap_counter += 1
            cap.id = f"CAP-{cap_counter}"
            capabilities.append(cap)

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

        # --- Strategy 4: Infrastructure file detection ---
        infra_caps = _infer_infrastructure_capabilities(inventory.modules, capabilities)
        for cap in infra_caps:
            cap_counter += 1
            cap.id = f"CAP-{cap_counter}"
            capabilities.append(cap)

        # --- Actors: infer from auth patterns, CLI entry points ---
        if not actors:
            actors = _infer_default_actors(inventory)

        # --- Behaviors: from trigger chains (route → function → calls) ---
        behaviors, behavior_uncertainties = _infer_behaviors(inventory, capabilities, actors)
        uncertainties.extend(behavior_uncertainties)

        # --- Library behaviors: for capabilities without existing behaviors ---
        caps_with_behaviors = {b.capability_id for b in behaviors if b.capability_id}
        lib_modules = [m for m in inventory.modules if not _is_non_source_module(m)]
        lib_behaviors = _infer_library_behaviors(lib_modules, capabilities, actors)
        # Only add library behaviors for capabilities not already covered
        for lb in lib_behaviors:
            if not lb.capability_id or lb.capability_id not in caps_with_behaviors:
                behaviors.append(lb)

        # --- Uncertainties for ambiguous modules ---
        for mod in inventory.modules:
            if not _module_has_clear_purpose(mod, capabilities):
                uncertainties.append(
                    Uncertainty(
                        category="ambiguous_module",
                        description=f"{mod.path} has no clear capability affiliation",
                        suggested_fallback="llm_analysis",
                        priority="informational",
                    )
                )

        # Fallback if no capabilities from primary strategies
        if not capabilities:
            fallback_caps = _infer_fallback_capabilities(inventory.modules, capabilities)
            capabilities.extend(fallback_caps)

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
                            diagnostics.append(
                                Diagnostic(
                                    severity="info",
                                    code="correction_applied",
                                    message=f"Renamed {cap.id} to '{new_name}' (prior correction)",
                                )
                            )
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
            summary=f"Inferred {len(capabilities)} capabilities, {len(actors)} actors, and {len(behaviors)} behaviors.",
        )


def _infer_from_routes(
    routes: list[RouteRecord],
) -> tuple[list[InferredCapability], list[InferredActor]]:
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
        actors.append(
            InferredActor(
                id="ACT-1",
                name="API Consumer",
                actor_type="system" if not has_auth else "human",
                evidence_source="routes",
            )
        )

    return capabilities, actors


def _extract_prefix(path: str) -> str:
    """Extract first meaningful path segment: /users/{id} → users."""
    parts = [p for p in path.strip("/").split("/") if p and not p.startswith("{")]
    return parts[0] if parts else "root"


# Directories that contain non-source modules (tests, examples, docs, etc.)
_NON_SOURCE_DIRS = frozenset(
    {
        "tests",
        "test",
        "testing",
        "examples",
        "example",
        "demos",
        "demo",
        "docs",
        "doc",
        "typing_tests",
        "benchmarks",
        "fixtures",
        "_unicode_data",
    }
)


def _is_non_source_module(mod: ModuleRecord) -> bool:
    """Check if a module is in a non-source directory (tests, examples, etc.)."""
    name = mod.path.stem
    if name.startswith("test_") or name.endswith("_test"):
        return True
    if name in ("conftest", "setup"):
        return True
    if name == "__init__":
        # Keep __init__.py if it has real code (functions, classes, or >10 lines)
        has_code = bool(mod.functions or mod.classes) or mod.line_count > 10
        return not has_code
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
    modules: list[ModuleRecord],
    existing: list[InferredCapability],
    *,
    scoped: bool = False,
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
        mod
        for mod in modules
        if not _is_non_source_module(mod)
        and mod.path.stem
        not in ("utils", "helpers", "common", "base", "constants", "types", "config")
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
                capabilities.append(
                    InferredCapability(
                        id="",
                        name=cap_name,
                        description=f"Domain logic in {mod.path}",
                        evidence_source="domain_module",
                    )
                )
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
            capabilities.append(
                InferredCapability(
                    id="",
                    name=cap_name,
                    description=f"Package group with {len(mods)} modules",
                    evidence_source="package_group",
                )
            )
            existing_names.add(cap_name.lower())

    return capabilities


def _infer_from_triggers(modules: list[ModuleRecord]) -> list[InferredCapability]:
    """Detect WebSocket handlers, gRPC services, and scheduled tasks."""
    capabilities: list[InferredCapability] = []
    has_websocket = False
    has_grpc = False
    has_scheduled = False

    for mod in modules:
        if _is_non_source_module(mod):
            continue
        for imp in mod.imports:
            # WebSocket detection
            if any(kw in imp for kw in ("websocket", "socketio", "channels", "ws_handler")):
                has_websocket = True
            # gRPC detection
            if any(kw in imp for kw in ("grpc", "grpcio", "proto")):
                has_grpc = True
            # Scheduled task detection (celery, apscheduler, cron)
            if any(
                kw in imp
                for kw in ("celery", "apscheduler", "schedule", "crontab", "periodic_task")
            ):
                has_scheduled = True

    if has_websocket:
        capabilities.append(
            InferredCapability(
                id="",
                name="WebSocket Handlers",
                description="Real-time WebSocket communication endpoints",
                evidence_source="websocket_pattern",
            )
        )
    if has_grpc:
        capabilities.append(
            InferredCapability(
                id="",
                name="gRPC Services",
                description="gRPC service definitions and handlers",
                evidence_source="grpc_pattern",
            )
        )
    if has_scheduled:
        capabilities.append(
            InferredCapability(
                id="",
                name="Scheduled Tasks",
                description="Periodic/scheduled task execution (cron/celery)",
                evidence_source="scheduler_pattern",
            )
        )

    return capabilities


def _infer_from_cli(modules: list[ModuleRecord]) -> list[InferredCapability]:
    """Infer capabilities from CLI command modules."""
    capabilities = []
    for mod in modules:
        if _is_non_source_module(mod):
            continue
        # Check for click/typer/argparse patterns
        has_cli = any("click" in imp or "typer" in imp or "argparse" in imp for imp in mod.imports)
        if has_cli and mod.path.stem not in ("__init__",):
            capabilities.append(
                InferredCapability(
                    id="",
                    name=f"CLI {mod.path.stem.replace('_', ' ').title()}",
                    description=f"CLI commands in {mod.path}",
                    evidence_source="cli_pattern",
                )
            )
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
        actors.append(
            InferredActor(
                id="ACT-1", name="CLI User", actor_type="human", evidence_source="cli_pattern"
            )
        )

    # Check for scheduled/timer patterns
    has_scheduler = any(
        any("schedule" in imp or "celery" in imp or "cron" in imp for imp in m.imports)
        for m in source_modules
    )
    if has_scheduler:
        actors.append(
            InferredActor(
                id=f"ACT-{len(actors) + 1}",
                name="Scheduler",
                actor_type="timer",
                evidence_source="scheduler_pattern",
            )
        )

    if not actors:
        actors.append(
            InferredActor(id="ACT-1", name="User", actor_type="human", evidence_source="default")
        )

    return actors


def _infer_behaviors(
    inventory: Inventory,
    capabilities: list[InferredCapability],
    actors: list[InferredActor],
) -> tuple[list[InferredBehavior], list[Uncertainty]]:
    """Infer behaviors from route handlers and function call chains."""
    behaviors = []
    uncertainties: list[Uncertainty] = []
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

        behaviors.append(
            InferredBehavior(
                id=f"BEH-{beh_counter}",
                name=f"{route.method} {route.path}",
                actor_id=actor_id,
                capability_id=cap_id,
                steps=[route.function_name],
                behavior_type="route_handler",
            )
        )

    # CLI command use cases
    CLI_IMPORTS = {"click", "typer", "argparse"}
    CLI_FUNC_NAMES = {"handle", "main", "run", "execute"}
    CLI_DECORATORS = {"command", "click"}

    for mod in inventory.modules:
        has_cli_import = any(cli_imp in imp for imp in mod.imports for cli_imp in CLI_IMPORTS)
        if not has_cli_import:
            continue

        for func in mod.functions:
            is_cli_func = func.name in CLI_FUNC_NAMES or any(
                any(dec_kw in dec.lower() for dec_kw in CLI_DECORATORS) for dec in func.decorators
            )
            if not is_cli_func:
                continue

            beh_counter += 1
            stem = mod.path.stem.replace("_", " ").title()
            behaviors.append(
                InferredBehavior(
                    id=f"BEH-{beh_counter}",
                    name=f"CLI: {stem}",
                    actor_id=actors[0].id if actors else "",
                    steps=func.calls[:5],
                    behavior_type="use_case",
                )
            )

    # Handler/view class use cases
    HANDLER_BASES = {"view", "handler", "command"}

    for mod in inventory.modules:
        for cls in mod.classes:
            if cls.name.startswith("_") or cls.name.lower().startswith("test"):
                continue
            bases_lower = [b.lower() for b in cls.bases]
            is_handler = any(kw in base for base in bases_lower for kw in HANDLER_BASES)
            if not is_handler:
                continue

            public_methods = [m for m in cls.methods if not m.startswith("_")]
            if not public_methods:
                continue

            beh_counter += 1
            behaviors.append(
                InferredBehavior(
                    id=f"BEH-{beh_counter}",
                    name=cls.name,
                    actor_id=actors[0].id if actors else "",
                    steps=public_methods,
                    behavior_type="use_case",
                )
            )

    # Workflow behaviors from ordered method patterns
    WORKFLOW_PATTERNS = {
        "middleware": {
            "bases": ["middleware", "mixin"],
            "ordered_methods": [
                "process_request",
                "process_view",
                "process_response",
                "process_exception",
            ],
        },
        "lifecycle": {
            "bases": ["model", "form", "serializer"],
            "ordered_methods": ["clean", "validate", "save", "delete"],
        },
    }

    for mod in inventory.modules:
        for cls in mod.classes:
            if cls.name.startswith("_") or cls.name.lower().startswith("test"):
                continue
            bases_lower = [b.lower() for b in cls.bases]

            for pattern_name, pattern in WORKFLOW_PATTERNS.items():
                base_match = any(kw in base for base in bases_lower for kw in pattern["bases"])
                if not base_match:
                    continue

                matched = [m for m in pattern["ordered_methods"] if m in cls.methods]
                if len(matched) < 2:
                    continue

                beh_counter += 1
                behaviors.append(
                    InferredBehavior(
                        id=f"BEH-{beh_counter}",
                        name=f"{cls.name} {pattern_name} workflow",
                        steps=matched,
                        behavior_type="workflow",
                    )
                )

    # --- Uncertainty: Complex classes (≥15 public methods) ---
    COMPLEX_METHOD_THRESHOLD = 15
    for mod in inventory.modules:
        for cls in mod.classes:
            if cls.name.startswith("_") or "Test" in cls.name:
                continue
            public_methods = [m for m in cls.methods if not m.startswith("_")]
            if len(public_methods) >= COMPLEX_METHOD_THRESHOLD:
                uncertainties.append(
                    Uncertainty(
                        category="complex_behavior",
                        description=f"{cls.name} in {mod.path} has {len(public_methods)} public methods — needs LLM analysis to identify key workflows and use cases",
                        context={
                            "class": cls.name,
                            "file": str(mod.path),
                            "methods": public_methods[:20],
                            "method_count": len(public_methods),
                        },
                        suggested_fallback=f"Create generic workflow for {cls.name}",
                        priority="medium",
                    )
                )

    # --- Uncertainty: Modules with many cross-calling functions ---
    MODULE_FUNCTION_THRESHOLD = 10
    for mod in inventory.modules:
        public_funcs = [f for f in mod.functions if not f.name.startswith("_")]
        if len(public_funcs) >= MODULE_FUNCTION_THRESHOLD:
            func_names = {f.name for f in public_funcs}
            cross_calls = sum(1 for f in public_funcs for c in (f.calls or []) if c in func_names)
            if cross_calls >= 3:
                uncertainties.append(
                    Uncertainty(
                        category="complex_behavior",
                        description=f"{mod.path} has {len(public_funcs)} public functions with {cross_calls} cross-calls — likely contains workflow patterns",
                        context={
                            "file": str(mod.path),
                            "functions": [f.name for f in public_funcs[:15]],
                            "cross_calls": cross_calls,
                        },
                        suggested_fallback=f"Create module-level workflow for {mod.path.stem}",
                        priority="medium",
                    )
                )

    # --- Cap: max 40 behaviors per capability (component proxy) ---
    MAX_BEHAVIORS_PER_COMPONENT = 40
    cap_groups: dict[str, list[InferredBehavior]] = defaultdict(list)
    for beh in behaviors:
        key = beh.capability_id or "__uncapped__"
        cap_groups[key].append(beh)

    capped: list[InferredBehavior] = []
    for key, group in cap_groups.items():
        if key == "__uncapped__" or len(group) <= MAX_BEHAVIORS_PER_COMPONENT:
            capped.extend(group)
        else:
            # Keep behaviors with the most steps (proxy for complexity)
            group.sort(key=lambda b: len(b.steps), reverse=True)
            capped.extend(group[:MAX_BEHAVIORS_PER_COMPONENT])
    behaviors = capped

    return behaviors, uncertainties


# Infrastructure detection patterns
_INFRA_PATTERNS = {
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".env.example",
    "Makefile",
    "Procfile",
    "fly.toml",
    "nginx.conf",
    "supervisord.conf",
}
_MIGRATION_DIRS = {"alembic", "migrations", "prisma"}
_CONFIG_FILES = {"config.py", "settings.py", "pyproject.toml", "setup.cfg"}


def _infer_infrastructure_capabilities(
    modules: list[ModuleRecord], existing: list[InferredCapability]
) -> list[InferredCapability]:
    """Detect infrastructure, migration, and config files and create capabilities."""
    existing_names = {c.name.lower() for c in existing}
    capabilities: list[InferredCapability] = []

    has_infra = False
    has_migrations = False
    has_config = False

    for mod in modules:
        filename = mod.path.name
        parts = set(mod.path.parts[:-1])  # directory components

        if filename in _INFRA_PATTERNS:
            has_infra = True
        if parts & _MIGRATION_DIRS:
            has_migrations = True
        if filename in _CONFIG_FILES:
            has_config = True

    if has_infra and "infrastructure & deployment" not in existing_names:
        capabilities.append(
            InferredCapability(
                id="",
                name="Infrastructure & Deployment",
                description="Infrastructure and deployment configuration files",
                evidence_source="infra_pattern",
            )
        )

    if has_migrations and "database migrations" not in existing_names:
        capabilities.append(
            InferredCapability(
                id="",
                name="Database Migrations",
                description="Database migration and schema management",
                evidence_source="infra_pattern",
            )
        )

    if has_config and "configuration" not in existing_names:
        capabilities.append(
            InferredCapability(
                id="",
                name="Configuration",
                description="Application configuration files",
                evidence_source="infra_pattern",
            )
        )

    return capabilities


# ---------------------------------------------------------------------------
# Library behavior inference — detects behaviors in pure libraries
# ---------------------------------------------------------------------------

_API_ENTRY_VERBS = frozenset({
    "init", "setup", "configure", "create", "build", "connect", "open", "close",
    "load", "run", "start", "stop", "deinit", "shutdown", "teardown", "destroy",
    "reset",
})

_LIFECYCLE_PAIRS = [
    ("open", "close"), ("connect", "disconnect"), ("start", "stop"),
    ("acquire", "release"), ("lock", "unlock"), ("setup", "teardown"),
    ("init", "deinit"), ("begin", "end"),
]

_PROCESSING_CHAINS = [
    ["parse", "validate", "apply"],
    ["read", "process", "write"],
    ["load", "transform", "save"],
    ["encode", "decode"],
    ["serialize", "deserialize"],
    ["compress", "decompress"],
    ["encrypt", "decrypt"],
    ["pack", "unpack"],
    ["marshal", "unmarshal"],
    ["tokenize", "parse"],
]


def _infer_library_behaviors(
    source_modules: list[ModuleRecord],
    capabilities: list[InferredCapability],
    actors: list,
) -> list[InferredBehavior]:
    """Infer behaviors from pure-library patterns (no routes/CLI needed)."""
    behaviors: list[InferredBehavior] = []
    counter = 0

    # Build cap lookup: module stem → capability id
    cap_by_mod: dict[str, str] = {}
    for cap in capabilities:
        # Match by module stem in description or name
        for mod in source_modules:
            stem = mod.path.stem
            if stem.lower() in cap.description.lower() or stem.lower() in cap.name.lower():
                cap_by_mod[stem] = cap.id

    for mod in source_modules:
        if _is_non_source_module(mod):
            continue

        stem = mod.path.stem
        mod_label = stem.replace("_", " ").title()
        cap_id = cap_by_mod.get(stem, "")

        public_funcs = [f for f in mod.functions if not f.name.startswith("_")]
        func_names = {f.name for f in public_funcs}

        # 1. API entry points
        for func in public_funcs:
            base = func.name.split("_")[0] if "_" in func.name else func.name
            if base in _API_ENTRY_VERBS or func.name in _API_ENTRY_VERBS:
                verb = func.name.replace("_", " ").title()
                counter += 1
                behaviors.append(InferredBehavior(
                    id=f"BEH-LIB-{counter}",
                    name=f"{verb} {mod_label}",
                    capability_id=cap_id,
                    steps=[func.name],
                    behavior_type="library_api",
                ))

        # 2. Context managers
        for cls in mod.classes:
            if cls.name.startswith("_"):
                continue
            methods = set(cls.methods)
            if "__enter__" in methods and "__exit__" in methods:
                counter += 1
                behaviors.append(InferredBehavior(
                    id=f"BEH-LIB-{counter}",
                    name=f"{cls.name} context management",
                    capability_id=cap_id,
                    steps=["__enter__", "__exit__"],
                    behavior_type="use_case",
                ))

        # 3. Lifecycle pairs
        for cls in mod.classes:
            if cls.name.startswith("_"):
                continue
            methods = set(cls.methods)
            for a, b in _LIFECYCLE_PAIRS:
                if a in methods and b in methods:
                    counter += 1
                    behaviors.append(InferredBehavior(
                        id=f"BEH-LIB-{counter}",
                        name=f"{cls.name} lifecycle",
                        capability_id=cap_id,
                        steps=[a, b],
                        behavior_type="workflow",
                    ))
                    break  # one lifecycle behavior per class

        # 4. Processing chains
        if len(public_funcs) >= 2:
            for chain in _PROCESSING_CHAINS:
                matched = [name for name in chain if name in func_names]
                if len(matched) >= 2:
                    counter += 1
                    behaviors.append(InferredBehavior(
                        id=f"BEH-LIB-{counter}",
                        name=f"{mod_label} processing pipeline",
                        capability_id=cap_id,
                        steps=matched,
                        behavior_type="workflow",
                    ))
                    break  # one chain per module

        # 5. Factory/builder
        for func in public_funcs:
            if func.name.startswith(("create_", "make_", "build_")):
                obj = func.name.split("_", 1)[1].replace("_", " ").title()
                counter += 1
                behaviors.append(InferredBehavior(
                    id=f"BEH-LIB-{counter}",
                    name=f"Create {obj}",
                    capability_id=cap_id,
                    steps=[func.name],
                    behavior_type="use_case",
                ))

        for cls in mod.classes:
            if cls.name.startswith("_"):
                continue
            if "Factory" in cls.name or "Builder" in cls.name:
                obj = cls.name.replace("Factory", "").replace("Builder", "").strip()
                if not obj:
                    obj = mod_label
                counter += 1
                behaviors.append(InferredBehavior(
                    id=f"BEH-LIB-{counter}",
                    name=f"Create {obj}",
                    capability_id=cap_id,
                    steps=[m for m in cls.methods if not m.startswith("_")][:5],
                    behavior_type="use_case",
                ))

    return behaviors


def _module_has_clear_purpose(mod: ModuleRecord, capabilities: list[InferredCapability]) -> bool:
    """Check if a module has a clear affiliation to any capability."""
    # Non-source modules are always "clear" (they don't need capabilities)
    if _is_non_source_module(mod):
        return True
    name = mod.path.stem
    # Utility/infra modules are fine without capability
    if name in (
        "__init__",
        "utils",
        "helpers",
        "common",
        "base",
        "constants",
        "types",
        "config",
        "conftest",
    ):
        return True
    # Has capability mentioning it
    for cap in capabilities:
        if name.lower() in cap.name.lower() or name.lower() in cap.description.lower():
            return True
    return False
