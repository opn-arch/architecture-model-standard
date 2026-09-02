import random
from pathlib import Path

import pytest

from architecture_model.core.parser import load_model
from architecture_model.core.se_view_projectors import project_logical_architecture
from architecture_model.core.view_context import ArchitectureViewContext
from architecture_model.core.view_curation import CuratedGroup, Selector, ViewCuration


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _context(tmp_path: Path, inline_count: int = 4, actor_count: int = 1) -> ArchitectureViewContext:
    inline = "\n".join(
        f"    - {{id: INLINE-{index}, name: {'Contract' if index % 2 else 'Worker'} {index}, status: ACTIVE, "
        f"layer: {'data' if index % 2 else 'services'}, files: [src/{'contracts' if index % 2 else 'workers'}/{index}.py]}}"
        for index in range(inline_count)
    )
    actors = "\n".join(
        f"    - {{id: ACT-{index + 1}, name: Operator {index + 1}, status: ACTIVE}}"
        for index in range(actor_count)
    )
    _write(tmp_path / ".architecture-model.yaml", f"""meta: {{project: logical, schema_version: '2.0'}}
entities:
  actors:
{actors}
  external_systems:
    - {{id: EXT-1, name: Identity Provider, status: ACTIVE}}
  systems:
    - {{id: SYS-WEB, name: Web Gateway, status: ACTIVE, layer: web, sub_model_ref: .architecture-models/web/.architecture-model.yaml}}
    - {{id: SYS-DOMAIN, name: Domain Engine, status: ACTIVE, layer: services, sub_model_ref: .architecture-models/domain/.architecture-model.yaml}}
  components:
{inline}
relationships:
  - {{from: web::COMP-1, to: domain::COMP-1, type: depends-on, strength: strong}}
  - {{from: web::COMP-1, to: domain::COMP-1, type: produces}}
  - {{from: domain::COMP-1, to: web::COMP-1, type: depends-on}}
  - {{from: ACT-1, to: web::IF-1, type: consumes}}
""")
    _write(tmp_path / ".architecture-models/web/.architecture-model.yaml", """meta: {project: web, schema_version: '2.0'}
entities:
  layers:
    - {id: L-WEB, name: Web, status: ACTIVE, order: 1, directories: [src/web]}
  components:
    - {id: COMP-1, name: Gateway, status: ACTIVE, layer: L-WEB, files: [src/web/gateway.py], failure_modes: [timeout], monitored: [latency]}
  interfaces:
    - {id: IF-1, name: Public API, status: ACTIVE, provider: COMP-1, consumer: ACT-1, protocol: HTTPS}
  capabilities:
    - {id: CAP-1, name: Accept Requests, status: ACTIVE, requirements: [REQ-1]}
  requirements:
    - {id: REQ-1, name: Fast ingress, status: ACTIVE}
relationships:
  - {from: COMP-1, to: IF-1, type: exposes}
  - {from: COMP-1, to: CAP-1, type: realizes}
""")
    _write(tmp_path / ".architecture-models/domain/.architecture-model.yaml", """meta: {project: domain, schema_version: '2.0'}
entities:
  components:
    - {id: COMP-1, name: Rules Service, status: ACTIVE, files: [src/domain/rules.py]}
    - {id: COMP-2, name: Event Store, status: ACTIVE, kind: repository, files: [src/data/store.py]}
  interfaces:
    - {id: IF-1, name: Rules API, status: ACTIVE, provider: COMP-1, consumer: web::COMP-1, protocol: gRPC}
  capabilities:
    - {id: CAP-1, name: Apply Rules, status: ACTIVE}
relationships:
  - {from: COMP-1, to: IF-1, type: exposes}
  - {from: COMP-1, to: COMP-2, type: depends-on}
  - {from: COMP-1, to: CAP-1, type: realizes}
""")
    return ArchitectureViewContext.load(load_model(tmp_path / ".architecture-model.yaml"), tmp_path)


