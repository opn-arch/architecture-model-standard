"""Infer user-facing capabilities from behavior trigger patterns."""
from __future__ import annotations

import re
from collections import defaultdict

from architecture_model.core.types import (
    ArchitectureModel, Capability, Entities, Relationship, RelationType
)


def _extract_url_prefix(trigger: str) -> str | None:
    """Extract first path segment: 'POST /users/{id}' -> 'users'."""
    match = re.search(r'/([a-zA-Z_][\w-]*)', trigger)
    return match.group(1).lower() if match else None


def _name_from_prefix(prefix: str) -> str:
    """Convert URL prefix to capability name: 'users' -> 'User Management'."""
    singular = prefix.rstrip("s") if prefix.endswith("s") and len(prefix) > 3 else prefix
    return f"{singular.replace('_', ' ').replace('-', ' ').title()} Management"


def infer_capabilities(model: ArchitectureModel) -> ArchitectureModel:
    """Infer capabilities from behaviors, add to model with realizes relationships.

    Clustering (priority order):
    1. URL prefix from trigger (/users/*, /orders/*)
    2. Actor (same actor -> same capability)
    3. Ungrouped -> "Internal Operations"

    Preserves existing capabilities. Returns new model with additions.
    """
    behaviors = model.entities.behaviors or []
    if not behaviors:
        return model

    existing_caps = list(model.entities.capabilities or [])
    existing_rels = list(model.relationships)

    # Group by URL prefix first, then actor
    prefix_groups: dict[str, list] = defaultdict(list)
    ungrouped = []

    for beh in behaviors:
        prefix = _extract_url_prefix(beh.trigger) if beh.trigger else None
        if prefix:
            prefix_groups[prefix].append(beh)
        elif beh.actor:
            prefix_groups[f"actor:{beh.actor}"].append(beh)
        else:
            ungrouped.append(beh)

    new_caps = []
    new_rels = []
    cap_counter = len(existing_caps) + 1

    for key, behs in sorted(prefix_groups.items()):
        cap_id = f"CAP-{cap_counter}"
        if key.startswith("actor:"):
            name = f"{key[6:].replace('_', ' ').title()} Operations"
        else:
            name = _name_from_prefix(key)

        cap = Capability(id=cap_id, name=name, status="ACTIVE")
        new_caps.append(cap)
        for beh in behs:
            new_rels.append(Relationship(
                type=RelationType.REALIZES, from_id=beh.id, to_id=cap_id
            ))
        cap_counter += 1

    if ungrouped:
        cap_id = f"CAP-{cap_counter}"
        new_caps.append(Capability(id=cap_id, name="Internal Operations", status="ACTIVE"))
        for beh in ungrouped:
            new_rels.append(Relationship(
                type=RelationType.REALIZES, from_id=beh.id, to_id=cap_id
            ))

    new_entities = Entities(
        components=model.entities.components,
        capabilities=existing_caps + new_caps,
        behaviors=behaviors,
        constraints=model.entities.constraints,
        interfaces=model.entities.interfaces,
        layers=model.entities.layers,
        actors=model.entities.actors,
        systems=model.entities.systems,
        data=model.entities.data,
        events=model.entities.events,
        resources=model.entities.resources,
        environments=model.entities.environments,
        quality_attributes=model.entities.quality_attributes,
        decisions=model.entities.decisions,
        lifecycles=model.entities.lifecycles,
        requirements=model.entities.requirements,
    )

    return ArchitectureModel(
        meta=model.meta,
        entities=new_entities,
        relationships=existing_rels + new_rels,
    )


def build_capability_hierarchy(model: ArchitectureModel) -> ArchitectureModel:
    """Add contains relationships between capabilities based on URL path depth.

    If capability A's behaviors use prefix /X and capability B's behaviors
    use prefix /X/Y, then A contains B.
    """
    from dataclasses import replace as dc_replace

    caps = model.entities.capabilities or []
    behaviors = model.entities.behaviors or []
    if len(caps) < 2:
        return model

    # Build cap_id -> set of full URL paths
    realizes = [r for r in model.relationships if r.type == RelationType.REALIZES]
    beh_index = {b.id: b for b in behaviors}

    cap_paths: dict[str, set[str]] = defaultdict(set)
    for rel in realizes:
        beh = beh_index.get(rel.from_id)
        if beh and beh.trigger:
            match = re.search(r'(/[\w/{}.-]+)', beh.trigger)
            if match:
                cap_paths[rel.to_id].add(match.group(1))

    # For each cap, determine common prefix
    cap_prefix: dict[str, str] = {}
    for cap_id, paths in cap_paths.items():
        if not paths:
            continue
        segments_list = [p.strip("/").split("/") for p in paths]
        min_segments = min(len(s) for s in segments_list)
        common = []
        for i in range(min_segments):
            vals = {s[i] for s in segments_list}
            if len(vals) == 1:
                common.append(vals.pop())
            else:
                break
        if common:
            cap_prefix[cap_id] = "/" + "/".join(common)

    # Find parent-child based on prefix containment
    new_rels = list(model.relationships)
    existing_contains = {
        (r.from_id, r.to_id) for r in model.relationships if r.type == RelationType.CONTAINS
    }

    for child_id, child_prefix in cap_prefix.items():
        child_parts = child_prefix.strip("/").split("/")
        if len(child_parts) <= 1:
            continue
        parent_prefix = "/" + "/".join(child_parts[:-1])
        for parent_id, p_prefix in cap_prefix.items():
            if parent_id == child_id:
                continue
            if p_prefix == parent_prefix:
                pair = (parent_id, child_id)
                if pair not in existing_contains:
                    new_rels.append(Relationship(
                        type=RelationType.CONTAINS, from_id=parent_id, to_id=child_id
                    ))
                    existing_contains.add(pair)
                break

    return dc_replace(model, relationships=new_rels)
