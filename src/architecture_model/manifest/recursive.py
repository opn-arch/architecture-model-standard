"""Recursive manifest generation -- per-F-block deep scans.

Produces a RecursiveManifest for each functional block, with full
module-level detail (functions with calls, docstrings, raises).
Each RecursiveManifest links to its parent model via component_id.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel

from architecture_model.monitoring import monitored
from architecture_model.config.loader import get_config
from architecture_model.manifest.interfaces import derive_interfaces
from architecture_model.manifest.scanner import scan_file
from architecture_model.manifest.types import (
    Manifest,
    MetricsResult,
    RecursiveManifest,
    ScanReport,
)
from architecture_model.utils.discovery import collect_py_files

logger = logging.getLogger(__name__)


def _block_id_to_component_id(
    block_id: str,
    config,
    model: "ArchitectureModel | None" = None,
) -> str:
    """Map F-block ID to component ID, preferring model lookup over convention."""
    if model is not None:
        for comp in model.entities.components:
            if getattr(comp, "f_block", None) == block_id:
                return comp.id
    # Fallback to convention
    block_def = config.fblock_dict.get(block_id, {})
    name = block_def.get("name", block_id)
    return f"COMP-{name.upper().replace(' ', '-')}"


def generate_block_manifest(
    root: Path,
    block_id: str,
    block_def: dict[str, Any],
) -> Manifest:
    """Generate a full Manifest scoped to a single F-block's files."""
    report = ScanReport()
    modules = []
    
    all_files: list[Path] = []
    for d in block_def.get("dirs", []):
        dir_path = root / d
        if dir_path.is_dir():
            all_files.extend(collect_py_files(dir_path))
    for f in block_def.get("files", []):
        fp = root / f
        if fp.is_file():
            all_files.append(fp)
    
    seen = set()
    unique_files = []
    for f in all_files:
        resolved = f.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_files.append(f)
    
    for filepath in sorted(unique_files):
        report.files_attempted += 1
        try:
            mod = scan_file(root, filepath)
            modules.append(mod)
            report.files_succeeded += 1
            report.functions_extracted += len(mod.functions)
            report.classes_extracted += len(mod.classes)
            report.constants_extracted += len(mod.module_constants)
        except Exception as exc:
            report.files_failed += 1
            report.parse_errors.append(f"{filepath}: {exc}")
    
    interfaces = derive_interfaces(modules, root)
    report.interfaces_derived = len(interfaces)
    
    metrics = MetricsResult(values={
        "py_files": len(unique_files),
        "total_lines": sum(m.line_count for m in modules),
        "functions": report.functions_extracted,
        "classes": report.classes_extracted,
        "constants": report.constants_extracted,
    })
    
    return Manifest(
        generated_at=datetime.now(timezone.utc).isoformat(),
        project_root=str(root),
        metrics=metrics,
        functional_blocks={},
        modules=modules,
        interfaces=interfaces,
        scan_report=report,
    )


@monitored(
    module="manifest.recursive",
    outputs=lambda r: {"block_count": len(r), "total_modules": sum(len(rm.manifest.modules) for rm in r.values())},
)
def generate_recursive_manifests(
    project_root: Path,
    parent_model: str = ".architecture-model.yaml",
) -> dict[str, RecursiveManifest]:
    """Generate a RecursiveManifest for each F-block in the project config."""
    config = get_config(project_root)
    results: dict[str, RecursiveManifest] = {}

    # Load parent model for component ID resolution
    model = None
    model_path = project_root / parent_model
    if model_path.exists():
        try:
            from architecture_model import load_model
            model = load_model(model_path)
        except Exception:
            pass  # Graceful degradation
    
    for block_id, block_def in config.fblock_dict.items():
        logger.info("Generating recursive manifest for %s: %s", block_id, block_def.get("name"))
        manifest = generate_block_manifest(project_root, block_id, block_def)
        component_id = _block_id_to_component_id(block_id, config, model)
        results[block_id] = RecursiveManifest(
            block_id=block_id,
            block_name=block_def.get("name", block_id),
            parent_model=parent_model,
            component_id=component_id,
            manifest=manifest,
        )
    
    # Compute cross-block dependencies
    block_deps = compute_block_dependencies(results, config)
    for block_id, deps in block_deps.items():
        if block_id in results:
            results[block_id].block_dependencies = deps
    
    return results


