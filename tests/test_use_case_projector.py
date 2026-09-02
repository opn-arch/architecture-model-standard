import random
from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.se_view_projectors import project_use_cases
from architecture_model.core.view_context import ArchitectureViewContext
from architecture_model.core.view_curation import Selector, ViewCuration


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _context(tmp_path: Path, count: int = 15) -> ArchitectureViewContext:
    behaviors = []
    for index in range(count):
        actor = "ACT-OPS" if index % 2 == 0 else "Partner Service"
        structured = "" if index == count - 1 else f"""
      structured_steps:
        - {{order: 1, action: Receive workflow {index}, component_ref: web::COMP-1, actor: {actor!r}, input: request-{index}, output: accepted-{index}, error_handling: Reject invalid request}}
        - {{order: 2, action: Persist workflow {index}, component_ref: domain::COMP-1, input: accepted-{index}, output: result-{index}, error_handling: Compensate persisted record}}"""
        behaviors.append(f"""    - id: BEH-{index:02}
      name: Workflow {index:02}
      status: ACTIVE
      actor: {actor!r}
      actor_id: {actor if actor.startswith('ACT-') else ''}
      trigger: request-{index}
      goals: [Complete workflow, Goal {index}]
      preconditions: [Request is authorized]
      postconditions: [Workflow {index} completed]
      requirements: [REQ-1]
      moes: [completion under one second]
      failure_modes: [Workflow unavailable]
      interface_refs: [web::IF-1]
      steps: [Plain fallback {index}]{structured}
""")
    trigger_links = "\n".join(
        f"  - {{from: BEH-{index:02}, to: BEH-{index + 1:02}, type: triggers}}"
        for index in range(count - 1)
    )
    _write(tmp_path / ".architecture-model.yaml", f"""meta: {{project: use-cases, schema_version: '2.0'}}
entities:
  actors:
    - {{id: ACT-OPS, name: Operator, status: ACTIVE, goals: [Complete workflow]}}
  systems:
    - {{id: SYS-WEB, name: Web, status: ACTIVE, sub_model_ref: .architecture-models/web/.architecture-model.yaml}}
    - {{id: SYS-DOMAIN, name: Domain, status: ACTIVE, sub_model_ref: .architecture-models/domain/.architecture-model.yaml}}
  requirements:
    - {{id: REQ-1, name: Reliable processing, status: ACTIVE}}
  behaviors:
{''.join(behaviors)}
relationships:
{trigger_links}
  - {{from: ACT-OPS, to: BEH-00, type: traces-to}}
  - {{from: BEH-00, to: BEH-02, type: contains}}
""")
    _write(tmp_path / ".architecture-models/web/.architecture-model.yaml", """meta: {project: web, schema_version: '2.0'}
entities:
  components:
    - {id: COMP-1, name: Request Gateway, status: ACTIVE, failure_modes: [Gateway timeout], monitored: [latency]}
  interfaces:
    - {id: IF-1, name: Workflow API, status: ACTIVE, provider: COMP-1, consumer: Partner Service, protocol: HTTPS}
  behaviors:
    - {id: BEH-00, name: Child Workflow, status: ACTIVE, actor: Partner Service, trigger: callback, goals: [Complete callback], steps: [Handle callback]}
relationships:
  - {from: COMP-1, to: IF-1, type: exposes}
""")
    _write(tmp_path / ".architecture-models/domain/.architecture-model.yaml", """meta: {project: domain, schema_version: '2.0'}
entities:
  components:
    - {id: COMP-1, name: Workflow Store, status: ACTIVE, failure_modes: [Write conflict], monitored: [write failures]}
relationships: []
""")
    return ArchitectureViewContext.load(load_model(tmp_path / ".architecture-model.yaml"), tmp_path)


