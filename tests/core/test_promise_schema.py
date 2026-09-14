"""Schema validation for Promise wire format (T0.14 Phase 1).

Validates that Promise.to_dict() output conforms to
src/architecture_model/spec/promise-graph.schema.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from architecture_model.core.promise import Promise, PromiseStatus

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "architecture_model"
    / "spec"
    / "promise-graph.schema.json"
)


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


@pytest.fixture(scope="module")
def promise_schema(schema: dict) -> dict:
    """Return the Promise sub-schema (for validating single promises)."""
    return {"$ref": "#/$defs/Promise", "$defs": schema["$defs"]}


def _validate_promise(instance: dict, promise_schema: dict) -> None:
    jsonschema.validate(instance=instance, schema=promise_schema)


# ---------------------------------------------------------------------------
# Positive cases
# ---------------------------------------------------------------------------

def test_minimal_promise_validates(promise_schema):
    p = Promise(attribute="intent", content="x", owner_entity="E1")
    _validate_promise(p.to_dict(), promise_schema)


def test_typed_gap_promise_validates(promise_schema):
    p = Promise(
        attribute="verification",
        content="",
        owner_entity="COMP-1",
        status=PromiseStatus.TYPED_GAP,
        gap_type="G-VERIFY",
    )
    _validate_promise(p.to_dict(), promise_schema)


def test_delivered_promise_with_lineage_validates(promise_schema):
    parent = Promise(attribute="intent", content="root", owner_entity="E0")
    child = Promise(
        attribute="intent",
        content="child",
        owner_entity="E1",
        delivered_from=parent.id,
        verified_by=("VER-1", "VER-2"),
        status=PromiseStatus.VERIFIED,
    )
    _validate_promise(child.to_dict(), promise_schema)


def test_list_content_validates(promise_schema):
    p = Promise(
        attribute="goals",
        content=["preserve framing", "keep decisions"],
        owner_entity="CAP-DF-INTENT",
    )
    _validate_promise(p.to_dict(), promise_schema)


# ---------------------------------------------------------------------------
# Negative cases (contract enforcement)
# ---------------------------------------------------------------------------

def test_bad_id_pattern_rejected(promise_schema):
    p = Promise(attribute="intent", content="x", owner_entity="E1").to_dict()
    p["id"] = "NOT-AN-ID"
    with pytest.raises(jsonschema.ValidationError):
        _validate_promise(p, promise_schema)


def test_unknown_status_rejected(promise_schema):
    p = Promise(attribute="intent", content="x", owner_entity="E1").to_dict()
    p["status"] = "bogus"
    with pytest.raises(jsonschema.ValidationError):
        _validate_promise(p, promise_schema)


def test_empty_attribute_rejected(promise_schema):
    p = Promise(attribute="intent", content="x", owner_entity="E1").to_dict()
    p["attribute"] = ""
    with pytest.raises(jsonschema.ValidationError):
        _validate_promise(p, promise_schema)


def test_typed_gap_without_gap_type_rejected(promise_schema):
    # Manually construct — the Promise class refuses at build time, but the
    # schema must independently catch this invariant on the wire.
    bad = {
        "id": "PR-000000000000",
        "attribute": "intent",
        "content": "",
        "owner_entity": "E1",
        "delivered_from": None,
        "verified_by": [],
        "status": "typed-gap",
        "gap_type": None,
        "provenance": "",
    }
    with pytest.raises(jsonschema.ValidationError):
        _validate_promise(bad, promise_schema)


def test_non_gap_with_gap_type_rejected(promise_schema):
    bad = {
        "id": "PR-000000000000",
        "attribute": "intent",
        "content": "x",
        "owner_entity": "E1",
        "delivered_from": None,
        "verified_by": [],
        "status": "open",
        "gap_type": "G-DELIVERY",
        "provenance": "",
    }
    with pytest.raises(jsonschema.ValidationError):
        _validate_promise(bad, promise_schema)


# ---------------------------------------------------------------------------
# PromiseGraph envelope
# ---------------------------------------------------------------------------

def test_promise_graph_envelope_validates(schema):
    p1 = Promise(attribute="intent", content="a", owner_entity="E1")
    p2 = Promise(attribute="goals", content=["x"], owner_entity="E1")
    envelope = {
        "contract_version": "1.0.0",
        "promises": [p1.to_dict(), p2.to_dict()],
    }
    jsonschema.validate(instance=envelope, schema=schema)


def test_promise_graph_requires_contract_version(schema):
    envelope = {"promises": []}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=envelope, schema=schema)


def test_promise_graph_rejects_wrong_contract_version(schema):
    envelope = {"contract_version": "0.9.0", "promises": []}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=envelope, schema=schema)
