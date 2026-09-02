from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.view_context import ArchitectureViewContext
from architecture_model.core.diagram_spec import Diagnostic


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _model(project: str, entities: str, relationships: str = "") -> str:
    return f"""meta:\n  project: {project}\n  schema_version: '2.0'\nentities:\n{entities}\nrelationships:\n{relationships or '  []'}\n"""


def test_context_qualifies_duplicate_ids_and_nested_models(tmp_path):
    root_path = tmp_path / ".architecture-model.yaml"
    _write(root_path, _model("root", """  systems:
    - id: SYS-A
      name: Alpha
      status: ACTIVE
      sub_model_ref: .architecture-models/a/.architecture-model.yaml
"""))
    _write(tmp_path / ".architecture-models/a/.architecture-model.yaml", _model("alpha", """  components:
    - id: COMP-1
      name: Alpha Component
      status: ACTIVE
      files: [src/shared.py]
  systems:
    - id: SYS-B
      name: Beta
      status: ACTIVE
      sub_model_ref: ../b/.architecture-model.yaml
"""))
    _write(tmp_path / ".architecture-models/b/.architecture-model.yaml", _model("beta", """  components:
    - id: COMP-1
      name: Beta Component
      status: ACTIVE
      files: [src/shared.py]
  capabilities:
    - id: CAP-1
      name: Search
      status: ACTIVE
""", """  - from: COMP-1
    to: CAP-1
    type: realizes
"""))

    context = ArchitectureViewContext.load(load_model(root_path), tmp_path)

    alpha = context.resolve(local_id="COMP-1", system="a")
    beta = context.resolve(local_id="COMP-1", system="b")
    assert alpha and beta and alpha.key != beta.key
    assert alpha.key == "a::COMP-1"
    assert beta.key == "b::COMP-1"
    assert context.entity(beta.key).name == "Beta Component"
    assert context.outgoing(beta.key)[0].target == "b::CAP-1"
    assert context.components_owning_file("src/shared.py") == ["a::COMP-1", "b::COMP-1"]
    assert context.systems_realizing_capability("b::CAP-1") == ["b"]
    assert context.resolve(local_id="COMP-1", system="SYS-A").key == "a::COMP-1"
    assert context.resolve(local_id="COMP-1", system="Beta").key == "b::COMP-1"


def test_context_warns_for_traversal_dead_and_cycle_refs(tmp_path):
    root_path = tmp_path / ".architecture-model.yaml"
    _write(root_path, _model("root", """  systems:
    - id: SYS-GOOD
      name: Good
      status: ACTIVE
      sub_model_ref: child/model.yaml
    - id: SYS-DEAD
      name: Dead
      status: ACTIVE
      sub_model_ref: missing.yaml
    - id: SYS-BAD
      name: Bad
      status: ACTIVE
      sub_model_ref: ../outside.yaml
"""))
    _write(tmp_path / "child/model.yaml", _model("child", """  systems:
    - id: SYS-CYCLE
      name: Cycle
      status: ACTIVE
      sub_model_ref: ../.architecture-model.yaml
"""))

    context = ArchitectureViewContext.load(load_model(root_path), tmp_path)

    assert len(context.models) == 2
    assert any("Missing sub-model" in warning.message for warning in context.warnings)
    assert any("Path traversal" in warning.message for warning in context.warnings)
    assert any("cycle" in warning.message.lower() for warning in context.warnings)


def test_context_selectors_do_not_choose_ambiguous_local_id(tmp_path):
    root_path = tmp_path / ".architecture-model.yaml"
    _write(root_path, _model("root", """  components:
    - id: COMP-1
      name: Root Component
      status: ACTIVE
      tags: [featured]
      files: [src/root.py]
    - id: COMP-2
      name: Root Component
      status: ACTIVE
"""))
    context = ArchitectureViewContext.load(load_model(root_path), tmp_path)

    assert context.resolve(local_id="COMP-1").key == "root::COMP-1"
    assert context.select(name="Root Component", system="root") == []
    assert context.select(source_file="src/root.py") == [context.entity("root::COMP-1")]
    assert context.provenance("root::COMP-1")["model"] == "root"


def test_context_indexes_intrinsic_links_and_loads_from_repo(tmp_path):
    root_path = tmp_path / ".architecture-model.yaml"
    _write(root_path, _model("root", """  actors:
    - id: ACT-1
      name: User
      status: ACTIVE
  capabilities:
    - id: CAP-1
      name: Search
      status: ACTIVE
  behaviors:
    - id: BEH-1
      name: Find
      status: ACTIVE
      actor_id: ACT-1
      capability_id: CAP-1
      requirements: [REQ-1]
  requirements:
    - id: REQ-1
      name: Fast results
      status: ACTIVE
"""))

    context = ArchitectureViewContext.from_repo(tmp_path)

    assert context.linked_entities("root::BEH-1") == [
        "root::ACT-1", "root::CAP-1", "root::REQ-1"
    ]


