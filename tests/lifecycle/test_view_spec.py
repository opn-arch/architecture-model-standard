"""Tests for the ViewSpec contract (T15)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from architecture_model.lifecycle.view_spec import (
    SliceRef,
    ViewCuration,
    ViewSpec,
    compute_view_spec_digest,
)
from architecture_model.lifecycle.versions import SchemaVersions


def _minimum_view(**overrides):
    kwargs = dict(
        id="view-conops-1",
        slice_ref=SliceRef(slice_id="slice-1", model_revision="sha256-v1:abc"),
        projector="se.conops",
        output_content_kind="diagram",
    )
    kwargs.update(overrides)
    return ViewSpec(**kwargs)


def test_construct_valid_minimum():
    v = _minimum_view()
    assert v.id == "view-conops-1"
    assert v.contract_version == SchemaVersions.VIEW_SPEC
    assert v.projector_config == {}
    assert v.parameters == {}
    assert v.generated_at is None
    assert v.signatures is None
    assert isinstance(v.curation, ViewCuration)


def test_reject_id_with_spaces():
    with pytest.raises(ValidationError):
        _minimum_view(id="bad id")


def test_reject_empty_id():
    with pytest.raises(ValidationError):
        _minimum_view(id="")


def test_reject_wrong_contract_version():
    with pytest.raises(ValidationError) as ei:
        _minimum_view(contract_version="99.99.99")
    msg = str(ei.value)
    assert "99.99.99" in msg
    assert SchemaVersions.VIEW_SPEC in msg


def test_reject_empty_slice_id():
    with pytest.raises(ValidationError):
        _minimum_view(slice_ref=SliceRef(slice_id="", model_revision="rev"))


def test_reject_slice_id_with_spaces():
    with pytest.raises(ValidationError):
        _minimum_view(slice_ref=SliceRef(slice_id="bad id", model_revision="rev"))


def test_reject_empty_model_revision():
    """Critical invariant: ViewSpec is bound to an immutable slice revision."""
    with pytest.raises(ValidationError):
        _minimum_view(slice_ref=SliceRef(slice_id="s1", model_revision=""))


def test_reject_missing_model_revision():
    with pytest.raises(ValidationError):
        SliceRef(slice_id="s1")  # type: ignore[call-arg]


def test_reject_empty_projector():
    with pytest.raises(ValidationError):
        _minimum_view(projector="")


@pytest.mark.parametrize("kind", ["diagram", "prose", "table"])
def test_output_content_kind_accepted(kind):
    v = _minimum_view(output_content_kind=kind)
    assert v.output_content_kind == kind


def test_reject_unknown_output_content_kind():
    with pytest.raises(ValidationError):
        _minimum_view(output_content_kind="video")


def test_reject_extra_field_root():
    with pytest.raises(ValidationError):
        ViewSpec(
            id="v1",
            slice_ref=SliceRef(slice_id="s1", model_revision="r"),
            projector="p",
            output_content_kind="diagram",
            unknown="oops",
        )


def test_reject_extra_field_slice_ref():
    with pytest.raises(ValidationError):
        SliceRef(slice_id="s1", model_revision="r", extra="x")  # type: ignore[call-arg]


def test_reject_extra_field_curation():
    with pytest.raises(ValidationError):
        ViewCuration(extra="x")  # type: ignore[call-arg]


def test_frozen():
    v = _minimum_view()
    with pytest.raises(ValidationError):
        v.id = "other"  # type: ignore[misc]


def test_digest_deterministic():
    a = _minimum_view()
    b = _minimum_view()
    assert compute_view_spec_digest(a) == compute_view_spec_digest(b)


def test_digest_excludes_generated_at_and_signatures():
    a = _minimum_view()
    b = _minimum_view(
        generated_at="2026-09-03T12:00:00Z",
        signatures=[{"alg": "ed25519", "sig": "aaa"}],
    )
    assert compute_view_spec_digest(a) == compute_view_spec_digest(b)


def test_digest_changes_when_projector_config_changes():
    a = _minimum_view(projector_config={})
    b = _minimum_view(projector_config={"depth": 2})
    assert compute_view_spec_digest(a) != compute_view_spec_digest(b)


def test_digest_changes_when_model_revision_changes():
    a = _minimum_view(slice_ref=SliceRef(slice_id="s1", model_revision="rev-a"))
    b = _minimum_view(slice_ref=SliceRef(slice_id="s1", model_revision="rev-b"))
    assert compute_view_spec_digest(a) != compute_view_spec_digest(b)


# --- JSON Schema tests ---

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "architecture_model"
    / "spec"
    / "view-spec.schema.json"
)


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _valid_dict():
    return {
        "id": "view-1",
        "contract_version": SchemaVersions.VIEW_SPEC,
        "slice_ref": {"slice_id": "slice-1", "model_revision": "sha256-v1:abc"},
        "projector": "se.conops",
        "projector_config": {},
        "curation": {},
        "parameters": {},
        "output_content_kind": "diagram",
    }


def test_schema_loads_and_accepts_valid():
    from jsonschema import Draft202012Validator

    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_valid_dict())


def test_schema_rejects_extra_top_level_field():
    from jsonschema import Draft202012Validator, ValidationError as JSErr

    v = Draft202012Validator(_load_schema())
    d = _valid_dict()
    d["nope"] = 1
    with pytest.raises(JSErr):
        v.validate(d)


def test_schema_rejects_invalid_output_content_kind():
    from jsonschema import Draft202012Validator, ValidationError as JSErr

    v = Draft202012Validator(_load_schema())
    d = _valid_dict()
    d["output_content_kind"] = "video"
    with pytest.raises(JSErr):
        v.validate(d)


def test_schema_rejects_empty_model_revision():
    from jsonschema import Draft202012Validator, ValidationError as JSErr

    v = Draft202012Validator(_load_schema())
    d = _valid_dict()
    d["slice_ref"]["model_revision"] = ""
    with pytest.raises(JSErr):
        v.validate(d)


def test_schema_rejects_extra_field_on_slice_ref():
    from jsonschema import Draft202012Validator, ValidationError as JSErr

    v = Draft202012Validator(_load_schema())
    d = _valid_dict()
    d["slice_ref"]["extra"] = "x"
    with pytest.raises(JSErr):
        v.validate(d)
