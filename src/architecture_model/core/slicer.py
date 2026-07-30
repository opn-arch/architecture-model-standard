"""
Slicer: Extract subsets of the architecture model.

Produces focused model slices for:
- Single F-block context (capability + its behaviors, components, interfaces)
- Single layer context (layer + its components + dependency rules)
- Status filter (only ACTIVE, or only PLANNED)
- Artifact-specific context (what an artifact needs to regenerate itself)
"""

from __future__ import annotations

from copy import deepcopy
from typing import Optional

from .types import (
    ArchitectureModel,
    Entities,
    ModelMeta,
    Relationship,
    Status,
    RelationType,
)

from architecture_model.monitoring import monitored


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@monitored(module="core.slicer", outputs=lambda r: {"entities_retained": len(r.entities.components), "relationships_retained": len(r.relationships)})
def slice_by_fblock(
    model: ArchitectureModel,
    f_block: str,
    include_relationships: bool = True,
) -> ArchitectureModel:
    """
    Extract all entities and relationships related to a specific F-block.

    Args:
        model: Full architecture model.
        f_block: F-block identifier (e.g., "F1", "F2").
        include_relationships: Whether to include relationships between sliced entities.

    Returns:
        New ArchitectureModel containing only the F-block's entities.
    """
    # Find capability for this f-block
    cap_ids = {c.id for c in model.entities.capabilities if c.f_block == f_block}

    # Find behaviors tagged with this f-block
    behaviors = [b for b in model.entities.behaviors if f_block in b.tags]
    behavior_ids = {b.id for b in behaviors}

    # Find components allocated to this f-block
    components = [c for c in model.entities.components if c.f_block == f_block]
    component_ids = {c.id for c in components}

    # Find interfaces where this f-block is provider or consumer
    interfaces = [
        i for i in model.entities.interfaces if f_block in i.provider or f_block in i.consumer
    ]
    interface_ids = {i.id for i in interfaces}

    # Collect all relevant entity IDs
    relevant_ids = cap_ids | behavior_ids | component_ids | interface_ids

    # Find data entities owned by components in this f-block
    data_entities = [d for d in model.entities.data if d.owner in component_ids]
    data_ids = {d.id for d in data_entities}

    # Find events sourced from or targeting components in this f-block
    events = [e for e in model.entities.events if e.source in component_ids or e.target in component_ids]
    event_ids = {e.id for e in events}

    # Find quality attributes that apply to entities in this f-block
    quality_attrs = [q for q in model.entities.quality_attributes if any(a in relevant_ids for a in q.applies_to)]
    qa_ids = {q.id for q in quality_attrs}

    relevant_ids = relevant_ids | data_ids | event_ids | qa_ids

    # Find actors referenced by behaviors
    actor_refs = set()
    for beh in behaviors:
        if beh.actor:
            for ref in beh.actor.split(","):
                actor_refs.add(ref.strip())
    actors = [a for a in model.entities.actors if a.id in actor_refs]

    # Filter relationships
    relationships = []
    if include_relationships:
        for rel in model.relationships:
            if rel.from_id in relevant_ids or rel.to_id in relevant_ids:
                relationships.append(deepcopy(rel))

    # Get capabilities for this f-block
    capabilities = [c for c in model.entities.capabilities if c.f_block == f_block]

    return ArchitectureModel(
        meta=ModelMeta(
            schema_version=model.meta.schema_version,
            project=model.meta.project,
            system=model.meta.system,
            generated_at=model.meta.generated_at,
            source_artifacts=model.meta.source_artifacts,
        ),
        entities=Entities(
            actors=actors,
            capabilities=capabilities,
            behaviors=behaviors,
            interfaces=interfaces,
            constraints=[],  # Constraints are global
            layers=[],  # Layers are global
            components=components,
            data=data_entities,
            events=events,
            quality_attributes=quality_attrs,
        ),
        relationships=relationships,
    )


