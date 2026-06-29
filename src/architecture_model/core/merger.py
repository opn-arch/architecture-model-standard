"""
Merger: Merge manifest facts into an existing architecture model.

The manifest provides code-grounded facts (file counts, module names, import graphs).
The model provides architectural decisions (what things mean, how they relate).

Merger SUPPLEMENTS the model with manifest data — it never overwrites architectural
decisions. It adds source_file/source_line provenance and fills in component file lists.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .types import ArchitectureModel, Component, Relationship, RelationType, Status


def merge_manifest(
    model: ArchitectureModel,
    manifest_path: str | Path,
    project_root: str | Path | None = None,
) -> ArchitectureModel:
    """
    Merge manifest data into the architecture model (in-place mutation).

    What gets merged:
    - Component file lists get enriched with manifest-discovered files.
    - Layers get directory lists from manifest module scan.
    - Meta gets manifest_hash updated.

    What does NOT get overwritten:
    - Entity names, descriptions, status markers.
    - Relationships (these are architectural decisions).
    - Capabilities, behaviors, constraints (model-level truth).

    Args:
        model: The architecture model to enrich.
        manifest_path: Path to the reality-manifest.json file.
        project_root: Root of the consumer project (for config lookup).
                      Defaults to manifest_path's grandparent (output/{project}/manifest → root).

    Returns the same model instance (mutated).
    """
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        return model

    # Resolve project root for config loading
    if project_root is None:
        # Heuristic: manifest is at output/{project}/reality-manifest.json → root is ../..
        project_root = manifest_path.resolve().parent.parent.parent
    else:
        project_root = Path(project_root).resolve()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Update manifest hash
    import hashlib

    content = manifest_path.read_bytes()
    model.meta.manifest_hash = hashlib.sha256(content).hexdigest()[:16]

    # Enrich layers with directory info
    _merge_layer_directories(model, manifest, project_root)

    # Enrich components with file provenance
    _merge_component_files(model, manifest)

    # Add discovered components not yet in model
    _add_missing_components(model, manifest, project_root)

    return model


def _merge_layer_directories(model: ArchitectureModel, manifest: dict, project_root: Path) -> None:
    """Map manifest directory categories to model layers."""
    modules = manifest.get("modules", [])
    if not modules:
        return

    # Load layer-dir mapping from config
    try:
        from architecture_model.config.loader import get_config

        config = get_config(project_root)
        layer_dir_map = config.layer_dir_map
    except Exception:
        # Fallback: derive from model layer IDs
        layer_dir_map = {}

    for layer in model.entities.layers:
        if layer.id in layer_dir_map:
            layer.directories = layer_dir_map[layer.id]


def _merge_component_files(model: ArchitectureModel, manifest: dict) -> None:
    """Add file provenance to components that match manifest modules."""
    modules = manifest.get("modules", [])
    if not modules:
        return

    # Build filename → path lookup (manifest uses 'file' key)
    file_lookup: dict[str, str] = {}
    for mod in modules:
        path = mod.get("file", mod.get("path", ""))
        filename = path.rsplit("/", 1)[-1] if "/" in path else path
        file_lookup[filename] = path

    for comp in model.entities.components:
        if comp.files:
            # Try to resolve full paths
            resolved: list[str] = []
            for f in comp.files:
                if f in file_lookup:
                    resolved.append(file_lookup[f])
                else:
                    resolved.append(f)
            comp.files = resolved
        elif comp.name in file_lookup:
            comp.files = [file_lookup[comp.name]]
            comp.source_file = file_lookup[comp.name]


def _add_missing_components(model: ArchitectureModel, manifest: dict, project_root: Path) -> None:
    """
    Add high-LOC modules from manifest that aren't yet represented as components.

    Only adds modules with >400 LOC that aren't already tracked.
    """
    modules = manifest.get("modules", [])
    if not modules:
        return

    existing_files: set[str] = set()
    for comp in model.entities.components:
        for f in comp.files:
            existing_files.add(f)
            # Also add just filename
            existing_files.add(f.rsplit("/", 1)[-1] if "/" in f else f)

    # F-block directory heuristics — loaded from config
    try:
        from architecture_model.config.loader import get_config

        config = get_config(project_root)
        fblock_dirs = config.fblock_dir_map
    except Exception:
        fblock_dirs = {}
        config = None

    for mod in modules:
        path = mod.get("file", mod.get("path", ""))
        loc = mod.get("line_count", mod.get("loc", 0))
        filename = path.rsplit("/", 1)[-1] if "/" in path else path

        if loc < 400:
            continue
        if filename in existing_files or path in existing_files:
            continue

        # Determine f_block
        f_block = ""
        for prefix, fb in fblock_dirs.items():
            if path.startswith(prefix):
                f_block = fb
                break

        # Determine layer from config
        layer = ""
        try:
            layer_dir_map = config.layer_dir_map
        except Exception:
            layer_dir_map = {}
        for layer_id, dirs in layer_dir_map.items():
            for d in dirs:
                if path.startswith(d):
                    layer = layer_id
                    break
            if layer:
                break

        comp_id = path.replace("/", "-").replace(".py", "").replace("_", "-")

        model.entities.components.append(
            Component(
                id=comp_id,
                name=filename,
                status=Status.ACTIVE,
                layer=layer,
                f_block=f_block,
                files=[path],
                source_file=path,
                description=f"Auto-discovered from manifest ({loc} LOC)",
            )
        )

    # Wire realizes relationships for newly added components
    fblock_to_cap = {cap.f_block: cap.id for cap in model.entities.capabilities}
    existing_rels = {(r.from_id, r.to_id, r.type) for r in model.relationships}
    for comp in model.entities.components:
        if comp.f_block and comp.f_block in fblock_to_cap:
            key = (comp.id, fblock_to_cap[comp.f_block], RelationType.REALIZES)
            if key not in existing_rels:
                model.relationships.append(
                    Relationship(
                        type=RelationType.REALIZES,
                        from_id=comp.id,
                        to_id=fblock_to_cap[comp.f_block],
                        description=f"{comp.name} realizes {comp.f_block}",
                    )
                )
                existing_rels.add(key)
