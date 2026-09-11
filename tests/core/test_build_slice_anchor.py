"""Track 4 Pass 1 Task 3 — build_slice_anchor factory for the 4 view names."""
import pytest

from architecture_model.core.slice_anchor import build_slice_anchor, VIEW_TO_ARTIFACT
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Status,
    Actor, Capability, Component, Behavior, Layer,
    Relationship, RelationType,
)


@pytest.fixture
def sample_model():
    return ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="2.1"),
        entities=Entities(
            actors=[Actor(id="ACT-1", name="user", status=Status.ACTIVE)],
            capabilities=[Capability(id="CAP-1", name="cap1", status=Status.ACTIVE)],
            behaviors=[Behavior(id="BEH-1", name="beh1", status=Status.ACTIVE)],
            layers=[Layer(id="LAY-1", name="lay1", status=Status.ACTIVE)],
            components=[
                Component(id="COMP-1", name="c1", status=Status.ACTIVE, files=["src/a.py", "src/b.py"]),
                Component(id="COMP-2", name="c2", status=Status.ACTIVE, files=["src/c.py"]),
            ],
        ),
        relationships=[
            Relationship(from_id="COMP-1", to_id="CAP-1", type=RelationType.REALIZES),
            Relationship(from_id="COMP-2", to_id="CAP-1", type=RelationType.REALIZES),
            Relationship(from_id="LAY-1", to_id="COMP-1", type=RelationType.CONTAINS),
        ],
    )


def test_build_anchor_for_functional(sample_model, tmp_path):
    anchor = build_slice_anchor(sample_model, "functional", tmp_path)
    assert anchor.view_name == "functional"
    assert anchor.artifact_name == "functional-architecture"
    cap_ids = {c.id for c in anchor.model.entities.capabilities}
    comp_ids = {c.id for c in anchor.model.entities.components}
    assert "CAP-1" in cap_ids
    assert "COMP-1" in comp_ids  # via realizes closure
    assert "COMP-2" in comp_ids


def test_build_anchor_derives_files_from_sliced_components(sample_model, tmp_path):
    anchor = build_slice_anchor(sample_model, "functional", tmp_path)
    assert anchor.files == ("src/a.py", "src/b.py", "src/c.py")


def test_build_anchor_unknown_view_falls_back(sample_model, tmp_path, caplog):
    import logging
    caplog.set_level(logging.WARNING)
    anchor = build_slice_anchor(sample_model, "no-such-view", tmp_path)
    assert anchor.view_name == "no-such-view"
    assert anchor.artifact_name == ""
    assert len(anchor.model.entities.components) == 2  # full model preserved


def test_build_anchor_for_all_four_view_names_produces_valid_anchors(sample_model, tmp_path):
    for view in VIEW_TO_ARTIFACT:
        anchor = build_slice_anchor(sample_model, view, tmp_path)
        assert anchor.view_name == view
        assert anchor.artifact_name == VIEW_TO_ARTIFACT[view]
        assert isinstance(anchor.files, tuple)
        assert isinstance(anchor.artifacts, tuple)


def test_build_anchor_artifacts_includes_primary_doc_when_present(sample_model, tmp_path):
    doc_dir = tmp_path / ".architecture-models" / "docs" / "se"
    doc_dir.mkdir(parents=True)
    (doc_dir / "functional-analysis.md").write_text("# stub")
    anchor = build_slice_anchor(sample_model, "functional", tmp_path)
    assert ".architecture-models/docs/se/functional-analysis.md" in anchor.artifacts


def test_build_anchor_artifacts_empty_when_docs_absent(sample_model, tmp_path):
    anchor = build_slice_anchor(sample_model, "functional", tmp_path)
    assert anchor.artifacts == ()
