import random
from pathlib import Path

import pytest
import yaml

from architecture_model.core.parser import load_model
from architecture_model.core.se_view_projectors import project_use_cases
from architecture_model.core.view_context import ArchitectureViewContext
from architecture_model.core.view_curation import Selector, ViewCuration, load_viewer_curation
from architecture_model.core.view_curation import (
    CuratedUseCaseActor,
    CuratedUseCaseAnnotation,
    CuratedUseCaseAssociation,
    EvidenceRecord,
)


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
    omitted = next((item.spec for item in spec.drilldowns if item.id == "drilldown:use-cases-omitted"), None)
    if omitted:
        omitted_refs = {node.entity_ref for node in omitted.nodes}
        assert not omitted_refs.intersection({"root::BEH-12", "root::BEH-14"})
    else:
        assert len(spec.nodes) == 6


def test_use_case_all_ten_featured_render_before_supporting_nodes(tmp_path):
    context = _context(tmp_path)
    featured_keys = [f"root::BEH-{index:02}" for index in range(10)]
    curation = ViewCuration(
        featured=[Selector(qualified_id=key, resolved_id=key) for key in featured_keys],
        order=list(reversed(featured_keys)),
    )

    spec = project_use_cases(context, curation, max_overview_nodes=15)

    cases = [node.entity_ref for node in spec.nodes if node.kind == "use-case"]
    assert cases == list(reversed(featured_keys))
    assert len(spec.nodes) <= 15
    omitted = next(node for node in spec.nodes if node.status == "omitted")
    omitted_detail = next(item.spec for item in spec.drilldowns if item.id == omitted.drilldown_ref)
    assert not {node.entity_ref for node in omitted_detail.nodes}.intersection(featured_keys)


def test_use_case_curated_associations_and_annotations_are_inferred_canonical_first_and_nonmutating(tmp_path):
    context = _context(tmp_path)
    behavior = context.entity("root::BEH-00")
    behavior.value.actor = ""
    behavior.value.actor_id = ""
    behavior.value.trigger = "canonical trigger"
    behavior.value.goals = []
    behavior.value.preconditions = []
    behavior.value.postconditions = []
    behavior.value.moes = []
    before = behavior.value.__dict__.copy()
    evidence = [EvidenceRecord("docs/use-cases.md", "Repository evidence for this use case.")]
    curation = ViewCuration(
        featured=[Selector(qualified_id=behavior.key, resolved_id=behavior.key)],
        actors=[CuratedUseCaseActor("knowledge-worker", "Knowledge Worker", True, evidence)],
        associations=[
            CuratedUseCaseAssociation("knowledge-worker", [behavior.key], True, evidence),
            CuratedUseCaseAssociation("root::ACT-OPS", [behavior.key], True, evidence),
        ],
        annotations=[CuratedUseCaseAnnotation(
            behavior.key,
            goal="Find knowledge",
            trigger="curated trigger",
            preconditions=["Access granted"],
            postconditions=["Knowledge returned"],
            success_outcome="Grounded result available",
            moes=["Under one second"],
            evidence=evidence,
        )],
    )

    spec = project_use_cases(context, curation)
    case = next(node for node in spec.nodes if node.entity_ref == behavior.key)
    assert "canonical trigger" in case.subtitle and "curated trigger" not in case.subtitle
    assert "Find knowledge" in case.subtitle
    actors = {node.label: node for node in spec.nodes if node.kind in {"actor", "external"}}
    assert {"Knowledge Worker", "Operator"} <= actors.keys()
    inferred_edges = [edge for edge in spec.edges if edge.kind == "participates" and edge.target == case.id]
    assert len(inferred_edges) == 2
    assert all(edge.inferred and edge.style == "dashed" and edge.evidence for edge in inferred_edges)
    for actor in (actors["Knowledge Worker"], actors["Operator"]):
        actor_detail = next(item.spec for item in spec.drilldowns if item.id == actor.drilldown_ref)
        association_edges = [
            edge for edge in actor_detail.edges
            if edge.kind == "participates" and edge.target == case.id
        ]
        assert association_edges
        assert all(edge.inferred and edge.style == "dashed" and edge.evidence for edge in association_edges)
    detail = next(item.spec for item in spec.drilldowns if item.id == case.drilldown_ref)
    assert {"Access granted", "Knowledge returned", "Grounded result available", "Under one second"} <= {
        node.label for node in detail.nodes
    }
    inferred = [node for node in detail.nodes if node.inferred]
    assert inferred and all("inferred" in node.badges and node.evidence for node in inferred)
    assert behavior.value.__dict__ == before