def _nested_specs(spec):
    result = [spec]
    for drilldown in spec.drilldowns:
        if drilldown.spec:
            result.extend(_nested_specs(drilldown.spec))
    return result


def _assert_hidden_and_edges_safe(spec, hidden_ref: str) -> None:
    for nested in _nested_specs(spec):
        assert all(node.entity_ref != hidden_ref for node in nested.nodes)
        node_ids = {node.id for node in nested.nodes}
        assert all(edge.source in node_ids and edge.target in node_ids for edge in nested.edges)


def test_logical_projects_tiered_systems_aggregates_and_semantic_exchanges(tmp_path):
    context = _context(tmp_path)
    spec = project_logical_architecture(context)
    spec.validate()

    systems = {node.entity_ref: node for node in spec.nodes if node.kind == "system"}
    assert {"root::SYS-WEB", "root::SYS-DOMAIN"} <= systems.keys()
    assert {"components:1", "interfaces:1", "capabilities:1"} <= set(systems["root::SYS-WEB"].badges)
    assert all(node.group and node.drilldown_ref for node in systems.values())
    assert any(node.kind == "aggregate" and node.metrics["members"] for node in spec.nodes)
    assert all(group.label != "Other" for group in spec.groups)

    exchanges = [edge for edge in spec.edges if edge.kind in {"depends-on", "produces"}]
    assert len([edge for edge in exchanges if edge.kind == "depends-on"]) == 2
    assert len([edge for edge in exchanges if edge.kind == "produces"]) == 1
    assert all(edge.evidence for edge in spec.edges)
    assert all(edge.count == 1 for edge in exchanges)
    assert all(edge.style == "cycle" for edge in exchanges if edge.kind == "depends-on")
    assert any(edge.critical for edge in exchanges)
    assert any(node.kind == "interface" and node.entity_ref == "web::IF-1" for node in spec.nodes)


def test_logical_system_drilldown_contains_layers_components_interfaces_and_facets(tmp_path):
    spec = project_logical_architecture(_context(tmp_path))
    system = next(node for node in spec.nodes if node.entity_ref == "root::SYS-WEB")
    detail = next(item.spec for item in spec.drilldowns if item.id == system.drilldown_ref)
    assert detail is not None
    assert {"web::COMP-1", "web::IF-1", "web::CAP-1", "web::REQ-1"} <= {
        node.entity_ref for node in detail.nodes
    }
    assert any(group.kind == "tier" for group in detail.groups)
    assert any(edge.kind == "exposes" for edge in detail.edges)
    component = next(node for node in detail.nodes if node.entity_ref == "web::COMP-1")
    assert {"monitoring:1", "failures:1"} <= set(component.badges)
    assert all(edge.evidence for edge in detail.edges)


def test_logical_curation_controls_tiers_labels_aggregation_hiding_and_drilldown(tmp_path):
    context = _context(tmp_path)
    aggregate = CuratedGroup(
        "workers", "Background Workers", "aggregate", order=4,
        members=["root::INLINE-0", "root::INLINE-2"],
    )
    curation = ViewCuration(
        tiers=[CuratedGroup("custom-domain", "Business Tier", "tier", order=1, members=["root::SYS-DOMAIN"])],
        groups=[aggregate],
        aggregate_components=[
            Selector(qualified_id="root::INLINE-0", resolved_id="root::INLINE-0"),
            Selector(qualified_id="root::INLINE-2", resolved_id="root::INLINE-2"),
        ],
        hide=[Selector(qualified_id="root::INLINE-1", resolved_id="root::INLINE-1")],
        labels={"root::SYS-DOMAIN": "Policy Core"},
        order=["root::SYS-DOMAIN", "root::SYS-WEB"],
        drilldowns={"domain-detail": Selector(qualified_id="root::SYS-DOMAIN", resolved_id="root::SYS-DOMAIN")},
    )
    spec = project_logical_architecture(context, curation)
    domain = next(node for node in spec.nodes if node.entity_ref == "root::SYS-DOMAIN")
    workers = next(node for node in spec.nodes if node.group == "workers")
    assert domain.label == "Policy Core" and domain.group == "custom-domain"
    assert domain.drilldown_ref == "domain-detail"
    assert workers.kind == "aggregate" and workers.metrics["members"] == "root::INLINE-0, root::INLINE-2"
    assert all(node.entity_ref != "root::INLINE-1" for node in spec.nodes)


