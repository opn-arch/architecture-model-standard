"""Recursive deep decomposition of a block into sub-components.

Takes a block manifest (modules + import edges) and clusters modules
into sub-components using import-graph affinity.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from architecture_model.core.cluster import cluster_modules
from architecture_model.manifest.interfaces import derive_interfaces
from architecture_model.manifest.types import Manifest

logger = logging.getLogger(__name__)


@dataclass
class SubComponent:
    """A sub-component produced by decomposition."""
    id: str
    name: str
    files: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    line_count: int = 0


@dataclass
class InternalRelationship:
    """A dependency between two sub-components."""
    from_id: str
    to_id: str
    edge_count: int = 1


@dataclass
class DecomposeResult:
    """Result of deep decomposition."""
    block_id: str
    block_name: str
    sub_components: list[SubComponent] = field(default_factory=list)
    internal_relationships: list[InternalRelationship] = field(default_factory=list)
    depth: int = 1


def deep_decompose_block(
    manifest: Manifest,
    *,
    block_id: str,
    block_name: str,
    max_modules: int = 15,
    target_k: int = 5,
    min_cluster_size: int = 3,
    parent_id: str = "",
) -> DecomposeResult:
    """Decompose a block manifest into sub-components via import clustering.

    Args:
        manifest: Block manifest with modules and their imports.
        block_id: F-block ID (e.g., "F6").
        block_name: Human name (e.g., "Integration MQTT").
        max_modules: Don't decompose if fewer modules than this.
        target_k: Target number of sub-components.
        min_cluster_size: Merge clusters smaller than this.
        parent_id: Parent component ID prefix for naming.

    Returns:
        DecomposeResult with sub_components and internal_relationships.
        Empty sub_components if block is too small to decompose.
    """
    result = DecomposeResult(block_id=block_id, block_name=block_name)

    # Filter __init__.py (not meaningful standalone)
    modules = [m for m in manifest.modules if Path(m.file).stem != "__init__"]

    if len(modules) <= max_modules:
        return result

    # Build edges from derive_interfaces
    edges_raw = derive_interfaces(modules, Path(manifest.project_root or "."))
    edges = [(e.source, e.target) for e in edges_raw]
    module_files = [m.file for m in modules]

    # Cluster
    groups = cluster_modules(module_files, edges, target_k=target_k, min_cluster_size=min_cluster_size)

    # Build sub-components
    comp_prefix = parent_id or f"COMP-{block_id}"
    file_to_module = {m.file: m for m in modules}

    for i, group in enumerate(groups, 1):
        comp_id = f"{comp_prefix}-{i}"
        classes = []
        functions = []
        line_count = 0
        for f in group:
            mod = file_to_module.get(f)
            if mod:
                classes.extend(c.name for c in mod.classes)
                functions.extend(fn.name for fn in mod.functions)
                line_count += mod.line_count

        result.sub_components.append(SubComponent(
            id=comp_id,
            name=f"{block_name} Sub-{i}",
            files=group,
            classes=classes,
            functions=functions,
            line_count=line_count,
        ))

    # Internal relationships (edges crossing sub-component boundaries)
    file_to_comp: dict[str, str] = {}
    for sc in result.sub_components:
        for f in sc.files:
            file_to_comp[f] = sc.id

    rel_counts: dict[tuple[str, str], int] = {}
    for src, tgt in edges:
        src_comp = file_to_comp.get(src)
        tgt_comp = file_to_comp.get(tgt)
        if src_comp and tgt_comp and src_comp != tgt_comp:
            key = (src_comp, tgt_comp)
            rel_counts[key] = rel_counts.get(key, 0) + 1

    for (from_id, to_id), count in rel_counts.items():
        result.internal_relationships.append(
            InternalRelationship(from_id=from_id, to_id=to_id, edge_count=count)
        )

    return result
