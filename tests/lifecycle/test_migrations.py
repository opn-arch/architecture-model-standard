"""Tests for lifecycle schema migration framework."""
from __future__ import annotations

import copy

import pytest

from architecture_model.lifecycle import migrations as migrations_mod
from architecture_model.lifecycle.migrations import (
    DEFAULT_REGISTRY,
    Migration,
    MigrationCycle,
    MigrationError,
    MigrationPathNotFound,
    MigrationRegistry,
    migrate,
)
from architecture_model.lifecycle.versions import ContractKind, SchemaVersions


def _bumping(from_v: str, to_v: str):
    def _apply(payload: dict) -> dict:
        out = copy.deepcopy(dict(payload))
        out["contract_version"] = to_v
        return out
    return _apply


def test_default_registry_is_empty():
    reg = MigrationRegistry()
    with pytest.raises(MigrationPathNotFound):
        reg.path(ContractKind.MODEL_SLICE, "1.0.0", "1.1.0")
    # DEFAULT_REGISTRY should also be empty by default (no auto-register)
    # We test by asking for any path -> should fail.
    with pytest.raises(MigrationPathNotFound):
        DEFAULT_REGISTRY.path(ContractKind.MODEL_SLICE, "0.0.0", "9.9.9")


def test_register_and_lookup_single_step():
    reg = MigrationRegistry()
    m = Migration(ContractKind.MODEL_SLICE, "1.0.0", "1.1.0", _bumping("1.0.0", "1.1.0"))
    reg.register(m)
    p = reg.path(ContractKind.MODEL_SLICE, "1.0.0", "1.1.0")
    assert p == [m]


def test_register_duplicate_raises():
    reg = MigrationRegistry()
    m1 = Migration(ContractKind.MODEL_SLICE, "1.0.0", "1.1.0", _bumping("1.0.0", "1.1.0"))
    m2 = Migration(ContractKind.MODEL_SLICE, "1.0.0", "1.2.0", _bumping("1.0.0", "1.2.0"))
    reg.register(m1)
    with pytest.raises(MigrationError):
        reg.register(m2)


def test_path_same_version_returns_empty():
    reg = MigrationRegistry()
    assert reg.path(ContractKind.MODEL_SLICE, "1.0.0", "1.0.0") == []


def test_path_multi_step_chain():
    reg = MigrationRegistry()
    m1 = Migration(ContractKind.MODEL_SLICE, "1.0.0", "1.1.0", _bumping("1.0.0", "1.1.0"))
    m2 = Migration(ContractKind.MODEL_SLICE, "1.1.0", "2.0.0", _bumping("1.1.0", "2.0.0"))
    reg.register(m1)
    reg.register(m2)
    assert reg.path(ContractKind.MODEL_SLICE, "1.0.0", "2.0.0") == [m1, m2]


def test_path_no_route_raises_MigrationPathNotFound():
    reg = MigrationRegistry()
    reg.register(Migration(ContractKind.MODEL_SLICE, "1.0.0", "1.1.0", _bumping("1.0.0", "1.1.0")))
    with pytest.raises(MigrationPathNotFound):
        reg.path(ContractKind.MODEL_SLICE, "1.0.0", "2.0.0")


def test_path_cycle_raises_MigrationCycle():
    reg = MigrationRegistry()
    reg.register(Migration(ContractKind.MODEL_SLICE, "1.0.0", "1.1.0", _bumping("1.0.0", "1.1.0")))
    reg.register(Migration(ContractKind.MODEL_SLICE, "1.1.0", "1.0.0", _bumping("1.1.0", "1.0.0")))
    with pytest.raises(MigrationCycle):
        reg.path(ContractKind.MODEL_SLICE, "1.0.0", "2.0.0")


def _make_reg_targeting_current(kind: ContractKind, from_v: str) -> MigrationRegistry:
    """Build a registry with one migration from from_v to SchemaVersions.for_kind(kind)."""
    reg = MigrationRegistry()
    target = SchemaVersions.for_kind(kind)
    reg.register(Migration(kind, from_v, target, _bumping(from_v, target)))
    return reg


def test_migrate_applies_chain_and_records_provenance():
    kind = ContractKind.MODEL_SLICE
    target = SchemaVersions.for_kind(kind)  # 1.0.0
    # Use a synthetic scenario: register 0.9.0 -> current
    reg = MigrationRegistry()
    reg.register(Migration(kind, "0.9.0", target, _bumping("0.9.0", target)))
    payload = {"contract_version": "0.9.0"}
    out, chain = reg.migrate(kind, payload)
    assert out["contract_version"] == target
    assert chain == [f"{kind.value}:0.9.0->{target}"]
    assert out["meta"]["migration_chain"] == [f"{kind.value}:0.9.0->{target}"]


def test_migrate_missing_contract_version_raises():
    reg = MigrationRegistry()
    with pytest.raises(MigrationError):
        reg.migrate(ContractKind.MODEL_SLICE, {})


def test_migrate_step_forgot_to_bump_version_raises():
    kind = ContractKind.MODEL_SLICE
    target = SchemaVersions.for_kind(kind)

    def _bad_apply(payload: dict) -> dict:
        out = copy.deepcopy(dict(payload))
        # forget to bump
        return out

    reg = MigrationRegistry()
    reg.register(Migration(kind, "0.9.0", target, _bad_apply))
    with pytest.raises(MigrationError):
        reg.migrate(kind, {"contract_version": "0.9.0"})


def test_migrate_appends_never_overwrites_migration_chain():
    kind = ContractKind.MODEL_SLICE
    target = SchemaVersions.for_kind(kind)
    reg = MigrationRegistry()
    reg.register(Migration(kind, "0.9.0", target, _bumping("0.9.0", target)))
    payload = {
        "contract_version": "0.9.0",
        "meta": {"migration_chain": ["prior"]},
    }
    out, chain = reg.migrate(kind, payload)
    assert out["meta"]["migration_chain"] == ["prior", f"{kind.value}:0.9.0->{target}"]


def test_migrate_no_op_when_already_at_target():
    kind = ContractKind.MODEL_SLICE
    target = SchemaVersions.for_kind(kind)
    reg = MigrationRegistry()  # isolated, empty
    payload = {"contract_version": target, "meta": {"foo": "bar"}}
    out, chain = reg.migrate(kind, payload)
    assert chain == []
    assert out == payload
    assert out is not payload  # copy


def test_module_level_migrate_delegates_to_default_registry(monkeypatch):
    # Save/restore default registry internal state
    original = dict(DEFAULT_REGISTRY._by_key)
    try:
        kind = ContractKind.MODEL_SLICE
        target = SchemaVersions.for_kind(kind)
        DEFAULT_REGISTRY.register(Migration(kind, "0.9.0", target, _bumping("0.9.0", target)))
        out, chain = migrate(kind, {"contract_version": "0.9.0"})
        assert out["contract_version"] == target
        assert chain == [f"{kind.value}:0.9.0->{target}"]
    finally:
        DEFAULT_REGISTRY._by_key.clear()
        DEFAULT_REGISTRY._by_key.update(original)


def test_migration_id_format():
    kind = ContractKind.MODEL_SLICE
    target = SchemaVersions.for_kind(kind)
    reg = MigrationRegistry()
    reg.register(Migration(kind, "0.9.0", target, _bumping("0.9.0", target)))
    _out, chain = reg.migrate(kind, {"contract_version": "0.9.0"})
    assert chain[0] == f"{kind.value}:0.9.0->{target}"
