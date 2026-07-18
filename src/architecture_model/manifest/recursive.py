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
from typing import Any

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


def _block_id_to_component_id(block_id: str, config) -> str:
    """Map F-block ID to component ID by convention."""
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


def generate_recursive_manifests(
    project_root: Path,
    parent_model: str = ".architecture-model.yaml",
) -> dict[str, RecursiveManifest]:
    """Generate a RecursiveManifest for each F-block in the project config."""
    config = get_config(project_root)
    results: dict[str, RecursiveManifest] = {}
    
    for block_id, block_def in config.fblock_dict.items():
        logger.info("Generating recursive manifest for %s: %s", block_id, block_def.get("name"))
        manifest = generate_block_manifest(project_root, block_id, block_def)
        component_id = _block_id_to_component_id(block_id, config)
        results[block_id] = RecursiveManifest(
            block_id=block_id,
            block_name=block_def.get("name", block_id),
            parent_model=parent_model,
            component_id=component_id,
            manifest=manifest,
        )
    
    return results


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
