"""Deterministic, bounded systems-engineering view projections."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import re
from typing import Callable, Iterable

from architecture_model.core.diagram_spec import (
    Diagnostic,
    DiagramCallout,
    DiagramDrilldown,
    DiagramEdge,
    DiagramGroup,
    DiagramNode,
    DiagramProvenance,
    DiagramSpec,
    bound_diagram_spec,
)
from architecture_model.core.view_context import ArchitectureViewContext, IndexedEntity, IndexedRelationship
from architecture_model.core.view_curation import (
    CuratedUseCaseAnnotation,
    EvidenceRecord,
    ViewCuration,
    validate_view_curation,
)


DEFAULT_MAX_OVERVIEW_NODES = 15


def _visibility(curation: ViewCuration) -> Callable[[str | IndexedEntity], bool]:
    hidden = frozenset(
        item.resolved_id or item.qualified_id
        for item in curation.hide if item.resolved_id or item.qualified_id
    )

    def visible(value: str | IndexedEntity) -> bool:
        key = value.key if isinstance(value, IndexedEntity) else value
        return key not in hidden

    return visible


def _node_id(key: str) -> str:
    return f"node:{key}"


def _provenance(entity: IndexedEntity) -> DiagramProvenance:
    return DiagramProvenance("model-entity", [entity.key], [entity.source_path])


def _relationship_provenance(relationship: IndexedRelationship) -> DiagramProvenance:
    return DiagramProvenance(
        "model-relationship", [relationship.source, relationship.target],
        context={"type": relationship.kind, "model": relationship.model},
    )


def _derived(source: str, refs: Iterable[str], **context: str | int) -> DiagramProvenance:
    return DiagramProvenance(source, list(refs), context=context)


def _curated_provenance(evidence: Iterable[EvidenceRecord]) -> list[DiagramProvenance]:
    return [DiagramProvenance("curated-inference", source_files=[item.source], context={"claim": item.claim}) for item in evidence]


def _curated_flow_provenance(flow: object) -> list[DiagramProvenance]:
    return [
        DiagramProvenance(
            "curated-inference", source_files=[item.source],
            context={"claim": item.claim, "source": flow.source, "target": flow.target},
        )
        for item in flow.evidence
    ]


def _compact_edge_label(value: str, limit: int = 22) -> str:
    words = " ".join(value.split()).split()
    if len(" ".join(words)) <= limit:
        return " ".join(words)
    compact = " ".join(word for word in words if word.casefold() not in {"and", "the", "of"})
    return compact if len(compact) <= limit else compact[:limit - 1].rstrip() + "…"


def _find_local(context: ArchitectureViewContext, owner: str, reference: str) -> IndexedEntity | None:
    if not reference:
        return None
    key = reference if "::" in reference else f"{owner}::{reference}"
    direct = context.entity(key, diagnose=False)
    if direct:
        return direct
    matches = [item for item in context.entities(model=owner) if item.name == reference]
    return matches[0] if len(matches) == 1 else None


def _label(entity: IndexedEntity, curation: ViewCuration) -> str:
    return curation.labels.get(entity.key, entity.name)


def _badges(entity: IndexedEntity, *, behaviors: int = 0, components: int = 0) -> list[str]:
    values = entity.value
    result = []
    if behaviors:
        result.append(f"behaviors:{behaviors}")
    if components:
        result.append(f"components:{components}")
    result.extend([
        f"requirements:{len(getattr(values, 'requirements', []) or [])}",
        f"moes:{len(getattr(values, 'moes', []) or [])}",
        f"failures:{len(getattr(values, 'failure_modes', []) or [])}",
        f"monitoring:{len(getattr(values, 'monitored', []) or [])}",
    ])
    return result


def _curation_diagnostics(name: str, context: ArchitectureViewContext, curation: ViewCuration) -> list[Diagnostic]:
    return [
        Diagnostic(item.severity, f"{name.upper()}_CURATION_INVALID", item.message, view=name, source=item.source)
        for item in validate_view_curation(curation, context)
    ]


def _group_map(curation: ViewCuration, *, scenarios: bool = False) -> tuple[list[DiagramGroup], dict[str, str]]:
    curated = [*curation.groups, *(curation.scenarios if scenarios else []), *curation.tiers]
    groups = [DiagramGroup(item.id, item.label, item.kind, item.parent, item.order) for item in curated]
    membership = {member: item.id for item in curated for member in item.members}
    return groups, membership


def _drilldown_id(curation: ViewCuration, entity_key: str) -> str:
    return next((identifier for identifier, selector in sorted(curation.drilldowns.items()) if selector.resolved_id == entity_key), f"drilldown:{entity_key}")


def _system_badges(context: ArchitectureViewContext, entity: IndexedEntity) -> list[str]:
    children = context.child_models_for_system(entity.key)
    if not children:
        return []
    return [
        f"capabilities:{sum(len(context.entities('capability', model)) for model in children)}",
        f"behaviors:{sum(len(context.entities('behavior', model)) for model in children)}",
    ]


def _support_nodes(owner: IndexedEntity, kind: str, values: Iterable[str]) -> list[DiagramNode]:
    return [
        DiagramNode(
            f"detail:{owner.key}:{kind}:{index}", value, kind,
            evidence=[_derived(f"{owner.entity_type}-{kind}", [owner.key])],
        )
        for index, value in enumerate(values)
    ]


def _curated_support_nodes(
    owner: IndexedEntity, kind: str, values: Iterable[str], annotation: CuratedUseCaseAnnotation,
) -> list[DiagramNode]:
    evidence = _curated_provenance(annotation.evidence)
    return [
        DiagramNode(
            f"detail:{owner.key}:{kind}:curated:{index}", value, kind,
            status="inferred", inferred=True, badges=["inferred"], evidence=evidence,
        )
        for index, value in enumerate(values)
    ]


def _scenario_drilldown(context: ArchitectureViewContext, behavior: IndexedEntity, curation: ViewCuration) -> DiagramSpec:
    nodes = [DiagramNode(_node_id(behavior.key), _label(behavior, curation), "behavior", entity_ref=behavior.key, evidence=[_provenance(behavior)])]
    edges: list[DiagramEdge] = []
    present = {behavior.key}

    def add(entity: IndexedEntity, kind: str | None = None) -> None:
        if entity.key in present:
            return
        present.add(entity.key)
        nodes.append(DiagramNode(_node_id(entity.key), _label(entity, curation), kind or entity.entity_type, entity_ref=entity.key, evidence=[_provenance(entity)]))
        evidence = _derived("scenario-participant", [behavior.key, entity.key])
        edges.append(DiagramEdge(_node_id(behavior.key), _node_id(entity.key), "involves", evidence=[evidence]))

    for reference in getattr(behavior.value, "interface_refs", []) or []:
        interface = _find_local(context, behavior.model, reference)
        if interface:
            add(interface, "interface")
            for endpoint in (interface.value.provider, interface.value.consumer):
                participant = _find_local(context, interface.model, endpoint)
                if participant and participant.entity_type in {"system", "component"}:
                    add(participant)
    for relationship in context.incoming(behavior.key, "traces-to"):
        participant = context.entity(relationship.source, diagnose=False)
        if participant and participant.entity_type in {"system", "component"}:
            add(participant)
    for step in getattr(behavior.value, "structured_steps", []) or []:
        participant = _find_local(context, behavior.model, step.component_ref)
        if participant:
            add(participant)
    requirements = []
    for reference in getattr(behavior.value, "requirements", []) or []:
        entity = _find_local(context, behavior.model, reference)
        if entity and entity.entity_type == "requirement":
            add(entity)
        else:
            requirements.append(reference)
    if not requirements and not any(node.kind == "requirement" for node in nodes):
        requirements = ["No linked requirements"]
    nodes.extend(_support_nodes(behavior, "requirement", requirements))
    nodes.extend(_support_nodes(behavior, "moe", getattr(behavior.value, "moes", []) or ["No measures defined"]))
    nodes.extend(_support_nodes(behavior, "failure", getattr(behavior.value, "failure_modes", []) or ["No failure modes defined"]))
    nodes.extend(_support_nodes(behavior, "monitoring", getattr(behavior.value, "monitored", []) or []))
    return DiagramSpec(f"conops-detail:{behavior.key}", f"Scenario: {behavior.name}", nodes=nodes, edges=edges)


def _participant_drilldown(
    context: ArchitectureViewContext, node: DiagramNode, entity: IndexedEntity | None,
    evidence: list[DiagramProvenance], curation: ViewCuration,
) -> DiagramSpec:
    root = DiagramNode(
        f"detail:{node.id}", node.label, node.kind, entity_ref=entity.key if entity else "",
        inferred=node.inferred, evidence=[_provenance(entity)] if entity else evidence,
    )
    nodes = [root]
    edges: list[DiagramEdge] = []
    names: set[str] = set()
    if entity:
        names.update({entity.local_id, entity.name})
        nodes.extend(_support_nodes(entity, "goal", entity.value.goals))
    referenced = {ref for item in evidence for ref in item.entity_refs}
    behaviors = [
        item for item in context.entities("behavior")
        if item.key in referenced or item.value.actor_id in names or item.value.actor in names
        or any(step.actor in names for step in item.value.structured_steps)
    ]
    interfaces = [
        item for item in context.entities("interface")
        if item.key in referenced or item.value.provider in names or item.value.consumer in names
        or any(item.local_id in behavior.value.interface_refs for behavior in behaviors)
    ]
    systems = sorted({
        system.key: system for interface in interfaces
        if (system := _interface_system(context, interface))
    }.values(), key=lambda item: item.key)
    for item in [*behaviors, *interfaces, *systems]:
        detail_id = _node_id(item.key)
        nodes.append(DiagramNode(
            detail_id, _label(item, curation), "scenario" if item.entity_type == "behavior" else item.entity_type,
            entity_ref=item.key, evidence=[_provenance(item)],
        ))
        refs = [item.key] if entity is None else [entity.key, item.key]
        edges.append(DiagramEdge(root.id, detail_id, "participates", inferred=True,
                                 evidence=[_derived("participant-association", refs)]))
    return DiagramSpec(f"participant-detail:{node.id}", f"Participant: {node.label}", nodes=nodes, edges=edges)


def _external_evidence(context: ArchitectureViewContext) -> dict[str, tuple[str, list[DiagramProvenance]]]:
    evidence: dict[str, tuple[str, list[DiagramProvenance]]] = {}

    def add(name: str, provenance: DiagramProvenance) -> None:
        normalized = " ".join(name.split()).casefold()
        if not normalized or _find_local(context, provenance.entity_refs[0].split("::", 1)[0], name):
            return
        if normalized not in evidence:
            evidence[normalized] = (" ".join(name.split()), [])
        if provenance not in evidence[normalized][1]:
            evidence[normalized][1].append(provenance)

    for interface in context.entities("interface"):
        for role in ("provider", "consumer"):
            name = getattr(interface.value, role, "")
            if name and not _find_local(context, interface.model, name):
                add(name, _derived("interface-endpoint", [interface.key], role=role, protocol=interface.value.protocol))
    for behavior in context.entities("behavior"):
        for step in getattr(behavior.value, "structured_steps", []) or []:
            if step.actor and not _find_local(context, behavior.model, step.actor):
                add(step.actor, _derived("structured-step-participant", [behavior.key], action=step.action))
    for component in context.entities("component"):
        for dependency in component.value.external_dependencies:
            if not isinstance(dependency, dict):
                continue
            name = str(dependency.get("name") or dependency.get("target") or "").strip()
            if name:
                    add(name, _derived(
                        "component-external-dependency", [component.key],
                    protocol=str(dependency.get("protocol", "")), evidence_source=str(dependency.get("source", "")),
                ))
    return evidence


def _interface_system(context: ArchitectureViewContext, interface: IndexedEntity) -> IndexedEntity | None:
    for endpoint in (interface.value.provider, interface.value.consumer):
        entity = _find_local(context, interface.model, endpoint)
        if entity and entity.entity_type == "system":
            return entity
    for relationship in [*context.incoming(interface.key, "exposes"), *context.outgoing(interface.key, "exposes")]:
        other = relationship.source if relationship.target == interface.key else relationship.target
        entity = context.entity(other, diagnose=False)
        if entity and entity.entity_type == "system":
            return entity
    return None


def _owning_system(context: ArchitectureViewContext, model: str) -> IndexedEntity | None:
    for system in context.entities("system"):
        if model in context.child_models_for_system(system.key):
            return system
    return None


def _merge_specs(identifier: str, title: str, specs: Iterable[DiagramSpec]) -> DiagramSpec:
    nodes: dict[str, DiagramNode] = {}
    edges: dict[tuple[str, str, str, str], DiagramEdge] = {}
    warnings: list[Diagnostic] = []
    for spec in specs:
        nodes.update((node.id, node) for node in spec.nodes)
        for edge in spec.edges:
            key = (edge.source, edge.target, edge.kind, edge.label)
            if key not in edges:
                edges[key] = edge
            else:
                existing = edges[key]
                existing.count += edge.count
                existing.evidence = list(dict.fromkeys([*existing.evidence, *edge.evidence]))
        warnings.extend(spec.warnings)
    return DiagramSpec(identifier, title, nodes=list(nodes.values()), edges=list(edges.values()), warnings=warnings)


def _curated_scenario_spec(
    context: ArchitectureViewContext, scenario: object, curation: ViewCuration,
) -> DiagramSpec:
    members = [context.entity(key, diagnose=False) for key in scenario.members]
    members = [item for item in members if item]
    behaviors = [item for item in members if item.entity_type == "behavior"]
    systems = [item for item in members if item.entity_type == "system"]
    specs = [_scenario_drilldown(context, behavior, curation) for behavior in behaviors]
    merged = _merge_specs(f"conops-detail:{scenario.id}", f"Scenario: {scenario.label}", specs)
    if scenario.goal:
        merged.nodes.extend(_curated_support_nodes(
            behaviors[0] if behaviors else members[0], "goal", [scenario.goal], scenario,
        ))
    if scenario.moes:
        merged.nodes.extend(_curated_support_nodes(
            behaviors[0] if behaviors else members[0], "moe", scenario.moes, scenario,
        ))
    if scenario.requirements:
        merged.nodes.extend(_curated_support_nodes(
            behaviors[0] if behaviors else members[0], "requirement", scenario.requirements, scenario,
        ))
    present = {node.entity_ref for node in merged.nodes if node.entity_ref}
    for system in systems:
        if system.key not in present:
            merged.nodes.append(DiagramNode(
                _node_id(system.key), _label(system, curation), "system",
                entity_ref=system.key, evidence=[_provenance(system)],
            ))
    merged.provenance = _derived("curated-scenario", [item.key for item in members], scenario=scenario.id)
    merged.validate()
    return merged


def _project_curated_conops(
    context: ArchitectureViewContext, curation: ViewCuration, limit: int,
) -> DiagramSpec:
    warnings = _curation_diagnostics("conops", context, curation)
    featured = {item.resolved_id for item in curation.featured if item.resolved_id}
    order = {key: index for index, key in enumerate(curation.order)}
    scenarios = sorted(curation.scenarios, key=lambda item: (
        not any(member in featured for member in item.members),
        min((order.get(member, len(order)) for member in item.members), default=len(order)),
        item.order, item.id,
    ))
    flow_external_ids = {endpoint for flow in curation.flows for endpoint in (flow.source, flow.target)}
    externals = [item for item in curation.externals if item.id in flow_external_ids]
    flows_by_external = {
        item.id: sorted(
            (flow.target, flow.kind) for flow in curation.flows if flow.source == item.id
        )
        for item in externals
    }
    external_groups: dict[tuple[str, tuple[tuple[str, str], ...]], list[object]] = defaultdict(list)
    for external in externals:
        role = external.kind or f"unknown:{external.id}"
        external_groups[(role, tuple(flows_by_external[external.id]))].append(external)
    bundled_externals = sorted(external_groups.values(), key=lambda items: (
        tuple(flows_by_external[items[0].id]),
        all("ai" in item.kind.casefold() or "ai" in item.name.casefold() for item in items),
        items[0].id,
    ))
    scenario_count = min(len(scenarios), limit)
    support_budget = max(0, limit - scenario_count)
    scenario_systems: dict[str, list[IndexedEntity]] = {}
    for scenario in scenarios[:scenario_count]:
        owned: dict[str, IndexedEntity] = {}
        for key in scenario.members:
            item = context.entity(key, diagnose=False)
            if item and item.entity_type == "system":
                owned[item.key] = item
            elif item and item.entity_type == "behavior":
                owned.update((system.key, system) for system in _behavior_systems(context, item, lambda _: True))
                for interface in _behavior_interfaces(context, item, lambda _: True):
                    system = _interface_system(context, interface)
                    if system:
                        owned[system.key] = system
        scenario_systems[scenario.id] = sorted(owned.values(), key=lambda item: item.key)
    member_systems = sorted({
        item.key: item for values in scenario_systems.values() for item in values
    }.values(), key=lambda item: item.key)
    boundary_systems = member_systems
    member_behaviors = [
        item for scenario in scenarios[:scenario_count] for key in scenario.members
        if (item := context.entity(key, diagnose=False)) and item.entity_type == "behavior"
    ]
    scenario_outcomes: dict[str, list[tuple[str, bool, list[DiagramProvenance]]]] = {}
    for scenario in scenarios[:scenario_count]:
        behaviors = [
            item for key in scenario.members
            if (item := context.entity(key, diagnose=False)) and item.entity_type == "behavior"
        ]
        canonical = sorted({value for item in behaviors for value in item.value.postconditions if value})
        scenario_outcomes[scenario.id] = [
            (value, True, _curated_provenance(scenario.evidence)) for value in scenario.outcomes
        ]
        scenario_outcomes[scenario.id].extend(
            (value, False, [_derived("behavior-outcome", [item.key for item in behaviors], scenario=scenario.id)])
            for value in canonical if value not in scenario.outcomes
        )
        if not scenario_outcomes[scenario.id]:
            scenario_outcomes[scenario.id] = [
                (flow.label, True, _curated_flow_provenance(flow))
                for flow in curation.flows
                if flow.source == scenario.id and flow.label and flow.inferred and flow.evidence
            ]
    outcome_values = [value for values in scenario_outcomes.values() for value in values]
    reserve_system = bool(member_systems) and support_budget > 0
    reserve_outcome = bool(outcome_values) and support_budget > int(reserve_system)
    external_budget = max(0, support_budget - int(reserve_system) - int(reserve_outcome))
    selected_external_groups = bundled_externals[:external_budget]
    nodes: list[DiagramNode] = []
    drilldowns: list[DiagramDrilldown] = []
    endpoint_ids: dict[str, str] = {}
    for scenario in scenarios[:scenario_count]:
        endpoint_ids.update({member: scenario.id for member in scenario.members})
        members = [context.entity(key, diagnose=False) for key in scenario.members]
        members = [item for item in members if item]
        behaviors = [item for item in members if item.entity_type == "behavior"]
        systems = scenario_systems[scenario.id]
        interfaces = sorted({ref for item in behaviors for ref in item.value.interface_refs})
        requirements = sorted({ref for item in behaviors for ref in item.value.requirements})
        evidence = [_provenance(item) for item in members]
        drilldown_id = f"drilldown:{scenario.id}"
        canonical_goal = next((goal for item in behaviors for goal in item.value.goals if goal), "")
        inferred_goal = not canonical_goal and bool(scenario.goal)
        nodes.append(DiagramNode(
            scenario.id, scenario.label, "scenario", lane="scenarios", drilldown_ref=drilldown_id,
            subtitle=canonical_goal or scenario.goal,
            badges=[f"behaviors:{len(behaviors)}", f"systems:{len(systems)}", f"interfaces:{len(interfaces)}", f"requirements:{len(requirements)}"],
            inferred=inferred_goal, status="inferred" if inferred_goal else "",
            evidence=[*evidence, *(_curated_provenance(scenario.evidence) if inferred_goal else [])],
        ))
        endpoint_ids[scenario.id] = scenario.id
        drilldowns.append(DiagramDrilldown(
            drilldown_id, scenario.id, spec=_curated_scenario_spec(context, scenario, curation),
        ))
    for group in selected_external_groups:
        aggregate = len(group) > 1
        external_id = "conops:external:" + hashlib.sha256(
            "\0".join(item.id for item in group).encode()
        ).hexdigest()[:10] if aggregate else group[0].id
        label = (
            "Knowledge Sources" if aggregate and all(item.kind == "source-system" for item in group)
            else "AI Services" if aggregate and all(item.kind == "ai-service" for item in group)
            else f"External Sources ({len(group)})" if aggregate else group[0].name
        )
        evidence = [value for external in group for value in _curated_provenance(external.evidence)]
        drilldown_id = f"drilldown:{external_id}"
        node = DiagramNode(external_id, label, "external", lane="actors", status="summary" if aggregate else "inferred",
                           inferred=True, drilldown_ref=drilldown_id, badges=[f"externals:{len(group)}"], evidence=evidence)
        nodes.append(node)
        for external in group:
            endpoint_ids[external.id] = external_id
        drilldowns.append(DiagramDrilldown(
            drilldown_id, external_id,
            spec=DiagramSpec(
                f"conops-external:{external_id}", label,
                nodes=[DiagramNode(item.id, item.name, "external", inferred=True, evidence=_curated_provenance(item.evidence)) for item in group],
            ),
        ))
    if reserve_system:
        system_id = "conops:system-boundary"
        drilldown_id = f"drilldown:{system_id}"
        nodes.append(DiagramNode(
            system_id, "Operational System Boundary", "system", lane="boundary", status="summary",
            drilldown_ref=drilldown_id, badges=[f"systems:{len(boundary_systems)}"],
            evidence=[_provenance(item) for item in boundary_systems],
        ))
        drilldowns.append(DiagramDrilldown(
            drilldown_id, system_id,
            spec=_entity_list_spec("conops-system-boundary", "Operational System Boundary", boundary_systems),
        ))
    callouts: list[DiagramCallout] = []
    if reserve_outcome:
        outcome_id = "conops:outcomes"
        outcome_evidence = [evidence for values in scenario_outcomes.values() for _, _, items in values for evidence in items]
        outcome_detail = DiagramSpec(
            "conops-outcomes", "Operational Outcomes",
            nodes=[
                DiagramNode(
                    f"outcome:{scenario_id}:{index}", value, "outcome", subtitle=scenario_id,
                    inferred=inferred, status="inferred" if inferred else "canonical", evidence=evidence,
                )
                for scenario_id, values in sorted(scenario_outcomes.items())
                for index, (value, inferred, evidence) in enumerate(values)
            ],
        )
        drilldown_id = f"drilldown:{outcome_id}"
        nodes.append(DiagramNode(
            outcome_id, "Operational Outcomes", "outcome", lane="outcomes", status="summary",
            inferred=any(inferred for values in scenario_outcomes.values() for _, inferred, _ in values),
            drilldown_ref=drilldown_id,
            badges=[f"outcomes:{len(outcome_values)}", f"scenarios:{sum(bool(values) for values in scenario_outcomes.values())}"],
            evidence=outcome_evidence,
        ))
        drilldowns.append(DiagramDrilldown(drilldown_id, outcome_id, spec=outcome_detail))
    elif not outcome_values and nodes:
        callouts.append(DiagramCallout(
            "conops:outcomes-unspecified", "Operational outcomes not specified", nodes[0].id,
            "diagnostic", [item.key for item in member_behaviors],
        ))
    flow_values: dict[tuple[str, str, str, str], DiagramEdge] = {}
    canonical_nodes = {node.entity_ref: node.id for node in nodes if node.entity_ref}
    for flow in curation.flows:
        source = endpoint_ids.get(flow.source, canonical_nodes.get(flow.source, flow.source if flow.source in {node.id for node in nodes} else ""))
        target = endpoint_ids.get(flow.target, canonical_nodes.get(flow.target, flow.target if flow.target in {node.id for node in nodes} else ""))
        if not source or not target or source == target:
            continue
        display_label = _compact_edge_label(flow.label)
        key = (source, target, flow.kind, display_label)
        evidence = _curated_flow_provenance(flow)
        if key not in flow_values:
            flow_values[key] = DiagramEdge(source, target, flow.kind, display_label, inferred=flow.inferred, evidence=[], title=flow.label)
        edge = flow_values[key]
        edge.count += 1 if edge.evidence else 0
        edge.evidence.extend(item for item in evidence if item not in edge.evidence)
    if reserve_system:
        for scenario in scenarios[:scenario_count]:
            systems = scenario_systems[scenario.id]
            if systems:
                flow_values[(scenario.id, system_id, "allocation", "")] = DiagramEdge(
                    scenario.id, system_id, "allocation",
                    evidence=[_derived("curated-scenario-system-membership", [item.key for item in systems], scenario=scenario.id)],
                    title="Scenario delivered by participating system boundary",
                )
    if reserve_outcome:
        for scenario in scenarios[:scenario_count]:
            values = scenario_outcomes[scenario.id]
            if values:
                flow_values[(scenario.id, outcome_id, "operational-flow", "outcomes")] = DiagramEdge(
                    scenario.id, outcome_id, "operational-flow", "outcomes",
                    inferred=any(inferred for _, inferred, _ in values),
                    evidence=[item for _, _, evidence in values for item in evidence],
                    title="Scenario operational outcomes",
                )
    spec = DiagramSpec(
        "conops", "Concept of Operations", layout="operational-lanes", nodes=nodes, edges=list(flow_values.values()),
        lanes=[
            DiagramGroup("actors", "Actors and Externals", "lane", order=0),
            DiagramGroup("scenarios", "Operational Scenarios", "lane", order=1),
            DiagramGroup("boundary", "System Boundary", "lane", order=2),
            DiagramGroup("outcomes", "Operational Outcomes", "lane", order=3),
        ], callouts=callouts, warnings=warnings, drilldowns=drilldowns,
        provenance=DiagramProvenance("curated-conops", context={"max_overview_nodes": limit}),
    )
    spec.validate()
    return spec


def project_conops(
    context: ArchitectureViewContext, curation: ViewCuration | None = None,
    *, max_overview_nodes: int = DEFAULT_MAX_OVERVIEW_NODES,
) -> DiagramSpec:
    """Project complete operational paths under one global node budget."""
    curation = curation or ViewCuration()
    limit = max(1, max_overview_nodes)
    if curation.scenarios:
        return bound_diagram_spec(_project_curated_conops(context, curation, limit))
    warnings = _curation_diagnostics("conops", context, curation)
    hidden = {item.resolved_id for item in curation.hide if item.resolved_id}
    featured = {item.resolved_id for item in curation.featured if item.resolved_id}
    order = {key: index for index, key in enumerate(curation.order)}
    groups, membership = _group_map(curation, scenarios=True)
    lanes = [
        DiagramGroup("actors", "Actors and Externals", "lane", order=0),
        DiagramGroup("scenarios", "Operational Scenarios", "lane", order=1),
        DiagramGroup("boundary", "Interfaces and System Boundary", "lane", order=2),
        DiagramGroup("outcomes", "Operational Outcomes", "lane", order=3),
    ]
    nodes: dict[str, DiagramNode] = {}
    edges: dict[tuple[str, str, str], DiagramEdge] = {}
    drilldowns: list[DiagramDrilldown] = []

    def include(node: DiagramNode) -> bool:
        if node.id in nodes:
            return True
        if len(nodes) >= limit:
            return False
        nodes[node.id] = node
        return True

    actors = [item for item in context.entities("actor") if item.key not in hidden]
    formal_externals = [item for item in context.entities("external_system") if item.key not in hidden]
    inferred = _external_evidence(context)
    degraded_interfaces: set[str] = set()
    for interface in context.entities("interface"):
        if interface.key in hidden or _interface_system(context, interface):
            continue
        unresolved = [
            value for value in (interface.value.provider, interface.value.consumer)
            if value and not _find_local(context, interface.model, value)
        ]
        if not unresolved or len(nodes) + 2 > limit:
            continue
        interface_node = DiagramNode(
            _node_id(interface.key), _label(interface, curation), "interface", lane="boundary",
            status="degraded", entity_ref=interface.key, evidence=[_provenance(interface)],
        )
        boundary_id = f"unknown-boundary:{interface.key}"
        boundary_evidence = [
            _derived("unresolved-interface-endpoint", [interface.key], endpoint=value, protocol=interface.value.protocol)
            for value in unresolved
        ]
        boundary_node = DiagramNode(
            boundary_id, unresolved[0], "unknown-boundary", lane="boundary", status="degraded",
            inferred=True, evidence=boundary_evidence,
        )
        include(interface_node)
        include(boundary_node)
        edges[(interface_node.id, boundary_node.id, "connects")] = DiagramEdge(
            interface_node.id, boundary_node.id, "connects", inferred=True, evidence=boundary_evidence,
        )
        degraded_interfaces.add(interface.key)
        warnings.append(Diagnostic(
            "warning", "CONOPS_DEGRADED_INTERFACE", f"Unresolved interface endpoint: {interface.name}", view="conops",
        ))

    behaviors = [item for item in context.entities("behavior") if item.key not in hidden]
    behaviors.sort(key=lambda item: (item.key not in featured, order.get(item.key, len(order)), item.key))
    omitted = 0
    for behavior in behaviors:
        actor = _find_local(context, behavior.model, behavior.value.actor_id or behavior.value.actor)
        interfaces = [
            value for ref in behavior.value.interface_refs
            if (value := _find_local(context, behavior.model, ref)) and value.entity_type == "interface"
        ]
        if not interfaces:
            interfaces = [
                item for item in context.entities("interface", behavior.model)
                if actor and actor.key in {rel.source for rel in context.incoming(item.key) + context.outgoing(item.key)}
            ]
        interface = interfaces[0] if interfaces else None
        system = _interface_system(context, interface) if interface else _owning_system(context, behavior.model)
        outcome = next(iter(behavior.value.postconditions or behavior.value.goals), "")
        path_nodes = []
        if actor:
            path_nodes.append(DiagramNode(_node_id(actor.key), _label(actor, curation), "actor", lane="actors", entity_ref=actor.key, evidence=[_provenance(actor)]))
        drilldown_id = _drilldown_id(curation, behavior.key)
        path_nodes.append(
            DiagramNode(_node_id(behavior.key), _label(behavior, curation), "scenario", lane="scenarios", group=membership.get(behavior.key, ""),
                        subtitle=" | ".join(value for value in (behavior.value.trigger, next(iter(behavior.value.goals), "")) if value),
                        entity_ref=behavior.key, drilldown_ref=drilldown_id, badges=_badges(behavior), evidence=[_provenance(behavior)])
        )
        if interface and system:
            path_nodes.append(DiagramNode(_node_id(interface.key), _label(interface, curation), "interface", lane="boundary", entity_ref=interface.key, evidence=[_provenance(interface)]))
        if system:
            path_nodes.append(DiagramNode(_node_id(system.key), _label(system, curation), "system", lane="boundary", entity_ref=system.key,
                                          badges=_system_badges(context, system), evidence=[_provenance(system)]))
        if outcome:
            path_nodes.append(DiagramNode(f"outcome:{behavior.key}", outcome, "outcome", lane="outcomes", evidence=[_derived("behavior-outcome", [behavior.key])]))
        needed = sum(node.id not in nodes for node in path_nodes)
        if len(nodes) + needed > limit:
            omitted += 1
            continue
        for node in path_nodes:
            include(node)
        scenario_id = _node_id(behavior.key)
        drilldowns.append(DiagramDrilldown(drilldown_id, scenario_id, spec=_scenario_drilldown(context, behavior, curation)))
        if actor and _node_id(actor.key) in nodes:
            evidence = _derived("behavior-actor", [behavior.key, actor.key])
            edges[(_node_id(actor.key), scenario_id, "initiates")] = DiagramEdge(_node_id(actor.key), scenario_id, "initiates", evidence=[evidence])
        if interface and system:
            evidence = _derived("behavior-interface", [behavior.key, interface.key])
            edges[(scenario_id, _node_id(interface.key), "uses")] = DiagramEdge(scenario_id, _node_id(interface.key), "uses", evidence=[evidence])
            relationship = next((item for item in context.incoming(interface.key, "exposes") if item.source == system.key), None)
            provenance = _relationship_provenance(relationship) if relationship else _derived("interface-endpoint", [interface.key, system.key])
            edges[(_node_id(interface.key), _node_id(system.key), "connects")] = DiagramEdge(_node_id(interface.key), _node_id(system.key), "connects", evidence=[provenance])
        if outcome:
            evidence = _derived("behavior-outcome", [behavior.key])
            edges[(scenario_id, f"outcome:{behavior.key}", "produces")] = DiagramEdge(scenario_id, f"outcome:{behavior.key}", "produces", evidence=[evidence])
    for actor in actors:
        include(DiagramNode(_node_id(actor.key), _label(actor, curation), "actor", lane="actors", entity_ref=actor.key, evidence=[_provenance(actor)]))
    for external in formal_externals:
        include(DiagramNode(_node_id(external.key), _label(external, curation), "external", lane="actors", entity_ref=external.key, evidence=[_provenance(external)]))
    curated_names: set[str] = set()
    for external in curation.externals:
        curated_names.add(external.name.casefold())
        include(DiagramNode(external.id, external.name, "external", lane="actors", status="inferred", inferred=True,
                            evidence=_curated_provenance(external.evidence)))
    for normalized, (name, evidence) in sorted(inferred.items()):
        if normalized not in curated_names and not any(
            ref in degraded_interfaces for item in evidence for ref in item.entity_refs
        ):
            include(DiagramNode(f"external:{normalized}", name, "external", lane="actors", status="inferred", inferred=True, evidence=evidence))
    node_by_ref = {node.entity_ref: node.id for node in nodes.values() if node.entity_ref}
    for relationship in context.relationships():
        if relationship.source in node_by_ref and relationship.target in node_by_ref:
            source = context.entity(relationship.source, diagnose=False)
            target = context.entity(relationship.target, diagnose=False)
            if source and target and "interface" in {source.entity_type, target.entity_type}:
                key = (node_by_ref[relationship.source], node_by_ref[relationship.target], relationship.kind)
                edges[key] = DiagramEdge(*key, evidence=[_relationship_provenance(relationship)])
    for node in list(nodes.values()):
        if node.kind not in {"actor", "external", "unknown-boundary"}:
            continue
        entity = context.entity(node.entity_ref, diagnose=False) if node.entity_ref else None
        drilldown_id = f"drilldown:{node.id}"
        node.drilldown_ref = drilldown_id
        drilldowns.append(DiagramDrilldown(
            drilldown_id, node.id, spec=_participant_drilldown(context, node, entity, node.evidence, curation),
        ))
    callout_values: dict[tuple[str, str], tuple[str, set[str]]] = {}

    def add_callout(label: str, target: str, source: str) -> None:
        normalized = " ".join(label.split()).casefold()
        key = (target, normalized)
        if key not in callout_values:
            callout_values[key] = (" ".join(label.split()), set())
        callout_values[key][1].add(source)

    for behavior in behaviors:
        target = _node_id(behavior.key)
        if target not in nodes:
            continue
        failures = [
            *behavior.value.failure_modes,
            *[step.error_handling for step in behavior.value.structured_steps if step.error_handling],
        ]
        for failure in failures:
            add_callout(failure, target, behavior.key)
    for system in context.entities("system"):
        target = _node_id(system.key)
        if target in nodes:
            for failure in system.value.failure_modes:
                add_callout(failure, target, system.key)
    for capability in context.entities("capability"):
        for behavior in behaviors:
            target = _node_id(behavior.key)
            if behavior.value.capability_id == capability.local_id and target in nodes:
                for failure in capability.value.failure_modes:
                    add_callout(failure, target, capability.key)
    callouts = []
    for (target, normalized), (label, evidence) in sorted(callout_values.items()):
        digest = hashlib.sha256(f"{target}\0{normalized}".encode()).hexdigest()[:12]
        callouts.append(DiagramCallout(f"failure:{digest}", label, target, "failure", sorted(evidence)))
    if omitted:
        warnings.append(Diagnostic("warning", "CONOPS_OVERVIEW_BOUNDED", f"{omitted} operational paths omitted (limit {limit})", view="conops"))
    if not nodes:
        include(DiagramNode("conops:empty", "Operational context unavailable", "warning", lane="scenarios"))
        warnings.append(Diagnostic("warning", "CONOPS_SPARSE_FALLBACK", "No operational entities were available", view="conops"))
    spec = DiagramSpec(
        "conops", "Concept of Operations", layout="operational-lanes", nodes=list(nodes.values()), edges=list(edges.values()), groups=groups,
        lanes=lanes, callouts=callouts[:6],
        warnings=[*context.diagnostics, *warnings], drilldowns=drilldowns,
        provenance=DiagramProvenance("architecture-view-context", context={"curated": curation != ViewCuration(), "max_overview_nodes": limit}),
    )
    spec.validate()
    return bound_diagram_spec(spec)


def _capability_roots(context: ArchitectureViewContext) -> list[IndexedEntity]:
    return [
        item for item in context.entities("capability")
        if not any(
            (parent := context.entity(key, diagnose=False)) and parent.entity_type == "capability"
            for key in context.entity_parents(item.key)
        )
    ]


def _capability_subtree(context: ArchitectureViewContext, root: str) -> list[IndexedEntity]:
    result: list[IndexedEntity] = []
    frontier = [root]
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
                if (value := context.entity(child, diagnose=False)) and value.entity_type == "capability"
            ))
    return result


def _capability_links(context: ArchitectureViewContext) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    behaviors: dict[str, list[str]] = defaultdict(list)
    components: dict[str, list[str]] = defaultdict(list)
    for behavior in context.entities("behavior"):
        capability = _find_local(context, behavior.model, behavior.value.capability_id)
        if capability and capability.entity_type == "capability":
            behaviors[capability.key].append(behavior.key)
            for step in behavior.value.structured_steps:
                component = _find_local(context, behavior.model, step.component_ref)
                if component and component.entity_type in {"component", "system"}:
                    components[capability.key].append(component.key)
    for capability in context.entities("capability"):
        components[capability.key] = sorted(set(components[capability.key]) | {
            relationship.source for relationship in context.incoming(capability.key, "realizes")
            if (source := context.entity(relationship.source, diagnose=False)) and source.entity_type in {"component", "system"}
        })
    return behaviors, components


def _tokens(value: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9]+", value.casefold()) if len(word) > 2}


def _step_capability(
    context: ArchitectureViewContext, behavior: IndexedEntity, component_ref: str, action: str,
) -> str | None:
    component = _find_local(context, behavior.model, component_ref)
    candidates = [] if not component else [
        context.entity(item.target, diagnose=False) for item in context.outgoing(component.key, "realizes")
        if context.entity(item.target, diagnose=False).entity_type == "capability"
    ]
    if len(candidates) == 1:
        return candidates[0].key
    action_words = _tokens(action)
    scores = [
        (len(action_words & _tokens(" ".join([candidate.name, candidate.intent, *candidate.goals]))), candidate.key)
        for candidate in candidates
    ]
    scores.sort(key=lambda item: (-item[0], item[1]))
    if scores and scores[0][0] and (len(scores) == 1 or scores[0][0] > scores[1][0]):
        return scores[0][1]
    capability = _find_local(context, behavior.model, behavior.value.capability_id)
    return capability.key if capability and not candidates else None


def _functional_drilldown(
    context: ArchitectureViewContext, capability: IndexedEntity, curation: ViewCuration,
    behavior_links: dict[str, list[str]], component_links: dict[str, list[str]],
) -> DiagramSpec:
    subtree = _capability_subtree(context, capability.key)
    nodes = []
    for item in subtree:
        inputs, outputs = set(), set()
        for behavior_key in behavior_links[item.key]:
            behavior = context.entity(behavior_key, diagnose=False)
            for step in behavior.value.structured_steps:
                if step.input:
                    inputs.add(step.input)
                if step.output:
                    outputs.add(step.output)
        nodes.append(DiagramNode(
            _node_id(item.key), _label(item, curation), "capability", entity_ref=item.key,
            badges=_badges(item, behaviors=len(behavior_links[item.key]), components=len(component_links[item.key])),
            metrics={"inputs": ", ".join(sorted(inputs)), "outputs": ", ".join(sorted(outputs))}, evidence=[_provenance(item)],
        ))
    edges: list[DiagramEdge] = []
    present = {item.key for item in subtree}
    for parent in subtree:
        for relationship in context.outgoing(parent.key, "contains"):
            if relationship.target in present:
                edges.append(DiagramEdge(_node_id(parent.key), _node_id(relationship.target), "decomposition", style="dotted", evidence=[_relationship_provenance(relationship)]))
    subtree_keys = {item.key for item in subtree}
    detail_flows: dict[tuple[str, str], DiagramEdge] = {}
    for behavior in context.entities("behavior"):
        steps = sorted(behavior.value.structured_steps, key=lambda step: (step.order, step.action))
        mapped = [(step, _step_capability(context, behavior, step.component_ref, step.action)) for step in steps]
        for (source_step, source), (target_step, target) in zip(mapped, mapped[1:]):
            if not source or not target or source == target or source not in subtree_keys or target not in subtree_keys:
                continue
            key = (source, target)
            evidence = _derived("behavior-step-transition", [behavior.key, source, target], source_step=source_step.order, target_step=target_step.order)
            if key not in detail_flows:
                detail_flows[key] = DiagramEdge(_node_id(source), _node_id(target), "operational-flow", style="solid", evidence=[])
            detail_flows[key].count += 1 if detail_flows[key].evidence else 0
            detail_flows[key].evidence.append(evidence)
    edges.extend(detail_flows.values())
    relevant = set(subtree_keys)
    relevant.update(key for item in subtree for key in behavior_links[item.key])
    relevant.update(key for item in subtree for key in component_links[item.key])
    for behavior_key in list(relevant):
        behavior = context.entity(behavior_key, diagnose=False)
        if not behavior or behavior.entity_type != "behavior":
            continue
        actor = _find_local(context, behavior.model, behavior.value.actor_id or behavior.value.actor)
        if actor:
            relevant.add(actor.key)
        for reference in behavior.value.interface_refs:
            interface = _find_local(context, behavior.model, reference)
            if interface:
                relevant.add(interface.key)
    for interface in context.entities("interface"):
        provider = _find_local(context, interface.model, interface.value.provider)
        consumer = _find_local(context, interface.model, interface.value.consumer)
        if interface.key in relevant or any(item and item.key in relevant for item in (provider, consumer)):
            relevant.add(interface.key)
            if provider:
                relevant.add(provider.key)
            if consumer:
                relevant.add(consumer.key)
    for item in subtree:
        for reference in item.value.requirements:
            requirement = _find_local(context, item.model, reference)
            if requirement:
                relevant.add(requirement.key)
    present = {node.entity_ref for node in nodes if node.entity_ref}
    for key in sorted(relevant - present):
        entity = context.entity(key, diagnose=False)
        if entity:
            nodes.append(DiagramNode(_node_id(key), entity.name, entity.entity_type, entity_ref=key, evidence=[_provenance(entity)]))
    present = {node.entity_ref for node in nodes if node.entity_ref}
    canonical_keys: set[tuple[str, str, str]] = set()
    for relationship in context.relationships():
        if relationship.source in present and relationship.target in present:
            key = (relationship.source, relationship.target, relationship.kind)
            canonical_keys.add(key)
            edges.append(DiagramEdge(_node_id(relationship.source), _node_id(relationship.target), relationship.kind,
                                     evidence=[_relationship_provenance(relationship)]))
    for behavior_key in sorted(key for key in present if context.entity(key, diagnose=False).entity_type == "behavior"):
        behavior = context.entity(behavior_key, diagnose=False)
        actor = _find_local(context, behavior.model, behavior.value.actor_id or behavior.value.actor)
        if actor and actor.key in present and (actor.key, behavior.key, "participates") not in canonical_keys:
            edges.append(DiagramEdge(_node_id(actor.key), _node_id(behavior.key), "participates", inferred=True,
                                     evidence=[_derived("behavior-actor", [actor.key, behavior.key])]))
    owner_refs = [item.key for item in subtree]
    requirements = sorted({value for item in subtree for value in item.value.requirements if not _find_local(context, item.model, value)})
    moes = sorted({value for item in subtree for value in item.value.moes})
    failures = sorted({value for item in subtree for value in item.value.failure_modes})
    nodes.extend(_support_nodes(capability, "requirement", requirements))
    nodes.extend(_support_nodes(capability, "moe", moes))
    nodes.extend(_support_nodes(capability, "failure", failures))
    nodes.extend(_support_nodes(capability, "monitoring", sorted({value for item in subtree for value in item.value.monitored})))
    return DiagramSpec(f"functional-detail:{capability.key}", f"Function: {capability.name}", direction="TB", nodes=nodes, edges=edges,
                       provenance=DiagramProvenance("capability-subtree", owner_refs))


def _entity_list_spec(identifier: str, title: str, entities: Iterable[IndexedEntity]) -> DiagramSpec:
    return DiagramSpec(identifier, title, nodes=[
        DiagramNode(_node_id(item.key), item.name, item.entity_type, entity_ref=item.key, evidence=[_provenance(item)])
        for item in sorted(entities, key=lambda value: value.key)
    ])


def _project_curated_functional(
    context: ArchitectureViewContext, curation: ViewCuration, limit: int,
) -> DiagramSpec:
    warnings = _curation_diagnostics("functional", context, curation)
    featured = {item.resolved_id for item in curation.featured if item.resolved_id}
    groups = sorted(curation.groups, key=lambda item: (item.order, item.id))
    member_to_group: dict[str, str] = {}
    for group in groups:
        for member in group.members:
            member_to_group.setdefault(member, group.id)
    outside_featured = sorted(featured - set(member_to_group))
    reserve_warning = bool(outside_featured) and limit > 0
    selected_groups = groups[:max(0, limit - int(reserve_warning))]
    behavior_links, component_links = _capability_links(context)
    nodes: list[DiagramNode] = []
    drilldowns: list[DiagramDrilldown] = []
    selected_ids = {group.id for group in selected_groups}
    for group in selected_groups:
        capabilities = [context.entity(key, diagnose=False) for key in group.members]
        capabilities = [item for item in capabilities if item and item.entity_type == "capability"]
        behavior_count = sum(len(behavior_links[item.key]) for item in capabilities)
        component_count = len({key for item in capabilities for key in component_links[item.key]})
        requirements = len({value for item in capabilities for value in item.value.requirements})
        moes = len({value for item in capabilities for value in item.value.moes})
        failures = len({value for item in capabilities for value in item.value.failure_modes})
        evidence = [_provenance(item) for item in capabilities]
        drilldown_id = f"drilldown:{group.id}"
        nodes.append(DiagramNode(
            group.id, group.label, "functional-block", drilldown_ref=drilldown_id,
            badges=[
                f"capabilities:{len(capabilities)}", f"behaviors:{behavior_count}",
                f"components:{component_count}", f"requirements:{requirements}",
                f"moes:{moes}", f"failures:{failures}",
            ], evidence=evidence,
        ))
        details = [
            _functional_drilldown(context, capability, curation, behavior_links, component_links)
            for capability in capabilities
        ]
        detail = _merge_specs(f"functional-detail:{group.id}", f"Function: {group.label}", details)
        detail.provenance = _derived("curated-functional-group", [item.key for item in capabilities], group=group.id)
        drilldowns.append(DiagramDrilldown(drilldown_id, group.id, spec=detail))
    flows: dict[tuple[str, str, str, str], DiagramEdge] = {}
    for flow in curation.flows:
        source = member_to_group.get(flow.source, flow.source)
        target = member_to_group.get(flow.target, flow.target)
        if source not in selected_ids or target not in selected_ids or source == target:
            continue
        display_label = _compact_edge_label(flow.label)
        key = (source, target, flow.kind, display_label)
        evidence = _curated_flow_provenance(flow)
        if key not in flows:
            flows[key] = DiagramEdge(source, target, flow.kind, display_label, inferred=flow.inferred, evidence=[], title=flow.label)
        edge = flows[key]
        edge.count += 1 if edge.evidence else 0
        edge.evidence.extend(item for item in evidence if item not in edge.evidence)
    if outside_featured and len(nodes) < limit:
        entities = [context.entity(key, diagnose=False) for key in outside_featured]
        entities = [item for item in entities if item]
        summary_id = "functional:featured-outside-groups"
        drilldown_id = f"drilldown:{summary_id}"
        nodes.append(DiagramNode(
            summary_id, f"Featured Functions Outside Groups ({len(entities)})", "summary",
            status="warning", drilldown_ref=drilldown_id,
            evidence=[_provenance(item) for item in entities],
        ))
        drilldowns.append(DiagramDrilldown(
            drilldown_id, summary_id,
            spec=_entity_list_spec("functional-featured-outside-groups", "Featured Functions Outside Groups", entities),
        ))
    if len(groups) > len(selected_groups):
        warnings.append(Diagnostic(
            "warning", "FUNCTIONAL_OVERVIEW_BOUNDED",
            f"{len(groups) - len(selected_groups)} curated functional groups omitted (limit {limit})",
            view="functional",
        ))
    spec = DiagramSpec(
        "functional", "Functional Architecture", direction="TB", layout="functional-flow", nodes=nodes,
        edges=list(flows.values()), warnings=warnings, drilldowns=drilldowns,
        provenance=DiagramProvenance("curated-functional", context={"max_overview_nodes": limit}),
    )
    spec.validate()
    return bound_diagram_spec(spec)


def project_functional_architecture(
    context: ArchitectureViewContext, curation: ViewCuration | None = None,
    *, max_overview_nodes: int = DEFAULT_MAX_OVERVIEW_NODES,
) -> DiagramSpec:
    """Project bounded capability roots, decomposition, supported flows, and allocation summaries."""
    curation = curation or ViewCuration()
    limit = max(1, max_overview_nodes)
    if curation.groups:
        return _project_curated_functional(context, curation, limit)
    warnings = _curation_diagnostics("functional", context, curation)
    hidden = {item.resolved_id for item in curation.hide if item.resolved_id}
    featured = {item.resolved_id for item in curation.featured if item.resolved_id}
    order = {key: index for index, key in enumerate(curation.order)}
    groups, membership = _group_map(curation)
    roots = _capability_roots(context)
    preferred = curation.mission_root or curation.preferred_capability_root
    preferred_key = preferred.resolved_id if preferred else ""
    roots.sort(key=lambda item: (item.key != preferred_key, item.key not in featured, order.get(item.key, len(order)), item.key))
    candidates: list[IndexedEntity] = []
    presentation_roots = list(roots)
    preferred_entity = context.entity(preferred_key, diagnose=False) if preferred_key else None
    if preferred_entity and preferred_entity.entity_type == "capability" and preferred_entity.key not in {item.key for item in presentation_roots}:
        presentation_roots.insert(0, preferred_entity)
    for root in presentation_roots:
        if root.key not in hidden:
            candidates.append(root)
        children = [
            context.entity(key, diagnose=False) for key in context.entity_children(root.key)
            if (child := context.entity(key, diagnose=False)) and child.entity_type == "capability" and child.key not in hidden
        ]
        children.sort(key=lambda item: (item.key not in featured, order.get(item.key, len(order)), item.key))
        candidates.extend(children)
    for key in sorted(featured):
        entity = context.entity(key, diagnose=False)
        if entity and entity.entity_type == "capability" and entity.key not in hidden:
            candidates.append(entity)
    if not roots:
        candidates = [item for item in context.entities("capability") if item.key not in hidden]
    behavior_links, component_links = _capability_links(context)
    allocated = {key for values in component_links.values() for key in values}
    orphans = [item for item in context.entities("component") if item.key not in allocated]
    all_capabilities = [item for item in context.entities("capability") if item.key not in hidden]
    deduplicated = list({item.key: item for item in candidates}.values())
    reserve = (1 if orphans else 0) + (1 if len(all_capabilities) > max(0, limit - (1 if orphans else 0)) else 0)
    root_keys = {root.key for root in presentation_roots}
    deduplicated.sort(key=lambda item: (item.key not in featured, item.key not in root_keys, order.get(item.key, len(order)), item.key))
    selected = deduplicated[:min(12, max(0, limit - reserve))]
    selected_keys = {item.key for item in selected}
    nodes: list[DiagramNode] = []
    drilldowns: list[DiagramDrilldown] = []
    for capability in selected:
        inputs, outputs = set(), set()
        for behavior_key in behavior_links[capability.key]:
            behavior = context.entity(behavior_key, diagnose=False)
            for step in behavior.value.structured_steps:
                if step.input:
                    inputs.add(step.input)
                if step.output:
                    outputs.add(step.output)
        drilldown_id = _drilldown_id(curation, capability.key)
        nodes.append(DiagramNode(
            _node_id(capability.key), _label(capability, curation), "capability", group=membership.get(capability.key, ""),
            entity_ref=capability.key, drilldown_ref=drilldown_id,
            badges=_badges(capability, behaviors=len(behavior_links[capability.key]), components=len(component_links[capability.key])),
            metrics={"inputs": ", ".join(sorted(inputs)), "outputs": ", ".join(sorted(outputs))}, evidence=[_provenance(capability)],
        ))
        drilldowns.append(DiagramDrilldown(
            drilldown_id, _node_id(capability.key),
            spec=_functional_drilldown(context, capability, curation, behavior_links, component_links),
        ))
    edges: list[DiagramEdge] = []
    for parent in selected:
        for relationship in context.outgoing(parent.key, "contains"):
            if relationship.target in selected_keys:
                edges.append(DiagramEdge(_node_id(parent.key), _node_id(relationship.target), "decomposition", style="dotted", evidence=[_relationship_provenance(relationship)]))

    flows: dict[tuple[str, str, str], DiagramEdge] = {}
    for behavior in context.entities("behavior"):
        steps = sorted(behavior.value.structured_steps, key=lambda step: (step.order, step.action))
        mapped = [(step, _step_capability(context, behavior, step.component_ref, step.action)) for step in steps]
        for (source_step, source), (target_step, target) in zip(mapped, mapped[1:]):
            if not source or not target or source == target or source not in selected_keys or target not in selected_keys:
                continue
            key = (source, target, "operational-flow")
            evidence = _derived("behavior-step-transition", [behavior.key, source, target], source_step=source_step.order, target_step=target_step.order)
            if key not in flows:
                flows[key] = DiagramEdge(_node_id(source), _node_id(target), key[2], style="solid", evidence=[])
            flows[key].count += 1 if flows[key].evidence else 0
            flows[key].evidence.append(evidence)
    edges.extend(flows.values())
    for flow in curation.flows:
        if flow.source not in selected_keys or flow.target not in selected_keys:
            continue
        evidence = _curated_provenance(flow.evidence)
        canonical = next((item for item in context.outgoing(flow.source, flow.kind) if item.target == flow.target), None)
        if canonical:
            evidence = [_relationship_provenance(canonical)]
        if evidence:
            edges.append(DiagramEdge(_node_id(flow.source), _node_id(flow.target), flow.kind, flow.label, evidence=evidence, inferred=flow.inferred, style="solid"))

    omitted_entities = [item for item in all_capabilities if item.key not in selected_keys]
    omitted = len(omitted_entities)
    if orphans and len(nodes) < limit:
        summary_id = "functional:orphan-summary"
        drilldown_id = "drilldown:functional-orphans"
        nodes.append(DiagramNode(summary_id, f"Unallocated Functions ({len(orphans)})", "summary", status="orphan",
                                 drilldown_ref=drilldown_id, badges=[f"components:{len(orphans)}"]))
        drilldowns.append(DiagramDrilldown(drilldown_id, summary_id, spec=_entity_list_spec("functional-orphans", "Unallocated Functions", orphans)))
        groups.append(DiagramGroup("functional:orphans", f"Unallocated Functions ({len(orphans)})", "warning", order=99))
    if omitted and len(nodes) < limit:
        summary_id = "functional:omitted-summary"
        drilldown_id = "drilldown:functional-omitted"
        nodes.append(DiagramNode(summary_id, f"More Functions ({omitted})", "summary", status="omitted",
                                 drilldown_ref=drilldown_id, badges=[f"capabilities:{omitted}"]))
        drilldowns.append(DiagramDrilldown(drilldown_id, summary_id, spec=_entity_list_spec("functional-omitted", "Omitted Functions", omitted_entities)))
    if omitted:
        warnings.append(Diagnostic("warning", "FUNCTIONAL_OVERVIEW_BOUNDED", f"{omitted} functional blocks omitted (limit {limit})", view="functional"))
    if not nodes:
        nodes.append(DiagramNode("functional:empty", "Functional architecture unavailable", "warning"))
        warnings.append(Diagnostic("warning", "FUNCTIONAL_SPARSE_FALLBACK", "No capabilities were available", view="functional"))
    spec = DiagramSpec(
        "functional", "Functional Architecture", direction="TB", layout="functional-flow", nodes=nodes, edges=edges, groups=groups,
        warnings=[*context.diagnostics, *warnings], drilldowns=drilldowns,
        provenance=DiagramProvenance("architecture-view-context", [item.key for item in roots],
                                     context={"curated": curation != ViewCuration(), "max_overview_nodes": limit}),
    )
    spec.validate()
    return bound_diagram_spec(spec)


_LOGICAL_TIERS = (
    ("web", "Web", ("web", "ui", "frontend", "api", "gateway")),
    ("application", "Application / Orchestration", ("application", "orchestration", "workflow", "pipeline", "cli")),
    ("domain", "Domain / Service", ("domain", "service", "core", "business")),
    ("data", "Data / Contracts", ("data", "repository", "store", "schema", "contract", "model")),
    ("infrastructure", "Infrastructure", ("infrastructure", "infra", "deployment", "monitor", "adapter")),
)
_LOGICAL_EDGE_KINDS = {"depends-on", "produces", "consumes", "transforms", "subscribes-to", "uses"}


def _logical_tier(entity: IndexedEntity) -> str:
    value = entity.value
    kind = getattr(getattr(value, "kind", ""), "value", getattr(value, "kind", ""))
    evidence = " ".join([
        getattr(value, "layer", ""), str(kind), entity.name,
        *getattr(value, "files", []), *getattr(value, "responsibilities", []),
    ]).casefold()
    for tier, _, terms in _LOGICAL_TIERS:
        if any(term in evidence for term in terms):
            return tier
    return "domain"


def _system_models(context: ArchitectureViewContext) -> tuple[dict[str, IndexedEntity], dict[str, str]]:
    systems: dict[str, IndexedEntity] = {}
    model_owner: dict[str, str] = {}
    for system in context.entities("system"):
        children = context.child_models_for_system(system.key)
        if not children:
            continue
        systems[system.key] = system
        for child in children:
            model_owner[child] = system.key
    return systems, model_owner


def _logical_facets(
    context: ArchitectureViewContext, models: Iterable[str], visible_interfaces: Iterable[IndexedEntity],
    visible: Callable[[str | IndexedEntity], bool],
) -> tuple[list[str], dict[str, str | int | bool]]:
    namespaces = set(models)
    capabilities = sum(visible(item) for model in namespaces for item in context.entities("capability", model))
    interfaces = sum(item.model in namespaces for item in visible_interfaces)
    components = sum(visible(item) for model in namespaces for item in context.entities("component", model))
    requirements = sum(visible(item) for model in namespaces for item in context.entities("requirement", model))
    monitoring = sum(
        len(getattr(item.value, "monitored", []) or []) + len(getattr(item.value, "observability", []) or [])
        for model in namespaces for item in context.entities("component", model) if visible(item)
    )
    failures = sum(
        len(getattr(item.value, "failure_modes", []) or [])
        for model in namespaces for item in context.entities(model=model) if visible(item)
    )
    badges = [f"components:{components}", f"interfaces:{interfaces}", f"capabilities:{capabilities}"]
    return badges, {
        "requirements": requirements, "monitoring": monitoring, "failures": failures,
        "facet:capabilities": capabilities > 0, "facet:requirements": requirements > 0,
        "facet:monitoring": monitoring > 0,
    }


def _logical_entity_spec(identifier: str, title: str, entities: Iterable[IndexedEntity]) -> DiagramSpec:
    return DiagramSpec(identifier, title, nodes=[
        DiagramNode(_node_id(item.key), item.name, item.entity_type, entity_ref=item.key, evidence=[_provenance(item)])
        for item in sorted(entities, key=lambda value: value.key)
    ])


def _logical_system_drilldown(
    context: ArchitectureViewContext, system: IndexedEntity, models: list[str], curation: ViewCuration,
    visible: Callable[[str | IndexedEntity], bool], *, max_nodes: int = 36,
) -> DiagramSpec:
    entities = [
        item for model in models for item in context.entities(model=model)
        if item.entity_type in {"layer", "component", "interface", "capability", "requirement"}
        and visible(item)
    ]
    priority = {"layer": 0, "component": 1, "interface": 2, "capability": 3, "requirement": 4}
    entities.sort(key=lambda item: (priority.get(item.entity_type, 9), item.key))
    reserve = 1 if len(entities) > max_nodes else 0
    selected = entities[:max_nodes - reserve]
    selected_keys = {item.key for item in selected}
    groups = [DiagramGroup(f"detail-tier:{tier}", label, "tier", order=index) for index, (tier, label, _) in enumerate(_LOGICAL_TIERS)]
    nodes = []
    for item in selected:
        group = f"detail-tier:{_logical_tier(item)}" if item.entity_type in {"component", "layer"} else ""
        badges = _badges(item)
        if item.entity_type == "component":
            badges.extend([
                f"failures:{len(item.value.failure_modes)}",
                f"monitoring:{len(item.value.monitored) + len(item.value.observability)}",
            ])
        nodes.append(DiagramNode(
            _node_id(item.key), _label(item, curation), item.entity_type, group=group,
            entity_ref=item.key, badges=badges, evidence=[_provenance(item)],
        ))
    edges = [
        DiagramEdge(_node_id(rel.source), _node_id(rel.target), rel.kind, evidence=[_relationship_provenance(rel)])
        for rel in context.relationships()
        if visible(rel.source) and visible(rel.target)
        and rel.source in selected_keys and rel.target in selected_keys
    ]
    warnings = []
    omitted = [item for item in entities if item.key not in selected_keys]
    drilldowns = []
    if omitted:
        summary_id = f"logical-detail:{system.key}:omitted"
        drilldown_id = f"drilldown:{summary_id}"
        nodes.append(DiagramNode(
            summary_id, f"More Internal Elements ({len(omitted)})", "summary",
            status="omitted", drilldown_ref=drilldown_id,
        ))
        drilldowns.append(DiagramDrilldown(
            drilldown_id, summary_id,
            spec=_logical_entity_spec(f"{summary_id}:entities", "Omitted Internal Elements", omitted),
        ))
        warnings.append(Diagnostic(
            "warning", "LOGICAL_DRILLDOWN_BOUNDED",
            f"{len(omitted)} internal entities omitted", view="logical",
        ))
    return DiagramSpec(
        f"logical-detail:{system.key}", f"System: {system.name}", direction="TB",
        nodes=nodes, edges=edges, groups=groups, warnings=warnings, drilldowns=drilldowns,
        provenance=_derived("system-boundary", [system.key, *[item.key for item in entities]]),
    )


def _logical_backbone(edges: Iterable[DiagramEdge], nodes: Iterable[DiagramNode], limit: int = 9) -> list[DiagramEdge]:
    node_values = {node.id: node for node in nodes}
    lane_order = {lane: index for index, lane in enumerate(dict.fromkeys(node.lane for node in nodes))}
    candidates: list[DiagramEdge] = []
    paired: set[tuple[str, str]] = set()
    values = list(edges)
    directions = {(edge.source, edge.target, edge.kind) for edge in values}
    for edge in sorted(values, key=lambda item: (item.source, item.target, item.kind, item.label)):
        if edge.kind == "depends-on" and (edge.target, edge.source, edge.kind) in directions:
            pair = tuple(sorted((edge.source, edge.target)))
            if pair in paired:
                continue
            paired.add(pair)
            reverse = next(item for item in values if item.source == edge.target and item.target == edge.source and item.kind == edge.kind)
            selected = edge if (edge.source, edge.target) == pair else reverse
            candidates.append(DiagramEdge(
                selected.source, selected.target, selected.kind, "cycle",
                evidence=list(dict.fromkeys([*edge.evidence, *reverse.evidence])),
                style="cycle", critical=edge.critical or reverse.critical,
                count=edge.count + reverse.count,
                title=f"Reciprocal depends-on: {edge.count + reverse.count} relationships",
            ))
        else:
            candidates.append(edge)

    def score(edge: DiagramEdge) -> tuple[int, int, int, int, str, str, str]:
        source_lane = lane_order.get(node_values[edge.source].lane, 99)
        target_lane = lane_order.get(node_values[edge.target].lane, 99)
        return (
            0 if edge.kind == "interface-port" else 1,
            0 if abs(source_lane - target_lane) == 1 else 1,
            -edge.count,
            0 if edge.critical or edge.style == "cycle" else 1,
            edge.source, edge.target, edge.kind,
        )

    parent = {identifier: identifier for identifier in node_values}

    def root(identifier: str) -> str:
        while parent[identifier] != identifier:
            parent[identifier] = parent[parent[identifier]]
            identifier = parent[identifier]
        return identifier

    selected: list[DiagramEdge] = []
    deferred: list[DiagramEdge] = []
    for edge in sorted(candidates, key=score):
        source_root, target_root = root(edge.source), root(edge.target)
        if source_root != target_root and len(selected) < limit:
            parent[target_root] = source_root
            selected.append(edge)
        else:
            deferred.append(edge)
    extras = 0
    for edge in sorted(deferred, key=score):
        if len(selected) >= limit:
            break
        if edge.kind == "interface-port" or extras < 1 and (edge.critical or edge.style == "cycle"):
            selected.append(edge)
            extras += edge.kind != "interface-port"
    return selected


def project_logical_architecture(
    context: ArchitectureViewContext, curation: ViewCuration | None = None,
    *, max_overview_nodes: int = DEFAULT_MAX_OVERVIEW_NODES,
) -> DiagramSpec:
    """Project canonical systems and bounded presentation-only inline aggregates."""
    curation = curation or ViewCuration()
    limit = max(1, max_overview_nodes)
    warnings = _curation_diagnostics("logical", context, curation)
    visible = _visibility(curation)
    visible_interfaces = [item for item in context.entities("interface") if visible(item)]
    order = {key: index for index, key in enumerate(curation.order)}
    systems, model_owner = _system_models(context)
    tier_defs = {tier: (label, index) for index, (tier, label, _) in enumerate(_LOGICAL_TIERS)}
    lanes = []
    membership: dict[str, str] = {}
    if curation.tiers:
        for curated in sorted(curation.tiers, key=lambda item: (item.order, item.id)):
            if visible(curated.id):
                lanes.append(DiagramGroup(curated.id, curated.label, "tier", curated.parent, curated.order))
                membership.update({member: curated.id for member in curated.members if visible(member)})
    else:
        lanes = [
            DiagramGroup(f"logical-tier:{tier}", label, "tier", order=index)
            for tier, (label, index) in tier_defs.items() if visible(f"logical-tier:{tier}")
        ]

    def lane_for(entity: IndexedEntity) -> str:
        assigned = membership.get(entity.key, "")
        if assigned:
            return assigned
        tier = _logical_tier(entity)
        automatic = f"logical-tier:{tier}"
        if any(item.id == automatic for item in lanes):
            return automatic
        return next((item.id for item in lanes if tier in f"{item.id} {item.label}".casefold()), lanes[0].id if lanes else "")

    system_nodes: list[DiagramNode] = []
    drilldowns: list[DiagramDrilldown] = []
    for key, system in sorted(systems.items(), key=lambda item: (order.get(item[0], len(order)), item[0])):
        if not visible(key):
            continue
        models = context.child_models_for_system(key)
        badges, metrics = _logical_facets(context, models, visible_interfaces, visible)
        if not any(int(badge.rsplit(":", 1)[1]) for badge in badges):
            continue
        drilldown_id = _drilldown_id(curation, key)
        system_nodes.append(DiagramNode(
            _node_id(key), _label(system, curation), "system",
            lane=lane_for(system),
            entity_ref=key, drilldown_ref=drilldown_id, badges=badges, metrics=metrics, evidence=[_provenance(system)],
        ))
        drilldowns.append(DiagramDrilldown(
            drilldown_id, _node_id(key),
            spec=_logical_system_drilldown(context, system, models, curation, visible),
        ))

    aggregate_members = {item.resolved_id for item in curation.aggregate_components if item.resolved_id}
    curated_aggregates = [item for item in curation.groups if item.kind == "aggregate" and visible(item.id)]
    consumed: set[str] = set()
    aggregates: list[tuple[str, str, str, list[IndexedEntity]]] = []
    for group in curated_aggregates:
        members = [
            entity for key in group.members
            if key in aggregate_members and visible(key)
            and (entity := context.entity(key, diagnose=False)) and entity.entity_type == "component"
        ]
        if members:
            consumed.update(item.key for item in members)
            lane = group.parent or next((membership.get(item.key, "") for item in members if membership.get(item.key)), "")
            if not lane:
                lane = lane_for(members[0])
            aggregates.append((group.id, group.label, lane, members))
    inline = [
        item for item in context.entities("component", "root")
        if visible(item) and item.key not in consumed
    ]
    semantic: dict[str, list[IndexedEntity]] = defaultdict(list)
    for component in inline:
        semantic[_logical_tier(component)].append(component)
    for tier, members in sorted(semantic.items(), key=lambda item: tier_defs[item[0]][1]):
        identifier = f"logical-inline:{tier}"
        if visible(identifier):
            aggregates.append((identifier, f"Inline {tier_defs[tier][0]}", lane_for(members[0]), members))

    aggregate_nodes: list[DiagramNode] = []
    for identifier, label, lane, members in aggregates:
        refs = [item.key for item in sorted(members, key=lambda value: value.key)]
        drilldown_id = f"drilldown:{identifier}"
        aggregate_nodes.append(DiagramNode(
            f"aggregate:{identifier}", label, "aggregate", lane=lane, drilldown_ref=drilldown_id,
            badges=[f"components:{len(refs)}"], metrics={"members": ", ".join(refs)},
            evidence=[_derived("presentation-aggregate", refs)],
        ))
        drilldowns.append(DiagramDrilldown(
            drilldown_id, f"aggregate:{identifier}", spec=_logical_entity_spec(f"detail:{identifier}", label, members),
        ))

    featured = {item.resolved_id for item in curation.featured if item.resolved_id}
    actors = [
        item for kind in ("actor", "external_system") for item in context.entities(kind)
        if visible(item) and (not curation.tiers or item.key in featured)
    ]
    actor_nodes = [DiagramNode(
        _node_id(item.key), _label(item, curation), "actor" if item.entity_type == "actor" else "external",
        entity_ref=item.key, evidence=[_provenance(item)],
    ) for item in actors]

    system_node_by_ref = {node.entity_ref: node for node in system_nodes}
    cross_system_interfaces: list[tuple[IndexedEntity, str, str]] = []
    for interface in visible_interfaces:
        endpoint_systems = []
        for reference in (interface.value.provider, interface.value.consumer):
            endpoint = _find_local(context, interface.model, reference)
            if endpoint and endpoint.model in model_owner:
                endpoint_systems.append(model_owner[endpoint.model])
            elif endpoint and endpoint.entity_type == "system":
                endpoint_systems.append(endpoint.key)
        distinct = sorted(set(endpoint_systems))
        if len(distinct) == 2 and all(key in system_node_by_ref for key in distinct):
            cross_system_interfaces.append((interface, distinct[0], distinct[1]))
    relationship_importance = defaultdict(int)
    for relationship in context.relationships():
        if relationship.kind in _LOGICAL_EDGE_KINDS:
            weight = 2 if getattr(relationship.value.strength, "value", "") == "strong" or relationship.value.extensions.get("critical") else 1
            relationship_importance[relationship.source] += weight
            relationship_importance[relationship.target] += weight
    cross_system_interfaces.sort(key=lambda item: (
        item[0].key not in featured,
        -relationship_importance[item[0].key],
        item[0].key,
    ))

    priority_nodes: list[DiagramNode] = []
    priority_interface = cross_system_interfaces[0] if cross_system_interfaces and limit >= 3 else None
    if priority_interface:
        interface, source_system, target_system = priority_interface
        priority_nodes = [
            system_node_by_ref[source_system],
            DiagramNode(
                _node_id(interface.key), _label(interface, curation), "interface",
                entity_ref=interface.key, evidence=[_provenance(interface)],
            ),
            system_node_by_ref[target_system],
        ]

    candidates = [*system_nodes, *aggregate_nodes, *actor_nodes]
    candidates.sort(key=lambda node: (node.kind not in {"system", "aggregate"}, order.get(node.entity_ref, len(order)), node.id))
    remaining = [node for node in candidates if node.id not in {item.id for item in priority_nodes}]
    reserve = 1 if len(priority_nodes) + len(remaining) > limit else 0
    selected = [*priority_nodes, *remaining[:max(0, limit - reserve - len(priority_nodes))]]
    selected_ids = {node.id for node in selected}
    selected_refs = {node.entity_ref for node in selected if node.entity_ref}
    aggregate_owner = {
        member: node.id for node in aggregate_nodes
        for member in str(node.metrics.get("members", "")).split(", ") if member
    }

    def owner(key: str) -> str:
        if not visible(key):
            return ""
        entity = context.entity(key, diagnose=False)
        if not entity:
            return ""
        if key in selected_refs:
            return _node_id(key)
        if entity.model in model_owner:
            return _node_id(model_owner[entity.model])
        return aggregate_owner.get(key, "")

    edge_values: dict[tuple[str, str, str], DiagramEdge] = {}
    full_dependency_details: list[dict[str, str | int | bool]] = []
    for relationship in context.relationships():
        if relationship.kind not in _LOGICAL_EDGE_KINDS or (
            relationship.kind == "depends-on" and not visible("logical:dependencies")
        ):
            continue
        if not visible(relationship.source) or not visible(relationship.target):
            continue
        source, target = owner(relationship.source), owner(relationship.target)
        if not source or not target or source == target or source not in selected_ids or target not in selected_ids:
            continue
        full_dependency_details.append({
            "source": relationship.source, "target": relationship.target,
            "overview_source": source, "overview_target": target,
            "kind": relationship.kind, "model": relationship.model,
            "critical": getattr(relationship.value.strength, "value", "") == "strong" or bool(relationship.value.extensions.get("critical")),
        })
        key = (source, target, relationship.kind)
        if key not in edge_values:
            edge_values[key] = DiagramEdge(source, target, relationship.kind, evidence=[])
        edge = edge_values[key]
        if edge.evidence:
            edge.count += 1
        edge.evidence.append(_relationship_provenance(relationship))
        edge.critical = edge.critical or getattr(relationship.value.strength, "value", "") == "strong" or bool(relationship.value.extensions.get("critical"))
    pairs = {(edge.source, edge.target) for edge in edge_values.values() if edge.kind == "depends-on"}
    for edge in edge_values.values():
        edge.title = edge.kind if edge.count == 1 else f"{edge.kind}: {edge.count} relationships"
        edge.label = "depends" if edge.kind == "depends-on" else edge.kind
        if edge.count != 1:
            edge.label += f" ×{edge.count}"
        if edge.kind == "depends-on" and (edge.target, edge.source) in pairs:
            edge.style = "cycle"

    interfaces = []
    for interface in visible_interfaces:
        endpoints = [
            item for reference in (interface.value.provider, interface.value.consumer)
            if (item := _find_local(context, interface.model, reference))
        ]
        owners = {owner(item.key) for item in endpoints} - {""}
        related_actor = any(item.entity_type in {"actor", "external_system"} for item in endpoints)
        if len(owners) > 1 or related_actor or any(rel.target == interface.key or rel.source == interface.key for rel in context.relationships("consumes")):
            interfaces.append(interface)
    for interface in interfaces:
        if interface.key in {node.entity_ref for node in selected}:
            continue
        endpoints = [
            endpoint for endpoint_name in (interface.value.provider, interface.value.consumer)
            if (endpoint := _find_local(context, interface.model, endpoint_name))
        ]
        endpoint_owners = {owner(endpoint.key) for endpoint in endpoints} - {""}
        if not endpoint_owners or not endpoint_owners <= selected_ids or len(selected) >= limit - reserve:
            break
        node = DiagramNode(_node_id(interface.key), _label(interface, curation), "interface", entity_ref=interface.key, evidence=[_provenance(interface)])
        if node.id not in selected_ids:
            selected.append(node)
            selected_ids.add(node.id)
        for endpoint_name in (interface.value.provider, interface.value.consumer):
            endpoint = _find_local(context, interface.model, endpoint_name)
            endpoint_owner = owner(endpoint.key) if endpoint else ""
            if endpoint_owner in selected_ids:
                evidence = _derived("interface-endpoint", [interface.key, endpoint.key], protocol=interface.value.protocol)
                edge_values[(endpoint_owner, node.id, "interface-port")] = DiagramEdge(endpoint_owner, node.id, "interface-port", evidence=[evidence])
    for interface, source_system, target_system in cross_system_interfaces:
        interface_id = _node_id(interface.key)
        if interface_id not in selected_ids:
            continue
        for system_key in (source_system, target_system):
            system_id = _node_id(system_key)
            evidence = _derived("interface-endpoint", [interface.key, system_key], protocol=interface.value.protocol)
            edge_values[(system_id, interface_id, "interface-port")] = DiagramEdge(
                system_id, interface_id, "interface-port", evidence=[evidence],
            )

    overview_edges = list(edge_values.values())
    if curation.tiers:
        overview_edges = _logical_backbone(overview_edges, selected, 9)
    connected = {endpoint for edge in edge_values.values() for endpoint in (edge.source, edge.target)}
    for node in selected:
        if node.id not in connected and "No cross-system dependency" not in node.badges:
            node.badges.append("No cross-system dependency")
    full_dependency_details.sort(key=lambda item: (
        str(item["source"]), str(item["target"]), str(item["kind"]), str(item["model"]),
    ))
    dependency_facet = {
        "displayed_count": len(overview_edges),
        "full_count": len(full_dependency_details),
        "edges": full_dependency_details,
    }
    for drilldown in drilldowns:
        if not drilldown.spec:
            continue
        source_node = next((node for node in selected if node.drilldown_ref == drilldown.id), None)
        members = {source_node.entity_ref} if source_node and source_node.entity_ref else set()
        if source_node and source_node.kind == "aggregate":
            members.update(str(source_node.metrics.get("members", "")).split(", "))
        relevant = [
            item for item in full_dependency_details
            if item["source"] in members or item["target"] in members
            or item["overview_source"] == source_node.id or item["overview_target"] == source_node.id
        ] if source_node else []
        drilldown.spec.facets["logical_dependencies"] = {
            "full_count": len(relevant), "edges": relevant,
        }

    omitted_nodes = [node for node in candidates if node.id not in selected_ids]
    if omitted_nodes and len(selected) < limit and not curation.tiers:
        summary_id = "logical:omitted-summary"
        drilldown_id = "drilldown:logical-omitted"
        selected.append(DiagramNode(summary_id, f"More Logical Elements ({len(omitted_nodes)})", "summary", status="omitted", drilldown_ref=drilldown_id))
        omitted_entities = [context.entity(node.entity_ref, diagnose=False) for node in omitted_nodes if node.entity_ref and visible(node.entity_ref)]
        drilldowns.append(DiagramDrilldown(
            drilldown_id, summary_id,
            spec=_logical_entity_spec("logical-omitted", "Omitted Logical Elements", [item for item in omitted_entities if item]),
        ))
        warnings.append(Diagnostic("warning", "LOGICAL_OVERVIEW_BOUNDED", f"{len(omitted_nodes)} logical elements omitted (limit {limit})", view="logical"))
    used_drilldowns = {node.drilldown_ref for node in selected if node.drilldown_ref}
    spec = DiagramSpec(
        "logical", "Logical Architecture", direction="TB", layout="logical-tiers", nodes=selected,
        edges=overview_edges, lanes=lanes,
        callouts=[DiagramCallout(
            "logical:dependency-backbone",
            f"Showing {len(overview_edges)} of {len(full_dependency_details)} dependency/interface relationships",
            kind="summary", evidence=["logical_dependencies"],
        )] if curation.tiers and full_dependency_details else [],
        warnings=[*context.diagnostics, *warnings],
        drilldowns=[item for item in drilldowns if item.id in used_drilldowns],
        provenance=DiagramProvenance("architecture-view-context", context={
            "curated": curation != ViewCuration(), "max_overview_nodes": limit,
            "displayed_dependency_edges": len(overview_edges), "full_dependency_edges": len(full_dependency_details),
        }),
        facets={"logical_dependencies": dependency_facet},
    )
    spec.validate()
    return bound_diagram_spec(spec)


def _behavior_actor(context: ArchitectureViewContext, behavior: IndexedEntity) -> IndexedEntity | None:
    return _find_local(context, behavior.model, behavior.value.actor_id or behavior.value.actor)


def _behavior_components(
    context: ArchitectureViewContext, behavior: IndexedEntity, visible: Callable[[str | IndexedEntity], bool],
) -> list[IndexedEntity]:
    result: dict[str, IndexedEntity] = {}
    for step in behavior.value.structured_steps:
        component = _find_local(context, behavior.model, step.component_ref)
        if component and visible(component) and component.entity_type in {"component", "system"}:
            result[component.key] = component
    for relationship in context.incoming(behavior.key, "traces-to"):
        component = context.entity(relationship.source, diagnose=False)
        if component and visible(component) and component.entity_type in {"component", "system"}:
            result[component.key] = component
    return sorted(result.values(), key=lambda item: item.key)


def _behavior_systems(
    context: ArchitectureViewContext, behavior: IndexedEntity,
    visible: Callable[[str | IndexedEntity], bool],
) -> list[IndexedEntity]:
    systems, model_owner = _system_models(context)
    result: dict[str, IndexedEntity] = {}
    for component in _behavior_components(context, behavior, visible):
        if component.entity_type == "system" and visible(component):
            result[component.key] = component
        elif component.model in model_owner and visible(model_owner[component.model]):
            owner = systems[model_owner[component.model]]
            result[owner.key] = owner
    return sorted(result.values(), key=lambda item: item.name)


def _behavior_interfaces(
    context: ArchitectureViewContext, behavior: IndexedEntity, visible: Callable[[str | IndexedEntity], bool],
) -> list[IndexedEntity]:
    return sorted({
        interface.key: interface for reference in behavior.value.interface_refs
        if (interface := _find_local(context, behavior.model, reference))
        and visible(interface) and interface.entity_type == "interface"
    }.values(), key=lambda item: item.key)


def _use_case_drilldown(
    context: ArchitectureViewContext, behavior: IndexedEntity, curation: ViewCuration,
    visible: Callable[[str | IndexedEntity], bool], annotation: CuratedUseCaseAnnotation | None = None,
) -> DiagramSpec:
    goal = next(iter(behavior.value.goals), "") or (annotation.goal if annotation else "")
    trigger = behavior.value.trigger or (annotation.trigger if annotation else "")
    uses_annotation = bool(annotation and (
        (not behavior.value.trigger and annotation.trigger)
        or (not behavior.value.goals and annotation.goal)
        or (not behavior.value.preconditions and annotation.preconditions)
        or (not behavior.value.postconditions and (annotation.postconditions or annotation.success_outcome))
        or (not behavior.value.moes and annotation.moes)
    ))
    nodes = [DiagramNode(
        _node_id(behavior.key), _label(behavior, curation), "use-case", entity_ref=behavior.key,
        subtitle=" | ".join(value for value in (trigger, goal) if value),
        badges=[*_badges(behavior), *(["inferred"] if uses_annotation else [])],
        inferred=uses_annotation,
        evidence=[_provenance(behavior), *(_curated_provenance(annotation.evidence) if uses_annotation and annotation else [])],
    )]
    edges: list[DiagramEdge] = []
    groups: list[DiagramGroup] = []
    warnings: list[Diagnostic] = []
    actor = _behavior_actor(context, behavior)
    if actor and visible(actor):
        actor_kind = "external" if actor.entity_type == "external_system" else "actor"
        nodes.append(DiagramNode(_node_id(actor.key), actor.name, actor_kind, entity_ref=actor.key, evidence=[_provenance(actor)]))
        edges.append(DiagramEdge(
            _node_id(actor.key), _node_id(behavior.key), "initiates",
            evidence=[_derived("behavior-actor", [behavior.key, actor.key])],
        ))

    systems, model_owner = _system_models(context)
    steps = sorted(behavior.value.structured_steps, key=lambda item: (item.order, item.action, item.component_ref))
    plain = False
    if not steps:
        plain = True
        steps = [type("PlainStep", (), {
            "order": index, "action": action, "component_ref": "", "actor": "",
            "input": "", "output": "", "error_handling": "",
        })() for index, action in enumerate(behavior.value.steps, 1)]
        warnings.append(Diagnostic(
            "warning", "USE_CASE_PLAIN_STEP_FALLBACK",
            f"{behavior.name} uses unstructured plain steps", view="use_cases", source=behavior.source_path,
        ))
    previous = ""
    participants: dict[str, IndexedEntity] = {}
    for index, step in enumerate(steps):
        component = _find_local(context, behavior.model, step.component_ref)
        component = component if component and visible(component) else None
        lane = ""
        if component:
            participants[component.key] = component
            owner = model_owner.get(component.model, component.key if component.entity_type == "system" else "")
            owner = owner if owner and visible(owner) else component.key
            lane = f"lane:{behavior.key}:{owner or component.key}"
            if lane not in {item.id for item in groups}:
                label_entity = systems.get(owner, component)
                groups.append(DiagramGroup(lane, label_entity.name, "lane", order=len(groups)))
        step_id = f"step:{behavior.key}:{index + 1}"
        nodes.append(DiagramNode(
            step_id, step.action, "step", group=lane, status="lower-evidence" if plain else "structured",
            metrics={"order": step.order, "input": step.input, "output": step.output},
            evidence=[_derived("plain-behavior-step" if plain else "structured-behavior-step", [behavior.key], order=step.order)],
        ))
        if previous:
            edges.append(DiagramEdge(
                previous, step_id, "next",
                evidence=[_derived("ordered-step-transition", [behavior.key], source_order=index, target_order=index + 1)],
            ))
        previous = step_id
        if step.error_handling:
            error_id = f"error:{behavior.key}:{index + 1}"
            nodes.append(DiagramNode(
                error_id, step.error_handling, "error", status="alternate-path",
                evidence=[_derived("step-error-handling", [behavior.key], order=step.order)],
            ))
            edges.append(DiagramEdge(
                step_id, error_id, "error", style="dotted",
                evidence=[_derived("step-error-handling", [behavior.key], order=step.order)],
            ))

    for component in sorted(participants.values(), key=lambda item: item.key):
        nodes.append(DiagramNode(
            _node_id(component.key), component.name, component.entity_type, entity_ref=component.key,
            badges=[
                f"failures:{len(component.value.failure_modes)}",
                f"monitoring:{len(component.value.monitored) + len(getattr(component.value, 'observability', []))}",
            ], evidence=[_provenance(component)],
        ))
    participant_systems: dict[str, IndexedEntity] = {}
    for component in participants.values():
        owner_key = model_owner.get(component.model, "")
        if owner_key and visible(owner_key):
            participant_systems[owner_key] = systems[owner_key]
    for system in sorted(participant_systems.values(), key=lambda item: item.key):
        nodes.append(DiagramNode(
            _node_id(system.key), system.name, "system", entity_ref=system.key,
            evidence=[_provenance(system)],
        ))
        for component in participants.values():
            if model_owner.get(component.model) == system.key:
                edges.append(DiagramEdge(
                    _node_id(system.key), _node_id(component.key), "owns",
                    evidence=[_derived("hierarchy-system-ownership", [system.key, component.key], model=component.model)],
                ))
    for interface in _behavior_interfaces(context, behavior, visible):
        nodes.append(DiagramNode(_node_id(interface.key), interface.name, "interface", entity_ref=interface.key, evidence=[_provenance(interface)]))
    for relationship in context.relationships():
        refs = {node.entity_ref for node in nodes if node.entity_ref}
        if (
            visible(relationship.source) and visible(relationship.target)
            and relationship.source in refs and relationship.target in refs
        ):
            edges.append(DiagramEdge(
                _node_id(relationship.source), _node_id(relationship.target), relationship.kind,
                evidence=[_relationship_provenance(relationship)],
            ))
    support = [
        ("precondition", behavior.value.preconditions, annotation.preconditions if annotation else []),
        ("postcondition", behavior.value.postconditions, annotation.postconditions if annotation else []),
        ("success-criterion", behavior.value.goals, [annotation.goal] if annotation and annotation.goal else []),
        (
            "success-outcome", behavior.value.postconditions or behavior.value.goals,
            [annotation.success_outcome] if annotation and annotation.success_outcome else [],
        ),
        ("moe", behavior.value.moes, annotation.moes if annotation else []),
    ]
    for kind, canonical, curated in support:
        nodes.extend(_support_nodes(behavior, kind, canonical))
        if not canonical and curated and annotation:
            nodes.extend(_curated_support_nodes(behavior, kind, curated, annotation))
    for reference in behavior.value.requirements:
        requirement = _find_local(context, behavior.model, reference)
        if requirement and visible(requirement):
            nodes.append(DiagramNode(_node_id(requirement.key), requirement.name, "requirement", entity_ref=requirement.key, evidence=[_provenance(requirement)]))
        elif not requirement:
            nodes.extend(_support_nodes(behavior, "requirement", [reference]))
    existing_errors = {node.label.casefold() for node in nodes if node.kind == "error"}
    additional_errors = [*behavior.value.failure_modes]
    for component in participants.values():
        additional_errors.extend(component.value.failure_modes)
    for index, failure in enumerate(sorted(set(additional_errors))):
        if failure.casefold() in existing_errors:
            continue
        error_id = f"failure:{behavior.key}:{index + 1}"
        nodes.append(DiagramNode(error_id, failure, "error", status="failure-mode", evidence=[_derived("failure-mode", [behavior.key])]))
        edges.append(DiagramEdge(
            _node_id(behavior.key), error_id, "error", style="dotted",
            evidence=[_derived("failure-mode", [behavior.key])],
        ))
    for index, compensation in enumerate(behavior.value.compensations):
        compensation_id = f"compensation:{behavior.key}:{index + 1}"
        nodes.append(DiagramNode(
            compensation_id, compensation.compensate, "compensation", status="alternate-path",
            evidence=[_derived("behavior-compensation", [behavior.key], step=compensation.step)],
        ))
        edges.append(DiagramEdge(
            _node_id(behavior.key), compensation_id, "compensates", style="dotted",
            evidence=[_derived("behavior-compensation", [behavior.key], step=compensation.step)],
        ))
    state_ids = {state.name: f"state:{behavior.key}:{index + 1}" for index, state in enumerate(behavior.value.states)}
    for state in behavior.value.states:
        state_id = state_ids[state.name]
        nodes.append(DiagramNode(
            state_id, state.name, "state",
            evidence=[_derived("behavior-state", [behavior.key], state=state.name)],
        ))
        for transition in state.transitions:
            target = state_ids.get(str(transition.get("to", "")))
            if target:
                edges.append(DiagramEdge(
                    state_id, target, "transition", str(transition.get("on", "")),
                    evidence=[_derived("behavior-state-transition", [behavior.key], state=state.name)],
                ))
    return DiagramSpec(
        f"use-case-detail:{behavior.key}", f"Use Case: {behavior.name}", direction="TB",
        nodes=nodes, edges=edges, groups=groups, warnings=warnings,
        provenance=_derived("behavior-detail", [behavior.key]),
    )


def _actor_use_case_drilldown(
    actor_id: str, label: str, entity: IndexedEntity | None,
    behaviors: Iterable[IndexedEntity], evidence: list[DiagramProvenance], curation: ViewCuration,
    visible: Callable[[str | IndexedEntity], bool],
    inferred_associations: dict[str, list[DiagramProvenance]] | None = None,
    secondary_associations: dict[str, list[DiagramProvenance]] | None = None,
) -> DiagramSpec:
    inferred_associations = inferred_associations or {}
    secondary_associations = secondary_associations or {}
    actor_node = DiagramNode(
        f"detail:{actor_id}", label, "actor", entity_ref=entity.key if entity else "",
        inferred=entity is None, evidence=[_provenance(entity)] if entity else evidence,
    )
    nodes = [actor_node]
    edges = []
    goals = list(entity.value.goals) if entity else []
    for behavior in sorted((item for item in behaviors if visible(item)), key=lambda item: item.key):
        node_id = _node_id(behavior.key)
        inferred_evidence = inferred_associations.get(behavior.key)
        canonical_evidence = [
            *([_provenance(entity)] if entity else []), _provenance(behavior),
            *secondary_associations.get(behavior.key, []),
        ]
        nodes.append(DiagramNode(node_id, _label(behavior, curation), "use-case", entity_ref=behavior.key, evidence=[_provenance(behavior)]))
        edges.append(DiagramEdge(
            actor_node.id, node_id, "participates",
            evidence=inferred_evidence or canonical_evidence,
            inferred=bool(inferred_evidence) or entity is None,
            style="dashed" if inferred_evidence else "",
        ))
        goals.extend(behavior.value.goals)
    for index, goal in enumerate(sorted(set(goals))):
        nodes.append(DiagramNode(f"goal:{actor_id}:{index + 1}", goal, "goal", evidence=[_derived("actor-goal", [entity.key] if entity else [])]))
    return DiagramSpec(f"actor-use-cases:{actor_id}", f"Actor: {label}", nodes=nodes, edges=edges)


def project_use_cases(
    context: ArchitectureViewContext, curation: ViewCuration | None = None,
    *, max_overview_nodes: int = DEFAULT_MAX_OVERVIEW_NODES,
) -> DiagramSpec:
    """Project a bounded actor-goal catalog with evidence-rich behavior drilldowns."""
    curation = curation or ViewCuration()
    limit = max(1, max_overview_nodes)
    warnings = _curation_diagnostics("use_case", context, curation)
    visible = _visibility(curation)
    featured = {item.resolved_id for item in curation.featured if item.resolved_id}
    annotations = {item.use_case: item for item in curation.annotations if visible(item.use_case)}
    order = {key: index for index, key in enumerate(curation.order)}
    behaviors = [item for item in context.entities("behavior") if visible(item)]
    by_actor: dict[str, list[IndexedEntity]] = defaultdict(list)
    for behavior in behaviors:
        actor = _behavior_actor(context, behavior)
        actor_name = actor.key if actor else " ".join((behavior.value.actor or "Unassigned").split()).casefold()
        by_actor[actor_name].append(behavior)
    for values in by_actor.values():
        values.sort(key=lambda item: (order.get(item.key, len(order)), item.key))
    selected: list[IndexedEntity] = []
    actor_keys = sorted(
        by_actor,
        key=lambda actor_key: (
            order.get(by_actor[actor_key][0].key, len(order)) if by_actor[actor_key] else len(order),
            by_actor[actor_key][0].key if by_actor[actor_key] else actor_key,
            actor_key,
        ),
    )
    featured_behaviors = sorted(
        (item for item in behaviors if item.key in featured),
        key=lambda item: (order.get(item.key, len(order)), item.key),
    )
    catalog_target = max(10, len(featured_behaviors))
    case_limit = min(catalog_target, len(behaviors), limit)
    selected.extend(featured_behaviors[:case_limit])
    selected_keys = {item.key for item in selected}
    for actor_key in actor_keys:
        by_actor[actor_key] = [item for item in by_actor[actor_key] if item.key not in selected_keys]
    while len(selected) < case_limit and any(by_actor.values()):
        for actor_key in actor_keys:
            if by_actor[actor_key] and len(selected) < case_limit:
                selected.append(by_actor[actor_key].pop(0))
    selected.sort(key=lambda item: (item.key not in featured, order.get(item.key, len(order)), item.key))
    selected_keys = {item.key for item in selected}
    nodes: list[DiagramNode] = []
    drilldowns: list[DiagramDrilldown] = []
    for behavior in selected:
        systems = _behavior_systems(context, behavior, visible)
        annotation = annotations.get(behavior.key)
        drilldown_id = _drilldown_id(curation, behavior.key)
        goal = next(iter(behavior.value.goals), "") or (annotation.goal if annotation else "")
        trigger = behavior.value.trigger or (annotation.trigger if annotation else "")
        outcome = next(iter(behavior.value.postconditions or behavior.value.goals), "") or (
            annotation.success_outcome or next(iter(annotation.postconditions), "") if annotation else ""
        )
        uses_annotation = bool(annotation and (
            (not behavior.value.trigger and annotation.trigger)
            or (not behavior.value.goals and annotation.goal)
            or (not behavior.value.postconditions and (annotation.postconditions or annotation.success_outcome))
            or (not behavior.value.preconditions and annotation.preconditions)
            or (not behavior.value.moes and annotation.moes)
        ))
        badges = _badges(behavior)
        visible_requirements = [
            requirement for reference in behavior.value.requirements
            if (requirement := _find_local(context, behavior.model, reference)) and visible(requirement)
        ]
        badges[0] = f"requirements:{len(visible_requirements)}"
        if uses_annotation:
            badges.append("inferred")
        node_evidence = [_provenance(behavior), *(_curated_provenance(annotation.evidence) if uses_annotation and annotation else [])]
        nodes.append(DiagramNode(
            _node_id(behavior.key), _label(behavior, curation), "use-case",
            subtitle=" | ".join(value for value in (trigger, goal, outcome) if value),
            entity_ref=behavior.key, drilldown_ref=drilldown_id, badges=badges,
            inferred="inferred" in badges,
            metrics={"implementing_systems": ", ".join(item.name for item in systems)}, evidence=node_evidence,
        ))
        drilldowns.append(DiagramDrilldown(
            drilldown_id, _node_id(behavior.key),
            spec=_use_case_drilldown(context, behavior, curation, visible, annotation),
        ))

    participant_values: dict[str, tuple[str, IndexedEntity | None, list[DiagramProvenance], list[IndexedEntity]]] = {}
    for behavior in selected:
        actor = _behavior_actor(context, behavior)
        if actor and visible(actor):
            key, label, evidence = actor.key, _label(actor, curation), [_provenance(actor)]
        elif actor:
            continue
        else:
            label = " ".join(behavior.value.actor.split())
            if not label:
                continue
            key = f"inferred-actor:{label.casefold()}"
            evidence = [_derived("behavior-actor-name", [behavior.key], actor=label)]
        if key not in participant_values:
            participant_values[key] = (label, actor, evidence, [])
        participant_values[key][3].append(behavior)
    curated_actor_by_id = {item.id: item for item in curation.actors if visible(item.id)}
    curated_associations = []
    inferred_by_actor: dict[str, dict[str, list[DiagramProvenance]]] = defaultdict(dict)
    secondary_by_actor: dict[str, dict[str, list[DiagramProvenance]]] = defaultdict(dict)
    for association in curation.associations:
        associated = [
            context.entity(key, diagnose=False) for key in association.use_cases
            if key in selected_keys and visible(key)
        ]
        associated = [item for item in associated if item and item.entity_type == "behavior"]
        if not associated or not visible(association.actor):
            continue
        actor = context.entity(association.actor, diagnose=False)
        curated_actor = curated_actor_by_id.get(association.actor)
        if actor:
            key, label = actor.key, _label(actor, curation)
        elif curated_actor:
            key, label = curated_actor.id, curated_actor.name
        else:
            continue
        evidence = _curated_provenance(association.evidence)
        if key not in participant_values:
            participant_values[key] = (label, actor, evidence, [])
        for behavior in associated:
            if behavior not in participant_values[key][3]:
                participant_values[key][3].append(behavior)
            canonical_actor = _behavior_actor(context, behavior)
            if canonical_actor and canonical_actor.key == key:
                secondary_by_actor[key][behavior.key] = evidence
            else:
                curated_associations.append((key, behavior.key, evidence))
                inferred_by_actor[key][behavior.key] = evidence
    for key, (label, actor, evidence, actor_behaviors) in sorted(participant_values.items()):
        if len(nodes) >= limit - (1 if len(behaviors) > len(selected) else 0):
            break
        node_id = _node_id(key) if actor else key
        drilldown_id = f"drilldown:{node_id}"
        participant_kind = "external" if not actor or actor.entity_type == "external_system" else "actor"
        nodes.append(DiagramNode(
            node_id, label, participant_kind, entity_ref=actor.key if actor else "",
            drilldown_ref=drilldown_id, inferred=actor is None, evidence=evidence,
        ))
        drilldowns.append(DiagramDrilldown(
            drilldown_id, node_id,
            spec=_actor_use_case_drilldown(
                node_id, label, actor, actor_behaviors, evidence, curation, visible,
                inferred_associations=inferred_by_actor.get(key),
                secondary_associations=secondary_by_actor.get(key),
            ),
        ))

    node_by_ref = {node.entity_ref: node.id for node in nodes if node.entity_ref}
    edges: list[DiagramEdge] = []
    for relationship in context.relationships():
        if relationship.kind not in {"triggers", "contains"}:
            continue
        if (
            visible(relationship.source) and visible(relationship.target)
            and relationship.source in selected_keys and relationship.target in selected_keys
        ):
            edges.append(DiagramEdge(
                _node_id(relationship.source), _node_id(relationship.target), relationship.kind,
                evidence=[_relationship_provenance(relationship)],
            ))
    for key, (_, actor, evidence, actor_behaviors) in participant_values.items():
        actor_node = _node_id(key) if actor else key
        if actor_node not in {node.id for node in nodes}:
            continue
        for behavior in actor_behaviors:
            if behavior.key in selected_keys:
                canonical_actor = _behavior_actor(context, behavior)
                canonical_pair = bool(canonical_actor and canonical_actor.key == key)
                edge_evidence = evidence
                if canonical_pair:
                    edge_evidence = [
                        _provenance(canonical_actor), _provenance(behavior),
                        *secondary_by_actor.get(key, {}).get(behavior.key, []),
                    ]
                edges.append(DiagramEdge(
                    actor_node, _node_id(behavior.key), "participates", evidence=edge_evidence,
                    inferred=actor is None and not canonical_pair,
                ))
    for actor_key, behavior_key, evidence in curated_associations:
        actor_node = _node_id(actor_key) if context.entity(actor_key, diagnose=False) else actor_key
        if actor_node in {node.id for node in nodes}:
            edges = [
                edge for edge in edges
                if not (edge.source == actor_node and edge.target == _node_id(behavior_key) and edge.kind == "participates")
            ]
            edges.append(DiagramEdge(
                actor_node, _node_id(behavior_key), "participates", evidence=evidence,
                inferred=True, style="dashed",
            ))
    omitted = [
        item for item in behaviors
        if item.key not in selected_keys and item.key not in featured and visible(item)
    ]
    if omitted and len(nodes) < limit and featured:
        callouts = [DiagramCallout(
            "use-cases:omitted", f"{len(omitted)} additional use cases", "",
            "omitted-count", [item.key for item in omitted],
        )]
        warnings.append(Diagnostic(
            "warning", "USE_CASE_OVERVIEW_BOUNDED",
            f"{len(omitted)} use cases omitted (limit {limit})", view="use_cases",
        ))
    else:
        callouts = []
    if omitted and len(nodes) < limit and not featured:
        summary_id = "use-cases:omitted-summary"
        drilldown_id = "drilldown:use-cases-omitted"
        nodes.append(DiagramNode(
            summary_id, f"More Use Cases ({len(omitted)})", "summary", status="omitted",
            drilldown_ref=drilldown_id, badges=[f"behaviors:{len(omitted)}"],
        ))
        drilldowns.append(DiagramDrilldown(
            drilldown_id, summary_id,
            spec=_logical_entity_spec("use-cases-omitted", "Omitted Use Cases", omitted),
        ))
        warnings.append(Diagnostic(
            "warning", "USE_CASE_OVERVIEW_BOUNDED",
            f"{len(omitted)} use cases omitted (limit {limit})", view="use_cases",
        ))
    if not nodes:
        nodes.append(DiagramNode("use-cases:empty", "Use case evidence unavailable", "warning"))
        warnings.append(Diagnostic("warning", "USE_CASE_SPARSE_FALLBACK", "No behaviors were available", view="use_cases"))
    used_drilldowns = {node.drilldown_ref for node in nodes if node.drilldown_ref}
    spec = DiagramSpec(
        "use-cases", "Use Cases", direction="LR", layout="use-case-catalog", nodes=nodes, edges=edges,
        callouts=callouts,
        warnings=[*context.diagnostics, *warnings],
        drilldowns=[item for item in drilldowns if item.id in used_drilldowns],
        provenance=DiagramProvenance("architecture-view-context", context={"curated": curation != ViewCuration(), "max_overview_nodes": limit}),
    )
    spec.validate()
    return bound_diagram_spec(spec)


__all__ = [
    "DEFAULT_MAX_OVERVIEW_NODES", "project_conops", "project_functional_architecture",
    "project_logical_architecture", "project_use_cases",
]
