import random
from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.view_context import ArchitectureViewContext
from architecture_model.core.view_curation import CuratedFlow, CuratedGroup, EvidenceRecord, Selector, ViewCuration
from architecture_model.core.se_view_projectors import project_functional_architecture


def _context(tmp_path: Path, capability_ids: list[str]) -> ArchitectureViewContext:
    tmp_path.mkdir(parents=True, exist_ok=True)
    capabilities = "\n".join(
        f"    - {{id: {identifier}, name: Function {identifier}, status: ACTIVE, goals: [Deliver {identifier}], moes: [quality], failure_modes: [failure], monitored: [metric]}}"
        for identifier in capability_ids
    )
    hierarchy = [capability_ids[0], *sorted(capability_ids[1:])]
    contains = "\n".join(
        f"  - {{from: {hierarchy[index - 1]}, to: {identifier}, type: contains}}"
        for index, identifier in enumerate(hierarchy[1:], 1)
    )
    path = tmp_path / ".architecture-model.yaml"
    path.write_text(f"""meta: {{project: functional, schema_version: '2.0'}}
entities:
  capabilities:
{capabilities}
  behaviors:
    - id: BEH-1
      name: Execute mission
      status: ACTIVE
      capability_id: {capability_ids[-1]}
      structured_steps:
        - {{order: 1, action: Receive, component_ref: COMP-1, input: request, output: accepted}}
        - {{order: 2, action: Deliver, component_ref: COMP-2, input: accepted, output: result}}
  components:
    - {{id: COMP-1, name: Input Adapter, status: ACTIVE}}
    - {{id: COMP-2, name: Output Adapter, status: ACTIVE}}
    - {{id: COMP-ORPHAN, name: Unallocated, status: ACTIVE}}
  interfaces:
    - {{id: IF-1, name: Mission Data, status: ACTIVE, provider: COMP-2, consumer: COMP-1}}
relationships:
{contains}
  - {{from: COMP-1, to: {hierarchy[-2]}, type: realizes}}
  - {{from: COMP-2, to: {hierarchy[-1]}, type: realizes}}
  - {{from: COMP-1, to: BEH-1, type: traces-to}}
""", encoding="utf-8")
    return ArchitectureViewContext.load(load_model(path), tmp_path)


def test_functional_discovers_arbitrary_deep_root_and_separates_edge_semantics(tmp_path):
    context = _context(tmp_path, ["MISSION-X", "CAP-A", "CAP-B", "CAP-C", "CAP-D"])
    spec = project_functional_architecture(context)
    spec.validate()

    assert spec.direction == "TB"
    nodes = {node.entity_ref: node for node in spec.nodes if node.entity_ref}
    assert "root::MISSION-X" in nodes and "root::CAP-A" in nodes
    decomposition = [edge for edge in spec.edges if edge.kind == "decomposition"]
    assert decomposition and all(edge.style == "dotted" for edge in decomposition)
    assert all(node.kind != "component" or node.status == "summary" for node in spec.nodes)
    detail = next(item.spec for item in spec.drilldowns if item.source == "node:root::MISSION-X")
    assert "root::CAP-D" in {node.entity_ref for node in detail.nodes}
    assert any(edge.kind == "operational-flow" and edge.style == "solid" for edge in detail.edges)
    leaf = next(node for node in detail.nodes if node.entity_ref == "root::CAP-D")
    assert {"behaviors:1", "components:2", "moes:1", "failures:1", "monitoring:1"} <= set(leaf.badges)
    assert "request" in leaf.metrics["inputs"] and "result" in leaf.metrics["outputs"]
    assert all(node.drilldown_ref for node in spec.nodes if node.kind == "capability")
    assert all(any(item.id == node.drilldown_ref for item in spec.drilldowns) for node in spec.nodes if node.drilldown_ref)
    assert any(group.kind == "warning" for group in spec.groups)


