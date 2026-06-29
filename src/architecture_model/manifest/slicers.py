"""Manifest slicing for artifact context injection.

Provides focused markdown extracts from the manifest tailored to each
documentation artifact's needs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


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


def get_manifest_slice(manifest: dict[str, Any], artifact_name: str) -> str:
    """Return focused markdown slice for artifact context injection.

    Args:
        manifest: The full manifest dictionary.
        artifact_name: One of the 10 artifact names.

    Returns:
        Formatted markdown string with relevant manifest data.
    """
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


def _slice_functional_architecture(manifest: dict) -> str:
    """Functional blocks + metrics."""
    lines = ["# Functional Architecture (from manifest)", ""]
    lines.append("## Metrics")
    for k, v in manifest.get("metrics", {}).items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Functional Blocks")
    for block_id, block in manifest.get("functional_blocks", {}).items():
        lines.append(f"\n### {block_id}: {block['name']} [{block['status']}]")
        for sf in block.get("sub_functions", []):
            status_tag = f"[{sf['status'].upper()}]" if sf.get("status") else ""
            lines.append(f"  - {sf['id']} {sf['name']} {status_tag} ({sf['file']})")
            if sf.get("functions"):
                for fn in sf["functions"][:3]:
                    lines.append(f"    - {fn}")
    return "\n".join(lines)


def _slice_logical_architecture(manifest: dict) -> str:
    """Modules grouped by layer + metrics."""
    lines = ["# Logical Architecture (from manifest)", ""]
    lines.append("## Metrics")
    for k, v in manifest.get("metrics", {}).items():
        lines.append(f"- {k}: {v}")
    lines.append("")

    # Group modules by layer
    layer_prefixes = _get_layer_prefixes()
    layers: dict[str, list[dict]] = {k: [] for k in layer_prefixes}
    layers["other"] = []

    for mod in manifest.get("modules", []):
        placed = False
        for layer_name, prefix in layer_prefixes.items():
            if mod["file"].startswith(prefix):
                layers[layer_name].append(mod)
                placed = True
                break
        if not placed:
            layers["other"].append(mod)

    for layer_name, mods in layers.items():
        if mods:
            lines.append(f"\n## {layer_name.title()} ({len(mods)} files)")
            for mod in mods[:20]:  # Limit output
                lines.append(f"  - {mod['file']} ({mod['line_count']} lines, {mod['status']})")
            if len(mods) > 20:
                lines.append(f"  ... and {len(mods) - 20} more")

    return "\n".join(lines)


def _slice_data_dictionary(manifest: dict) -> str:
    """Modules from app/models/ + schema reference."""
    lines = ["# Data Dictionary (from manifest)", ""]
    for mod in manifest.get("modules", []):
        if mod["file"].startswith("app/models/"):
            lines.append(f"\n## {mod['file']}")
            if mod.get("docstring"):
                lines.append(f"  {mod['docstring'].split(chr(10))[0]}")
            for fn in mod.get("functions", []):
                lines.append(f"  - {fn}")
    return "\n".join(lines)


def _slice_icd(manifest: dict) -> str:
    """Comprehensive interface data: routers by F-block, external services, model access, pipeline stages."""
    lines = ["# Interface Control Document (from manifest)", ""]

    # --- Router endpoints grouped by functional domain ---
    lines.append("## Router Endpoints (F4: Serve API & UI)")
    routers = [m for m in manifest.get("modules", []) if m["file"].startswith("app/routers/")]
    for mod in sorted(routers, key=lambda m: m["file"]):
        lines.append(f"\n### {mod['file']} ({mod.get('line_count', '?')} lines)")
        for fn in mod.get("functions", []):
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
    interfaces = manifest.get("interfaces", [])
    # Group by source prefix to show layer boundaries
    layer_deps: dict[str, list[str]] = {}
    for iface in interfaces:
        src_prefix = iface["source"].split("/")[0] if "/" in iface["source"] else "root"
        tgt_prefix = iface["target"].split("/")[0] if "/" in iface["target"] else "root"
        if src_prefix != tgt_prefix:  # only cross-layer
            key = f"{src_prefix} -> {tgt_prefix}"
            if key not in layer_deps:
                layer_deps[key] = []
            layer_deps[key].append(f"{iface['source']} -> {iface['target']}")
    for layer_boundary, deps in sorted(layer_deps.items()):
        lines.append(f"\n### {layer_boundary} ({len(deps)} dependencies)")
        for dep in deps[:10]:
            lines.append(f"  - {dep}")
        if len(deps) > 10:
            lines.append(f"  ... and {len(deps) - 10} more")

    # --- Pipeline stage modules (F6 + scripts/) ---
    lines.append("\n\n## Pipeline Stage Modules")
    pipeline_mods = [
        m for m in manifest.get("modules", []) if m["file"].startswith("scripts/_pipeline_")
    ]
    for mod in sorted(pipeline_mods, key=lambda m: m["file"]):
        lines.append(
            f"  - {mod['file']} ({mod.get('line_count', '?')} lines): {', '.join(mod.get('functions', [])[:5])}"
        )

    # --- Model files (database interface) ---
    lines.append("\n\n## Database Models (app/models/)")
    models = [m for m in manifest.get("modules", []) if m["file"].startswith("app/models/")]
    for mod in sorted(models, key=lambda m: m["file"]):
        classes = mod.get("classes", [])
        lines.append(f"  - {mod['file']}: {', '.join(classes) if classes else '(no classes)'}")

    return "\n".join(lines)


def _slice_readme(manifest: dict) -> str:
    """Functional blocks summary + metrics."""
    lines = ["# Project Summary (from manifest)", ""]
    metrics = manifest.get("metrics", {})
    lines.append(f"Total Python files: {metrics.get('total_python_files', '?')}")
    lines.append(
        f"Routers: {metrics.get('router_count', '?')}, "
        f"Models: {metrics.get('model_count', '?')}, "
        f"Migrations: {metrics.get('migration_count', '?')}, "
        f"Templates: {metrics.get('template_count', '?')}"
    )
    lines.append("")
    lines.append("## Functional Blocks")
    for block_id, block in manifest.get("functional_blocks", {}).items():
        sf_count = len(block.get("sub_functions", []))
        lines.append(
            f"- {block_id}: {block['name']} [{block['status']}] ({sf_count} sub-functions)"
        )
    return "\n".join(lines)


def _slice_testing(manifest: dict) -> str:
    """Test files + coverage reference."""
    lines = ["# Testing (from manifest)", ""]
    test_modules = [m for m in manifest.get("modules", []) if "test" in m["file"].lower()]
    if test_modules:
        lines.append(f"## Test Files ({len(test_modules)})")
        for mod in test_modules:
            lines.append(f"  - {mod['file']} ({mod['line_count']} lines)")
    else:
        lines.append("No test files found in scanned modules.")
    return "\n".join(lines)


def _slice_deployment_guide(manifest: dict) -> str:
    """Deployment-relevant metrics."""
    lines = ["# Deployment Guide (from manifest)", ""]
    metrics = manifest.get("metrics", {})
    lines.append(f"- Migrations: {metrics.get('migration_count', '?')}")
    lines.append(f"- Models: {metrics.get('model_count', '?')}")
    lines.append(f"- Total Python files: {metrics.get('total_python_files', '?')}")
    lines.append("")
    lines.append("## Infrastructure Files")
    root = Path(manifest.get("project_root", "."))
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


def _slice_operations_manual(manifest: dict) -> str:
    """Scheduler jobs + router endpoints + CLI commands."""
    lines = ["# Operations Manual (from manifest)", ""]

    # CLI commands (scripts with main or run_ functions)
    lines.append("## CLI / Pipeline Commands")
    for mod in manifest.get("modules", []):
        if mod["file"].startswith("scripts/"):
            run_fns = [f for f in mod.get("functions", []) if "run_" in f or "cmd_" in f]
            if run_fns:
                lines.append(f"\n### {mod['file']}")
                for fn in run_fns:
                    lines.append(f"  - {fn}")

    # Router endpoints
    lines.append("\n## API Endpoints")
    for mod in manifest.get("modules", []):
        if mod["file"].startswith("app/routers/"):
            lines.append(f"  - {mod['file']}: {len(mod.get('functions', []))} endpoints")

    return "\n".join(lines)


def _slice_use_cases(manifest: dict) -> str:
    """Router endpoints + CLI commands + functional blocks summary for UC grounding."""
    lines = ["# Use Case Grounding (from manifest)", ""]

    # Functional blocks summary (for F-block traceability)
    lines.append("## Functional Blocks")
    for block_id, block in manifest.get("functional_blocks", {}).items():
        sf_count = len(block.get("sub_functions", []))
        active = sum(1 for sf in block.get("sub_functions", []) if sf["status"] == "active")
        lines.append(f"- {block_id}: {block['name']} ({active}/{sf_count} active)")
    lines.append("")

    # Router endpoints (user-facing capabilities)
    lines.append("## API Endpoints (Web UI capabilities)")
    for mod in manifest.get("modules", []):
        if mod["file"].startswith("app/routers/"):
            lines.append(f"\n### {mod['file']}")
            for fn in mod.get("functions", []):
                lines.append(f"  - {fn}")
    lines.append("")

    # CLI commands (pipeline capabilities)
    lines.append("## CLI Commands (Pipeline capabilities)")
    for mod in manifest.get("modules", []):
        if mod["file"].startswith("scripts/"):
            run_fns = [f for f in mod.get("functions", []) if "run_" in f or "cmd_" in f]
            if run_fns:
                lines.append(f"  - {mod['file']}:")
                for fn in run_fns:
                    lines.append(f"    - {fn}")
    lines.append("")

    # Scheduler jobs
    lines.append("## Scheduled Jobs")
    for mod in manifest.get("modules", []):
        if "scheduler" in mod["file"].lower() or "main" in mod["file"].lower():
            sched_fns = [
                f
                for f in mod.get("functions", [])
                if "daily" in f or "register" in f or "schedule" in f
            ]
            if sched_fns:
                lines.append(f"  - {mod['file']}:")
                for fn in sched_fns:
                    lines.append(f"    - {fn}")

    return "\n".join(lines)


def _slice_requirements_analysis(manifest: dict) -> str:
    """System metrics, capabilities, and F-block coverage for requirements grounding."""
    lines = ["# Requirements Analysis (from manifest)", ""]

    # --- Hard metrics (ground truth for NFRs) ---
    metrics = manifest.get("metrics", {})
    lines.append("## System Metrics (verified)")
    lines.append(f"- Total Python files: {metrics.get('total_python_files', '?')}")
    lines.append(f"- Routers: {metrics.get('router_count', '?')}")
    lines.append(f"- Models: {metrics.get('model_count', '?')}")
    lines.append(f"- Migrations: {metrics.get('migration_count', '?')}")
    lines.append(f"- Templates: {metrics.get('template_count', '?')}")
    lines.append(f"- Interfaces (import deps): {len(manifest.get('interfaces', []))}")
    lines.append(f"- Modules scanned: {len(manifest.get('modules', []))}")

    # --- Functional blocks with sub-function counts (ground truth for FRs) ---
    lines.append("\n## Functional Blocks (capability inventory)")
    for block_id, block in manifest.get("functional_blocks", {}).items():
        sfs = block.get("sub_functions", [])
        active = sum(1 for sf in sfs if sf["status"] == "active")
        lines.append(
            f"\n### {block_id}: {block['name']} [{block['status']}] ({active}/{len(sfs)} active)"
        )
        for sf in sfs:
            lines.append(f"  - {sf['name']} [{sf['status']}]")

    # --- All router capabilities (what the system CAN do via API) ---
    lines.append("\n## API Capabilities (30 routers)")
    routers = [m for m in manifest.get("modules", []) if m["file"].startswith("app/routers/")]
    for mod in sorted(routers, key=lambda m: m["file"]):
        fn_count = len(mod.get("functions", []))
        lines.append(f"  - {mod['file']}: {fn_count} endpoints")

    # --- Pipeline capabilities (what the system CAN do via CLI) ---
    lines.append("\n## Pipeline Capabilities")
    pipeline_mods = [
        m
        for m in manifest.get("modules", [])
        if m["file"].startswith("scripts/_pipeline_") and not m["file"].endswith("__pycache__")
    ]
    for mod in sorted(pipeline_mods, key=lambda m: m["file"]):
        run_fns = [f for f in mod.get("functions", []) if f.startswith("run_")]
        if run_fns:
            lines.append(f"  - {mod['file']}: {', '.join(run_fns)}")

    # --- Test coverage (ground truth for verification) ---
    lines.append("\n## Test Files")
    test_mods = [m for m in manifest.get("modules", []) if "test" in m["file"].lower()]
    lines.append(f"  Total test files: {len(test_mods)}")
    for mod in test_mods[:20]:
        lines.append(f"  - {mod['file']} ({mod.get('line_count', '?')} lines)")
    if len(test_mods) > 20:
        lines.append(f"  ... and {len(test_mods) - 20} more")

    return "\n".join(lines)