def test_context_indexes_explicit_cross_model_relationships_and_hierarchy(tmp_path):
    root_path = tmp_path / ".architecture-model.yaml"
    _write(root_path, _model("root", """  components:
    - id: ROOT-COMP
      name: Root
      status: ACTIVE
  systems:
    - id: SYS-A
      name: Alpha
      status: ACTIVE
      sub_model_ref: .architecture-models/a/.architecture-model.yaml
""", """  - from: root::ROOT-COMP
    to: a::COMP-1
    type: depends-on
"""))
    _write(tmp_path / ".architecture-models/a/.architecture-model.yaml", _model("a", """  components:
    - id: COMP-1
      name: Child
      status: ACTIVE
  systems:
    - id: SYS-B
      name: Beta
      status: ACTIVE
      sub_model_ref: ../b/.architecture-model.yaml
""", """  - from: COMP-1
    to: b::COMP-2
    type: depends-on
"""))
    _write(tmp_path / ".architecture-models/b/.architecture-model.yaml", _model("b", """  components:
    - id: COMP-2
      name: Grandchild
      status: ACTIVE
"""))

    context = ArchitectureViewContext.from_repo(tmp_path)

    assert context.outgoing("root::ROOT-COMP")[0].target == "a::COMP-1"
    assert context.outgoing("a::COMP-1")[0].target == "b::COMP-2"
    assert context.parent_model("b") == "a"
    assert context.child_models("root") == ["a"]
    assert context.ancestors("b") == ["a", "root"]
    assert context.parent("b") == "a"
    assert context.children("root") == ["a"]
    assert context.qualified_entity("b", "COMP-2").key == "b::COMP-2"
    assert context.qualified_entity("b", "root::ROOT-COMP") is None


def test_unknown_unqualified_relationship_endpoint_is_not_guessed_in_other_model(tmp_path):
    root_path = tmp_path / ".architecture-model.yaml"
    _write(root_path, _model("root", """  systems:
    - id: SYS-A
      name: Alpha
      status: ACTIVE
      sub_model_ref: child.yaml
""", """  - from: COMP-1
    to: SYS-A
    type: depends-on
"""))
    _write(tmp_path / "child.yaml", _model("child", """  components:
    - id: COMP-1
      name: Child only
      status: ACTIVE
"""))

    context = ArchitectureViewContext.from_repo(tmp_path)

    assert context.incoming("root::SYS-A") == []
    assert any("root::COMP-1" in warning.message for warning in context.warnings)


def test_entity_containment_ancestry_is_qualified_cycle_safe_and_separate_from_models(tmp_path):
    root_path = tmp_path / ".architecture-model.yaml"
    _write(root_path, _model("root", """  capabilities:
    - {id: CAP-A, name: A, status: ACTIVE}
    - {id: CAP-B, name: B, status: ACTIVE}
    - {id: CAP-C, name: C, status: ACTIVE}
""", """  - {from: CAP-A, to: CAP-B, type: contains}
  - {from: CAP-B, to: CAP-C, type: contains}
  - {from: CAP-C, to: CAP-A, type: contains}
"""))
    context = ArchitectureViewContext.from_repo(tmp_path)
    assert context.entity_parents("root::CAP-C") == ["root::CAP-B"]
    assert context.entity_children("root::CAP-A") == ["root::CAP-B"]
    assert context.entity_ancestors("root::CAP-C") == ["root::CAP-B", "root::CAP-A"]
    assert context.ancestors("root") == []


def test_missing_and_ambiguous_queries_record_deduplicated_diagnostics(tmp_path):
    context = _context_with_duplicate_names(tmp_path)
    assert context.entity("root::MISSING") is None
    assert context.entity("root::MISSING") is None
    assert context.select(name="Duplicate", system="root") == []
    assert context.select(name="Duplicate", system="root") == []
    assert all(isinstance(item, Diagnostic) for item in context.diagnostics)
    assert [item.code for item in context.diagnostics].count("ENTITY_NOT_FOUND") == 1
    assert [item.code for item in context.diagnostics].count("SELECTOR_AMBIGUOUS") == 1


def _context_with_duplicate_names(tmp_path):
    root_path = tmp_path / ".architecture-model.yaml"
    _write(root_path, _model("root", """  components:
    - {id: COMP-A, name: Duplicate, status: ACTIVE}
    - {id: COMP-B, name: Duplicate, status: ACTIVE}
"""))
    return ArchitectureViewContext.from_repo(tmp_path)
