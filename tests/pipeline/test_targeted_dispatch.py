"""targeted_extract(changed_files, repo_root) → dispatch plan."""

from pathlib import Path

from architecture_model.pipeline.targeted import compute_dispatch_plan


def test_single_file_maps_to_single_subsystem(tmp_path):
    # Simulate a repo with 2 M2 sub-models
    (tmp_path / ".architecture-models" / "core").mkdir(parents=True)
    (tmp_path / ".architecture-models" / "core" / ".architecture-model.yaml").write_text(
        "meta: {project: t, schema_version: '1.3'}\n"
        "entities:\n  components:\n"
        "    - {id: COMP-1, name: Parser, status: ACTIVE, files: [src/pkg/core/parser.py]}\n"
        "relationships: []\n"
    )
    (tmp_path / ".architecture-models" / "manifest").mkdir(parents=True)
    (tmp_path / ".architecture-models" / "manifest" / ".architecture-model.yaml").write_text(
        "meta: {project: t, schema_version: '1.3'}\n"
        "entities:\n  components:\n"
        "    - {id: COMP-2, name: Scanner, status: ACTIVE, files: [src/pkg/manifest/scanner.py]}\n"
        "relationships: []\n"
    )

    plan = compute_dispatch_plan(
        changed_files=[Path("src/pkg/core/parser.py")],
        repo_root=tmp_path,
    )
    assert plan.subsystems_to_extract == ["core"]
    assert plan.needs_m1_aggregation is True


def test_unknown_file_flags_investigation(tmp_path):
    (tmp_path / ".architecture-models").mkdir()
    plan = compute_dispatch_plan(
        changed_files=[Path("src/new/module.py")],
        repo_root=tmp_path,
    )
    assert plan.subsystems_to_extract == []
    assert plan.unknown_files == [Path("src/new/module.py")]
    assert plan.needs_m1_aggregation is True  # M1 must investigate new file
