from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.view_context import ArchitectureViewContext
from architecture_model.core.view_curation import CuratedExternal, EvidenceRecord, ViewCuration
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
    primary = [node for node in first["nodes"] if node["kind"] in {"actor", "external", "scenario", "system"}]
    assert len(primary) <= 15
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
