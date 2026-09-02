from pathlib import Path

import pytest

from architecture_model.core.parser import load_model
from architecture_model.core.view_context import ArchitectureViewContext
from architecture_model.core.view_curation import CuratedExternal, CuratedFlow, CuratedGroup, EvidenceRecord, Selector, ViewCuration, load_viewer_curation
from architecture_model.core.se_view_projectors import project_conops


def _context(tmp_path: Path, *, behaviors: int = 1) -> ArchitectureViewContext:
    behavior_rows = "\n".join(
        f"    - {{id: BEH-{index}, name: Operate {index}, status: ACTIVE, actor_id: ACT-1, capability_id: CAP-1, trigger: Request {index}, goals: [Goal {index}], postconditions: [Outcome {index}], interface_refs: [IF-1], moes: [Latency], failure_modes: [Timeout], monitored: [success_rate]}}"
        for index in range(behaviors)
    )
    path = tmp_path / ".architecture-model.yaml"
    path.write_text(f"""meta: {{project: conops, schema_version: '2.0'}}
entities:
  actors:
    - {{id: ACT-1, name: Operator, status: ACTIVE}}
    - {{id: ACT-2, name: Observer, status: ACTIVE}}
  capabilities:
    - {{id: CAP-1, name: Mission, status: ACTIVE}}
  behaviors:
{behavior_rows or '    []'}
  interfaces:
    - {{id: IF-1, name: Command API, status: ACTIVE, provider: SYS-1, consumer: ACT-1}}
  systems:
    - {{id: SYS-1, name: Mission System, status: ACTIVE}}
relationships:
  - {{from: ACT-1, to: IF-1, type: consumes}}
  - {{from: SYS-1, to: IF-1, type: exposes}}
""", encoding="utf-8")
    return ArchitectureViewContext.load(load_model(path), tmp_path)


def test_conops_uses_semantic_actor_path_and_never_fabricates_cartesian_edges(tmp_path):
    spec = project_conops(_context(tmp_path))
    spec.validate()

    nodes = {node.entity_ref: node for node in spec.nodes if node.entity_ref}
    assert {lane.id for lane in spec.lanes} == {"actors", "scenarios", "boundary", "outcomes"}
    assert "root::ACT-1" in nodes and "root::IF-1" in nodes and "root::SYS-1" in nodes
    assert any(edge.source == nodes["root::ACT-1"].id and edge.target == nodes["root::IF-1"].id for edge in spec.edges)
    observer = nodes["root::ACT-2"]
    assert all(edge.source != observer.id and edge.target != observer.id for edge in spec.edges)
    assert all(edge.evidence for edge in spec.edges)
    scenario = next(node for node in spec.nodes if node.kind == "scenario")
    assert {"requirements:0", "moes:1", "failures:1", "monitoring:1"} <= set(scenario.badges)
    assert scenario.drilldown_ref


def test_conops_bounds_primary_nodes_deterministically_and_reports_sparse_fallback(tmp_path):
    context = _context(tmp_path, behaviors=25)
    first = project_conops(context).to_dict()
    second = project_conops(context).to_dict()
    assert first == second
    assert len(first["nodes"]) <= 15
    assert any(item["code"] == "CONOPS_OVERVIEW_BOUNDED" for item in first["warnings"])

    sparse_path = tmp_path / "sparse" / ".architecture-model.yaml"
    sparse_path.parent.mkdir()
    sparse_path.write_text("meta: {project: sparse, schema_version: '2.0'}\nentities: {}\nrelationships: []\n", encoding="utf-8")
    sparse = ArchitectureViewContext.load(load_model(sparse_path), sparse_path.parent)
    result = project_conops(sparse)
    result.validate()
    assert result.nodes
    assert any(item.code == "CONOPS_SPARSE_FALLBACK" for item in result.warnings)


def test_conops_curated_inferred_external_is_styled_and_evidence_backed_without_model_mutation(tmp_path):
    context = _context(tmp_path)
    before = len(context.entities("external_system"))
    curation = ViewCuration(externals=[CuratedExternal(
        "EXT-INFERRED", "Telemetry Vendor", True,
        [EvidenceRecord("docs/evidence.md", "Observed telemetry exchange")],
    )])

    spec = project_conops(context, curation)
    external = next(node for node in spec.nodes if node.id == "EXT-INFERRED")
    assert external.kind == "external" and external.inferred
    assert external.status == "inferred" and external.evidence
    assert len(context.entities("external_system")) == before