def test_use_cases_selects_bounded_actor_goal_catalog_with_honest_links(tmp_path):
    spec = project_use_cases(_context(tmp_path))
    spec.validate()
    cases = [node for node in spec.nodes if node.kind == "use-case"]
    assert 8 <= len(cases) <= 10
    assert len(spec.nodes) <= 15
    assert all("request-" in node.subtitle and "Complete workflow" in node.subtitle for node in cases)
    assert all({"requirements:1", "moes:1", "failures:1"} <= set(node.badges) for node in cases)
    assert all(node.metrics["implementing_systems"] == "Domain, Web" for node in cases)
    assert all(edge.evidence for edge in spec.edges)
    assert {edge.kind for edge in spec.edges} <= {"triggers", "contains", "shared-goal", "participates"}
    serialized = str(spec.to_dict()).casefold()
    assert "include" not in serialized and "extend" not in serialized


def test_use_case_structured_drilldown_has_sequence_io_errors_and_outcomes(tmp_path):
    spec = project_use_cases(_context(tmp_path))
    case = next(node for node in spec.nodes if node.entity_ref == "root::BEH-00")
    detail = next(item.spec for item in spec.drilldowns if item.id == case.drilldown_ref)
    assert detail is not None
    steps = sorted((node for node in detail.nodes if node.kind == "step"), key=lambda node: node.metrics["order"])
    assert len(steps) == 2
    assert steps[0].metrics["input"] == "request-0" and steps[1].metrics["output"] == "result-0"
    assert {node.entity_ref for node in detail.nodes} >= {
        "root::ACT-OPS", "web::COMP-1", "domain::COMP-1", "web::IF-1", "root::REQ-1",
    }
    assert any(edge.kind == "next" for edge in detail.edges)
    assert any(edge.kind == "error" and edge.target.startswith("error:") for edge in detail.edges)
    assert all(edge.evidence for edge in detail.edges)
    assert any(node.kind == "precondition" for node in detail.nodes)
    assert any(node.kind in {"postcondition", "success-criterion", "moe"} for node in detail.nodes)
    assert {group.kind for group in detail.groups} >= {"lane"}


def test_use_case_plain_steps_are_marked_lower_evidence(tmp_path):
    context = _context(tmp_path)
    behavior = context.entity("root::BEH-14")
    detail = project_use_cases(
        context,
        ViewCuration(featured=[Selector(qualified_id=behavior.key, resolved_id=behavior.key)]),
    )
    case = next(node for node in detail.nodes if node.entity_ref == behavior.key)
    spec = next(item.spec for item in detail.drilldowns if item.id == case.drilldown_ref)
    fallback = next(node for node in spec.nodes if node.kind == "step")
    assert fallback.status == "lower-evidence"
    assert any(item.code == "USE_CASE_PLAIN_STEP_FALLBACK" for item in spec.warnings)


def test_use_case_actor_and_omitted_summaries_have_actual_drilldowns(tmp_path):
    spec = project_use_cases(_context(tmp_path))
    actor = next(node for node in spec.nodes if node.entity_ref == "root::ACT-OPS")
    actor_detail = next(item.spec for item in spec.drilldowns if item.id == actor.drilldown_ref)
    assert actor_detail and any(node.kind == "goal" for node in actor_detail.nodes)
    assert any(node.kind == "use-case" for node in actor_detail.nodes)
    omitted = next(node for node in spec.nodes if node.status == "omitted")
    omitted_detail = next(item.spec for item in spec.drilldowns if item.id == omitted.drilldown_ref)
    assert omitted_detail and all(node.entity_ref for node in omitted_detail.nodes)


def test_use_case_curation_overrides_featured_order_hide_labels_and_drilldown(tmp_path):
    context = _context(tmp_path)
    featured = Selector(qualified_id="root::BEH-14", resolved_id="root::BEH-14")
    hidden = Selector(qualified_id="root::BEH-00", resolved_id="root::BEH-00")
    curation = ViewCuration(
        featured=[featured], hide=[hidden], order=["root::BEH-14", "root::BEH-01"],
        labels={"root::BEH-14": "Close Audit"},
        drilldowns={"audit-detail": featured},
    )
    spec = project_use_cases(context, curation)
    audit = next(node for node in spec.nodes if node.entity_ref == "root::BEH-14")
    assert audit.label == "Close Audit" and audit.drilldown_ref == "audit-detail"
    assert all(node.entity_ref != "root::BEH-00" for node in spec.nodes)