def test_use_case_complete_canonical_semantics_ignore_curated_annotation(tmp_path):
    context = _context(tmp_path)
    behavior = context.entity("root::BEH-00")
    behavior.value.trigger = "canonical trigger"
    behavior.value.goals = ["Canonical goal"]
    behavior.value.preconditions = ["Canonical precondition"]
    behavior.value.postconditions = ["Canonical outcome"]
    behavior.value.moes = ["Canonical measure"]
    evidence = [EvidenceRecord("docs/use-cases.md", "Curated fallback evidence.")]
    curation = ViewCuration(annotations=[CuratedUseCaseAnnotation(
        behavior.key,
        goal="Curated goal",
        trigger="curated trigger",
        preconditions=["Curated precondition"],
        postconditions=["Curated postcondition"],
        success_outcome="Curated outcome",
        moes=["Curated measure"],
        evidence=evidence,
    )])

    spec = project_use_cases(context, curation)
    case = next(node for node in spec.nodes if node.entity_ref == behavior.key)
    detail = next(item.spec for item in spec.drilldowns if item.id == case.drilldown_ref)

    assert not case.inferred and "inferred" not in case.badges
    assert all(item.source != "curated-inference" for item in case.evidence)
    labels = {node.label for node in detail.nodes}
    assert {"Canonical goal", "Canonical precondition", "Canonical outcome", "Canonical measure"} <= labels
    assert not labels.intersection({"Curated goal", "Curated precondition", "Curated postcondition", "Curated outcome", "Curated measure"})


def test_actor_drilldown_preserves_mixed_canonical_and_inferred_associations(tmp_path):
    context = _context(tmp_path)
    curated_behavior = context.entity("root::BEH-01")
    curated_behavior.value.actor = ""
    curated_behavior.value.actor_id = ""
    evidence = [EvidenceRecord("docs/use-cases.md", "API consumer also initiates workflow one.")]
    curation = ViewCuration(associations=[
        CuratedUseCaseAssociation("root::ACT-OPS", [curated_behavior.key], True, evidence),
    ])

    spec = project_use_cases(context, curation)
    actor = next(node for node in spec.nodes if node.entity_ref == "root::ACT-OPS")
    detail = next(item.spec for item in spec.drilldowns if item.id == actor.drilldown_ref)
    edges = {edge.target: edge for edge in detail.edges if edge.kind == "participates"}

    assert not edges["node:root::BEH-00"].inferred
    assert edges["node:root::BEH-00"].style == ""
    assert edges["node:root::BEH-01"].inferred
    assert edges["node:root::BEH-01"].style == "dashed"


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


def test_use_case_hidden_formal_actor_is_not_reintroduced_as_inferred(tmp_path):
    hidden = Selector(qualified_id="root::ACT-OPS", resolved_id="root::ACT-OPS")
    spec = project_use_cases(_context(tmp_path), ViewCuration(hide=[hidden]))

    _assert_hidden_and_edges_safe(spec, "root::ACT-OPS")
    assert all(node.label != "Operator" for nested in _nested_specs(spec) for node in nested.nodes)
    assert all(
        not (node.inferred and node.label == "ACT-OPS")
        for nested in _nested_specs(spec) for node in nested.nodes
    )


@pytest.mark.parametrize("hidden_ref", [
    "root::ACT-OPS",
    "root::EXT-AUDIT",
    "root::SYS-WEB",
    "web::COMP-1",
    "root::BEH-00",
    "web::IF-1",
    "root::REQ-1",
])
def test_use_case_hide_applies_recursively_per_entity_type(tmp_path, hidden_ref):
    context = _context(tmp_path)
    if hidden_ref == "root::EXT-AUDIT":
        from architecture_model.core.types import ExternalSystem, Status
        external = ExternalSystem(id="EXT-AUDIT", name="Audit Service", status=Status.ACTIVE)
        context.models["root"].entities.external_systems.append(external)
        behavior = context.models["root"].entities.behaviors[0]
        behavior.actor = external.name
        behavior.actor_id = external.id
    hidden = Selector(qualified_id=hidden_ref, resolved_id=hidden_ref)
    spec = project_use_cases(
        ArchitectureViewContext(context.root, context.models, []),
        ViewCuration(hide=[hidden]),
    )

    _assert_hidden_and_edges_safe(spec, hidden_ref)
    if hidden_ref == "root::SYS-WEB":
        assert all(
            hidden_ref not in group.id and group.label != "Web"
            for nested in _nested_specs(spec) for group in nested.groups
        )
    if hidden_ref == "root::REQ-1":
        assert all(
            "requirements:0" in node.badges
            for node in spec.nodes if node.kind == "use-case"
        )


