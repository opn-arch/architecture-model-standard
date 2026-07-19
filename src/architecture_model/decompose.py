"""Generate recursive sub-models from parent model + recursive manifests.

For each F-block, produces an ArchitectureModel where:
- Meta links to parent via parent_model/refines_component
- Components from parent model (matched by file paths)
- Capabilities derived from public functions in manifest
- Interfaces derived from cross-module imports within the block
- Relationships: contains, exposes, depends-on
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from architecture_model.config.loader import get_config
from architecture_model.core.parser import load_model, save_model
from architecture_model.core.types import (
    ArchitectureModel,
    Capability,
    Component,
    ComponentKind,
    Entities,
    Interface,
    InterfaceType,
    ModelMeta,
    Priority,
    Relationship,
    RelationType,
    Status,
    Strength,
)

logger = logging.getLogger(__name__)


def _find_block_components(
    model: ArchitectureModel,
    block_dirs: list[str],
) -> list[Component]:
    """Find components whose files are under the given block directories."""
    result = []
    for comp in model.entities.components:
        if not comp.files:
            continue
        for f in comp.files:
            for d in block_dirs:
                if f.startswith(d):
                    result.append(comp)
                    break
            else:
                continue
            break
    return result


def _find_parent_component(
    model: ArchitectureModel,
    block_components: list[Component],
) -> str | None:
    """Find the top-level parent component that contains block sub-components.

    Looks for a component that has 'contains' relationships to the block components.
    """
    block_ids = {c.id for c in block_components}
    for rel in model.relationships:
        if rel.type == RelationType.CONTAINS and rel.to_id in block_ids:
            if rel.from_id.startswith("COMP-"):
                return rel.from_id
    if len(block_components) == 1:
        return block_components[0].id
    return None


def _load_block_manifest(project_root: Path, block_id: str) -> dict | None:
    """Load a recursive manifest for a block."""
    manifest_path = project_root / "output" / "manifests" / block_id / "manifest.json"
    if not manifest_path.exists():
        logger.warning("No recursive manifest for %s at %s", block_id, manifest_path)
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _derive_capabilities(
    manifest_data: dict,
    block_id: str,
) -> list[Capability]:
    """Derive capabilities from public functions in manifest modules."""
    caps = []
    modules = manifest_data.get("manifest", {}).get("modules", [])
    cap_idx = 1
    for mod in modules:
        for func in mod.get("functions", []):
            name = func.get("name", "")
            docstring = func.get("docstring", "")
            if not name:
                continue
            caps.append(Capability(
                id=f"CAP-{block_id}-{cap_idx}",
                name=name,
                status=Status.ACTIVE,
                description=docstring or f"Function {name}",
                f_block=block_id,
            ))
            cap_idx += 1
    return caps


def _derive_interfaces(
    manifest_data: dict,
    block_id: str,
    block_dirs: list[str],
) -> list[Interface]:
    """Derive interfaces from cross-module imports within the block."""
    interfaces = []
    manifest_interfaces = manifest_data.get("manifest", {}).get("interfaces", [])
    iface_idx = 1
    seen: set[tuple[str, str]] = set()
    for iface in manifest_interfaces:
        source = iface.get("source", "")
        target = iface.get("target", "")
        import_path = iface.get("import_path", "")
        key = (source, target)
        if key in seen:
            continue
        seen.add(key)
        interfaces.append(Interface(
            id=f"IF-{block_id}-{iface_idx}",
            name=f"{Path(source).stem} -> {Path(target).stem}",
            status=Status.ACTIVE,
            type=InterfaceType.INTERNAL,
            provider=target,
            consumer=source,
            description=f"Import: {import_path}",
        ))
        iface_idx += 1
    return interfaces


def _derive_relationships(
    components: list[Component],
    capabilities: list[Capability],
    interfaces: list[Interface],
    parent_component_id: str | None,
    parent_model: ArchitectureModel,
) -> list[Relationship]:
    """Build relationships for the sub-model."""
    rels = []
    comp_ids = {c.id for c in components}

    # Copy relevant relationships from parent
    for rel in parent_model.relationships:
        if rel.from_id in comp_ids and rel.to_id in comp_ids:
            rels.append(rel)

    # Add contains: parent -> each component (if parent exists and is not in block)
    if parent_component_id and parent_component_id not in comp_ids:
        for comp in components:
            rels.append(Relationship(
                type=RelationType.CONTAINS,
                from_id=parent_component_id,
                to_id=comp.id,
            ))

    return rels


def decompose_model(
    project_root: Path,
) -> dict[str, ArchitectureModel]:
    """Generate sub-models for each F-block.

    Args:
        project_root: Root directory with .architecture-model.yaml and output/manifests/

    Returns:
        Dict mapping block_id -> ArchitectureModel (sub-model)
    """
    model = load_model(project_root / ".architecture-model.yaml")
    config = get_config(project_root)
    results: dict[str, ArchitectureModel] = {}

    for block_id, block_def in config.fblock_dict.items():
        block_name = block_def.get("name", block_id)
        block_dirs = block_def.get("dirs", [])

        logger.info("Decomposing %s: %s", block_id, block_name)

        # Find components from parent model
        components = _find_block_components(model, block_dirs)
        if not components:
            logger.warning("No components found for %s (dirs: %s)", block_id, block_dirs)
            continue

        # Find parent component
        parent_comp_id = _find_parent_component(model, components)

        # Load recursive manifest
        manifest_data = _load_block_manifest(project_root, block_id)

        # Derive capabilities from manifest
        capabilities: list[Capability] = []
        interfaces: list[Interface] = []
        if manifest_data:
            capabilities = _derive_capabilities(manifest_data, block_id)
            interfaces = _derive_interfaces(manifest_data, block_id, block_dirs)

        # Build relationships
        relationships = _derive_relationships(
            components, capabilities, interfaces,
            parent_comp_id, model,
        )

        # Build sub-model
        sub_model = ArchitectureModel(
            meta=ModelMeta(
                schema_version="2.0",
                project=f"{model.meta.project}/{block_name}",
                system=block_name,
                generated_at=model.meta.generated_at,
                parent_model="../../.architecture-model.yaml",
                refines_component=parent_comp_id or "",
            ),
            entities=Entities(
                components=components,
                capabilities=capabilities,
                interfaces=interfaces,
            ),
            relationships=relationships,
        )

        results[block_id] = sub_model
        logger.info(
            "  %s: %d components, %d capabilities, %d interfaces, %d relationships",
            block_id, len(components), len(capabilities), len(interfaces), len(relationships),
        )

    return results


def write_sub_models(
    sub_models: dict[str, ArchitectureModel],
    output_dir: Path,
) -> list[Path]:
    """Write sub-models to YAML files.

    Output structure:
        output_dir/<block_id>/.architecture-model.yaml
    """
    written = []
    for block_id, model in sub_models.items():
        block_dir = output_dir / block_id
        block_dir.mkdir(parents=True, exist_ok=True)
        out_path = block_dir / ".architecture-model.yaml"
        save_model(model, out_path)
        written.append(out_path)
        logger.info("Wrote sub-model: %s", out_path)
    return written
