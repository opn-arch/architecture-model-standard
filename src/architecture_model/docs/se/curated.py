"""Markdown projections of the same curated artifact context used by native views."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Iterable

from architecture_model.core.diagram_spec import DiagramEdge, DiagramNode, DiagramProvenance, DiagramSpec


def _text(value: object) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split()) or "—"


def _cell(value: object) -> str:
    return _text(value).replace("\\", "\\\\").replace("|", "\\|")


def _values(values: Iterable[object]) -> str:
    result = [_text(value) for value in values if value]
    return "; ".join(result) if result else "—"


def _evidence(values: Iterable[DiagramProvenance]) -> str:
    parts: list[str] = []
    for value in values:
        files = list(value.source_files)
        refs = list(value.entity_refs)
        item = value.source or "evidence"
        if files:
            item += f": {', '.join(files)}"
        if refs:
            item += f" ({', '.join(refs)})"
        if item not in parts:
            parts.append(item)
    return _values(parts)


def _curation_evidence(values: Iterable[Any]) -> str:
    return _values(f"{item.source}: {item.claim}" for item in values)


def _node_map(spec: DiagramSpec) -> dict[str, DiagramNode]:
    return {node.id: node for node in spec.nodes}


def _drilldown(spec: DiagramSpec, node: DiagramNode) -> DiagramSpec | None:
    return next((item.spec for item in spec.drilldowns if item.id == node.drilldown_ref), None)


def _status(view: dict[str, Any]) -> list[str]:
    curation = view["curation"]
    warnings = view["spec"].warnings
    lines = ["## Curation Status", "", f"This narrative is **{_text(curation['status'])}** and is projected from the same view specification as the generated SVG."]
    lines.append(f"Curation source: `{_text(curation['path'])}`.")
    if warnings:
        lines.append("Evidence diagnostics: " + "; ".join(_text(item.message) for item in warnings) + ".")
    lines.append("Inferred statements are explicitly marked and are not canonical model facts.")
    lines.append("")
    return lines


def _badge(node: DiagramNode, name: str) -> str:
    prefix = f"{name}:"
    return next((badge[len(prefix):] for badge in node.badges if badge.startswith(prefix)), "0")


def _entity(context: Any, reference: str) -> Any | None:
    return context.entity(reference, diagnose=False) if reference else None


def _scenario_members(context: Any, scenario: Any, entity_type: str) -> list[Any]:
    return [item for key in scenario.members if (item := _entity(context, key)) and item.entity_type == entity_type]


def render_conops(model: Any, view: dict[str, Any], diagram_reference: str) -> str:
    spec, context, curation = view["spec"], view["context"], view["view_curation"]
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    curated_scenarios = {item.id: item for item in curation.scenarios}
    scenario_nodes = [node for node in spec.nodes if node.kind == "scenario"]
    scenarios = [
        curated_scenarios.get(node.id) or SimpleNamespace(
            id=node.id, label=node.label, goal=node.subtitle,
            members=[node.entity_ref] if node.entity_ref else [], outcomes=[],
            requirements=[], moes=[], evidence=[],
        )
        for node in scenario_nodes
    ]
    lines = [f"# Concept of Operations: {project}", "", "## System Overview", ""]
    lines.append(f"{project} operates through {len(scenarios)} curated operational scenarios: {_values(item.label for item in scenarios)}.")
    lines.extend(["", diagram_reference, "", *_status(view), "## Stakeholders", "", "| Stakeholder | Type | Status | Goals / Role | Evidence |", "|---|---|---|---|---|"])
    for actor in context.entities("actor"):
        lines.append(f"| {_cell(actor.name)} | {_cell(getattr(actor.value, 'type', 'actor'))} | Canonical | {_cell(_values(actor.value.goals))} | {_cell(actor.source_path)} |")
    for external in curation.externals:
        lines.append(f"| {_cell(external.name)} | {_cell(external.kind or 'external')} | **Inferred** | External operational source | {_cell(_curation_evidence(external.evidence))} |")
    lines.extend(["", "## Operational Scenarios", ""])
    for scenario in scenarios:
        node = next(node for node in spec.nodes if node.id == scenario.id)
        behaviors = _scenario_members(context, scenario, "behavior")
        explicit_systems = _scenario_members(context, scenario, "system")
        detail = _drilldown(spec, node)
        systems = [item for item in (detail.nodes if detail else []) if item.kind == "system"]
        interfaces = [item for item in (detail.nodes if detail else []) if item.kind == "interface"]
        failures = [item.label for item in (detail.nodes if detail else []) if item.kind in {"failure", "error"}]
        incoming = [edge for edge in spec.edges if edge.target == scenario.id and edge.source != scenario.id]
        outgoing = [edge for edge in spec.edges if edge.source == scenario.id and edge.target != scenario.id]
        lines.extend([f"### {scenario.label}", "", f"**Goal:** {_text(node.subtitle or scenario.goal)}{' **(Inferred)**' if node.inferred else ''}"])
        lines.append(f"**Member use cases:** {_values(item.name for item in behaviors)}")
        lines.append(f"**Participating systems:** {_values([item.label for item in systems] or [item.name for item in explicit_systems])}")
        lines.append(f"**Inputs / external sources:** {_values(f'{_node_map(spec).get(edge.source, DiagramNode('', '', '')).label}: {edge.title or edge.label or edge.kind}' for edge in incoming if edge.kind != 'allocation')}")
        lines.append(f"**Outputs / outcomes:** {_values([*scenario.outcomes, *(edge.title or edge.label for edge in outgoing if edge.kind not in {'allocation'})])}")
        lines.append(f"**Interfaces:** {_values(item.label for item in interfaces)}")
        requirements = sorted({value for item in behaviors for value in item.value.requirements})
        moes = sorted({value for item in behaviors for value in item.value.moes})
        lines.append(f"**Requirements / MoEs:** {_values([*scenario.requirements, *requirements, *scenario.moes, *moes])}")
        lines.append(f"**Degraded / failure modes:** {_values(failures or [value for item in behaviors for value in item.value.failure_modes])}")
        lines.append(f"**Evidence / provenance:** {_curation_evidence(scenario.evidence)}; {_evidence(node.evidence)}")
        lines.append("")
    boundary = next((node for node in spec.nodes if node.id == "conops:system-boundary"), None)
    boundary_detail = _drilldown(spec, boundary) if boundary else None
    lines.extend(["## System Context", "", "| Participating System | Boundary Exchanges | Evidence |", "|---|---|---|"])
    exchanges = [edge for edge in spec.edges if edge.kind in {"exchange", "operational-flow", "data-flow"}]
    for system in (boundary_detail.nodes if boundary_detail else []):
        lines.append(f"| {_cell(system.label)} | {_cell(_values(edge.title or edge.label or edge.kind for edge in exchanges))} | {_cell(_evidence(system.evidence))} |")
    lines.extend(["", "| Exchange Source | Exchange Target | Kind | Data / Exchange | Evidence |", "|---|---|---|---|---|"])
    nodes = _node_map(spec)
    for edge in spec.edges:
        lines.append(f"| {_cell(nodes[edge.source].label)} | {_cell(nodes[edge.target].label)} | {_cell(edge.kind)} | {_cell(edge.title or edge.label)}{' **(Inferred)**' if edge.inferred else ''} | {_cell(_evidence(edge.evidence))} |")
    lines.extend(["", "## Operational Outcomes", ""])
    outcome = next((node for node in spec.nodes if node.id == "conops:outcomes"), None)
    outcome_detail = _drilldown(spec, outcome) if outcome else None
    for item in (outcome_detail.nodes if outcome_detail else []):
        marker = " **(Inferred)**" if item.inferred else ""
        lines.append(f"- **{_text(item.subtitle)}:** {_text(item.label)}{marker} [{_evidence(item.evidence)}]")
    return "\n".join(lines)


def render_functional(model: Any, view: dict[str, Any], diagram_reference: str) -> str:
    spec, context, curation = view["spec"], view["context"], view["view_curation"]
    project = getattr(model.meta, "project", "") or "System"
    groups = {item.id: item for item in curation.groups}
    lines = [f"# Functional Analysis: {project}", "", diagram_reference, "", *_status(view), "## Capability Inventory and Decomposition", ""]
    for node in spec.nodes:
        group = groups.get(node.id)
        if node.kind != "functional-block" or not group:
            continue
        lines.extend([f"### {node.label}", "", f"Badges: {_values(node.badges)}.", "", "| Member Capability | Intent / Description | Allocation | Requirements / MoEs | Failure / Monitoring | Evidence |", "|---|---|---|---|---|---|"])
        for reference in group.members:
            capability = _entity(context, reference)
            if not capability:
                continue
            components = [context.entity(rel.source, diagnose=False) for rel in context.incoming(reference, "realizes")]
            components = [item for item in components if item]
            lines.append(f"| {_cell(capability.name)} | {_cell(capability.value.intent or capability.value.description)} | {_cell(_values(item.name for item in components))} | {_cell(_values([*capability.value.requirements, *capability.value.moes]))} | {_cell(_values([*capability.value.failure_modes, *capability.value.monitored]))} | {_cell(capability.source_path)} |")
        lines.append("")
    nodes = _node_map(spec)
    lines.extend(["## Functional Flows", "", "| Source | Target | Kind | Data / Exchange | Evidence |", "|---|---|---|---|---|"])
    for edge in spec.edges:
        lines.append(f"| {_cell(nodes[edge.source].label)} | {_cell(nodes[edge.target].label)} | {_cell(edge.kind)} | {_cell(edge.title or edge.label)}{' **(Inferred)**' if edge.inferred else ''} | {_cell(_evidence(edge.evidence))} |")
    total = len(context.entities("capability"))
    represented = {member for group in groups.values() for member in group.members}
    lines.extend(["", "## Appendix: Overview Omissions", "", f"The hierarchy contains {total} raw capabilities. The curated overview represents {len(represented)} member capabilities in {len(spec.nodes)} functional blocks; {max(0, total - len(represented))} capabilities are omitted from the primary view and remain available in model and drilldown detail.", ""])
    return "\n".join(lines)


def render_logical(model: Any, view: dict[str, Any], diagram_reference: str) -> str:
    spec = view["spec"]
    project = getattr(model.meta, "project", "") or "System"
    by_lane = {lane.id: [] for lane in spec.lanes}
    for node in spec.nodes:
        by_lane.setdefault(node.lane, []).append(node)
    lines = [f"# Logical Architecture: {project}", "", diagram_reference, "", *_status(view), "## Logical Tiers and Systems", ""]
    for lane in spec.lanes:
        lines.extend([f"### {lane.label}", "", "| System / Aggregate | Kind | Badges | Monitoring / Failures | Drilldown |", "|---|---|---|---|---|"])
        for node in by_lane.get(lane.id, []):
            health = f"monitoring:{node.metrics.get('monitoring', 0)}; failures:{node.metrics.get('failures', 0)}"
            if "No cross-system dependency" in node.badges:
                health += "; isolate"
            lines.append(f"| {_cell(node.label)} | {_cell(node.kind)} | {_cell(_values(node.badges))} | {_cell(health)} | `{_cell(node.drilldown_ref)}` |")
        lines.append("")
    nodes = _node_map(spec)
    facet = spec.facets.get("logical_dependencies", {})
    lines.extend(["## Cross-System Dependency and Interface Backbone", "", f"The overview displays {len(spec.edges)} of {facet.get('full_count', len(spec.edges))} relationships; full dependencies live in system drilldowns.", "", "| Source | Target | Kind | Exchange / Badge | Evidence |", "|---|---|---|---|---|"])
    for edge in spec.edges:
        marker = "cycle" if edge.style == "cycle" else "critical" if edge.critical else edge.title or edge.label
        lines.append(f"| {_cell(nodes[edge.source].label)} | {_cell(nodes[edge.target].label)} | {_cell(edge.kind)} | {_cell(marker)} | {_cell(_evidence(edge.evidence))} |")
    lines.append("")
    return "\n".join(lines)


def render_use_cases(model: Any, view: dict[str, Any], diagram_reference: str) -> str:
    spec, context, curation = view["spec"], view["context"], view["view_curation"]
    project = getattr(model.meta, "project", "") or "System"
    case_nodes = [node for node in spec.nodes if node.kind == "use-case"]
    cases = {node.entity_ref: node for node in case_nodes}
    annotations = {item.use_case: item for item in curation.annotations}
    associations: dict[str, list[Any]] = {}
    for item in curation.associations:
        associations.setdefault(item.actor, []).append(item)
    actors: dict[str, tuple[str, bool, str]] = {}
    for actor in curation.actors:
        actors[actor.id] = (actor.name, True, _curation_evidence(actor.evidence))
    for reference in cases:
        behavior = _entity(context, reference)
        actor_ref = behavior.value.actor_id or behavior.value.actor if behavior else ""
        actor = next((item for item in context.entities("actor") if actor_ref in {item.local_id, item.name, item.key}), None)
        if actor:
            actors[actor.key] = (actor.name, False, actor.source_path)
    canonical_names: set[str] = set()
    for actor in context.entities("actor"):
        participating = [
            node.label for reference, node in cases.items()
            if (behavior := _entity(context, reference))
            and (behavior.value.actor_id or behavior.value.actor) in {actor.key, actor.local_id, actor.name}
        ]
        if participating or actor.name not in canonical_names:
            actors[actor.key] = (actor.name, False, actor.source_path)
            canonical_names.add(actor.name)
    lines = [f"# Use Cases: {project}", "", diagram_reference, "", *_status(view), "## Actor-Goal Matrix", "", "| Actor | Status | Featured Use Cases / Goals | Evidence |", "|---|---|---|---|"]
    for key, (name, inferred, evidence) in actors.items():
        linked = []
        for association in associations.get(key, []):
            linked.extend(cases[ref].label for ref in association.use_cases if ref in cases)
        if not inferred:
            linked.extend(node.label for ref, node in cases.items() if (behavior := _entity(context, ref)) and (behavior.value.actor_id or behavior.value.actor) in {key, key.split("::")[-1], name})
        lines.append(f"| {_cell(name)} | {'**Inferred**' if inferred else 'Canonical'} | {_cell(_values(dict.fromkeys(linked)))} | {_cell(evidence)} |")
    lines.extend(["", "## Featured Use Case Catalog", ""])
    for node in case_nodes:
        behavior = _entity(context, node.entity_ref)
        detail = _drilldown(spec, node)
        annotation = annotations.get(node.entity_ref)
        fields = {
            "Goal": next(iter(behavior.value.goals), "") if behavior else "",
            "Trigger": behavior.value.trigger if behavior else "",
            "Preconditions": _values(behavior.value.preconditions) if behavior and behavior.value.preconditions else "",
            "Postconditions": _values(behavior.value.postconditions) if behavior and behavior.value.postconditions else "",
            "Success Outcome": _values(behavior.value.postconditions or behavior.value.goals) if behavior else "",
            "MoE": _values(behavior.value.moes) if behavior and behavior.value.moes else "",
        }
        fallbacks = {
            "Goal": annotation.goal if annotation else "", "Trigger": annotation.trigger if annotation else "",
            "Preconditions": _values(annotation.preconditions) if annotation else "",
            "Postconditions": _values(annotation.postconditions) if annotation else "",
            "Success Outcome": annotation.success_outcome if annotation else "",
            "MoE": _values(annotation.moes) if annotation else "",
        }
        lines.extend([f"### UC: {node.label}", "", f"**ID:** `{_text(node.entity_ref)}`"])
        for label, canonical in fields.items():
            inferred = not canonical and bool(fallbacks[label])
            lines.append(f"**{label}:** {_text(canonical or fallbacks[label])}{' **(Inferred)**' if inferred else ''}")
        lines.append(f"**Implementing systems:** {_text(node.metrics.get('implementing_systems'))}")
        steps = sorted(behavior.value.structured_steps, key=lambda item: item.order) if behavior else []
        lines.append("**Canonical structured steps / components:**")
        for step in steps:
            lines.append(f"{step.order}. {_text(step.action)} [{_text(step.component_ref)}] input={_text(step.input)}; output={_text(step.output)}")
        support = [item for item in (detail.nodes if detail else []) if item.kind in {"requirement", "error", "failure"}]
        lines.append(f"**Requirements and failure/error evidence:** {_values(item.label for item in support)}")
        lines.append(f"**Evidence / provenance:** {_evidence(node.evidence)}; {_curation_evidence(annotation.evidence) if annotation else '—'}")
        lines.append(f"**Drilldown:** `{_text(node.drilldown_ref)}`")
        lines.append("")
    omitted = next((item for item in spec.callouts if item.kind == "omitted-count"), None)
    omitted_count = len(omitted.evidence) if omitted else max(0, len(context.entities("behavior")) - len(case_nodes))
    lines.extend(["## Appendix: Overview Omissions", "", f"{omitted_count} nonfeatured use cases are omitted from the primary catalog and remain available in the model overview/drilldowns.", ""])
    return "\n".join(lines)