def test_conops_root_system_summarizes_qualified_submodel_operations(tmp_path):
    root = tmp_path / ".architecture-model.yaml"
    root.write_text("""meta: {project: root, schema_version: '2.0'}
entities:
  systems:
    - {id: SYS-A, name: Alpha, status: ACTIVE, sub_model_ref: .architecture-models/a/.architecture-model.yaml}
    - {id: SYS-B, name: Beta, status: ACTIVE, sub_model_ref: .architecture-models/b/.architecture-model.yaml}
relationships: []
""", encoding="utf-8")
    for name in ("a", "b"):
        path = tmp_path / f".architecture-models/{name}/.architecture-model.yaml"
        path.parent.mkdir(parents=True)
        path.write_text(f"""meta: {{project: {name}, schema_version: '2.0'}}
entities:
  capabilities: [{{id: CAP-1, name: {name} capability, status: ACTIVE}}]
  behaviors: [{{id: BEH-1, name: {name} scenario, status: ACTIVE, capability_id: CAP-1}}]
relationships: []
""", encoding="utf-8")

    spec = project_conops(ArchitectureViewContext.load(load_model(root), tmp_path))
    systems = {node.entity_ref: node for node in spec.nodes if node.kind == "system"}
    assert systems["root::SYS-A"].badges == ["capabilities:1", "behaviors:1"]
    assert systems["root::SYS-B"].badges == ["capabilities:1", "behaviors:1"]
    assert {node.entity_ref for node in spec.nodes if node.kind == "scenario"} >= {"a::BEH-1", "b::BEH-1"}


def test_conops_global_bound_keeps_interface_system_path_atomic(tmp_path):
    spec = project_conops(_context(tmp_path, behaviors=12), max_overview_nodes=7)
    assert len(spec.nodes) <= 7
    refs = {node.entity_ref for node in spec.nodes}
    assert ("root::IF-1" in refs) == ("root::SYS-1" in refs)
    assert all(edge.source in {node.id for node in spec.nodes} and edge.target in {node.id for node in spec.nodes} for edge in spec.edges)


def test_conops_infers_and_deduplicates_external_only_from_structured_evidence(tmp_path):
    path = tmp_path / ".architecture-model.yaml"
    path.write_text("""meta: {project: inferred, schema_version: '2.0'}
entities:
  behaviors:
    - id: BEH-1
      name: Exchange
      status: ACTIVE
      structured_steps:
        - {order: 1, action: Receive, actor: Vendor API}
        - {order: 2, action: Ignore arbitrary prose}
  interfaces:
    - {id: IF-1, name: Vendor REST, status: ACTIVE, provider: Vendor API, consumer: Local System, protocol: HTTPS}
  systems:
    - {id: SYS-1, name: Local System, status: ACTIVE}
relationships: []
""", encoding="utf-8")

    spec = project_conops(ArchitectureViewContext.from_repo(tmp_path))
    inferred = [node for node in spec.nodes if node.kind == "external" and node.inferred]
    assert len(inferred) == 1
    assert inferred[0].label == "Vendor API"
    assert {item.source for item in inferred[0].evidence} == {"interface-endpoint", "structured-step-participant"}
    assert all("arbitrary prose" not in node.label.lower() for node in spec.nodes)


def test_conops_infers_external_from_structured_component_dependency(tmp_path):
    path = tmp_path / ".architecture-model.yaml"
    path.write_text("""meta: {project: dependencies, schema_version: '2.0'}
entities:
  components:
    - id: COMP-1
      name: Adapter
      status: ACTIVE
      external_dependencies:
        - {name: Payments API, source: requirements.md, protocol: HTTPS}
relationships: []
""", encoding="utf-8")
    spec = project_conops(ArchitectureViewContext.from_repo(tmp_path))
    external = next(node for node in spec.nodes if node.label == "Payments API")
    assert external.inferred
    assert external.evidence[0].source == "component-external-dependency"
    assert external.evidence[0].entity_refs == ("root::COMP-1",)