def test_logical_is_globally_bounded_deterministic_and_omissions_are_drillable(tmp_path):
    context = _context(tmp_path, inline_count=24, actor_count=20)
    first = project_logical_architecture(context).to_dict()
    random.Random(13).shuffle(context.models["root"].entities.components)
    random.Random(19).shuffle(context.models["root"].relationships)
    second = project_logical_architecture(ArchitectureViewContext(context.root, context.models, [])).to_dict()
    assert len(first["nodes"]) <= 15
    assert first == second
    summary = next(node for node in first["nodes"] if node["status"] == "omitted")
    drilldown = next(item for item in first["drilldowns"] if item["id"] == summary["drilldown_ref"])
    assert drilldown["spec"]["nodes"]
    assert any(item["code"] == "LOGICAL_OVERVIEW_BOUNDED" for item in first["warnings"])


def test_logical_qualified_ids_keep_duplicate_local_components_safe(tmp_path):
    spec = project_logical_architecture(_context(tmp_path))
    details = [item.spec for item in spec.drilldowns if item.spec]
    refs = {node.entity_ref for detail in details for node in detail.nodes}
    assert "web::COMP-1" in refs and "domain::COMP-1" in refs


def test_logical_dense_drilldown_has_actual_omitted_entity_drilldown(tmp_path):
    context = _context(tmp_path)
    template = context.models["web"].entities.components[0]
    from copy import deepcopy
    for index in range(40):
        component = deepcopy(template)
        component.id = f"DENSE-{index}"
        component.name = f"Dense Component {index}"
        context.models["web"].entities.components.append(component)
    context = ArchitectureViewContext(context.root, context.models, [])
    spec = project_logical_architecture(context)
    system = next(node for node in spec.nodes if node.entity_ref == "root::SYS-WEB")
    detail = next(item.spec for item in spec.drilldowns if item.id == system.drilldown_ref)
    summary = next(node for node in detail.nodes if node.status == "omitted")
    omitted = next(item.spec for item in detail.drilldowns if item.id == summary.drilldown_ref)
    assert omitted and omitted.nodes


def test_logical_aggregated_exchange_reports_count_and_label(tmp_path):
    context = _context(tmp_path)
    from copy import deepcopy
    context.models["root"].relationships.append(deepcopy(context.models["root"].relationships[0]))
    spec = project_logical_architecture(ArchitectureViewContext(context.root, context.models, []))
    edge = next(
        edge for edge in spec.edges
        if edge.kind == "depends-on" and edge.source == "node:root::SYS-WEB"
    )
    assert edge.count == 2
    assert edge.label == "depends-on (2)"


def test_logical_saturated_budget_keeps_cross_system_interface_path_atomic(tmp_path):
    spec = project_logical_architecture(
        _context(tmp_path, inline_count=20, actor_count=20),
        max_overview_nodes=4,
    )
    refs = {node.entity_ref for node in spec.nodes}
    interface = next(node for node in spec.nodes if node.entity_ref == "domain::IF-1")
    assert len(spec.nodes) <= 4
    assert {"root::SYS-WEB", "root::SYS-DOMAIN", "domain::IF-1"} <= refs
    ports = [edge for edge in spec.edges if edge.kind == "interface-port" and interface.id in {edge.source, edge.target}]
    assert {edge.source for edge in ports} == {"node:root::SYS-WEB", "node:root::SYS-DOMAIN"}
    assert all(node.kind != "interface" or len([
        edge for edge in spec.edges if node.id in {edge.source, edge.target}
    ]) >= 2 for node in spec.nodes)