@monitored(module="core.slicer", outputs=lambda r: {"entities_retained": len(r.entities.components), "relationships_retained": len(r.relationships)})
def slice_by_layer(
    model: ArchitectureModel,
    layer_id: str,
) -> ArchitectureModel:
    """
    Extract all entities allocated to a specific layer.

    Args:
        model: Full architecture model.
        layer_id: Layer identifier (e.g., "web-layer", "pipeline-layer").

    Returns:
        New ArchitectureModel with layer-specific entities.
    """
    # Find layer
    layers = [l for l in model.entities.layers if l.id == layer_id]

    # Find components in this layer
    components = [c for c in model.entities.components if c.layer == layer_id]
    component_ids = {c.id for c in components}

    # Find relationships involving these components
    relationships = [
        deepcopy(r)
        for r in model.relationships
        if r.from_id in component_ids or r.to_id in component_ids
    ]

    return ArchitectureModel(
        meta=ModelMeta(
            schema_version=model.meta.schema_version,
            project=model.meta.project,
            system=model.meta.system,
            generated_at=model.meta.generated_at,
            source_artifacts=model.meta.source_artifacts,
        ),
        entities=Entities(
            layers=layers,
            components=components,
        ),
        relationships=relationships,
    )


@monitored(module="core.slicer", outputs=lambda r: {"entities_retained": len(r.entities.components), "relationships_retained": len(r.relationships)})
def slice_by_status(
    model: ArchitectureModel,
    status: Status,
) -> ArchitectureModel:
    """
    Filter model to only include entities with a specific status.

    Args:
        model: Full architecture model.
        status: Status to filter by.

    Returns:
        New ArchitectureModel with only matching entities.
    """
    entities = Entities(
        actors=[a for a in model.entities.actors if a.status == status],
        capabilities=[c for c in model.entities.capabilities if c.status == status],
        behaviors=[b for b in model.entities.behaviors if b.status == status],
        interfaces=[i for i in model.entities.interfaces if i.status == status],
        constraints=[c for c in model.entities.constraints if c.status == status],
        layers=[l for l in model.entities.layers if l.status == status],
        components=[c for c in model.entities.components if c.status == status],
        systems=[s for s in model.entities.systems if s.status == status],
        data=[d for d in model.entities.data if d.status == status],
        events=[e for e in model.entities.events if e.status == status],
        resources=[r for r in model.entities.resources if r.status == status],
        environments=[e for e in model.entities.environments if e.status == status],
        quality_attributes=[q for q in model.entities.quality_attributes if q.status == status],
        decisions=[d for d in model.entities.decisions if d.status == status],
        lifecycles=[l for l in model.entities.lifecycles if l.status == status],
    )

    # Only include relationships where both endpoints exist in filtered set
    all_ids = set()
    for attr_name in ['actors', 'capabilities', 'behaviors', 'interfaces', 'constraints',
                      'layers', 'components', 'systems', 'data', 'events', 'resources',
                      'environments', 'quality_attributes', 'decisions', 'lifecycles']:
        for e in getattr(entities, attr_name, []):
            all_ids.add(e.id)

    relationships = [
        deepcopy(r) for r in model.relationships if r.from_id in all_ids and r.to_id in all_ids
    ]

    return ArchitectureModel(
        meta=deepcopy(model.meta),
        entities=entities,
        relationships=relationships,
    )


@monitored(module="core.slicer", outputs=lambda r: {"entities_retained": len(r.entities.components), "relationships_retained": len(r.relationships)})
def slice_for_artifact(
    model: ArchitectureModel,
    artifact_name: str,
) -> ArchitectureModel:
    """
    Extract the model subset relevant to a specific artifact's regeneration.

    Artifact-specific slicing rules:
    - functional-architecture: capabilities, behaviors (summary), relationships
    - logical-architecture: layers, components, inter-layer relationships
    - use-cases: actors, behaviors (full), capabilities (summary)
    - icd: interfaces, components (providers/consumers)
    - requirements-analysis: constraints, capabilities, behaviors (summary)
    - readme: everything (summary level)

    Args:
        model: Full architecture model.
        artifact_name: Name of the artifact to slice for.

    Returns:
        Model subset appropriate for the artifact.
    """
    slicers = {
        "functional-architecture": _slice_for_functional,
        "logical-architecture": _slice_for_logical,
        "use-cases": _slice_for_use_cases,
        "icd": _slice_for_icd,
        "requirements-analysis": _slice_for_requirements,
        "operations-manual": _slice_for_operations_manual,
        "conops": _slice_for_conops,
        "testing": _slice_for_testing,
        "deployment-guide": _slice_for_deployment,
        "data-dictionary": _slice_for_data_dictionary,
        "readme": _slice_for_readme,
    }

    slicer_fn = slicers.get(artifact_name)
    if slicer_fn:
        return slicer_fn(model)

    # Default: return full model
    return deepcopy(model)


