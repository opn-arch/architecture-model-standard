"""Generate recursive sub-models from parent model via relationship tracing.

For each F-block, produces an ArchitectureModel by tracing relationships
outward from the block's components:
- realizes --> Capability
- exposes --> Interface
- traces-to --> Behavior
- constrained-by --> Constraint
- depends-on --> boundary relationships to external components

This produces sub-models that are faithful slices of the parent model,
not invented entities.
"""
from __future__ import annotations

import logging
from pathlib import Path

from architecture_model.config.loader import get_config
from architecture_model.core.parser import load_model, save_model
from architecture_model.core.types import (
    ArchitectureModel,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
)

logger = logging.getLogger(__name__)


def _find_block_components(model, block_dirs, block_files=None):
    """Find components whose files are under the given block directories."""
    result = []
    block_files_set = set(block_files or [])
    for comp in model.entities.components:
        if not comp.files:
            continue
        for f in comp.files:
            for d in block_dirs:
                if f.startswith(d):
                    result.append(comp)
                    break
            else:
                if f in block_files_set:
                    result.append(comp)
                    break
                continue
            break
    return result


def _find_parent_component(model, block_components):
    """Find the top-level parent component that contains block sub-components.

    Returns (parent_id, parent_component) tuple.
    """
    block_ids = {c.id for c in block_components}
    for rel in model.relationships:
        if rel.type == RelationType.CONTAINS and rel.to_id in block_ids:
            parent_id = rel.from_id
            if parent_id.startswith("COMP-"):
                parent_comp = next(
                    (c for c in model.entities.components if c.id == parent_id),
                    None,
                )
                return parent_id, parent_comp
    if len(block_components) == 1:
        return block_components[0].id, block_components[0]
    return None, None


def _trace_entities(model, block_comp_ids):
    """Trace relationships from block components to find connected entities.

    Follows:
    - realizes --> Capability
    - exposes --> Interface
    - traces-to --> Behavior
    - constrained-by --> Constraint
    """
    cap_ids = set()
    iface_ids = set()
    behavior_ids = set()
    constraint_ids = set()

    for rel in model.relationships:
        if rel.from_id in block_comp_ids:
            if rel.type == RelationType.REALIZES:
                cap_ids.add(rel.to_id)
            elif rel.type == RelationType.EXPOSES:
                iface_ids.add(rel.to_id)
            elif rel.type == RelationType.TRACES_TO:
                behavior_ids.add(rel.to_id)
            elif rel.type == RelationType.CONSTRAINED_BY:
                constraint_ids.add(rel.to_id)
        # Also check reverse: something traces-to a block component
        if rel.to_id in block_comp_ids:
            if rel.type == RelationType.TRACES_TO:
                behavior_ids.add(rel.from_id)

    caps = [c for c in model.entities.capabilities if c.id in cap_ids]
    ifaces = [i for i in model.entities.interfaces if i.id in iface_ids]
    behaviors = [b for b in model.entities.behaviors if b.id in behavior_ids]
    constraints = [c for c in model.entities.constraints if c.id in constraint_ids]

    return caps, ifaces, behaviors, constraints


def _collect_relationships(model, entity_ids, block_comp_ids):
    """Collect relationships relevant to the sub-model.

    - Internal: both endpoints in entity_ids
    - Boundary: depends-on crossing block boundary
    """
    rels = []
    seen = set()

    for rel in model.relationships:
        key = (rel.from_id, rel.to_id, rel.type.value)
        if key in seen:
            continue

        # Internal: both endpoints in our entity set
        if rel.from_id in entity_ids and rel.to_id in entity_ids:
            seen.add(key)
            rels.append(rel)
            continue

        # Boundary: depends-on crossing block boundary
        if rel.type == RelationType.DEPENDS_ON:
            if rel.from_id in block_comp_ids and rel.to_id not in block_comp_ids:
                seen.add(key)
                rels.append(rel)
            elif rel.to_id in block_comp_ids and rel.from_id not in block_comp_ids:
                seen.add(key)
                rels.append(rel)

    return rels


def decompose_model(project_root):
    """Generate sub-models for each F-block by tracing parent model relationships.

    For each F-block:
    1. Find components by file path matching
    2. Trace realizes/exposes/traces-to/constrained-by to find connected entities
    3. Collect internal + boundary relationships
    4. Build sub-model with parent's actual entities (not invented ones)

    Args:
        project_root: Root directory with .architecture-model.yaml

    Returns:
        Dict mapping block_id -> ArchitectureModel (sub-model)
    """
    model = load_model(project_root / ".architecture-model.yaml")
    config = get_config(project_root)
    results = {}

    for block_id, block_def in config.fblock_dict.items():
        block_name = block_def.get("name", block_id)
        block_dirs = block_def.get("dirs", [])
        block_files = block_def.get("files", [])

        logger.info("Decomposing %s: %s", block_id, block_name)

        # 1. Find components from parent model
        components = _find_block_components(model, block_dirs, block_files)
        if not components:
            logger.warning("No components found for %s (dirs: %s)", block_id, block_dirs)
            continue

        # Include parent component if it exists
        parent_comp_id, parent_comp = _find_parent_component(model, components)
        comp_ids = {c.id for c in components}
        if parent_comp and parent_comp.id not in comp_ids:
            components = [parent_comp] + components
            comp_ids.add(parent_comp.id)

        block_comp_ids = comp_ids.copy()

        # 2. Trace relationships to find connected entities
        capabilities, interfaces, behaviors, constraints = _trace_entities(
            model, block_comp_ids,
        )

        # 3. Build full entity ID set for relationship collection
        all_entity_ids = block_comp_ids.copy()
        all_entity_ids.update(c.id for c in capabilities)
        all_entity_ids.update(i.id for i in interfaces)
        all_entity_ids.update(b.id for b in behaviors)
        all_entity_ids.update(c.id for c in constraints)

        # 4. Collect relationships
        relationships = _collect_relationships(model, all_entity_ids, block_comp_ids)

        # 5. Build sub-model
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
                behaviors=behaviors,
                constraints=constraints,
            ),
            relationships=relationships,
        )

        results[block_id] = sub_model
        logger.info(
            "  %s: %d comps, %d caps, %d ifaces, %d behaviors, %d constraints, %d rels",
            block_id,
            len(components), len(capabilities), len(interfaces),
            len(behaviors), len(constraints), len(relationships),
        )

    return results


def write_sub_models(sub_models, output_dir):
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
