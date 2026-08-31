"""Derive subsystem views from the single root architecture model.

Each view is a filtered slice of the root model containing one top-level
component and all its children, plus all entities reachable via relationships
(capabilities, behaviors, interfaces, constraints, requirements, actors).

Views are written as standard .architecture-model.yaml files — one per
subsystem — so they can be used as input to SE doc generators, LLM authoring,
and any tool that operates on ArchitectureModel objects.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel, Component


@dataclass
class SubsystemView:
    """A derived view for one subsystem (top-level component + children)."""

    component_id: str
    component_name: str
    slug: str  # directory-safe name, e.g. "core", "pipeline"
    model: "ArchitectureModel"


def _slug_from_name(name: str) -> str:
    """Convert component name to a directory-safe slug."""
    return name.lower().replace(" & ", "-").replace(" ", "-").replace("/", "-")


def _collect_component_subtree(
    root_comp_id: str,
    all_components: list["Component"],
) -> list["Component"]:
    """Collect a top-level component and all its children (by ID prefix)."""
    prefix = root_comp_id + "."
    return [
        c
        for c in all_components
        if c.id == root_comp_id or c.id.startswith(prefix)
    ]


def _collect_related_entity_ids(
    comp_ids: set[str],
    relationships: list,
) -> set[str]:
    """Find all entity IDs connected to the given component IDs via relationships."""
    related: set[str] = set()
    for rel in relationships:
        if rel.from_id in comp_ids:
            related.add(rel.to_id)
        if rel.to_id in comp_ids:
            related.add(rel.from_id)
    return related - comp_ids  # exclude the components themselves


def _filter_entities_by_ids(entities, ids: set[str]) -> list:
    """Filter a list of entities to only those whose ID is in the given set."""
    return [e for e in entities if e.id in ids]


def derive_subsystem_views(
    model: "ArchitectureModel",
    *,
    observe_inventory: dict[str, Any] | None = None,
) -> list[SubsystemView]:
    """Derive per-subsystem views from the root model.

    Args:
        model: The root architecture model (single source of truth).
        observe_inventory: Optional observe stage output for code-level enrichment.

    Returns:
        List of SubsystemView objects, one per top-level component.
    """
    from architecture_model.core.types import (
        ArchitectureModel,
        Entities,
        ModelMeta,
    )

    views: list[SubsystemView] = []

    # Identify top-level components (no dot in ID, or exactly one segment)
    top_level = [c for c in model.entities.components if "." not in c.id]

    for top_comp in top_level:
        # 1. Collect component subtree
        subtree = _collect_component_subtree(top_comp.id, model.entities.components)
        comp_ids = {c.id for c in subtree}

        # 2. Find related entity IDs via relationships
        related_ids = _collect_related_entity_ids(comp_ids, model.relationships)
        all_ids = comp_ids | related_ids

        # 3. Filter relationships: keep only those where BOTH endpoints are in our view
        view_rels = [
            r for r in model.relationships
            if r.from_id in all_ids and r.to_id in all_ids
        ]

        # 4. Filter entities by collected IDs
        view_entities = Entities(
            components=list(subtree),
            capabilities=_filter_entities_by_ids(model.entities.capabilities, related_ids),
            behaviors=_filter_entities_by_ids(model.entities.behaviors, related_ids),
            interfaces=_filter_entities_by_ids(model.entities.interfaces, related_ids),
            constraints=_filter_entities_by_ids(model.entities.constraints, related_ids),
            requirements=_filter_entities_by_ids(model.entities.requirements, related_ids),
            actors=_filter_entities_by_ids(model.entities.actors, related_ids),
            layers=_filter_entities_by_ids(model.entities.layers, related_ids),
        )

        # 5. Build subsystem meta
        slug = _slug_from_name(top_comp.name)
        view_meta = ModelMeta(
            project=f"{getattr(model.meta, 'project', 'System')} / {top_comp.name}",
            schema_version=getattr(model.meta, "schema_version", "2.0"),
            system=top_comp.name,
        )
        # Copy optional meta fields
        for attr in ("domain_profile",):
            if hasattr(model.meta, attr) and getattr(model.meta, attr):
                setattr(view_meta, attr, getattr(model.meta, attr))

        view_model = ArchitectureModel(
            meta=view_meta,
            entities=view_entities,
            relationships=view_rels,
        )

        views.append(SubsystemView(
            component_id=top_comp.id,
            component_name=top_comp.name,
            slug=slug,
            model=view_model,
        ))

    return views


def write_subsystem_views(
    views: list[SubsystemView],
    output_dir: Path,
) -> list[Path]:
    """Write subsystem views as .architecture-model.yaml files.

    Args:
        views: List of derived subsystem views.
        output_dir: Root output directory (e.g. .architecture-models/).

    Returns:
        List of paths written.
    """
    written: list[Path] = []
    for view in views:
        view_dir = output_dir / view.slug
        view_dir.mkdir(parents=True, exist_ok=True)
        out_path = view_dir / ".architecture-model.yaml"

        model_dict = view.model.to_dict()
        content = yaml.dump(model_dict, default_flow_style=False, sort_keys=False, allow_unicode=True)
        out_path.write_text(content)
        written.append(out_path)

    return written
