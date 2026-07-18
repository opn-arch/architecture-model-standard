"""Manifest slicing for artifact context injection.

Provides focused markdown extracts from the manifest tailored to each
documentation artifact's needs.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from architecture_model.manifest.types import (
    BlockManifest,
    InterfaceEdge,
    Manifest,
    MetricsResult,
    ModuleInfo,
    ModuleStatus,
    ScanReport,
    SubFunctionEntry,
)

logger = logging.getLogger(__name__)


def _render_block_tree(sub_blocks: list[dict], indent: int = 1) -> list[str]:
    """Recursively render sub-block hierarchy as indented markdown lines."""
    lines: list[str] = []
    prefix = "  " * indent
    for sb in sub_blocks:
        status_tag = f"[{sb['status'].upper()}]" if sb.get("status") else ""
        desc = f" — {sb['description']}" if sb.get("description") else ""
        lines.append(f"{prefix}**{sb['id']}: {sb['name']}** {status_tag}{desc}")
        for sf in sb.get("sub_functions", []):
            sf_status = f"[{sf['status'].upper()}]" if sf.get("status") else ""
            loc = f", {sf['line_count']} LOC" if sf.get("line_count") else ""
            lines.append(f"{prefix}  - {sf['id']} {sf['name']} {sf_status} ({sf['file']}{loc})")
            for fn in sf.get("functions", [])[:3]:
                lines.append(f"{prefix}    - `{fn}`")
        # Recurse into nested sub-blocks
        if sb.get("sub_blocks"):
            lines.extend(_render_block_tree(sb["sub_blocks"], indent + 1))
    return lines


def _get_layer_prefixes() -> dict[str, str]:
    """Derive layer prefix map from config for module grouping.

    Returns dict mapping display name to directory prefix.
    Falls back to common defaults if config unavailable.
    """
    try:
        from architecture_model.config.loader import get_config

        config = get_config(Path("."))
        prefixes: dict[str, str] = {}
        for layer in config.layers:
            for d in layer.dirs:
                # Use directory basename as display label
                label = d.split("/")[-1] if "/" in d else d
                prefix = d if d.endswith("/") else d + "/"
                prefixes[label] = prefix
        if prefixes:
            return prefixes
    except Exception:
        pass
    # Fallback
    return {
        "models": "app/models/",
        "routers": "app/routers/",
        "schemas": "app/schemas/",
        "services": "app/services/",
        "scripts": "scripts/",
        "migrations": "alembic/versions/",
    }


def _manifest_from_dict(d: dict[str, Any]) -> Manifest:
    """Convert a raw manifest dict to a typed Manifest object.

    This provides backward compatibility for callers passing raw dicts.
    The conversion is best-effort — it wraps dict data into typed objects.
    """
    logger.debug("Converting raw dict manifest to typed Manifest")

    # Metrics
    raw_metrics = d.get("metrics", {})
    metrics = MetricsResult(values=dict(raw_metrics))

    # Modules — keep as dicts wrapped in a lightweight adapter
    raw_modules = d.get("modules", [])
    modules: list[ModuleInfo] = []
    for m in raw_modules:
        # Functions may be strings or dicts with 'name' key
        raw_fns = m.get("functions", [])
        from architecture_model.manifest.types import FunctionInfo
        func_list = []
        for f in raw_fns:
            if isinstance(f, str):
                func_list.append(FunctionInfo(name=f, signature=""))
            elif isinstance(f, dict):
                func_list.append(FunctionInfo(name=f.get("name", ""), signature=f.get("signature", "")))
            else:
                func_list.append(FunctionInfo(name=str(f), signature=""))

        # Classes may be strings or dicts
        raw_classes = m.get("classes", [])
        from architecture_model.manifest.types import ClassInfo
        class_list = []
        for c in raw_classes:
            if isinstance(c, str):
                class_list.append(ClassInfo(name=c))
            elif isinstance(c, dict):
                class_list.append(ClassInfo(
                    name=c.get("name", ""),
                    bases=c.get("bases", []),
                    methods=c.get("methods", []),
                    is_abstract=c.get("is_abstract", False),
                    decorators=c.get("decorators", []),
                    attributes=c.get("attributes", {}),
                ))

        status_raw = m.get("status", "active")
        try:
            status = ModuleStatus(status_raw)
        except ValueError:
            status = ModuleStatus.ACTIVE

        modules.append(ModuleInfo(
            file=m.get("file", ""),
            name=m.get("name", ""),
            docstring=m.get("docstring"),
            functions=func_list,
            imports=m.get("imports", []),
            line_count=m.get("line_count", 0),
            status=status,
            classes=class_list,
        ))

    # Interfaces
    raw_interfaces = d.get("interfaces", [])
    interfaces = [
        InterfaceEdge(
            source=i.get("source", ""),
            target=i.get("target", ""),
            import_path=i.get("import_path", ""),
        )
        for i in raw_interfaces
    ]

    # Functional blocks
    raw_blocks = d.get("functional_blocks", {})
    blocks: dict[str, BlockManifest] = {}
    for block_id, block_data in raw_blocks.items():
        raw_sfs = block_data.get("sub_functions", [])
        sfs = [
            SubFunctionEntry(
                id=sf.get("id", ""),
                name=sf.get("name", ""),
                file=sf.get("file", ""),
                functions=sf.get("functions", []),
                inputs=sf.get("inputs", []),
                outputs=sf.get("outputs", []),
                status=sf.get("status", "active"),
                line_count=sf.get("line_count", 0),
            )
            for sf in raw_sfs
        ]
        blocks[block_id] = BlockManifest(
            name=block_data.get("name", ""),
            status=block_data.get("status", "active"),
            description_source=block_data.get("description_source", ""),
            sub_functions=sfs,
            sub_blocks=block_data.get("sub_blocks", []),
        )

    return Manifest(
        generated_at=d.get("generated_at", ""),
        project_root=d.get("project_root", "."),
        metrics=metrics,
        functional_blocks=blocks,
        modules=modules,
        interfaces=interfaces,
        scan_report=ScanReport(),
    )


def _module_function_names(mod: ModuleInfo) -> list[str]:
    """Extract function names from a ModuleInfo."""
    return [f.name for f in mod.functions]


def _module_class_names(mod: ModuleInfo) -> list[str]:
    """Extract class names from a ModuleInfo."""
    return [c.name for c in mod.classes]


def get_manifest_slice(manifest: Manifest | dict[str, Any], artifact_name: str) -> str:
    """Return focused markdown slice for artifact context injection.

    Args:
        manifest: A typed Manifest or legacy raw dict.
        artifact_name: One of the 10 artifact names.

    Returns:
        Formatted markdown string with relevant manifest data.
    """
    if isinstance(manifest, dict):
        logger.debug("get_manifest_slice received dict, converting to Manifest")
        manifest = _manifest_from_dict(manifest)

    slicers = {
        "functional-architecture": _slice_functional_architecture,
        "logical-architecture": _slice_logical_architecture,
        "data-dictionary": _slice_data_dictionary,
        "icd": _slice_icd,
        "readme": _slice_readme,
        "testing": _slice_testing,
        "deployment-guide": _slice_deployment_guide,
        "operations-manual": _slice_operations_manual,
        "use-cases": _slice_use_cases,
        "requirements-analysis": _slice_requirements_analysis,
    }

    slicer = slicers.get(artifact_name)
    if slicer is None:
        return f"[unknown artifact: {artifact_name}]"

    return slicer(manifest)


def _slice_functional_architecture(manifest: Manifest) -> str:
    """Functional blocks + metrics."""
    lines = ["# Functional Architecture (from manifest)", ""]
    lines.append("## Metrics")
    for k, v in manifest.metrics.values.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Functional Blocks")
    for block_id, block in manifest.functional_blocks.items():
        lines.append(f"\n### {block_id}: {block.name} [{block.status}]")

        if block.sub_blocks:
            # Use hierarchical rendering
            lines.extend(_render_block_tree(block.sub_blocks))
        else:
            # Flat rendering (backward compat)
            for sf in block.sub_functions:
                status_tag = f"[{sf.status.upper()}]" if sf.status else ""
                lines.append(f"  - {sf.id} {sf.name} {status_tag} ({sf.file})")
                if sf.functions:
                    for fn in sf.functions[:3]:
                        lines.append(f"    - {fn}")
    return "\n".join(lines)


def _slice_logical_architecture(manifest: Manifest) -> str:
    """Modules grouped by layer + metrics."""
    lines = ["# Logical Architecture (from manifest)", ""]
    lines.append("## Metrics")
    for k, v in manifest.metrics.values.items():
        lines.append(f"- {k}: {v}")
    lines.append("")

    # Group modules by layer
    layer_prefixes = _get_layer_prefixes()
    layers: dict[str, list[ModuleInfo]] = {k: [] for k in layer_prefixes}
    layers["other"] = []

    for mod in manifest.modules:
        placed = False
        for layer_name, prefix in layer_prefixes.items():
            if mod.file.startswith(prefix):
                layers[layer_name].append(mod)
                placed = True
                break
        if not placed:
            layers["other"].append(mod)

    for layer_name, mods in layers.items():
        if mods:
            lines.append(f"\n## {layer_name.title()} ({len(mods)} files)")
            for mod in mods[:20]:  # Limit output
                status_val = mod.status.value if isinstance(mod.status, ModuleStatus) else mod.status
                lines.append(f"  - {mod.file} ({mod.line_count} lines, {status_val})")
            if len(mods) > 20:
                lines.append(f"  ... and {len(mods) - 20} more")

    return "\n".join(lines)


def _slice_data_dictionary(manifest: Manifest) -> str:
    """Modules from app/models/ + schema reference."""
    lines = ["# Data Dictionary (from manifest)", ""]
    for mod in manifest.modules:
        if mod.file.startswith("app/models/"):
            lines.append(f"\n## {mod.file}")
            if mod.docstring:
                lines.append(f"  {mod.docstring.split(chr(10))[0]}")
            for fn in _module_function_names(mod):
                lines.append(f"  - {fn}")
    return "\n".join(lines)


def _slice_icd(manifest: Manifest) -> str:
    """Comprehensive interface data: routers by F-block, external services, model access, pipeline stages."""
    lines = ["# Interface Control Document (from manifest)", ""]

    # --- Router endpoints grouped by functional domain ---
    lines.append("## Router Endpoints (F4: Serve API & UI)")
    routers = [m for m in manifest.modules if m.file.startswith("app/routers/")]
    for mod in sorted(routers, key=lambda m: m.file):
        lines.append(f"\n### {mod.file} ({mod.line_count} lines)")
        for fn in _module_function_names(mod):
            lines.append(f"  - {fn}")

    # --- External service interfaces (detected from imports + known patterns) ---
    lines.append("\n\n## External Service Interfaces (detected)")
    ext_services = {
        "Ollama (LLM classification)": "localhost:11434",
        "Copilot-relay (LLM generation)": "localhost:8400",
        "PostgreSQL + pgvector": "localhost:5432",
        "HuggingFace sentence-transformers": "offline cache",
    }
    for svc, endpoint in ext_services.items():
        lines.append(f"  - {svc} @ {endpoint}")

    # --- Import dependency graph (inter-layer interfaces) ---
    lines.append("\n\n## Inter-layer Import Dependencies")
    # Group by source prefix to show layer boundaries
    layer_deps: dict[str, list[str]] = {}
    for iface in manifest.interfaces:
        src_prefix = iface.source.split("/")[0] if "/" in iface.source else "root"
        tgt_prefix = iface.target.split("/")[0] if "/" in iface.target else "root"
        if src_prefix != tgt_prefix:  # only cross-layer
            key = f"{src_prefix} -> {tgt_prefix}"
            if key not in layer_deps:
                layer_deps[key] = []
            layer_deps[key].append(f"{iface.source} -> {iface.target}")
    for layer_boundary, deps in sorted(layer_deps.items()):
        lines.append(f"\n### {layer_boundary} ({len(deps)} dependencies)")
        for dep in deps[:10]:
            lines.append(f"  - {dep}")
        if len(deps) > 10:
            lines.append(f"  ... and {len(deps) - 10} more")

    # --- Pipeline stage modules (F6 + scripts/) ---
    lines.append("\n\n## Pipeline Stage Modules")
    pipeline_mods = [
        m for m in manifest.modules if m.file.startswith("scripts/_pipeline_")
    ]
    for mod in sorted(pipeline_mods, key=lambda m: m.file):
        fn_names = _module_function_names(mod)
        lines.append(
            f"  - {mod.file} ({mod.line_count} lines): {', '.join(fn_names[:5])}"
        )

    # --- Model files (database interface) ---
    lines.append("\n\n## Database Models (app/models/)")
    models = [m for m in manifest.modules if m.file.startswith("app/models/")]
    for mod in sorted(models, key=lambda m: m.file):
        classes = _module_class_names(mod)
        lines.append(f"  - {mod.file}: {', '.join(classes) if classes else '(no classes)'}")

    return "\n".join(lines)


def _slice_readme(manifest: Manifest) -> str:
    """Functional blocks summary + metrics."""
    lines = ["# Project Summary (from manifest)", ""]
    metrics = manifest.metrics.values
    lines.append(f"Total Python files: {metrics.get('total_python_files', '?')}")
    lines.append(
        f"Routers: {metrics.get('router_count', '?')}, "
        f"Models: {metrics.get('model_count', '?')}, "
        f"Migrations: {metrics.get('migration_count', '?')}, "
        f"Templates: {metrics.get('template_count', '?')}"
    )
    lines.append("")
    lines.append("## Functional Blocks")
    for block_id, block in manifest.functional_blocks.items():
        sf_count = len(block.sub_functions)
        sub_block_count = len(block.sub_blocks)
        extra = f", {sub_block_count} sub-blocks" if sub_block_count else ""
        lines.append(
            f"- {block_id}: {block.name} [{block.status}] ({sf_count} modules{extra})"
        )
    return "\n".join(lines)


def _slice_testing(manifest: Manifest) -> str:
    """Test files + coverage reference + sub-block mapping."""
    lines = ["# Testing (from manifest)", ""]
    test_modules = [m for m in manifest.modules if "test" in m.file.lower()]
    if test_modules:
        lines.append(f"## Test Files ({len(test_modules)})")
        for mod in test_modules:
            lines.append(f"  - {mod.file} ({mod.line_count} lines)")
    else:
        lines.append("No test files found in scanned modules.")

    # Sub-block test mapping
    lines.append("\n## Functional Block Test Coverage")
    for block_id, block in manifest.functional_blocks.items():
        if block.sub_blocks:
            lines.append(f"\n### {block_id}: {block.name}")
            lines.extend(_render_block_tree(block.sub_blocks))

    return "\n".join(lines)


def _slice_deployment_guide(manifest: Manifest) -> str:
    """Deployment-relevant metrics."""
    lines = ["# Deployment Guide (from manifest)", ""]
    metrics = manifest.metrics.values
    lines.append(f"- Migrations: {metrics.get('migration_count', '?')}")
    lines.append(f"- Models: {metrics.get('model_count', '?')}")
    lines.append(f"- Total Python files: {metrics.get('total_python_files', '?')}")
    lines.append("")
    lines.append("## Infrastructure Files")
    root = Path(manifest.project_root)
    infra_files = [
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "alembic.ini",
        ".env.example",
        "pyproject.toml",
        "requirements.txt",
    ]
    for f in infra_files:
        fp = root / f
        if fp.exists():
            lines.append(f"  - {f} (exists)")
        else:
            lines.append(f"  - {f} (not found)")
    return "\n".join(lines)


def _slice_operations_manual(manifest: Manifest) -> str:
    """Scheduler jobs + router endpoints + CLI commands."""
    lines = ["# Operations Manual (from manifest)", ""]

    # CLI commands (scripts with main or run_ functions)
    lines.append("## CLI / Pipeline Commands")
    for mod in manifest.modules:
        if mod.file.startswith("scripts/"):
            fn_names = _module_function_names(mod)
            run_fns = [f for f in fn_names if "run_" in f or "cmd_" in f]
            if run_fns:
                lines.append(f"\n### {mod.file}")
                for fn in run_fns:
                    lines.append(f"  - {fn}")

    # Router endpoints
    lines.append("\n## API Endpoints")
    for mod in manifest.modules:
        if mod.file.startswith("app/routers/"):
            lines.append(f"  - {mod.file}: {len(mod.functions)} endpoints")

    return "\n".join(lines)


def _slice_use_cases(manifest: Manifest) -> str:
    """Router endpoints + CLI commands + functional blocks summary for UC grounding."""
    lines = ["# Use Case Grounding (from manifest)", ""]

    # Functional blocks summary (for F-block traceability)
    lines.append("## Functional Blocks")
    for block_id, block in manifest.functional_blocks.items():
        sf_count = len(block.sub_functions)
        active = sum(1 for sf in block.sub_functions if sf.status == "active")
        sub_block_count = len(block.sub_blocks)
        extra = f", {sub_block_count} sub-blocks" if sub_block_count else ""
        lines.append(f"- {block_id}: {block.name} ({active}/{sf_count} active{extra})")
    lines.append("")

    # Router endpoints (user-facing capabilities)
    lines.append("## API Endpoints (Web UI capabilities)")
    for mod in manifest.modules:
        if mod.file.startswith("app/routers/"):
            lines.append(f"\n### {mod.file}")
            for fn in _module_function_names(mod):
                lines.append(f"  - {fn}")
    lines.append("")

    # CLI commands (pipeline capabilities)
    lines.append("## CLI Commands (Pipeline capabilities)")
    for mod in manifest.modules:
        if mod.file.startswith("scripts/"):
            fn_names = _module_function_names(mod)
            run_fns = [f for f in fn_names if "run_" in f or "cmd_" in f]
            if run_fns:
                lines.append(f"  - {mod.file}:")
                for fn in run_fns:
                    lines.append(f"    - {fn}")
    lines.append("")

    # Scheduler jobs
    lines.append("## Scheduled Jobs")
    for mod in manifest.modules:
        if "scheduler" in mod.file.lower() or "main" in mod.file.lower():
            fn_names = _module_function_names(mod)
            sched_fns = [
                f
                for f in fn_names
                if "daily" in f or "register" in f or "schedule" in f
            ]
            if sched_fns:
                lines.append(f"  - {mod.file}:")
                for fn in sched_fns:
                    lines.append(f"    - {fn}")

    return "\n".join(lines)


def _slice_requirements_analysis(manifest: Manifest) -> str:
    """System metrics, capabilities, and F-block coverage for requirements grounding."""
    lines = ["# Requirements Analysis (from manifest)", ""]

    # --- Hard metrics (ground truth for NFRs) ---
    metrics = manifest.metrics.values
    lines.append("## System Metrics (verified)")
    lines.append(f"- Total Python files: {metrics.get('total_python_files', '?')}")
    lines.append(f"- Routers: {metrics.get('router_count', '?')}")
    lines.append(f"- Models: {metrics.get('model_count', '?')}")
    lines.append(f"- Migrations: {metrics.get('migration_count', '?')}")
    lines.append(f"- Templates: {metrics.get('template_count', '?')}")
    lines.append(f"- Interfaces (import deps): {len(manifest.interfaces)}")
    lines.append(f"- Modules scanned: {len(manifest.modules)}")

    # --- Functional blocks with sub-function counts (ground truth for FRs) ---
    lines.append("\n## Functional Blocks (capability inventory)")
    for block_id, block in manifest.functional_blocks.items():
        sfs = block.sub_functions
        active = sum(1 for sf in sfs if sf.status == "active")
        lines.append(
            f"\n### {block_id}: {block.name} [{block.status}] ({active}/{len(sfs)} active)"
        )

        if block.sub_blocks:
            # Use hierarchical rendering for requirement traceability
            lines.extend(_render_block_tree(block.sub_blocks))
        else:
            # Flat rendering (backward compat)
            for sf in sfs:
                lines.append(f"  - {sf.name} [{sf.status}]")

    # --- All router capabilities (what the system CAN do via API) ---
    lines.append("\n## API Capabilities (30 routers)")
    routers = [m for m in manifest.modules if m.file.startswith("app/routers/")]
    for mod in sorted(routers, key=lambda m: m.file):
        fn_count = len(mod.functions)
        lines.append(f"  - {mod.file}: {fn_count} endpoints")

    # --- Pipeline capabilities (what the system CAN do via CLI) ---
    lines.append("\n## Pipeline Capabilities")
    pipeline_mods = [
        m
        for m in manifest.modules
        if m.file.startswith("scripts/_pipeline_") and not m.file.endswith("__pycache__")
    ]
    for mod in sorted(pipeline_mods, key=lambda m: m.file):
        fn_names = _module_function_names(mod)
        run_fns = [f for f in fn_names if f.startswith("run_")]
        if run_fns:
            lines.append(f"  - {mod.file}: {', '.join(run_fns)}")

    # --- Test coverage (ground truth for verification) ---
    lines.append("\n## Test Files")
    test_mods = [m for m in manifest.modules if "test" in m.file.lower()]
    lines.append(f"  Total test files: {len(test_mods)}")
    for mod in test_mods[:20]:
        lines.append(f"  - {mod.file} ({mod.line_count} lines)")
    if len(test_mods) > 20:
        lines.append(f"  ... and {len(test_mods) - 20} more")

    return "\n".join(lines)