def test_conops_drilldown_and_curation_are_structural(tmp_path):
    context = _context(tmp_path)
    curation = ViewCuration(
        featured=[Selector(qualified_id="root::BEH-0", resolved_id="root::BEH-0")],
        scenarios=[CuratedGroup("priority", "Priority", members=["root::BEH-0"])],
        labels={"root::BEH-0": "Curated Mission"},
        drilldowns={"mission-detail": Selector(qualified_id="root::BEH-0", resolved_id="root::BEH-0")},
    )
    spec = project_conops(context, curation)
    scenario = next(node for node in spec.nodes if node.id == "priority")
    detail = next(item for item in spec.drilldowns if item.id == scenario.drilldown_ref).spec
    assert scenario.label == "Priority"
    assert next(node for node in detail.nodes if node.entity_ref == "root::BEH-0").label == "Curated Mission"
    assert detail and {node.kind for node in detail.nodes} >= {"behavior", "interface", "system", "requirement", "moe", "failure"}


def test_conops_keeps_unresolved_interface_on_degraded_boundary_path(tmp_path):
    path = tmp_path / ".architecture-model.yaml"
    path.write_text("""meta: {project: degraded, schema_version: '2.0'}
entities:
  interfaces:
    - {id: IF-LOST, name: Lost Link, status: ACTIVE, provider: Missing Provider, protocol: HTTPS}
relationships: []
""", encoding="utf-8")
    spec = project_conops(ArchitectureViewContext.from_repo(tmp_path), max_overview_nodes=2)
    assert len(spec.nodes) == 2
    interface = next(node for node in spec.nodes if node.entity_ref == "root::IF-LOST")
    boundary = next(node for node in spec.nodes if node.kind == "unknown-boundary")
    edge = next(edge for edge in spec.edges if {edge.source, edge.target} == {interface.id, boundary.id})
    assert edge.inferred and edge.evidence[0].source == "unresolved-interface-endpoint"
    assert any(item.code == "CONOPS_DEGRADED_INTERFACE" for item in spec.warnings)


def test_conops_actor_and_external_drilldowns_list_participation_and_evidence(tmp_path):
    context = _context(tmp_path)
    context.entity("root::ACT-1").value.goals = ["Complete mission"]
    spec = project_conops(context)
    actor = next(node for node in spec.nodes if node.entity_ref == "root::ACT-1")
    detail = next(item.spec for item in spec.drilldowns if item.id == actor.drilldown_ref)
    assert detail and {node.kind for node in detail.nodes} >= {"actor", "goal", "scenario", "interface", "system"}
    assert all(node.evidence for node in detail.nodes)
    assert all(not node.drilldown_ref or any(item.id == node.drilldown_ref for item in spec.drilldowns) for node in spec.nodes)


def test_conops_restores_bounded_failure_and_error_handling_callouts(tmp_path):
    context = _context(tmp_path)
    behavior = context.entity("root::BEH-0").value
    from architecture_model.core.types import Step
    behavior.structured_steps = [Step(1, "Run", "", error_handling="Use degraded mode")]
    context.entity("root::SYS-1").value.failure_modes = ["System outage"]
    spec = project_conops(context)
    assert {item.label for item in spec.callouts} >= {"Timeout", "Use degraded mode", "System outage"}
    assert len(spec.callouts) <= 6
    assert all(item.target and item.evidence for item in spec.callouts)


def test_conops_failure_callouts_have_global_ids_and_aggregate_same_target_text(tmp_path):
    context = _context(tmp_path)
    context.entity("root::CAP-1").value.failure_modes = ["Timeout"]
    context.entity("root::SYS-1").value.failure_modes = ["Outage"]
    first = project_conops(context)
    second = project_conops(context)
    assert first.to_dict() == second.to_dict()
    assert len({item.id for item in first.callouts}) == len(first.callouts)
    timeout = [item for item in first.callouts if item.label == "Timeout"]
    assert len(timeout) == 1
    assert set(timeout[0].evidence) == {"root::BEH-0", "root::CAP-1"}


def test_conops_renamed_actor_drilldown_uses_canonical_identity(tmp_path):
    context = _context(tmp_path)
    context.entity("root::BEH-0").value.actor = "Operator"
    curation = ViewCuration(labels={"root::ACT-1": "Mission Commander", "root::ACT-2": "Operator"})
    spec = project_conops(context, curation)
    actor = next(node for node in spec.nodes if node.entity_ref == "root::ACT-1")
    assert actor.label == "Mission Commander"
    detail = next(item.spec for item in spec.drilldowns if item.id == actor.drilldown_ref)
    refs = {node.entity_ref for node in detail.nodes}
    assert {"root::ACT-1", "root::BEH-0", "root::IF-1", "root::SYS-1"} <= refs
    observer = next(node for node in spec.nodes if node.entity_ref == "root::ACT-2")
    observer_detail = next(item.spec for item in spec.drilldowns if item.id == observer.drilldown_ref)
    assert "root::BEH-0" not in {node.entity_ref for node in observer_detail.nodes}