# ---------------------------------------------------------------------------
# Artifact-specific slicers
# ---------------------------------------------------------------------------


def _slice_for_functional(model: ArchitectureModel) -> ArchitectureModel:
    """Slice for functional-architecture: capabilities, behaviors, data flows."""
    # Include all capabilities, behaviors (for realization links), and key relationships
    relationships = [
        deepcopy(r)
        for r in model.relationships
        if r.type in (RelationType.REALIZES, RelationType.CONTAINS, RelationType.DEPENDS_ON)
    ]

    return ArchitectureModel(
        meta=deepcopy(model.meta),
        entities=Entities(
            actors=list(model.entities.actors),
            capabilities=list(model.entities.capabilities),
            behaviors=list(model.entities.behaviors),
            interfaces=[],
            constraints=[],
            layers=[],
            components=[],
        ),
        relationships=relationships,
    )


def _slice_for_logical(model: ArchitectureModel) -> ArchitectureModel:
    """Slice for logical-architecture: layers, components, technology allocation."""
    relationships = [
        deepcopy(r)
        for r in model.relationships
        if r.type in (RelationType.ALLOCATED_TO, RelationType.CONTAINS, RelationType.DEPENDS_ON)
    ]

    return ArchitectureModel(
        meta=deepcopy(model.meta),
        entities=Entities(
            capabilities=list(model.entities.capabilities),
            layers=list(model.entities.layers),
            components=list(model.entities.components),
        ),
        relationships=relationships,
    )


def _slice_for_use_cases(model: ArchitectureModel) -> ArchitectureModel:
    """Slice for use-cases: actors, behaviors (full), capabilities for traceability."""
    relationships = [
        deepcopy(r)
        for r in model.relationships
        if r.type in (RelationType.REALIZES, RelationType.DEPENDS_ON)
    ]

    return ArchitectureModel(
        meta=deepcopy(model.meta),
        entities=Entities(
            actors=list(model.entities.actors),
            capabilities=list(model.entities.capabilities),
            behaviors=list(model.entities.behaviors),
        ),
        relationships=relationships,
    )


def _slice_for_icd(model: ArchitectureModel) -> ArchitectureModel:
    """Slice for ICD: interfaces, provider/consumer components."""
    # Find components that are providers or consumers
    interface_refs = set()
    for iface in model.entities.interfaces:
        if iface.provider:
            interface_refs.add(iface.provider)
        if iface.consumer:
            interface_refs.add(iface.consumer)

    relationships = [
        deepcopy(r)
        for r in model.relationships
        if r.type in (RelationType.EXPOSES, RelationType.CONSUMES)
    ]

    return ArchitectureModel(
        meta=deepcopy(model.meta),
        entities=Entities(
            capabilities=list(model.entities.capabilities),
            interfaces=list(model.entities.interfaces),
            components=list(model.entities.components),
            layers=list(model.entities.layers),
        ),
        relationships=relationships,
    )


def _slice_for_requirements(model: ArchitectureModel) -> ArchitectureModel:
    """Slice for requirements-analysis: constraints, capabilities, behavior summaries."""
    relationships = [
        deepcopy(r)
        for r in model.relationships
        if r.type in (RelationType.CONSTRAINED_BY, RelationType.TRACES_TO, RelationType.REALIZES)
    ]

    return ArchitectureModel(
        meta=deepcopy(model.meta),
        entities=Entities(
            capabilities=list(model.entities.capabilities),
            behaviors=list(model.entities.behaviors),
            constraints=list(model.entities.constraints),
            quality_attributes=list(model.entities.quality_attributes),
            decisions=list(model.entities.decisions),
        ),
        relationships=relationships,
    )


def _slice_for_operations_manual(model: ArchitectureModel) -> ArchitectureModel:
    """Slice for operations-manual: behaviors (operational), components, interfaces."""
    # Ops manual needs: what the system does (behaviors), how to interact (interfaces),
    # and what components are involved (for troubleshooting)
    relationships = [
        deepcopy(r)
        for r in model.relationships
        if r.type in (RelationType.REALIZES, RelationType.EXPOSES)
    ]

    return ArchitectureModel(
        meta=deepcopy(model.meta),
        entities=Entities(
            capabilities=list(model.entities.capabilities),
            behaviors=list(model.entities.behaviors),
            interfaces=list(model.entities.interfaces),
            components=list(model.entities.components),
            events=list(model.entities.events),
            resources=list(model.entities.resources),
        ),
        relationships=relationships,
    )