def test_logical_hidden_priority_interface_does_not_reserve_connected_systems(tmp_path):
    context = _context(tmp_path, inline_count=20, actor_count=20)
    hidden = Selector(qualified_id="domain::IF-1", resolved_id="domain::IF-1")
    spec = project_logical_architecture(
        context,
        ViewCuration(hide=[hidden]),
        max_overview_nodes=4,
    )
    context.models["domain"].entities.interfaces = [
        item for item in context.models["domain"].entities.interfaces if item.id != "IF-1"
    ]
    without_interface = project_logical_architecture(
        ArchitectureViewContext(context.root, context.models, []),
        max_overview_nodes=4,
    )

    refs = {node.entity_ref for node in spec.nodes}
    assert len(spec.nodes) <= 4
    assert "domain::IF-1" not in refs
    assert all("node:domain::IF-1" not in {edge.source, edge.target} for edge in spec.edges)
    assert {
        node.entity_ref for node in spec.nodes if node.kind == "system"
    } == {
        node.entity_ref for node in without_interface.nodes if node.kind == "system"
    }


def test_logical_hidden_nonpriority_interface_never_renders_indirectly(tmp_path):
    hidden = Selector(qualified_id="web::IF-1", resolved_id="web::IF-1")
    spec = project_logical_architecture(
        _context(tmp_path),
        ViewCuration(hide=[hidden]),
        max_overview_nodes=10,
    )

    nested_specs = [spec]
    for drilldown in spec.drilldowns:
        if drilldown.spec:
            nested_specs.append(drilldown.spec)
            nested_specs.extend(item.spec for item in drilldown.spec.drilldowns if item.spec)
    assert all(
        node.entity_ref != "web::IF-1"
        for nested in nested_specs for node in nested.nodes
    )
    assert all(
        "node:web::IF-1" not in {edge.source, edge.target}
        for nested in nested_specs for edge in nested.edges
    )
    assert all(
        not (edge.kind == "consumes" and edge.target == "node:root::SYS-WEB")
        for edge in spec.edges
    )
    web = next(node for node in spec.nodes if node.entity_ref == "root::SYS-WEB")
    assert "interfaces:0" in web.badges


@pytest.mark.parametrize("hidden_ref", [
    "root::ACT-1",
    "root::EXT-1",
    "root::SYS-WEB",
    "web::COMP-1",
    "web::CAP-1",
    "web::IF-1",
    "web::REQ-1",
])
def test_logical_hide_applies_recursively_per_entity_type(tmp_path, hidden_ref):
    hidden = Selector(qualified_id=hidden_ref, resolved_id=hidden_ref)
    spec = project_logical_architecture(_context(tmp_path), ViewCuration(hide=[hidden]))

    _assert_hidden_and_edges_safe(spec, hidden_ref)


def test_logical_hide_applies_to_presentation_groups_and_membership(tmp_path):
    aggregate = CuratedGroup(
        "workers", "Background Workers", "aggregate",
        members=["root::INLINE-0", "root::INLINE-2"],
    )
    curation = ViewCuration(
        groups=[aggregate],
        aggregate_components=[
            Selector(qualified_id="root::INLINE-0", resolved_id="root::INLINE-0"),
            Selector(qualified_id="root::INLINE-2", resolved_id="root::INLINE-2"),
        ],
        hide=[Selector(qualified_id="workers")],
    )
    spec = project_logical_architecture(_context(tmp_path), curation)

    assert all(group.id != "workers" for nested in _nested_specs(spec) for group in nested.groups)
    assert all(node.group != "workers" for nested in _nested_specs(spec) for node in nested.nodes)
