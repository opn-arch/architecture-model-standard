"""Functional block definitions and processing.

Loads functional blocks from .architecture-model.yaml config. Falls back to
auto-discovery if no config exists. The FUNCTIONAL_BLOCKS constant is maintained
for backward compatibility but now reads from config.
"""

from __future__ import annotations

import logging
import re
import warnings
from pathlib import Path
from typing import Any, Optional

from architecture_model.manifest.scanner import scan_file
from architecture_model.manifest.types import BlockManifest, SubFunctionEntry
from architecture_model.utils.discovery import collect_py_files

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config-driven block loading
# ---------------------------------------------------------------------------


def _get_functional_blocks(root: Optional[Path] = None) -> dict[str, dict[str, Any]]:
    """Load functional blocks from config.

    Returns the blocks dict in legacy format for backward compatibility.
    Falls back to empty dict if no config and no hardcoded fallback.
    """
    from architecture_model.config.loader import get_config

    if root is None:
        root = Path(".")
    config = get_config(root)
    return config.fblock_dict


# DEPRECATED: Backward-compatible module-level constant.
# Will be removed in a future version. Use _get_functional_blocks(root) instead.
def _load_blocks_from_config() -> dict[str, dict[str, Any]]:
    """Load blocks from config at import time (for backward compat).

    .. deprecated::
        Use :func:`_get_functional_blocks` with an explicit root instead.
    """
    try:
        from architecture_model.config.loader import get_config

        config = get_config(Path("."))
        if config.functional_blocks:
            return config.fblock_dict
    except Exception:
        pass
    # Fallback: return empty (callers should use _get_functional_blocks with root)
    return {}


# DEPRECATED: Module-level constant for backward compatibility.
# Code that imports FUNCTIONAL_BLOCKS directly will get the config-loaded version.
# Use _get_functional_blocks(root) instead.
FUNCTIONAL_BLOCKS: dict[str, dict[str, Any]] = _load_blocks_from_config()


def _build_sub_block_manifest(
    sub_block_cfg: Any, all_sub_functions: list[SubFunctionEntry], block_id: str
) -> dict[str, Any]:
    """Build manifest entry for a sub-block, claiming matching files from the pool."""
    claimed_files: set[str] = set()
    my_sub_functions: list[SubFunctionEntry] = []

    for sf in all_sub_functions:
        filename = sf.file.split("/")[-1]  # basename
        rel_path = sf.file
        # Match by filename in files list, or by directory prefix in dirs list
        if filename in sub_block_cfg.files or any(
            rel_path.startswith(d) for d in sub_block_cfg.dirs
        ):
            my_sub_functions.append(sf)
            claimed_files.add(sf.file)

    # Recurse for nested sub-blocks
    child_blocks: list[dict[str, Any]] = []
    for child_cfg in sub_block_cfg.sub_blocks:
        child_manifest = _build_sub_block_manifest(child_cfg, my_sub_functions, sub_block_cfg.id)
        child_blocks.append(child_manifest)

    # Determine status
    status = "active" if any(sf.status == "active" for sf in my_sub_functions) else "dormant"

    return {
        "id": sub_block_cfg.id,
        "name": sub_block_cfg.name,
        "description": sub_block_cfg.description,
        "status": status,
        "sub_functions": [sf.to_dict() for sf in my_sub_functions],
        "sub_blocks": child_blocks,
    }


def process_block(
    root: Path, block_id: str, block_def: dict, sub_block_configs: list | None = None
) -> BlockManifest:
    """Process a single functional block, scanning all its files.

    Returns a typed :class:`BlockManifest` with :class:`SubFunctionEntry` objects.
    """
    sub_functions: list[SubFunctionEntry] = []
    all_files: list[Path] = []

    # Collect files from dirs
    for dir_path in block_def["dirs"]:
        all_files.extend(collect_py_files(root / dir_path))

    # Collect explicit files
    for file_path in block_def["files"]:
        fp = root / file_path
        if fp.exists() and fp not in all_files:
            all_files.append(fp)

    logger.debug("Block %s: %d files from %d dirs", block_id, len(all_files), len(block_def["dirs"]))

    # Scan each file
    for idx, filepath in enumerate(all_files, 1):
        module_info = scan_file(root, filepath)
        sub_id = f"{block_id}.{idx}"

        # Derive inputs/outputs from function signatures
        inputs: list[str] = []
        outputs: list[str] = []
        for func in module_info.functions:
            sig = func.signature
            # Extract params from signature
            match = re.match(r"\w+\(([^)]*)\)", sig)
            if match and match.group(1):
                params = [p.strip() for p in match.group(1).split(",")]
                inputs.extend(params[:3])  # Limit to avoid noise
            # Extract return type
            ret_match = re.search(r"->\s*(.+)$", sig)
            if ret_match:
                outputs.append(ret_match.group(1).strip())

        sub_functions.append(
            SubFunctionEntry(
                id=sub_id,
                name=module_info.name,
                file=module_info.file,
                functions=[f.signature for f in module_info.functions],
                inputs=inputs[:6],  # Cap at 6 for readability
                outputs=list(set(outputs))[:4],
                status=module_info.status.value,
                line_count=module_info.line_count,
            )
        )

    # Block status: active if any sub-function is active
    block_status = "active" if any(sf.status == "active" for sf in sub_functions) else "dormant"

    # Build hierarchical sub_blocks if config provides them
    sub_blocks_manifest: list[dict[str, Any]] = []
    if sub_block_configs:
        claimed: set[str] = set()
        for sb_cfg in sub_block_configs:
            sb_manifest = _build_sub_block_manifest(sb_cfg, sub_functions, block_id)
            sub_blocks_manifest.append(sb_manifest)
            claimed.update(sf["file"] for sf in sb_manifest["sub_functions"])

        # Ungrouped files
        ungrouped = [sf for sf in sub_functions if sf.file not in claimed]
        if ungrouped:
            logger.debug("Block %s: %d unclaimed files", block_id, len(ungrouped))
            sub_blocks_manifest.append(
                {
                    "id": f"{block_id}.misc",
                    "name": "Ungrouped",
                    "description": "",
                    "status": "active"
                    if any(sf.status == "active" for sf in ungrouped)
                    else "dormant",
                    "sub_functions": [sf.to_dict() for sf in ungrouped],
                    "sub_blocks": [],
                }
            )

    logger.debug(
        "Block %s: %d sub_functions, %d sub_blocks",
        block_id, len(sub_functions), len(sub_blocks_manifest),
    )

    return BlockManifest(
        name=block_def["name"],
        status=block_status,
        description_source=block_def["description_source"],
        sub_functions=sub_functions,
        sub_blocks=sub_blocks_manifest,
    )


def _process_block(
    root: Path, block_id: str, block_def: dict, sub_block_configs: list | None = None
) -> dict[str, Any]:
    """Process a single functional block, scanning all its files.

    .. deprecated::
        Use :func:`process_block` which returns a typed :class:`BlockManifest`.
    """
    warnings.warn(
        "_process_block is deprecated, use process_block",
        DeprecationWarning,
        stacklevel=2,
    )
    return process_block(root, block_id, block_def, sub_block_configs).to_dict()
