"""Task 4 (Phase 2 schema-and-semantic-content): verify schema 2.1 additions.

Guards:
- ``SCHEMA_VERSION`` constant exists in :mod:`architecture_model.spec` and
  equals ``"2.1.0"`` (matches ``schema.json`` ``$id``).
- New ``$defs`` are present: maturity, failure_mode_obj, trade_off_obj,
  slo_obj, requirement_ref_obj, verification_ref_obj, plus union list
  variants (failure_mode_list, trade_off_list, requirement_ref_list,
  verification_ref_list, slo_list).
- Each entity kind that received Phase 2 fields advertises the new
  properties in its ``properties`` block. ``unevaluatedProperties:
  false`` on every entity block means an omission here would silently
  make the new fields un-representable in 2.1 models.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from architecture_model.spec import SCHEMA_VERSION

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "src" / "architecture_model" / "spec" / "schema.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def test_schema_version_constant() -> None:
    assert SCHEMA_VERSION == "2.1.0"


def test_schema_id_matches_version(schema: dict) -> None:
    assert SCHEMA_VERSION in schema["$id"], schema["$id"]


@pytest.mark.parametrize(
    "def_name",
    [
        "maturity",
        "failure_mode_obj",
        "trade_off_obj",
        "slo_obj",
        "requirement_ref_obj",
        "verification_ref_obj",
        "failure_mode_list",
        "trade_off_list",
        "slo_list",
        "requirement_ref_list",
        "verification_ref_list",
    ],
)
def test_semantic_defs_present(schema: dict, def_name: str) -> None:
    assert def_name in schema["$defs"], f"missing $defs/{def_name}"


def test_maturity_enum_values(schema: dict) -> None:
    assert schema["$defs"]["maturity"]["enum"] == [
        "proposal",
        "draft",
        "active",
        "stable",
        "deprecated",
    ]


def test_failure_mode_obj_required_fields(schema: dict) -> None:
    req = set(schema["$defs"]["failure_mode_obj"]["required"])
    assert req == {"id", "cause", "effect", "likelihood", "severity", "detection", "mitigation"}


def test_slo_obj_required_fields(schema: dict) -> None:
    req = set(schema["$defs"]["slo_obj"]["required"])
    assert req == {"metric", "target", "window"}


# --- Entity-kind property coverage ---------------------------------------

COMPONENT_NEW = {
    "stakeholders",
    "success_criteria",
    "assumptions",
    "open_questions",
    "verification",
    "slos",
    "owner",
    "maturity",
    "dependencies_rationale",
}

CAPABILITY_NEW = {
    "stakeholders",
    "success_criteria",
    "assumptions",
    "open_questions",
    "verification",
    "owner",
    "maturity",
}

BEHAVIOR_NEW = {
    "stakeholders",
    "success_criteria",
    "assumptions",
    "open_questions",
    "verification",
    "maturity",
}

INTERFACE_NEW = {
    "stakeholders",
    "success_criteria",
    "assumptions",
    "open_questions",
    "verification",
    "slos",
    "maturity",
}

ACTOR_NEW = {"assumptions", "open_questions"}
CONSTRAINT_NEW = {
    "success_criteria",
    "assumptions",
    "open_questions",
    "verification",
    "maturity",
}
LAYER_NEW = {"owner", "maturity"}


@pytest.mark.parametrize(
    "entity,expected_new",
    [
        ("component", COMPONENT_NEW),
        ("capability", CAPABILITY_NEW),
        ("behavior", BEHAVIOR_NEW),
        ("interface", INTERFACE_NEW),
        ("actor", ACTOR_NEW),
        ("constraint", CONSTRAINT_NEW),
        ("layer", LAYER_NEW),
    ],
)
def test_entity_declares_new_properties(schema: dict, entity: str, expected_new: set[str]) -> None:
    props = set(schema["$defs"][entity]["properties"].keys())
    missing = expected_new - props
    assert not missing, f"{entity} missing Phase 2 fields: {sorted(missing)}"


def test_base_entity_failure_modes_accepts_typed_and_string(schema: dict) -> None:
    fm = schema["$defs"]["base_entity"]["properties"]["failure_modes"]
    assert fm == {"$ref": "#/$defs/failure_mode_list"}


def test_base_entity_trade_offs_accepts_typed_and_string(schema: dict) -> None:
    to_ = schema["$defs"]["base_entity"]["properties"]["trade_offs"]
    assert to_ == {"$ref": "#/$defs/trade_off_list"}


def test_base_entity_requirements_accepts_typed_and_string(schema: dict) -> None:
    r = schema["$defs"]["base_entity"]["properties"]["requirements"]
    assert r["$ref"] == "#/$defs/requirement_ref_list"