def test_functional_is_bounded_and_independent_of_input_order(tmp_path):
    identifiers = ["ROOT"] + [f"CAP-{index:02}" for index in range(20)]
    context = _context(tmp_path, identifiers)
    model = context.models["root"]
    model.relationships = [item for item in model.relationships if item.type.value != "contains"]
    from architecture_model.core.types import Relationship, RelationType
    model.relationships.extend(Relationship(RelationType.CONTAINS, "ROOT", item) for item in identifiers[1:])
    first = project_functional_architecture(ArchitectureViewContext(context.root, context.models, [])).to_dict()
    random.Random(17).shuffle(model.entities.capabilities)
    random.Random(23).shuffle(model.relationships)
    second_context = ArchitectureViewContext(context.root, context.models, [])
    second = project_functional_architecture(second_context).to_dict()
    assert len([node for node in first["nodes"] if node["kind"] == "capability"]) <= 12
    assert len(first["nodes"]) <= 15
    assert any(item["code"] == "FUNCTIONAL_OVERVIEW_BOUNDED" for item in first["warnings"])
    assert first == second


def test_functional_curation_changes_presentation_and_requires_evidence_for_inferred_flow(tmp_path):
    context = _context(tmp_path, ["MISSION", "CAP-A", "CAP-B"])
    root = Selector(qualified_id="root::CAP-A", resolved_id="root::CAP-A")
    flow = CuratedFlow(
        "root::CAP-A", "root::CAP-B", "data-flow", "curated", True,
        [EvidenceRecord("docs/evidence.md", "Observed transition")],
    )
    curation = ViewCuration(mission_root=root, order=["root::CAP-B", "root::CAP-A"], flows=[flow])
    spec = project_functional_architecture(context, curation)
    assert spec.provenance.context
    assert any(edge.inferred and edge.label == "curated" and edge.evidence for edge in spec.edges)

    invalid = project_functional_architecture(
        context,
        ViewCuration(flows=[CuratedFlow("missing", "root::CAP-B", "data-flow", inferred=True)]),
    )
    assert any(item.code == "FUNCTIONAL_CURATION_INVALID" for item in invalid.warnings)


def test_functional_step_flow_uses_one_specific_capability_and_aggregates_duplicates(tmp_path):
    path = tmp_path / ".architecture-model.yaml"
    path.write_text("""meta: {project: flows, schema_version: '2.0'}
entities:
  capabilities:
    - {id: ROOT, name: Mission, status: ACTIVE}
    - {id: CAP-A, name: Receive, status: ACTIVE}
    - {id: CAP-B, name: Deliver, status: ACTIVE}
    - {id: CAP-X, name: Unsupported, status: ACTIVE}
  components:
    - {id: COMP-A, name: Receiver, status: ACTIVE}
    - {id: COMP-B, name: Deliverer, status: ACTIVE}
  behaviors:
    - id: BEH-1
      name: Run
      status: ACTIVE
      capability_id: ROOT
      structured_steps:
        - {order: 1, action: Receive one, component_ref: COMP-A}
        - {order: 2, action: Deliver one, component_ref: COMP-B}
        - {order: 3, action: Receive two, component_ref: COMP-A}
        - {order: 4, action: Deliver two, component_ref: COMP-B}
relationships:
  - {from: ROOT, to: CAP-A, type: contains}
  - {from: ROOT, to: CAP-B, type: contains}
  - {from: ROOT, to: CAP-X, type: contains}
  - {from: COMP-A, to: CAP-A, type: realizes}
  - {from: COMP-A, to: CAP-X, type: realizes}
  - {from: COMP-B, to: CAP-B, type: realizes}
""", encoding="utf-8")
    spec = project_functional_architecture(ArchitectureViewContext.from_repo(tmp_path))
    flows = [edge for edge in spec.edges if edge.kind == "operational-flow"]
    assert [(edge.source, edge.target, edge.count) for edge in flows] == [
        ("node:root::CAP-A", "node:root::CAP-B", 2),
        ("node:root::CAP-B", "node:root::CAP-A", 1),
    ]
    assert all("CAP-X" not in (edge.source + edge.target) for edge in flows)


def test_functional_represents_disconnected_roots_and_real_drilldowns_with_global_bound(tmp_path):
    context = _context(tmp_path, ["ROOT-A", "CAP-A"])
    model = context.models["root"]
    from architecture_model.core.types import Capability, Status
    model.entities.capabilities.extend([
        Capability("ROOT-B", "Second Mission", Status.ACTIVE),
        Capability("CAP-B", "Second Function", Status.ACTIVE),
    ])
    from architecture_model.core.types import Relationship, RelationType
    model.relationships.append(Relationship(RelationType.CONTAINS, "ROOT-B", "CAP-B"))
    context = ArchitectureViewContext(context.root, context.models, [])

    spec = project_functional_architecture(context, max_overview_nodes=6)
    refs = {node.entity_ref for node in spec.nodes}
    assert {"root::ROOT-A", "root::ROOT-B"} <= refs
    assert len(spec.nodes) <= 6
    detail = next(item.spec for item in spec.drilldowns if item.source == "node:root::ROOT-A")
    assert detail and "root::CAP-A" in {node.entity_ref for node in detail.nodes}


