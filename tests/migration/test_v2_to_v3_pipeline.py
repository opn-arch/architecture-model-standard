"""Tests for CAP-PB-PIPELINE Promise-graph PoC migration (Phase 2 of T0.14).

Validates ``architecture_model.migration.v2_to_v3`` on the Plan B model's
CAP-PB-PIPELINE entity:

- Reads ``.architecture-model.plan-b.yaml`` (schema 2.1)
- Converts CAP-PB-PIPELINE's semantic fields into Promise records
- Writes ``.architecture-model.plan-b.v3-poc.yaml``
- Round-trips: re-reads and asserts every original semantic field is
  present as a Promise with matching content and no data loss

The migration is field-by-field, not free-form: every semantic field
recognized by AMS 2.1 becomes exactly one Promise. Scalar strings emit
a str-content Promise; list fields emit a list-content Promise.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from architecture_model.core.promise import Promise, PromiseStatus
from architecture_model.migration.v2_to_v3 import (
    SEMANTIC_FIELDS,
    migrate_entity_semantic_fields,
    migrate_model_entity,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_B_MODEL = REPO_ROOT / ".architecture-model.plan-b.yaml"
TARGET_ID = "CAP-PB-PIPELINE"


@pytest.fixture(scope="module")
def plan_b_raw() -> dict:
    return yaml.safe_load(PLAN_B_MODEL.read_text())


@pytest.fixture(scope="module")
def cap_pipeline(plan_b_raw: dict) -> dict:
    for cap in plan_b_raw["entities"]["capabilities"]:
        if cap["id"] == TARGET_ID:
            return cap
    raise AssertionError(f"{TARGET_ID} not found in plan-b model")


# ---------------------------------------------------------------------------
# Field-level migration
# ---------------------------------------------------------------------------

def test_migration_covers_all_semantic_fields_present_on_entity(cap_pipeline):
    """Every recognized semantic field on the entity becomes a Promise."""
    promises = migrate_entity_semantic_fields(cap_pipeline, provenance="T0.14.2")
    attrs_out = {p.attribute for p in promises}
    expected = {f for f in SEMANTIC_FIELDS if f in cap_pipeline}
    assert attrs_out == expected


def test_migration_skips_absent_fields(cap_pipeline):
    """Fields NOT present on the entity yield no Promise (no synthetic gaps)."""
    promises = migrate_entity_semantic_fields(cap_pipeline, provenance="T0.14.2")
    attrs_out = {p.attribute for p in promises}
    for missing in set(SEMANTIC_FIELDS) - set(cap_pipeline.keys()):
        assert missing not in attrs_out


def test_migration_preserves_scalar_intent(cap_pipeline):
    promises = migrate_entity_semantic_fields(cap_pipeline, provenance="T0.14.2")
    intent = next(p for p in promises if p.attribute == "intent")
    assert intent.content == cap_pipeline["intent"]
    assert intent.owner_entity == TARGET_ID


def test_migration_preserves_list_goals(cap_pipeline):
    promises = migrate_entity_semantic_fields(cap_pipeline, provenance="T0.14.2")
    goals = next(p for p in promises if p.attribute == "goals")
    assert goals.content == cap_pipeline["goals"]
    assert isinstance(goals.content, list)


def test_migration_preserves_list_ordering(cap_pipeline):
    """Order carries semantics — goals[0] is not interchangeable with goals[1]."""
    promises = migrate_entity_semantic_fields(cap_pipeline, provenance="T0.14.2")
    for attr in ("goals", "success_criteria", "failure_modes"):
        if attr in cap_pipeline:
            p = next(pr for pr in promises if pr.attribute == attr)
            assert p.content == cap_pipeline[attr], f"order changed for {attr}"


def test_migration_stamps_provenance(cap_pipeline):
    promises = migrate_entity_semantic_fields(cap_pipeline, provenance="T0.14.2")
    for p in promises:
        assert p.provenance == "T0.14.2"


def test_migration_default_status_open(cap_pipeline):
    promises = migrate_entity_semantic_fields(cap_pipeline, provenance="T0.14.2")
    for p in promises:
        assert p.status == PromiseStatus.OPEN


def test_migration_all_promises_have_stable_ids(cap_pipeline):
    """PR-<sha1[:12]> ids are deterministic across two migration runs."""
    a = migrate_entity_semantic_fields(cap_pipeline, provenance="T0.14.2")
    b = migrate_entity_semantic_fields(cap_pipeline, provenance="T0.14.2")
    assert [p.id for p in a] == [p.id for p in b]


def test_migration_ids_unique_within_entity(cap_pipeline):
    promises = migrate_entity_semantic_fields(cap_pipeline, provenance="T0.14.2")
    ids = [p.id for p in promises]
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Model-level migration (writes v3 shape)
# ---------------------------------------------------------------------------

def test_migrate_model_entity_produces_promises_alongside_original(cap_pipeline):
    """migrate_model_entity attaches a `promises` list without dropping the
    original semantic fields (2.1 → 3.0 additive during PoC)."""
    migrated = migrate_model_entity(cap_pipeline, provenance="T0.14.2")
    assert "promises" in migrated
    assert isinstance(migrated["promises"], list)
    assert len(migrated["promises"]) > 0
    # Original scalar fields still present (additive migration)
    assert migrated["intent"] == cap_pipeline["intent"]
    assert migrated["goals"] == cap_pipeline["goals"]


def test_migrate_model_entity_promise_dicts_round_trip(cap_pipeline):
    migrated = migrate_model_entity(cap_pipeline, provenance="T0.14.2")
    for p_dict in migrated["promises"]:
        p = Promise.from_dict(p_dict)
        assert p.owner_entity == TARGET_ID


def test_migrate_model_entity_no_data_loss(cap_pipeline):
    """Every semantic field present on the 2.1 entity is recoverable from
    the resulting Promise list."""
    migrated = migrate_model_entity(cap_pipeline, provenance="T0.14.2")
    promises_by_attr = {p["attribute"]: p for p in migrated["promises"]}
    for field in SEMANTIC_FIELDS:
        if field in cap_pipeline:
            assert field in promises_by_attr, f"lost field {field}"
            assert promises_by_attr[field]["content"] == cap_pipeline[field]


# ---------------------------------------------------------------------------
# End-to-end PoC round-trip via YAML (tmp file, not repo file)
# ---------------------------------------------------------------------------

def test_poc_round_trip_via_yaml(cap_pipeline, tmp_path):
    """Write the migrated entity to YAML, read back, assert no data loss."""
    migrated = migrate_model_entity(cap_pipeline, provenance="T0.14.2")
    out_path = tmp_path / "poc.yaml"
    out_path.write_text(yaml.safe_dump(migrated, sort_keys=False))
    reloaded = yaml.safe_load(out_path.read_text())

    assert reloaded["id"] == TARGET_ID
    assert reloaded["intent"] == cap_pipeline["intent"]
    assert len(reloaded["promises"]) == len(migrated["promises"])
    for original, roundtripped in zip(
        migrated["promises"], reloaded["promises"]
    ):
        assert Promise.from_dict(roundtripped) == Promise.from_dict(original)
