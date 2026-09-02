from pathlib import Path

from architecture_model.cli.main import main


def test_visualize_cli_always_writes_native_se_svgs(tmp_path: Path) -> None:
    (tmp_path / ".architecture-model.yaml").write_text(
        """meta: {project: cli-visualize, schema_version: '2.0'}
entities:
  actors: [{id: ACT-1, name: User, status: ACTIVE}]
  capabilities: [{id: CAP-1, name: Operate, status: ACTIVE}]
  components: [{id: COMP-1, name: Service, status: ACTIVE}]
  behaviors: [{id: BEH-1, name: Use service, status: ACTIVE, actor_id: ACT-1}]
relationships:
  - {from_id: COMP-1, to_id: CAP-1, type: realizes}
""",
        encoding="utf-8",
    )
    output = tmp_path / "diagrams"

    assert main(["visualize", str(tmp_path), "-o", str(output)]) == 0
    assert {path.name for path in output.glob("*.svg")} == {
        "conops.svg", "functional-architecture.svg", "logical-architecture.svg", "use-cases.svg",
    }