def _slice_for_conops(model: ArchitectureModel) -> ArchitectureModel:
    """Slice for conops: actors, capabilities, behaviors overview."""
    # ConOps needs the full operational picture: who uses it, what it does, how it behaves
    relationships = [
        deepcopy(r)
        for r in model.relationships
        if r.type in (RelationType.REALIZES, RelationType.DEPENDS_ON)
    ]

    return ArchitectureModel(
        meta=deepcopy(model.meta),
        entities=Entities(
            actors=list(model.entities.actors),
            capabilities=list(model.entities.capabilities),
            behaviors=list(model.entities.behaviors),
            constraints=list(model.entities.constraints),
            environments=list(model.entities.environments),
            lifecycles=list(model.entities.lifecycles),
        ),
        relationships=relationships,
    )


def _slice_for_testing(model: ArchitectureModel) -> ArchitectureModel:
    """Slice for testing: constraints (NFRs), behaviors (UCs to test), components."""
    # Testing needs: what to test (behaviors), acceptance criteria (constraints),
    # and what components realize each requirement (for test allocation)
    relationships = [
        deepcopy(r)
        for r in model.relationships
        if r.type in (RelationType.REALIZES, RelationType.CONSTRAINED_BY)
    ]

    return ArchitectureModel(
        meta=deepcopy(model.meta),
        entities=Entities(
            capabilities=list(model.entities.capabilities),
            behaviors=list(model.entities.behaviors),
            constraints=list(model.entities.constraints),
            components=list(model.entities.components),
            quality_attributes=list(model.entities.quality_attributes),
        ),
        relationships=relationships,
    )


def _slice_for_deployment(model: ArchitectureModel) -> ArchitectureModel:
    """Slice for deployment-guide: layers, components, interfaces (infra focus)."""
    # Deployment needs: what layers exist, what components must be deployed,
    # and what external interfaces must be configured
    relationships = [
        deepcopy(r)
        for r in model.relationships
        if r.type in (RelationType.DEPENDS_ON, RelationType.EXPOSES, RelationType.CONSUMES)
    ]

    return ArchitectureModel(
        meta=deepcopy(model.meta),
        entities=Entities(
            capabilities=list(model.entities.capabilities),
            interfaces=list(model.entities.interfaces),
            layers=list(model.entities.layers),
            components=list(model.entities.components),
            actors=[a for a in model.entities.actors if a.type.value == "external_service"],
            environments=list(model.entities.environments),
            resources=list(model.entities.resources),
        ),
        relationships=relationships,
    )


def _slice_for_data_dictionary(model: ArchitectureModel) -> ArchitectureModel:
    """Slice for data-dictionary: components (data layer), interfaces, layers."""
    # Data dictionary needs: data-layer components (models), interfaces (DB, internal),
    # and F-block ownership for entity allocation
    data_components = [
        c
        for c in model.entities.components
        if c.layer in ("data-layer", "services-layer") or "model" in c.name.lower()
    ]

    relationships = [
        deepcopy(r)
        for r in model.relationships
        if r.type in (RelationType.REALIZES, RelationType.EXPOSES)
    ]

    return ArchitectureModel(
        meta=deepcopy(model.meta),
        entities=Entities(
            capabilities=list(model.entities.capabilities),
            interfaces=list(model.entities.interfaces),
            layers=list(model.entities.layers),
            components=data_components,
            data=list(model.entities.data),
        ),
        relationships=relationships,
    )


def _slice_for_readme(model: ArchitectureModel) -> ArchitectureModel:
    """Slice for readme: high-level overview (capabilities, layers, actors only).

    The readme needs a project overview — not the full 129 entities.
    Provides: what the system does (capabilities), who uses it (actors),
    and how it's structured (layers). Skips detailed behaviors, interfaces,
    constraints, and individual components.
    """
    relationships = [
        deepcopy(r)
        for r in model.relationships
        if r.type == RelationType.REALIZES
        and (r.from_id.startswith("COMP-") and r.to_id.startswith("CAP-"))
    ]

    return ArchitectureModel(
        meta=deepcopy(model.meta),
        entities=Entities(
            actors=list(model.entities.actors),
            capabilities=list(model.entities.capabilities),
            layers=list(model.entities.layers),
            decisions=list(model.entities.decisions),
        ),
        relationships=relationships,
    )
