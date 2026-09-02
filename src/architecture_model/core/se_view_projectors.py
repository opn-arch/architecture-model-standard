"""Deterministic, bounded ConOps and functional architecture projections."""

from __future__ import annotations

from collections import defaultdict
import re
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
from architecture_model.core.view_curation import EvidenceRecord, ViewCuration, validate_view_curation


DEFAULT_MAX_OVERVIEW_NODES = 15


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


def project_conops(
    context: ArchitectureViewContext, curation: ViewCuration | None = None,
    *, max_overview_nodes: int = DEFAULT_MAX_OVERVIEW_NODES,
) -> DiagramSpec:
    """Project complete operational paths under one global node budget."""
    curation = curation or ViewCuration()
    limit = max(1, max_overview_nodes)
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
        if normalized not in curated_names:
            include(DiagramNode(f"external:{normalized}", name, "external", lane="actors", status="inferred", inferred=True, evidence=evidence))
    node_by_ref = {node.entity_ref: node.id for node in nodes.values() if node.entity_ref}
    for relationship in context.relationships():
        if relationship.source in node_by_ref and relationship.target in node_by_ref:
            source = context.entity(relationship.source, diagnose=False)
            target = context.entity(relationship.target, diagnose=False)
            if source and target and "interface" in {source.entity_type, target.entity_type}:
                key = (node_by_ref[relationship.source], node_by_ref[relationship.target], relationship.kind)
                edges[key] = DiagramEdge(*key, evidence=[_relationship_provenance(relationship)])
    if omitted:
        warnings.append(Diagnostic("warning", "CONOPS_OVERVIEW_BOUNDED", f"{omitted} operational paths omitted (limit {limit})", view="conops"))
    if not nodes:
        include(DiagramNode("conops:empty", "Operational context unavailable", "warning", lane="scenarios"))
        warnings.append(Diagnostic("warning", "CONOPS_SPARSE_FALLBACK", "No operational entities were available", view="conops"))
    spec = DiagramSpec(
        "conops", "Concept of Operations", nodes=list(nodes.values()), edges=list(edges.values()), groups=groups,
        lanes=lanes, callouts=[DiagramCallout("conops:omitted", f"{omitted} paths available in drilldown")][:1] if omitted else [],
        warnings=[*context.diagnostics, *warnings], drilldowns=drilldowns,
        provenance=DiagramProvenance("architecture-view-context", context={"curated": curation != ViewCuration(), "max_overview_nodes": limit}),
    )
    spec.validate()
    return spec


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
    related_behaviors = sorted({key for item in subtree for key in behavior_links[item.key]})
    related_components = sorted({key for item in subtree for key in component_links[item.key]})
    for key in [*related_behaviors, *related_components]:
        entity = context.entity(key, diagnose=False)
        if entity:
            nodes.append(DiagramNode(_node_id(key), entity.name, entity.entity_type, entity_ref=key, evidence=[_provenance(entity)]))
    interfaces = [
        item for item in context.entities("interface")
        if any(ref in {item.value.provider, item.value.consumer} for ref in [context.entity(key, diagnose=False).local_id for key in related_components])
        or any(item.local_id in (context.entity(key, diagnose=False).value.interface_refs or []) for key in related_behaviors)
    ]
    for interface in interfaces:
        nodes.append(DiagramNode(_node_id(interface.key), interface.name, "interface", entity_ref=interface.key, evidence=[_provenance(interface)]))
    owner_refs = [item.key for item in subtree]
    requirements = sorted({value for item in subtree for value in item.value.requirements})
    moes = sorted({value for item in subtree for value in item.value.moes})
    failures = sorted({value for item in subtree for value in item.value.failure_modes})
    nodes.extend(_support_nodes(capability, "requirement", requirements))
    nodes.extend(_support_nodes(capability, "moe", moes))
    nodes.extend(_support_nodes(capability, "failure", failures))
    nodes.extend(_support_nodes(capability, "monitoring", sorted({value for item in subtree for value in item.value.monitored})))
    return DiagramSpec(f"functional-detail:{capability.key}", f"Function: {capability.name}", direction="TB", nodes=nodes, edges=edges,
                       provenance=DiagramProvenance("capability-subtree", owner_refs))


def project_functional_architecture(
    context: ArchitectureViewContext, curation: ViewCuration | None = None,
    *, max_overview_nodes: int = DEFAULT_MAX_OVERVIEW_NODES,
) -> DiagramSpec:
    """Project bounded capability roots, decomposition, supported flows, and allocation summaries."""
    curation = curation or ViewCuration()
    limit = max(1, max_overview_nodes)
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
    reserve = 1 if any(component_links.values()) and limit > 1 else 0
    deduplicated = list({item.key: item for item in candidates}.values())
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

    allocated = {key for values in component_links.values() for key in values}
    orphan_count = len([item for item in context.entities("component") if item.key not in allocated])
    if reserve and len(nodes) < limit:
        summary_id = "functional:allocation-summary"
        nodes.append(DiagramNode(summary_id, "System Allocation", "system", status="summary", badges=[f"components:{len(allocated)}", f"unallocated:{orphan_count}"]))
        for capability in selected:
            if component_links[capability.key]:
                evidence = _derived("allocation-summary", [capability.key, *component_links[capability.key]], count=len(component_links[capability.key]))
                edges.append(DiagramEdge(_node_id(capability.key), summary_id, "allocation", style="dashed", evidence=[evidence], count=len(component_links[capability.key])))
    if orphan_count:
        groups.append(DiagramGroup("functional:orphans", f"Unallocated Functions ({orphan_count})", "warning", order=99))
    omitted = len(deduplicated) - len(selected)
    if omitted:
        warnings.append(Diagnostic("warning", "FUNCTIONAL_OVERVIEW_BOUNDED", f"{omitted} functional blocks omitted (limit {limit})", view="functional"))
    if not nodes:
        nodes.append(DiagramNode("functional:empty", "Functional architecture unavailable", "warning"))
        warnings.append(Diagnostic("warning", "FUNCTIONAL_SPARSE_FALLBACK", "No capabilities were available", view="functional"))
    spec = DiagramSpec(
        "functional", "Functional Architecture", direction="TB", nodes=nodes, edges=edges, groups=groups,
        warnings=[*context.diagnostics, *warnings], drilldowns=drilldowns,
        provenance=DiagramProvenance("architecture-view-context", [item.key for item in roots],
                                     context={"curated": curation != ViewCuration(), "max_overview_nodes": limit}),
    )
    spec.validate()
    return spec


__all__ = ["DEFAULT_MAX_OVERVIEW_NODES", "project_conops", "project_functional_architecture"]
