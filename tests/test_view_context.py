from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.view_context import ArchitectureViewContext


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
    assert any("Missing sub-model" in warning for warning in context.warnings)
    assert any("Path traversal" in warning for warning in context.warnings)
    assert any("cycle" in warning.lower() for warning in context.warnings)


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