def test_conops_curated_scenarios_are_primary_aggregates_with_flows_and_drilldowns(tmp_path):
    context = _context(tmp_path, behaviors=4)
    evidence = [EvidenceRecord("docs/evidence.md", "Observed curated exchange")]
    curation = ViewCuration(
        featured=[Selector(qualified_id="root::BEH-2", resolved_id="root::BEH-2")],
        order=["root::BEH-2", "root::BEH-0"],
        scenarios=[
            CuratedGroup("scenario-acquire", "Acquire Knowledge", order=1, members=["root::BEH-2", "root::SYS-1"]),
            CuratedGroup("scenario-use", "Use Knowledge", order=2, members=["root::BEH-0"]),
        ],
        externals=[CuratedExternal("ext-source", "Source System", True, evidence)],
        flows=[
            CuratedFlow("ext-source", "scenario-acquire", "exchange", "records", True, evidence),
            CuratedFlow("scenario-acquire", "scenario-use", "operational-flow", "knowledge", True, evidence),
            CuratedFlow("root::BEH-2", "root::BEH-0", "data-flow", "member evidence", True, evidence),
        ],
    )
    spec = project_conops(context, curation, max_overview_nodes=6)
    assert spec.layout == "operational-lanes"
    assert len(spec.nodes) <= 6
    assert [node.label for node in spec.nodes if node.kind == "scenario"] == ["Acquire Knowledge", "Use Knowledge"]
    assert all(node.entity_ref not in {"root::BEH-1", "root::BEH-3"} for node in spec.nodes)
    assert {(edge.source, edge.target) for edge in spec.edges} >= {
        ("ext-source", "scenario-acquire"), ("scenario-acquire", "scenario-use"),
    }
    assert any(
        edge.source == "scenario-acquire" and edge.target == "scenario-use" and edge.label == "member evidence"
        for edge in spec.edges
    )
    assert all(edge.evidence and edge.inferred for edge in spec.edges if edge.kind in {"exchange", "operational-flow"})
    scenario = next(node for node in spec.nodes if node.id == "scenario-acquire")
    detail = next(item.spec for item in spec.drilldowns if item.id == scenario.drilldown_ref)
    refs = {node.entity_ref for node in detail.nodes}
    assert {"root::BEH-2", "root::SYS-1", "root::IF-1"} <= refs
    assert any(node.kind == "failure" for node in detail.nodes)
    assert not spec.callouts
    boundary = next(node for node in spec.nodes if node.id == "conops:system-boundary")
    assert boundary.lane == "boundary"
    assert any(edge.source == "scenario-acquire" and edge.target == boundary.id for edge in spec.edges)
    assert all(node.kind not in {"actor", "external"} for node in spec.nodes if node.lane == "outcomes")


def test_real_logs_db_conops_curation_projects_five_scenarios_and_curated_flows():
    repo = Path("/Users/baigm2/Documents/Projects/logs_db")
    if not (repo / ".architecture/viewer-curation.yaml").is_file():
        pytest.skip("logs-db curation unavailable")
    context = ArchitectureViewContext.from_repo(repo)
    curation = load_viewer_curation(repo, context).views.conops
    spec = project_conops(context, curation)
    labels = [node.label for node in spec.nodes if node.kind == "scenario"]
    assert labels == ["Acquire Knowledge", "Enrich & Organize", "Search & Use", "Review & Govern", "Learn & Improve"]
    assert all("CLI" not in node.label and "Audit Kb" not in node.label for node in spec.nodes)
    assert {node.id for node in spec.nodes} >= {"ext-github-opencode", "ext-ai-services"}
    assert len([edge for edge in spec.edges if edge.kind in {"exchange", "operational-flow", "data-flow"}]) == 10
    assert len(spec.nodes) <= 15
    boundary = next(node for node in spec.nodes if node.id == "conops:system-boundary")
    assert any(boundary.id in {edge.source, edge.target} for edge in spec.edges)
    allocations = [edge for edge in spec.edges if edge.kind == "allocation"]
    assert allocations and all(not edge.label and edge.title for edge in allocations)