def test_real_logs_db_use_case_profile_renders_all_ten_featured():
    repo = Path("/Users/baigm2/Documents/Projects/logs_db")
    if not (repo / ".architecture/viewer-curation.yaml").is_file():
        pytest.skip("logs-db curation unavailable")
    context = ArchitectureViewContext.from_repo(repo)
    loaded = load_viewer_curation(repo, context)
    curation = loaded.views.use_cases

    spec = project_use_cases(context, curation)

    featured = [selector.resolved_id for selector in curation.featured if selector.resolved_id]
    cases = [node.entity_ref for node in spec.nodes if node.kind == "use-case"]
    assert len(featured) == 10
    assert cases[:10] == featured
    assert len(spec.nodes) <= 15


def test_logs_db_profile_accepts_proposed_evidenced_use_case_additions(tmp_path):
    repo = Path("/Users/baigm2/Documents/Projects/logs_db")
    if not (repo / ".architecture/viewer-curation.yaml").is_file():
        pytest.skip("logs-db curation unavailable")
    context = ArchitectureViewContext.from_repo(repo)
    evidence = tmp_path / "scripts/_pipeline_ingest.py"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("copied evidence fixture", encoding="utf-8")
    source_profile = yaml.safe_load((repo / ".architecture/viewer-curation.yaml").read_text(encoding="utf-8"))
    raw = {"version": 1, "views": {"use_cases": source_profile["views"]["use_cases"]}}
    use_cases = raw["views"]["use_cases"]
    featured_selectors = [{"qualified_id": value} for value in use_cases["featured"]]
    use_cases["actors"] = [{
        "id": "knowledge-worker", "name": "Knowledge Worker", "inferred": True,
        "evidence": [{"source": "scripts/_pipeline_ingest.py", "claim": "Knowledge workers initiate repository ingestion."}],
    }]
    use_cases["associations"] = [{
        "actor": {"qualified_id": "root::ACT-1"},
        "use_cases": featured_selectors,
        "inferred": True,
        "evidence": [{"source": "scripts/_pipeline_ingest.py", "claim": "API consumers initiate multi-source ingestion."}],
    }, {
        "actor": {"qualified_id": "project-documentation-orchestration-2-related::ACT-1"},
        "use_cases": featured_selectors,
        "inferred": True,
        "evidence": [{"source": "scripts/_pipeline_ingest.py", "claim": "CLI users initiate project knowledge workflows."}],
    }, {
        "actor": "knowledge-worker",
        "use_cases": featured_selectors,
        "inferred": True,
        "evidence": [{"source": "scripts/_pipeline_ingest.py", "claim": "Knowledge workers initiate multi-source ingestion."}],
    }]
    use_cases["annotations"] = [{
        "use_case": {"qualified_id": "project-documentation-orchestration-2-related::BEH-104"},
        "goal": "Acquire normalized project knowledge",
        "trigger": "A knowledge source is ready",
        "preconditions": ["Source access is configured"],
        "postconditions": ["Normalized records are persisted"],
        "success_outcome": "Project knowledge is searchable",
        "moes": ["All configured sources are processed"],
        "evidence": [{"source": "scripts/_pipeline_ingest.py", "claim": "The ingestion pipeline normalizes and persists configured sources."}],
    }]
    profile = tmp_path / ".architecture/viewer-curation.yaml"
    profile.parent.mkdir()
    profile.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    loaded = load_viewer_curation(tmp_path, context)
    spec = project_use_cases(context, loaded.views.use_cases)

    assert loaded.diagnostics == []
    cases = [node for node in spec.nodes if node.kind == "use-case"]
    assert len(cases) == 10
    actor_labels = {node.label for node in spec.nodes if node.kind in {"actor", "external"}}
    assert {"API Consumer", "CLI User", "Knowledge Worker"} <= actor_labels
    assert len(spec.nodes) <= 15
    assert any(edge.inferred and edge.style == "dashed" for edge in spec.edges)
    connected = {edge.source for edge in spec.edges} | {edge.target for edge in spec.edges}
    assert all(node.id in connected for node in cases)