def test_functional_groups_featured_capabilities_and_bounds_orphans(tmp_path):
    context = _context(tmp_path, ["MISSION", "CAP-A", "CAP-B"])
    group = CuratedGroup("priority", "Priority", members=["root::CAP-B"])
    curation = ViewCuration(
        groups=[group], featured=[Selector(qualified_id="root::CAP-B", resolved_id="root::CAP-B")],
        hide=[Selector(qualified_id="root::CAP-A", resolved_id="root::CAP-A")],
    )
    spec = project_functional_architecture(context, curation, max_overview_nodes=4)
    nodes = {node.entity_ref: node for node in spec.nodes if node.entity_ref}
    assert len(spec.nodes) <= 4
    assert "root::CAP-A" not in nodes
    assert nodes["root::CAP-B"].group == "priority"


def test_functional_curated_drilldown_key_replaces_generated_presentation_id(tmp_path):
    context = _context(tmp_path, ["MISSION", "CAP-A"])
    selector = Selector(qualified_id="root::CAP-A", resolved_id="root::CAP-A")
    spec = project_functional_architecture(context, ViewCuration(drilldowns={"inspect-function": selector}))
    node = next(item for item in spec.nodes if item.entity_ref == "root::CAP-A")
    assert node.drilldown_ref == "inspect-function"
    assert next(item for item in spec.drilldowns if item.id == "inspect-function").spec is not None


def test_functional_drilldown_connects_every_semantic_participant(tmp_path):
    path = tmp_path / ".architecture-model.yaml"
    path.write_text("""meta: {project: detail, schema_version: '2.0'}
entities:
  actors: [{id: ACT-1, name: Operator, status: ACTIVE}]
  capabilities: [{id: CAP-1, name: Mission, status: ACTIVE, requirements: [REQ-1]}]
  behaviors:
    - {id: BEH-1, name: Start, status: ACTIVE, actor_id: ACT-1, capability_id: CAP-1, interface_refs: [IF-1]}
    - {id: BEH-2, name: Finish, status: ACTIVE, capability_id: CAP-1}
  components:
    - {id: COMP-1, name: Producer, status: ACTIVE}
    - {id: COMP-2, name: Consumer, status: ACTIVE}
  interfaces: [{id: IF-1, name: Data, status: ACTIVE, provider: COMP-1, consumer: COMP-2}]
  requirements: [{id: REQ-1, name: Safe operation, status: ACTIVE}]
relationships:
  - {from: COMP-1, to: CAP-1, type: realizes}
  - {from: COMP-1, to: BEH-1, type: traces-to}
  - {from: BEH-1, to: BEH-2, type: triggers}
  - {from: COMP-1, to: IF-1, type: exposes}
  - {from: COMP-2, to: IF-1, type: consumes}
  - {from: COMP-1, to: REQ-1, type: satisfies}
  - {from: CAP-1, to: REQ-1, type: constrained-by}
""", encoding="utf-8")
    spec = project_functional_architecture(ArchitectureViewContext.from_repo(tmp_path))
    detail = spec.drilldowns[0].spec
    kinds = {edge.kind for edge in detail.edges}
    assert {"realizes", "traces-to", "triggers", "participates", "exposes", "consumes", "satisfies", "constrained-by"} <= kinds
    assert all(edge.evidence for edge in detail.edges)


def test_functional_orphan_and_omitted_summaries_are_bounded_and_navigable(tmp_path):
    context = _context(tmp_path, ["ROOT", *[f"CAP-{index}" for index in range(8)]])
    spec = project_functional_architecture(context, max_overview_nodes=5)
    assert len(spec.nodes) <= 5
    summaries = [node for node in spec.nodes if node.kind == "summary"]
    assert {node.status for node in summaries} >= {"orphan", "omitted"}
    for node in summaries:
        detail = next(item.spec for item in spec.drilldowns if item.id == node.drilldown_ref)
        assert detail and detail.nodes
        assert all(item.entity_ref and item.evidence for item in detail.nodes)
