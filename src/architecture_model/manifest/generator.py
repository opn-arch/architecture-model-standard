"""Main manifest generation and caching logic."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from architecture_model.manifest.blocks import _get_functional_blocks, process_block
from architecture_model.manifest.interfaces import derive_interfaces
from architecture_model.manifest.metrics import compute_metrics
from architecture_model.manifest.scanner import scan_file
from architecture_model.utils.discovery import collect_py_files
from architecture_model.manifest.types import (
    Manifest,
    MetricsResult,
    ScanReport,
)

logger = logging.getLogger(__name__)


def generate_manifest(project_root: Path, config: Optional[Any] = None) -> Manifest:
    """Generate a full reality manifest via AST scan of the project.

    Args:
        project_root: Absolute path to the project root directory.
        config: Optional ProjectConfig. If None, loaded from .architecture-model.yaml.

    Returns:
        Typed Manifest dataclass. Call .to_dict() for JSON-compatible dict.
    """
    root = project_root.resolve()
    report = ScanReport()

    if config is None:
        from architecture_model.config.loader import get_config

        config = get_config(root)

    # Compute metrics
    logger.info("Computing project metrics for %s", root)
    metrics_result = compute_metrics(root, config)
    logger.info("Metrics computed: %s", metrics_result.values)

    # Get functional blocks from config
    blocks_dict = config.fblock_dict

    # Process functional blocks
    logger.info("Processing %d functional blocks", len(blocks_dict))
    from architecture_model.manifest.types import BlockManifest

    functional_blocks: dict[str, BlockManifest] = {}
    scanned_files: set[str] = set()

    for block_id, block_def in blocks_dict.items():
        # Find matching FunctionalBlockConfig to get sub_block_configs
        block_cfg = next((b for b in config.functional_blocks if b.id == block_id), None)
        sub_block_configs = block_cfg.sub_blocks if block_cfg else None
        block_result = process_block(
            root, block_id, block_def, sub_block_configs=sub_block_configs
        )
        functional_blocks[block_id] = block_result
        report.blocks_processed += 1
        for sf in block_result.sub_functions:
            if sf.file not in scanned_files:
                scanned_files.add(sf.file)

    logger.info("Processed %d blocks, found %d files", report.blocks_processed, len(scanned_files))

    # Scan additional directories from config layers (web, services, data)
    extra_dirs: set[str] = set()
    for layer in config.layers:
        for d in layer.dirs:
            if d not in ("scripts",):  # scripts already covered by blocks
                extra_dirs.add(d)

    for dir_path in sorted(extra_dirs):
        for filepath in collect_py_files(root, dir_path):
            rel = str(filepath.relative_to(root))
            if rel not in scanned_files:
                scanned_files.add(rel)

    # Build full module list
    logger.info("Scanning %d files for module metadata", len(scanned_files))
    from architecture_model.manifest.types import ModuleInfo

    all_modules: list[ModuleInfo] = []

    for rel_path in sorted(scanned_files):
        filepath = root / rel_path
        if filepath.exists():
            report.files_attempted += 1
            try:
                meta = scan_file(root, filepath)
                all_modules.append(meta)
                report.files_succeeded += 1
                report.functions_extracted += len(meta.functions)
                report.classes_extracted += len(meta.classes)
                report.constants_extracted += len(meta.module_constants)
            except Exception as exc:
                report.files_failed += 1
                report.parse_errors.append(f"{rel_path}: {exc}")
                logger.warning("Failed to scan %s: %s", rel_path, exc)

    # Derive interfaces
    logger.info("Deriving interfaces from %d modules", len(all_modules))
    interfaces = derive_interfaces(all_modules, root)
    report.interfaces_derived = len(interfaces)

    report.log_summary()

    return Manifest(
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        project_root=str(root),
        metrics=metrics_result,
        functional_blocks=functional_blocks,
        modules=all_modules,
        interfaces=interfaces,
        scan_report=report,
    )


def load_or_generate_manifest(project_root: Path, output_dir: Path | None = None) -> dict[str, Any]:
    """Load cached manifest if fresh (< 1 hour old), otherwise regenerate.

    Args:
        project_root: Path to the project root.
        output_dir: Optional output directory. If None, uses config output paths.

    Returns:
        The manifest dictionary (for backward compatibility with CLI/callers).
    """
    from architecture_model.config.loader import get_config

    config = get_config(project_root)

    if output_dir is None:
        resolved = config.resolved_output()
        manifest_path = resolved.manifest
    else:
        manifest_path = output_dir / "reality-manifest.json"

    # Check cache freshness (1 hour)
    if manifest_path.exists():
        age_seconds = time.time() - manifest_path.stat().st_mtime
        if age_seconds < 3600:
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                return data
            except (json.JSONDecodeError, OSError):
                pass  # Regenerate on error

    # Generate fresh
    manifest = generate_manifest(project_root, config)
    manifest_dict = manifest.to_dict()

    # Write to disk
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest_dict, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return manifest_dict
