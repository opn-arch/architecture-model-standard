"""Track 4 Pass 1 Task 1 — SliceAnchor dataclass and view/artifact constants."""
from architecture_model.core.slice_anchor import (
    SliceAnchor,
    VIEW_TO_ARTIFACT,
    ARTIFACT_TO_DOC,
)
from architecture_model.core.types import ArchitectureModel, Entities, ModelMeta


def _empty_model() -> ArchitectureModel:
    return ArchitectureModel(meta=ModelMeta(project="t", schema_version="2.1"), entities=Entities(), relationships=[])


def test_view_to_artifact_covers_all_four_views():
    assert set(VIEW_TO_ARTIFACT.keys()) == {"conops", "functional", "logical", "use_cases"}
    assert VIEW_TO_ARTIFACT["functional"] == "functional-architecture"
    assert VIEW_TO_ARTIFACT["logical"] == "logical-architecture"
    assert VIEW_TO_ARTIFACT["use_cases"] == "use-cases"
    assert VIEW_TO_ARTIFACT["conops"] == "conops"


def test_artifact_to_doc_covers_all_four_artifacts():
    assert set(ARTIFACT_TO_DOC.keys()) == {
        "conops", "functional-architecture", "logical-architecture", "use-cases"
    }
    for path in ARTIFACT_TO_DOC.values():
        assert path.startswith(".architecture-models/docs/se/")
        assert path.endswith(".md")


def test_slice_anchor_is_frozen_dataclass():
    anchor = SliceAnchor(
        view_name="functional",
        artifact_name="functional-architecture",
        model=_empty_model(),
        files=(),
        artifacts=(),
    )
    assert anchor.view_name == "functional"
    assert anchor.files == ()
    import dataclasses
    with __import__("pytest").raises(dataclasses.FrozenInstanceError):
        anchor.view_name = "logical"
