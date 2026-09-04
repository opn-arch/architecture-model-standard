"""Tests for the ArtifactSpec contract (T17)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from architecture_model.lifecycle.artifact_spec import (
    ArtifactSpec,
    SignatureSlot,
    ViewRef,
    compute_artifact_spec_digest,
)
from architecture_model.lifecycle.versions import SchemaVersions


def _view_ref(**overrides):
    kwargs = dict(view_id="view-1", model_revision="sha256-v1:abc")
    kwargs.update(overrides)
    return ViewRef(**kwargs)


def _non_zip(**overrides):
    kwargs = dict(
        id="artifact-svg-1",
        contract_version=SchemaVersions.ARTIFACT_SPEC,
        renderer="svg",
        view_ref=_view_ref(),
    )
    kwargs.update(overrides)
    return ArtifactSpec(**kwargs)


def _zip(**overrides):
    kwargs = dict(
        id="artifact-zip-1",
        contract_version=SchemaVersions.ARTIFACT_SPEC,
        renderer="zip",
        bundle_refs=["artifact-svg-1", "artifact-md-1"],
    )
    kwargs.update(overrides)
    return ArtifactSpec(**kwargs)


# --- construction ---

def test_construct_valid_non_zip():
    a = _non_zip()
    assert a.renderer == "svg"
    assert a.view_ref is not None
    assert a.bundle_refs is None
    assert a.parameters == {}
    assert a.signature_slots == []
    assert a.generated_at is None


def test_construct_valid_zip():
    a = _zip()
    assert a.renderer == "zip"
    assert a.view_ref is None
    assert a.bundle_refs == ["artifact-svg-1", "artifact-md-1"]


@pytest.mark.parametrize("renderer", ["svg", "markdown", "html", "ai-context"])
def test_all_non_zip_renderers_accepted(renderer):
    a = _non_zip(renderer=renderer, id=f"a-{renderer}")
    assert a.renderer == renderer


def test_zip_renderer_accepted():
    a = _zip()
    assert a.renderer == "zip"


def test_reject_unknown_renderer():
    with pytest.raises(ValidationError):
        _non_zip(renderer="pdf")


# --- id / version validation ---

def test_reject_bad_id_with_spaces():
    with pytest.raises(ValidationError):
        _non_zip(id="bad id")


def test_reject_empty_id():
    with pytest.raises(ValidationError):
        _non_zip(id="")


def test_reject_wrong_contract_version():
    with pytest.raises(ValidationError) as ei:
        _non_zip(contract_version="99.99.99")
    assert "99.99.99" in str(ei.value)


# --- zip vs non-zip mutual exclusion ---

def test_reject_zip_with_view_ref():
    with pytest.raises(ValidationError):
        ArtifactSpec(
            id="a1",
            contract_version=SchemaVersions.ARTIFACT_SPEC,
            renderer="zip",
            view_ref=_view_ref(),
            bundle_refs=["x"],
        )


def test_reject_non_zip_without_view_ref():
    with pytest.raises(ValidationError):
        ArtifactSpec(
            id="a1",
            contract_version=SchemaVersions.ARTIFACT_SPEC,
            renderer="svg",
        )


def test_reject_non_zip_with_non_empty_bundle_refs():
    with pytest.raises(ValidationError):
        ArtifactSpec(
            id="a1",
            contract_version=SchemaVersions.ARTIFACT_SPEC,
            renderer="svg",
            view_ref=_view_ref(),
            bundle_refs=["x"],
        )


def test_non_zip_with_empty_bundle_refs_ok():
    # empty list treated as absent
    a = ArtifactSpec(
        id="a1",
        contract_version=SchemaVersions.ARTIFACT_SPEC,
        renderer="svg",
        view_ref=_view_ref(),
        bundle_refs=[],
    )
    assert a.bundle_refs == [] or a.bundle_refs is None


def test_reject_zip_with_empty_bundle_refs():
    with pytest.raises(ValidationError):
        ArtifactSpec(
            id="a1",
            contract_version=SchemaVersions.ARTIFACT_SPEC,
            renderer="zip",
            bundle_refs=[],
        )


def test_reject_zip_missing_bundle_refs():
    with pytest.raises(ValidationError):
        ArtifactSpec(
            id="a1",
            contract_version=SchemaVersions.ARTIFACT_SPEC,
            renderer="zip",
        )


def test_reject_bundle_ref_with_spaces():
    with pytest.raises(ValidationError):
        _zip(bundle_refs=["bad id"])


# --- view_ref validation ---

def test_reject_empty_view_id():
    with pytest.raises(ValidationError):
        _non_zip(view_ref=ViewRef(view_id="", model_revision="r"))


def test_reject_view_id_with_spaces():
    with pytest.raises(ValidationError):
        _non_zip(view_ref=ViewRef(view_id="bad id", model_revision="r"))


def test_reject_empty_model_revision():
    with pytest.raises(ValidationError):
        _non_zip(view_ref=ViewRef(view_id="v1", model_revision=""))


# --- frozen / extra ---

def test_frozen():
    a = _non_zip()
    with pytest.raises(ValidationError):
        a.id = "x"  # type: ignore[misc]


def test_reject_extra_field_root():
    with pytest.raises(ValidationError):
        ArtifactSpec(
            id="a1",
            contract_version=SchemaVersions.ARTIFACT_SPEC,
            renderer="svg",
            view_ref=_view_ref(),
            extra="x",
        )


def test_reject_extra_field_view_ref():
    with pytest.raises(ValidationError):
        ViewRef(view_id="v", model_revision="r", extra="x")  # type: ignore[call-arg]


def test_reject_extra_field_signature_slot():
    with pytest.raises(ValidationError):
        SignatureSlot(algorithm="ed25519", key_id="k1", extra="x")  # type: ignore[call-arg]


# --- digest ---

def test_digest_deterministic():
    a = _non_zip()
    b = _non_zip()
    assert compute_artifact_spec_digest(a) == compute_artifact_spec_digest(b)


def test_digest_excludes_generated_at():
    a = _non_zip()
    b = _non_zip(generated_at="2026-09-03T12:00:00Z")
    assert compute_artifact_spec_digest(a) == compute_artifact_spec_digest(b)


def test_digest_excludes_signature_values():
    slot_empty = SignatureSlot(algorithm="ed25519", key_id="k1")
    slot_signed = SignatureSlot(algorithm="ed25519", key_id="k1", signature="deadbeef")
    a = _non_zip(signature_slots=[slot_empty])
    b = _non_zip(signature_slots=[slot_signed])
    assert compute_artifact_spec_digest(a) == compute_artifact_spec_digest(b)


def test_digest_includes_signature_slot_algorithm_key_id():
    a = _non_zip(signature_slots=[SignatureSlot(algorithm="ed25519", key_id="k1")])
    b = _non_zip(signature_slots=[SignatureSlot(algorithm="ed25519", key_id="k2")])
    assert compute_artifact_spec_digest(a) != compute_artifact_spec_digest(b)


def test_digest_changes_on_parameters_change():
    a = _non_zip(parameters={})
    b = _non_zip(parameters={"depth": 2})
    assert compute_artifact_spec_digest(a) != compute_artifact_spec_digest(b)


def test_digest_changes_on_model_revision_change():
    a = _non_zip(view_ref=_view_ref(model_revision="rev-a"))
    b = _non_zip(view_ref=_view_ref(model_revision="rev-b"))
    assert compute_artifact_spec_digest(a) != compute_artifact_spec_digest(b)


# --- JSON Schema ---

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "architecture_model"
    / "spec"
    / "artifact-spec.schema.json"
)


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _valid_non_zip_dict():
    return {
        "id": "a1",
        "contract_version": SchemaVersions.ARTIFACT_SPEC,
        "renderer": "svg",
        "view_ref": {"view_id": "v1", "model_revision": "sha256-v1:abc"},
    }


def _valid_zip_dict():
    return {
        "id": "a1",
        "contract_version": SchemaVersions.ARTIFACT_SPEC,
        "renderer": "zip",
        "bundle_refs": ["a2", "a3"],
    }


def test_schema_loads_and_accepts_valid_non_zip():
    from jsonschema import Draft202012Validator

    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_valid_non_zip_dict())


def test_schema_accepts_valid_zip():
    from jsonschema import Draft202012Validator

    Draft202012Validator(_load_schema()).validate(_valid_zip_dict())


def test_schema_rejects_zip_missing_bundle_refs():
    from jsonschema import Draft202012Validator, ValidationError as JSErr

    v = Draft202012Validator(_load_schema())
    d = {
        "id": "a1",
        "contract_version": SchemaVersions.ARTIFACT_SPEC,
        "renderer": "zip",
    }
    with pytest.raises(JSErr):
        v.validate(d)


def test_schema_rejects_non_zip_missing_view_ref():
    from jsonschema import Draft202012Validator, ValidationError as JSErr

    v = Draft202012Validator(_load_schema())
    d = {
        "id": "a1",
        "contract_version": SchemaVersions.ARTIFACT_SPEC,
        "renderer": "svg",
    }
    with pytest.raises(JSErr):
        v.validate(d)


def test_schema_rejects_invalid_renderer():
    from jsonschema import Draft202012Validator, ValidationError as JSErr

    v = Draft202012Validator(_load_schema())
    d = _valid_non_zip_dict()
    d["renderer"] = "pdf"
    with pytest.raises(JSErr):
        v.validate(d)


def test_schema_rejects_extra_field_root():
    from jsonschema import Draft202012Validator, ValidationError as JSErr

    v = Draft202012Validator(_load_schema())
    d = _valid_non_zip_dict()
    d["nope"] = 1
    with pytest.raises(JSErr):
        v.validate(d)


def test_schema_rejects_extra_field_view_ref():
    from jsonschema import Draft202012Validator, ValidationError as JSErr

    v = Draft202012Validator(_load_schema())
    d = _valid_non_zip_dict()
    d["view_ref"]["extra"] = "x"
    with pytest.raises(JSErr):
        v.validate(d)


def test_schema_rejects_extra_field_signature_slot():
    from jsonschema import Draft202012Validator, ValidationError as JSErr

    v = Draft202012Validator(_load_schema())
    d = _valid_non_zip_dict()
    d["signature_slots"] = [{"algorithm": "ed25519", "key_id": "k", "extra": "x"}]
    with pytest.raises(JSErr):
        v.validate(d)