def test_use_case_featured_are_guaranteed_first_then_actor_round_robin_fills(tmp_path):
    context = _context(tmp_path)
    for index, behavior in enumerate(context.models["root"].entities.behaviors):
        behavior.actor = f"Actor {index:02}"
        behavior.actor_id = ""
    featured = [
        Selector(qualified_id="root::BEH-14", resolved_id="root::BEH-14"),
        Selector(qualified_id="root::BEH-12", resolved_id="root::BEH-12"),
    ]
    curation = ViewCuration(
        featured=featured,
        order=["root::BEH-12", "root::BEH-14", "root::BEH-03"],
    )

    spec = project_use_cases(
        ArchitectureViewContext(context.root, context.models, []),
        curation,
        max_overview_nodes=6,
    )

    cases = [node.entity_ref for node in spec.nodes if node.kind == "use-case"]
    assert cases[:2] == ["root::BEH-12", "root::BEH-14"]
    assert "root::BEH-03" in cases[2:]
    omitted = next(item.spec for item in spec.drilldowns if item.id == "drilldown:use-cases-omitted")
    omitted_refs = {node.entity_ref for node in omitted.nodes}
    assert not omitted_refs.intersection({"root::BEH-12", "root::BEH-14"})


def test_use_cases_are_deterministic_with_duplicate_local_ids(tmp_path):
    context = _context(tmp_path)
    first = project_use_cases(context).to_dict()
    random.Random(29).shuffle(context.models["root"].entities.behaviors)
    random.Random(31).shuffle(context.models["root"].relationships)
    second = project_use_cases(ArchitectureViewContext(context.root, context.models, [])).to_dict()
    assert first == second
    qualified = {
        node["entity_ref"] for drilldown in first["drilldowns"] if "spec" in drilldown
        for node in drilldown["spec"]["nodes"] if node["entity_ref"].endswith("::BEH-00")
    }
    assert "root::BEH-00" in qualified


def test_use_cases_sparse_fallback_validates(tmp_path):
    _write(tmp_path / ".architecture-model.yaml", """meta: {project: sparse, schema_version: '2.0'}
entities: {}
relationships: []
""")
    context = ArchitectureViewContext.load(load_model(tmp_path / ".architecture-model.yaml"), tmp_path)
    spec = project_use_cases(context)
    spec.validate()
    assert spec.nodes[0].kind == "warning"
    assert any(item.code == "USE_CASE_SPARSE_FALLBACK" for item in spec.warnings)


def test_use_cases_honors_small_global_bound(tmp_path):
    spec = project_use_cases(_context(tmp_path), max_overview_nodes=6)
    assert len(spec.nodes) <= 6
    spec.validate()


def test_use_case_drilldown_includes_implementing_system_nodes(tmp_path):
    spec = project_use_cases(_context(tmp_path))
    case = next(node for node in spec.nodes if node.entity_ref == "root::BEH-00")
    detail = next(item.spec for item in spec.drilldowns if item.id == case.drilldown_ref)
    assert {"root::SYS-WEB", "root::SYS-DOMAIN"} <= {
        node.entity_ref for node in detail.nodes if node.kind == "system"
    }


def test_use_case_formal_external_actor_and_states_retain_evidence(tmp_path):
    context = _context(tmp_path)
    from architecture_model.core.types import ExternalSystem, StateTransition, Status
    behavior = context.entity("root::BEH-00").value
    external = ExternalSystem(id="EXT-AUDIT", name="Audit Service", status=Status.ACTIVE)
    context.models["root"].entities.external_systems.append(external)
    behavior.actor = "Audit Service"
    behavior.actor_id = "EXT-AUDIT"
    behavior.states = [StateTransition("Waiting", [{"on": "timeout", "to": "Failed"}])]
    spec = project_use_cases(ArchitectureViewContext(context.root, context.models, []))
    participant = next(node for node in spec.nodes if node.entity_ref == "root::EXT-AUDIT")
    assert participant.kind == "external" and participant.evidence
    case = next(node for node in spec.nodes if node.entity_ref == "root::BEH-00")
    detail = next(item.spec for item in spec.drilldowns if item.id == case.drilldown_ref)
    state = next(node for node in detail.nodes if node.kind == "state")
    assert state.label == "Waiting" and state.evidence
