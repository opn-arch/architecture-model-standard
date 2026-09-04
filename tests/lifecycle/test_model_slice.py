"""Tests for the ModelSlice contract (T13)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from architecture_model.lifecycle.model_slice import (
    ModelSlice,
    Selectors,
    Curation,
    compute_slice_digest,
)
from architecture_model.lifecycle.versions import SchemaVersions


def _minimum_slice(**overrides):
    kwargs = dict(
        id="slice-core-1",
        architecture_id="pkg-root",
        model_revision="sha256-v1:abc",
        scope="local",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_kinds=["component"]),
        curation=Curation(),
    )
    kwargs.update(overrides)
    return ModelSlice(**kwargs)


def test_construct_valid_minimum():
    s = _minimum_slice()
    assert s.id == "slice-core-1"
    assert s.contract_version == SchemaVersions.MODEL_SLICE
    assert s.parameters == {}
    assert s.generated_at is None
    assert s.signatures is None


def test_reject_id_with_spaces():
    with pytest.raises(ValidationError):
        _minimum_slice(id="bad id")


def test_reject_empty_id():
    with pytest.raises(ValidationError):
        _minimum_slice(id="")


def test_reject_wrong_contract_version():
    with pytest.raises(ValidationError) as ei:
        _minimum_slice(contract_version="99.99.99")
    msg = str(ei.value)
    assert "99.99.99" in msg
    assert SchemaVersions.MODEL_SLICE in msg


def test_federated_requires_bounding_selector():
    with pytest.raises(ValidationError):
        _minimum_slice(
            scope="federated",
            selectors=Selectors(entity_kinds=["component"]),  # not bounding
        )
    # OK with entity_ids
    s = _minimum_slice(
        scope="federated",
        selectors=Selectors(entity_ids=["COMP-1"]),
    )
    assert s.scope == "federated"


def test_empty_selectors_rejected():
    with pytest.raises(ValidationError):
        _minimum_slice(selectors=Selectors())


@pytest.mark.parametrize("scope", ["local", "descendants", "federated"])
def test_scope_enum_accepted(scope):
    sels = (
        Selectors(entity_ids=["X"])
        if scope == "federated"
        else Selectors(entity_kinds=["component"])
    )
    s = _minimum_slice(scope=scope, selectors=sels)
    assert s.scope == scope


@pytest.mark.parametrize("closure", ["strict", "boundary-stubs", "transitive"])
def test_closure_enum_accepted(closure):
    assert _minimum_slice(closure=closure).closure == closure


@pytest.mark.parametrize("sr", ["none", "explicit", "transitive"])
def test_shared_refs_enum_accepted(sr):
    assert _minimum_slice(shared_refs=sr).shared_refs == sr


def test_reject_unknown_enum():
    with pytest.raises(ValidationError):
        _minimum_slice(scope="global")
    with pytest.raises(ValidationError):
        _minimum_slice(closure="loose")
    with pytest.raises(ValidationError):
        _minimum_slice(shared_refs="all")


def test_reject_extra_field():
    with pytest.raises(ValidationError):
        ModelSlice(
            id="s1",
            architecture_id="pkg",
            model_revision="x",
            scope="local",
            closure="strict",
            shared_refs="none",
            selectors=Selectors(entity_kinds=["component"]),
            curation=Curation(),
            unknown_field="oops",
        )


def test_digest_deterministic():
    a = _minimum_slice()
    b = _minimum_slice()
    assert compute_slice_digest(a) == compute_slice_digest(b)


def test_digest_excludes_generated_at_and_signatures():
    a = _minimum_slice()
    b = _minimum_slice(
        generated_at="2026-09-03T12:00:00Z",
        signatures=[{"alg": "ed25519", "sig": "aaa"}],
    )
    assert compute_slice_digest(a) == compute_slice_digest(b)


def test_digest_changes_when_selector_changes():
    a = _minimum_slice(selectors=Selectors(entity_kinds=["component"]))
    b = _minimum_slice(selectors=Selectors(entity_kinds=["capability"]))
    assert compute_slice_digest(a) != compute_slice_digest(b)


def test_frozen():
    s = _minimum_slice()
    with pytest.raises(ValidationError):
        s.id = "other"  # type: ignore[misc]


# --- JSON Schema tests ---

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "architecture_model"
    / "spec"
    / "model-slice.schema.json"
)


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _valid_dict():
    return {
        "id": "slice-1",
        "contract_version": SchemaVersions.MODEL_SLICE,
        "architecture_id": "pkg-root",
        "model_revision": "sha256-v1:abc",
        "scope": "local",
        "closure": "strict",
        "shared_refs": "none",
        "selectors": {"entity_kinds": ["component"]},
        "curation": {},
        "parameters": {},
    }


def test_schema_loads_and_accepts_valid_slice():
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


def test_schema_rejects_invalid_enum():
    from jsonschema import Draft202012Validator, ValidationError as JSErr

    v = Draft202012Validator(_load_schema())
    d = _valid_dict()
    d["scope"] = "global"
    with pytest.raises(JSErr):
        v.validate(d)
