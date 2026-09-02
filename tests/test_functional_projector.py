import random
from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.view_context import ArchitectureViewContext
from architecture_model.core.view_curation import CuratedFlow, EvidenceRecord, Selector, ViewCuration
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
    assert "root::MISSION-X" in nodes and "root::CAP-D" in nodes
    decomposition = [edge for edge in spec.edges if edge.kind == "decomposition"]
    assert decomposition and all(edge.style == "dotted" for edge in decomposition)
    assert any(edge.kind in {"operational-flow", "data-flow"} and edge.style == "solid" for edge in spec.edges)
    assert any(edge.kind == "allocation" and edge.style == "dashed" for edge in spec.edges)
    leaf = nodes["root::CAP-D"]
    assert {"behaviors:1", "components:2", "moes:1", "failures:1", "monitoring:1"} <= set(leaf.badges)
    assert "request" in leaf.metrics["inputs"] and "result" in leaf.metrics["outputs"]
    assert leaf.drilldown_ref
    assert any(group.kind == "warning" for group in spec.groups)


def test_functional_is_bounded_and_independent_of_input_order(tmp_path):
    identifiers = ["ROOT"] + [f"CAP-{index:02}" for index in range(20)]
    first = project_functional_architecture(_context(tmp_path, identifiers)).to_dict()
    shuffled = identifiers[1:]
    random.Random(17).shuffle(shuffled)
    second_context = _context(tmp_path, ["ROOT", *shuffled])
    second = project_functional_architecture(second_context).to_dict()
    assert len([node for node in first["nodes"] if node["kind"] == "capability"]) <= 12
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
