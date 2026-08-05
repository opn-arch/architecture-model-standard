"""Behavior flow filtering, grouping, scoped manifests & sub-models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from architecture_model.core.types import (
    ArchitectureModel, Behavior, Component, Entities, Interface,
    ModelMeta, Relationship, RelationType, Status,
)
from architecture_model.manifest.call_graph import CallGraph, FlowTrace, map_flow_to_components, trace_flow
from architecture_model.manifest.types import InterfaceEdge, Manifest, MetricsResult


@dataclass
class BehaviorClassification:
    """Result of classifying behaviors."""
    cross_component: list[tuple[Behavior, FlowTrace]] = field(default_factory=list)
    crud_groups: dict[str, list[Behavior]] = field(default_factory=dict)
    trivial: list[Behavior] = field(default_factory=list)


@dataclass
class CrudSummary:
    """Summary of a CRUD group for a component."""
    component_id: str
    count: int
    verbs: dict[str, int]
    summary: str


def classify_behaviors(
    behaviors: list[Behavior],
    relationships: list[Relationship],
    call_graph: CallGraph,
    file_to_comp: dict[str, str],
) -> BehaviorClassification:
    """Classify behaviors into cross-component, single-component CRUD, and trivial."""
    result = BehaviorClassification()

    for beh in behaviors:
        # Trivial: 0-1 steps
        if len(beh.steps) <= 1:
            result.trivial.append(beh)
            continue

        # Trace flow to determine component crossing
        flow = _trace_behavior(beh, call_graph, file_to_comp)
        unique_comps = set(flow.components_crossed)
        if len(unique_comps) >= 2:
            result.cross_component.append((beh, flow))
        else:
            # Single-component CRUD
            comp_id = flow.components_crossed[0] if flow.components_crossed else "_unknown"
            result.crud_groups.setdefault(comp_id, []).append(beh)

    return result


def _trace_behavior(beh: Behavior, call_graph: CallGraph, file_to_comp: dict[str, str]) -> FlowTrace:
    """Trace a behavior's flow through the call graph."""
    entry = f"{beh.source_file}:{beh.name}" if beh.source_file else f":{beh.name}"
    if entry in call_graph.functions:
        flow = trace_flow(call_graph, entry)
    else:
        # No entry in call graph - create minimal flow
        steps = [(beh.source_file, beh.name)] if beh.source_file else []
        flow = FlowTrace(entry=entry, steps=steps, components_crossed=[], depth=0, truncated=False)
    return map_flow_to_components(flow, file_to_comp)


def summarize_crud_group(component_id: str, behaviors: list[Behavior]) -> CrudSummary:
    """Summarize a group of CRUD behaviors for one component."""
    verbs: dict[str, int] = {}
    for beh in behaviors:
        verb = beh.trigger.split()[0].upper() if beh.trigger and " " in beh.trigger else "OTHER"
        verbs[verb] = verbs.get(verb, 0) + 1

    parts = [f"{count} {verb}" for verb, count in sorted(verbs.items())]
    summary = f"{len(behaviors)} CRUD endpoints ({', '.join(parts)})"
    return CrudSummary(component_id=component_id, count=len(behaviors), verbs=verbs, summary=summary)


def build_behavior_manifest(
    behavior: Behavior,
    flow_trace: FlowTrace,
    manifest: Manifest,
) -> Manifest:
    """Build a scoped manifest containing only modules touched by the flow."""
    touched_files = {file for file, _ in flow_trace.steps}
    filtered_modules = [m for m in manifest.modules if m.file in touched_files]
    filtered_interfaces = [i for i in manifest.interfaces if i.source in touched_files and i.target in touched_files]

    return Manifest(
        modules=filtered_modules,
        interfaces=filtered_interfaces,
        functional_blocks={},
        generated_at=manifest.generated_at,
        project_root=manifest.project_root,
        metrics=MetricsResult(values={}),
    )


def build_behavior_sub_model(
    behavior: Behavior,
    flow_trace: FlowTrace,
    model: ArchitectureModel,
    file_to_comp: dict[str, str],
) -> ArchitectureModel:
    """Build a sub-model for a specific behavior flow."""
    touched_comp_ids = set(flow_trace.components_crossed)

    # Get components
    entities = model.entities
    components = [c for c in entities.components if c.id in touched_comp_ids]

    # Filter relationships: both ends in touched components or involve this behavior
    relevant_ids = touched_comp_ids | {behavior.id}
    relationships = [
        r for r in model.relationships
        if r.from_id in relevant_ids and r.to_id in relevant_ids
    ]

    # Filter interfaces: provider or consumer in touched components
    interfaces = [
        i for i in entities.interfaces
        if getattr(i, 'provider', '') in touched_comp_ids or getattr(i, 'consumer', '') in touched_comp_ids
    ]

    meta = ModelMeta(
        project=model.meta.project,
        schema_version="1.3",
    )
    # Add refines_behavior (may not exist on ModelMeta, so set dynamically)
    meta.refines_behavior = behavior.id  # type: ignore[attr-defined]

    return ArchitectureModel(
        meta=meta,
        entities=Entities(
            components=components,
            behaviors=[behavior],
            interfaces=interfaces,
        ),
        relationships=relationships,
    )


def build_file_to_comp(model: ArchitectureModel, manifest: Manifest) -> dict[str, str]:
    """Build file->component mapping from model + manifest."""
    mapping: dict[str, str] = {}

    entities = model.entities
    components = entities.components if isinstance(entities, Entities) else []

    # Strategy 1: Use component.files directly
    for comp in components:
        for f in comp.files:
            mapping[f] = comp.id

    # If we got mappings, return them
    if mapping:
        return mapping

    # Strategy 2: Use behavior source_files via relationships
    beh_map: dict[str, str] = {}  # beh_id -> source_file
    for beh in (entities.behaviors if isinstance(entities, Entities) else []):
        if beh.source_file:
            beh_map[beh.id] = beh.source_file

    for rel in model.relationships:
        if rel.type == RelationType.REALIZES and rel.to_id in beh_map:
            mapping[beh_map[rel.to_id]] = rel.from_id

    return mapping
