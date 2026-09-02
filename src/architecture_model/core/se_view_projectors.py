"""Deterministic ConOps and functional architecture projections."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from architecture_model.core.diagram_spec import (
    Diagnostic,
    DiagramCallout,
    DiagramDrilldown,
    DiagramEdge,
    DiagramGroup,
    DiagramNode,
    DiagramProvenance,
    DiagramSpec,
)
from architecture_model.core.view_context import ArchitectureViewContext, IndexedEntity, IndexedRelationship
from architecture_model.core.view_curation import CuratedFlow, EvidenceRecord, ViewCuration, validate_view_curation


CONOPS_PRIMARY_LIMIT = 15
FUNCTIONAL_BLOCK_LIMIT = 12
SUPPORTING_LIMIT = 12


def _node_id(key: str) -> str:
    return f"node:{key}"


def _provenance(entity: IndexedEntity) -> DiagramProvenance:
    return DiagramProvenance(
        source="model-entity", entity_refs=[entity.key], source_files=[entity.source_path],
    )


def _relationship_provenance(relationship: IndexedRelationship) -> DiagramProvenance:
    return DiagramProvenance(
        source="model-relationship",
        entity_refs=[relationship.source, relationship.target],
        context={"type": relationship.kind, "model": relationship.model},
    )


def _curated_provenance(evidence: Iterable[EvidenceRecord]) -> list[DiagramProvenance]:
    return [
        DiagramProvenance(source="curated-inference", source_files=[item.source], context={"claim": item.claim})
        for item in evidence
    ]


def _badges(entity: IndexedEntity, *, behaviors: int = 0, components: int = 0) -> list[str]:
    values = entity.value
    result: list[str] = []
    if behaviors:
        result.append(f"behaviors:{behaviors}")
    if components:
        result.append(f"components:{components}")
    result.extend((
        f"requirements:{len(getattr(values, 'requirements', []) or [])}",
        f"moes:{len(getattr(values, 'moes', []) or [])}",
        f"failures:{len(getattr(values, 'failure_modes', []) or [])}",
        f"monitoring:{len(getattr(values, 'monitored', []) or [])}",
    ))
    return result


def _label(entity: IndexedEntity, curation: ViewCuration) -> str:
    return curation.labels.get(entity.key, entity.name)


def _system_badges(context: ArchitectureViewContext, entity: IndexedEntity) -> list[str]:
    child_models = context.child_models_for_system(entity.key)
    if not child_models:
        return []
    capabilities = sum(len(context.entities("capability", model)) for model in child_models)
    behaviors = sum(len(context.entities("behavior", model)) for model in child_models)
    return [f"capabilities:{capabilities}", f"behaviors:{behaviors}"]


def _curation_diagnostics(
    view_name: str, context: ArchitectureViewContext, curation: ViewCuration,
) -> list[Diagnostic]:
    diagnostics = validate_view_curation(curation, context)
    return [
        Diagnostic(item.severity, f"{view_name.upper()}_CURATION_INVALID", item.message, view=view_name, source=item.source)
        for item in diagnostics
    ]


def _canonical_edge(source: str, target: str, kind: str, relationship: IndexedRelationship) -> DiagramEdge:
    return DiagramEdge(source, target, kind, evidence=[_relationship_provenance(relationship)])


def _find_local(context: ArchitectureViewContext, owner: str, reference: str) -> IndexedEntity | None:
    if not reference:
        return None
    key = reference if "::" in reference else f"{owner}::{reference}"
    return context.entity(key, diagnose=False)


def project_conops(
    context: ArchitectureViewContext, curation: ViewCuration | None = None,
) -> DiagramSpec:
    """Project operational paths without inventing actor-to-system connectivity."""
    curation = curation or ViewCuration()
    warnings = _curation_diagnostics("conops", context, curation)
    hidden = {item.resolved_id for item in curation.hide if item.resolved_id}
    actors = [item for item in context.entities("actor") if item.key not in hidden]
    externals = [item for item in context.entities("external_system") if item.key not in hidden]
    behaviors = [item for item in context.entities("behavior") if item.key not in hidden]
    systems = [item for item in context.entities("system") if item.key not in hidden]

    connected_actor_keys = {
        actor.key for behavior in behaviors
        for actor in [
            (_find_local(context, behavior.model, getattr(behavior.value, "actor_id", "")) or
             _find_local(context, behavior.model, getattr(behavior.value, "actor", "")))
        ] if actor and actor.entity_type == "actor"
    }
    actors.sort(key=lambda item: (item.key not in connected_actor_keys, item.key))
    primary: list[tuple[str, IndexedEntity]] = [
        *[("actor", item) for item in actors],
        *[("external", item) for item in externals],
        *[("scenario", item) for item in behaviors],
        *[("system", item) for item in systems],
    ]
    curated_order = {key: index for index, key in enumerate(curation.order)}
    primary.sort(key=lambda pair: (
        curated_order.get(pair[1].key, len(curated_order)),
        {"actor": 0, "external": 1, "scenario": 2, "system": 3}[pair[0]], pair[1].key,
    ))
    selected = primary[:CONOPS_PRIMARY_LIMIT]
    if len(primary) > len(selected):
        warnings.append(Diagnostic(
            "warning", "CONOPS_OVERVIEW_BOUNDED",
            f"{len(primary) - len(selected)} primary nodes omitted (limit {CONOPS_PRIMARY_LIMIT})", view="conops",
        ))
    selected_keys = {item.key for _, item in selected}
    lanes = [
        DiagramGroup("actors", "Actors and Externals", "lane", order=0),
        DiagramGroup("scenarios", "Operational Scenarios", "lane", order=1),
        DiagramGroup("boundary", "Interfaces and System Boundary", "lane", order=2),
        DiagramGroup("outcomes", "Operational Outcomes", "lane", order=3),
    ]
    nodes: list[DiagramNode] = []
    drilldowns: list[DiagramDrilldown] = []
    for kind, entity in selected:
        identifier = _node_id(entity.key)
        lane = "actors" if kind in {"actor", "external"} else "scenarios" if kind == "scenario" else "boundary"
        subtitle = ""
        if kind == "scenario":
            trigger = getattr(entity.value, "trigger", "")
            goal = next(iter(getattr(entity.value, "goals", []) or []), getattr(entity.value, "intent", ""))
            subtitle = " | ".join(value for value in (trigger, goal) if value)
            drilldown_id = f"drilldown:{entity.key}"
            drilldowns.append(DiagramDrilldown(drilldown_id, identifier, spec_ref=f"conops:{entity.key}"))
        else:
            drilldown_id = ""
        nodes.append(DiagramNode(
            identifier, _label(entity, curation), kind, subtitle=subtitle, lane=lane,
            entity_ref=entity.key, drilldown_ref=drilldown_id,
            badges=_badges(entity) if kind == "scenario" else _system_badges(context, entity) if kind == "system" else [],
            evidence=[_provenance(entity)],
        ))

    for external in curation.externals[:SUPPORTING_LIMIT]:
        evidence = _curated_provenance(external.evidence)
        if evidence and external.id not in {node.id for node in nodes}:
            nodes.append(DiagramNode(
                external.id, external.name, "external", lane="actors", status="inferred",
                inferred=True, evidence=evidence,
            ))

    interfaces = context.entities("interface")[:SUPPORTING_LIMIT]
    for interface in interfaces:
        if interface.key in hidden:
            continue
        nodes.append(DiagramNode(
            _node_id(interface.key), _label(interface, curation), "interface", lane="boundary",
            entity_ref=interface.key, evidence=[_provenance(interface)],
        ))

    node_by_ref = {node.entity_ref: node.id for node in nodes if node.entity_ref}
    edges: list[DiagramEdge] = []
    edge_keys: set[tuple[str, str, str]] = set()
    for relationship in context.relationships():
        if relationship.source not in node_by_ref or relationship.target not in node_by_ref:
            continue
        source_type = context.entity(relationship.source, diagnose=False).entity_type
        target_type = context.entity(relationship.target, diagnose=False).entity_type
        if "interface" not in {source_type, target_type} and relationship.kind != "triggers":
            continue
        edge = _canonical_edge(node_by_ref[relationship.source], node_by_ref[relationship.target], relationship.kind, relationship)
        key = (edge.source, edge.target, edge.kind)
        if key not in edge_keys:
            edge_keys.add(key)
            edges.append(edge)

    for behavior in behaviors:
        if behavior.key not in node_by_ref:
            continue
        scenario_id = node_by_ref[behavior.key]
        actor = _find_local(context, behavior.model, getattr(behavior.value, "actor_id", ""))
        if actor and actor.key in node_by_ref:
            evidence = DiagramProvenance(source="behavior-actor", entity_refs=[behavior.key, actor.key])
            edges.append(DiagramEdge(node_by_ref[actor.key], scenario_id, "initiates", evidence=[evidence]))
        for reference in getattr(behavior.value, "interface_refs", []) or []:
            interface = _find_local(context, behavior.model, reference)
            if interface and interface.key in node_by_ref:
                evidence = DiagramProvenance(source="behavior-interface", entity_refs=[behavior.key, interface.key])
                edges.append(DiagramEdge(scenario_id, node_by_ref[interface.key], "uses", evidence=[evidence]))

    outcomes: list[tuple[DiagramNode, DiagramEdge]] = []
    callouts: list[DiagramCallout] = []
    for behavior in behaviors:
        if behavior.key not in node_by_ref:
            continue
        values = list(getattr(behavior.value, "postconditions", []) or getattr(behavior.value, "goals", []) or [])
        for index, outcome in enumerate(values[:2]):
            identifier = f"outcome:{behavior.key}:{index}"
            evidence = DiagramProvenance(source="behavior-outcome", entity_refs=[behavior.key])
            node = DiagramNode(identifier, outcome, "outcome", lane="outcomes", evidence=[evidence])
            edge = DiagramEdge(node_by_ref[behavior.key], identifier, "produces", evidence=[evidence])
            outcomes.append((node, edge))
        for index, failure in enumerate((getattr(behavior.value, "failure_modes", []) or [])[:1]):
            callouts.append(DiagramCallout(f"callout:{behavior.key}:{index}", failure, node_by_ref[behavior.key], "failure"))
    for node, edge in outcomes[:SUPPORTING_LIMIT]:
        nodes.append(node)
        edges.append(edge)
    if not nodes:
        nodes.append(DiagramNode("conops:empty", "Operational context unavailable", "warning", lane="scenarios"))
        warnings.append(Diagnostic("warning", "CONOPS_SPARSE_FALLBACK", "No operational entities were available", view="conops"))

    spec = DiagramSpec(
        "conops", "Concept of Operations", direction="LR", nodes=nodes, edges=edges,
        lanes=lanes, callouts=callouts[:SUPPORTING_LIMIT], warnings=[*context.diagnostics, *warnings],
        provenance=DiagramProvenance(source="architecture-view-context", context={"curated": curation != ViewCuration()}),
        drilldowns=drilldowns,
    )
    spec.validate()
    return spec


def _capability_links(context: ArchitectureViewContext) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    behaviors: dict[str, list[str]] = defaultdict(list)
    components: dict[str, list[str]] = defaultdict(list)
    for behavior in context.entities("behavior"):
        capability = _find_local(context, behavior.model, getattr(behavior.value, "capability_id", ""))
        if capability:
            behaviors[capability.key].append(behavior.key)
            for step in getattr(behavior.value, "structured_steps", []) or []:
                component = _find_local(context, behavior.model, step.component_ref)
                if component and component.entity_type in {"component", "system"}:
                    components[capability.key].append(component.key)
    for capability in context.entities("capability"):
        for relationship in context.incoming(capability.key, "realizes"):
            source = context.entity(relationship.source, diagnose=False)
            if source and source.entity_type in {"component", "system"}:
                components[capability.key].append(source.key)
    for key in components:
        components[key] = sorted(set(components[key]))
    return behaviors, components


def _capability_root(context: ArchitectureViewContext, curation: ViewCuration) -> IndexedEntity | None:
    selector = curation.mission_root or curation.preferred_capability_root
    if selector and selector.resolved_id:
        candidate = context.entity(selector.resolved_id, diagnose=False)
        if candidate and candidate.entity_type == "capability":
            return candidate
    roots = [
        item for item in context.entities("capability")
        if not any(context.entity(parent, diagnose=False).entity_type == "capability" for parent in context.entity_parents(item.key))
    ]
    return roots[0] if roots else next(iter(context.entities("capability")), None)


def _capability_order(context: ArchitectureViewContext, root: IndexedEntity | None) -> list[IndexedEntity]:
    if root is None:
        return []
    result: list[IndexedEntity] = []
    frontier = [root.key]
    seen: set[str] = set()
    while frontier:
        key = frontier.pop(0)
        if key in seen:
            continue
        seen.add(key)
        entity = context.entity(key, diagnose=False)
        if entity and entity.entity_type == "capability":
            result.append(entity)
            frontier.extend(sorted(
                child for child in context.entity_children(key)
                if context.entity(child, diagnose=False).entity_type == "capability"
            ))
    return result


def project_functional_architecture(
    context: ArchitectureViewContext, curation: ViewCuration | None = None,
) -> DiagramSpec:
    """Project capability decomposition, functional flow, and allocation distinctly."""
    curation = curation or ViewCuration()
    warnings = _curation_diagnostics("functional", context, curation)
    root = _capability_root(context, curation)
    ordered = _capability_order(context, root)
    curated_order = {key: index for index, key in enumerate(curation.order)}
    if curated_order and ordered:
        ordered = [ordered[0], *sorted(
            ordered[1:], key=lambda item: (curated_order.get(item.key, len(curated_order)), item.key),
        )]
    selected = ordered[:FUNCTIONAL_BLOCK_LIMIT]
    if len(ordered) > len(selected):
        warnings.append(Diagnostic(
            "warning", "FUNCTIONAL_OVERVIEW_BOUNDED",
            f"{len(ordered) - len(selected)} functional blocks omitted (limit {FUNCTIONAL_BLOCK_LIMIT})", view="functional",
        ))
    behavior_links, component_links = _capability_links(context)
    selected_keys = {item.key for item in selected}
    nodes: list[DiagramNode] = []
    drilldowns: list[DiagramDrilldown] = []
    component_to_capabilities: dict[str, list[str]] = defaultdict(list)
    for capability in selected:
        for component in component_links[capability.key]:
            component_to_capabilities[component].append(capability.key)
        inputs: set[str] = set()
        outputs: set[str] = set()
        for behavior_key in behavior_links[capability.key]:
            behavior = context.entity(behavior_key, diagnose=False)
            for step in getattr(behavior.value, "structured_steps", []) or []:
                if step.input:
                    inputs.add(step.input)
                if step.output:
                    outputs.add(step.output)
        identifier = _node_id(capability.key)
        drilldown_id = f"drilldown:{capability.key}"
        nodes.append(DiagramNode(
            identifier, _label(capability, curation), "capability", entity_ref=capability.key,
            drilldown_ref=drilldown_id,
            badges=_badges(capability, behaviors=len(behavior_links[capability.key]), components=len(component_links[capability.key])),
            metrics={"inputs": ", ".join(sorted(inputs)), "outputs": ", ".join(sorted(outputs))},
            evidence=[_provenance(capability)],
        ))
        drilldowns.append(DiagramDrilldown(drilldown_id, identifier, spec_ref=f"functional:{capability.key}"))

    edges: list[DiagramEdge] = []
    for parent in selected:
        for relationship in context.outgoing(parent.key, "contains"):
            if relationship.target in selected_keys and context.entity(relationship.target, diagnose=False).entity_type == "capability":
                edges.append(_canonical_edge(_node_id(parent.key), _node_id(relationship.target), "decomposition", relationship))
                edges[-1].style = "dotted"

    allocation_nodes: set[str] = set()
    for capability in selected:
        for component_key in sorted(component_links[capability.key]):
            component = context.entity(component_key, diagnose=False)
            if not component:
                continue
            if component.key not in allocation_nodes:
                allocation_nodes.add(component.key)
                nodes.append(DiagramNode(
                    _node_id(component.key), component.name, component.entity_type,
                    entity_ref=component.key, evidence=[_provenance(component)],
                ))
            relationship = next((
                item for item in context.incoming(capability.key, "realizes") if item.source == component.key
            ), None)
            if relationship:
                edge = _canonical_edge(_node_id(capability.key), _node_id(component.key), "allocation", relationship)
            else:
                behavior_refs = [
                    behavior for behavior in behavior_links[capability.key]
                    if any(
                        f"{context.entity(behavior, diagnose=False).model}::{step.component_ref}" == component.key
                        for step in getattr(context.entity(behavior, diagnose=False).value, "structured_steps", []) or []
                    )
                ]
                evidence = DiagramProvenance(
                    source="behavior-step-allocation", entity_refs=[capability.key, component.key, *behavior_refs],
                )
                edge = DiagramEdge(_node_id(capability.key), _node_id(component.key), "allocation", evidence=[evidence])
            edges.append(edge)
            edges[-1].style = "dashed"

    flow_keys: set[tuple[str, str, str]] = set()
    for behavior in context.entities("behavior"):
        steps = sorted(getattr(behavior.value, "structured_steps", []) or [], key=lambda step: (step.order, step.action))
        for source_step, target_step in zip(steps, steps[1:]):
            sources = component_to_capabilities.get(f"{behavior.model}::{source_step.component_ref}", [])
            targets = component_to_capabilities.get(f"{behavior.model}::{target_step.component_ref}", [])
            for source in sources:
                for target in targets:
                    if source in selected_keys and target in selected_keys and source != target:
                        key = (source, target, "operational-flow")
                        if key not in flow_keys:
                            flow_keys.add(key)
                            evidence = DiagramProvenance(source="behavior-step-transition", entity_refs=[behavior.key, source, target])
                            edges.append(DiagramEdge(_node_id(source), _node_id(target), key[2], style="solid", evidence=[evidence]))
    for interface in context.entities("interface"):
        provider = _find_local(context, interface.model, getattr(interface.value, "provider", ""))
        consumer = _find_local(context, interface.model, getattr(interface.value, "consumer", ""))
        for source in component_to_capabilities.get(consumer.key if consumer else "", []):
            for target in component_to_capabilities.get(provider.key if provider else "", []):
                if source in selected_keys and target in selected_keys and source != target:
                    key = (source, target, "data-flow")
                    if key not in flow_keys:
                        flow_keys.add(key)
                        evidence = DiagramProvenance(source="interface-flow", entity_refs=[interface.key, source, target])
                        edges.append(DiagramEdge(_node_id(source), _node_id(target), key[2], style="solid", evidence=[evidence]))

    node_refs = {node.entity_ref for node in nodes}
    for flow in curation.flows:
        if flow.source not in selected_keys or flow.target not in selected_keys:
            continue
        evidence = _curated_provenance(flow.evidence)
        canonical = next((
            relationship for relationship in context.outgoing(flow.source, flow.kind)
            if relationship.target == flow.target
        ), None)
        if canonical:
            evidence = [_relationship_provenance(canonical)]
        if evidence:
            edges.append(DiagramEdge(
                _node_id(flow.source), _node_id(flow.target), flow.kind, flow.label,
                evidence=evidence, inferred=flow.inferred, style="solid",
            ))

    allocated_components = {key for values in component_links.values() for key in values}
    orphans = [item for item in context.entities("component") if item.key not in allocated_components]
    groups: list[DiagramGroup] = []
    if orphans:
        groups.append(DiagramGroup("functional:orphans", "Unallocated Functions", "warning", order=99))
        for component in orphans[:SUPPORTING_LIMIT]:
            if component.key not in node_refs:
                nodes.append(DiagramNode(
                    _node_id(component.key), component.name, "component", group="functional:orphans",
                    entity_ref=component.key, status="unallocated", evidence=[_provenance(component)],
                ))
    if not selected:
        nodes.append(DiagramNode("functional:empty", "Functional architecture unavailable", "warning"))
        warnings.append(Diagnostic("warning", "FUNCTIONAL_SPARSE_FALLBACK", "No capabilities were available", view="functional"))

    spec = DiagramSpec(
        "functional", "Functional Architecture", direction="TB", nodes=nodes, edges=edges,
        groups=groups, warnings=[*context.diagnostics, *warnings], drilldowns=drilldowns,
        provenance=DiagramProvenance(
            source="architecture-view-context",
            entity_refs=[root.key] if root else [],
            context={"curated": curation != ViewCuration(), "mission_root": root.key if root else ""},
        ),
    )
    spec.validate()
    return spec


__all__ = ["project_conops", "project_functional_architecture"]