@monitored(
    module="manifest.recursive",
    outputs=lambda r: {"total_edges": sum(len(v) for v in r.values()), "block_count": len(r)},
)
def compute_block_dependencies(
    manifests: dict[str, RecursiveManifest],
    config,
) -> dict[str, list[str]]:
    """Compute cross-block dependency graph from import analysis.

    For each block, examines all imports in its modules. If an import resolves
    to a file belonging to a different block, that's a cross-block dependency.

    Returns:
        Dict mapping block_id -> list of block_ids it depends on.
    """
    # Get fblock definitions - from config or reconstruct from manifests
    if config is not None:
        fblock_dict = config.fblock_dict
    else:
        fblock_dict = {}
        for block_id, rm in manifests.items():
            fblock_dict[block_id] = {
                "name": rm.block_name,
                "dirs": [],
                "files": [m.file for m in rm.manifest.modules],
            }

    # Build lookup structures
    dir_prefixes: dict[str, str] = {}  # normalized dir prefix -> block_id
    file_index: dict[str, str] = {}    # module path (slash or dot form) -> block_id

    for block_id, block_def in fblock_dict.items():
        for d in block_def.get("dirs", []):
            dir_prefixes[d.rstrip("/")] = block_id
        for f in block_def.get("files", []):
            # Index without .py extension in both slash and dot form
            no_ext = f.removesuffix(".py")
            file_index[no_ext] = block_id
            file_index[no_ext.replace("/", ".")] = block_id

    def _resolve_import_to_block(slash_path: str) -> str | None:
        """Map import path to block_id via file index OR dir prefix."""
        # Try exact file match (slash form)
        if slash_path in file_index:
            return file_index[slash_path]
        # Try dot form
        dot_form = slash_path.replace("/", ".")
        if dot_form in file_index:
            return file_index[dot_form]
        # Try dir prefix matching
        for prefix, bid in dir_prefixes.items():
            norm_prefix = prefix.replace(".", "/").rstrip("/")
            if slash_path.startswith(norm_prefix + "/") or slash_path == norm_prefix:
                return bid
            if norm_prefix.startswith("src/"):
                stripped = norm_prefix[4:]
                if slash_path.startswith(stripped + "/") or slash_path == stripped:
                    return bid
        return None

    dependencies: dict[str, list[str]] = {}
    for block_id, rm in manifests.items():
        deps: set[str] = set()
        for mod in rm.manifest.modules:
            mod_dir = str(Path(mod.file).parent)
            # Check detailed imports if available
            for imp in mod.imports_detailed:
                if isinstance(imp, dict):
                    module_name = imp.get("module", "")
                    is_relative = imp.get("is_relative", False)
                else:
                    module_name = getattr(imp, "module", "")
                    is_relative = getattr(imp, "is_relative", False)
                if not module_name:
                    continue
                # Resolve relative imports to absolute path
                if is_relative:
                    # Relative imports go up from the module's package
                    # e.g., from ..core.parser in cli/main.py -> architecture_model/core/parser
                    # Try both: same-level and parent-level resolution
                    parts = module_name.replace(".", "/")
                    # Same level: mod_dir/parts
                    resolved = mod_dir + "/" + parts
                    target_block = _resolve_import_to_block(resolved)
                    if not target_block or target_block == block_id:
                        # Parent level: go up one from mod_dir
                        parent_dir = str(Path(mod_dir).parent)
                        resolved = parent_dir + "/" + parts
                        target_block = _resolve_import_to_block(resolved)
                    if target_block and target_block != block_id:
                        deps.add(target_block)
                    continue
                else:
                    resolved = module_name.replace(".", "/")
                target_block = _resolve_import_to_block(resolved)
                if target_block and target_block != block_id:
                    deps.add(target_block)
            # Also check simple imports list
            for imp_str in mod.imports:
                if isinstance(imp_str, str):
                    target_block = _resolve_import_to_block(imp_str.replace(".", "/"))
                    if target_block and target_block != block_id:
                        deps.add(target_block)
        dependencies[block_id] = sorted(deps)
    return dependencies


def write_recursive_manifests(
    manifests: dict[str, RecursiveManifest],
    output_dir: Path,
) -> list[Path]:
    """Write each RecursiveManifest to its own JSON file."""
    written: list[Path] = []
    for block_id, rm in manifests.items():
        block_dir = output_dir / block_id
        block_dir.mkdir(parents=True, exist_ok=True)
        out_path = block_dir / "manifest.json"
        out_path.write_text(
            json.dumps(rm.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )
        written.append(out_path)
        logger.info("Wrote %s", out_path)
    return written
