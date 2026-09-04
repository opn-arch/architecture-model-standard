"""Tests for model/manifest revision pairing helpers."""

from __future__ import annotations

import copy

import pytest

from architecture_model.lifecycle.pairing import (
    MANIFEST_VOLATILE_PATHS,
    MODEL_VOLATILE_PATHS,
    PairingMismatch,
    assert_cross_system_files,
    compute_manifest_digest,
    compute_model_digest,
    stamp_pairing,
    verify_pairing,
)
from architecture_model.lifecycle.versions import SchemaVersions


def _sample_model() -> dict:
    return {
        "meta": {
            "project": "demo",
            "schema_version": "2.0",
            "generated_at": "2026-09-03T00:00:00Z",
            "signatures": {"author": "alice"},
        },
        "entities": {
            "components": [{"id": "COMP-1", "name": "Core", "status": "ACTIVE"}],
        },
        "relationships": [],
    }


def _sample_manifest() -> dict:
    return {
        "generated_at": "2026-09-03T00:00:00Z",
        "signatures": {"author": "alice"},
        "modules": [{"path": "src/x.py", "functions": []}],
    }


def test_compute_model_digest_deterministic():
    m = _sample_model()
    assert compute_model_digest(m) == compute_model_digest(copy.deepcopy(m))


def test_compute_model_digest_excludes_signatures_and_generated_at():
    m1 = _sample_model()
    d1 = compute_model_digest(m1)
    m2 = _sample_model()
    m2["meta"]["generated_at"] = "2099-01-01T00:00:00Z"
    m2["meta"]["signatures"] = {"author": "bob"}
    assert compute_model_digest(m2) == d1


def test_compute_manifest_digest_excludes_top_level_signatures_and_generated_at():
    m1 = _sample_manifest()
    d1 = compute_manifest_digest(m1)
    m2 = _sample_manifest()
    m2["generated_at"] = "2099-01-01T00:00:00Z"
    m2["signatures"] = {"author": "bob"}
    assert compute_manifest_digest(m2) == d1


def test_stamp_pairing_populates_both_blocks():
    model, manifest = stamp_pairing(_sample_model(), _sample_manifest())
    assert model["meta"]["manifest_digest"]
    assert manifest["pairing"]["model_digest"]
    assert manifest["pairing"]["algo"] == SchemaVersions.DIGEST_ALGO


def test_stamp_pairing_idempotent():
    m1, mf1 = stamp_pairing(_sample_model(), _sample_manifest())
    m2, mf2 = stamp_pairing(m1, mf1)
    assert m1["meta"]["manifest_digest"] == m2["meta"]["manifest_digest"]
    assert mf1["pairing"]["model_digest"] == mf2["pairing"]["model_digest"]


def test_verify_pairing_passes_for_stamped_pair():
    model, manifest = stamp_pairing(_sample_model(), _sample_manifest())
    verify_pairing(model, manifest)


def test_verify_pairing_fails_on_model_mutation():
    model, manifest = stamp_pairing(_sample_model(), _sample_manifest())
    model["entities"]["components"][0]["name"] = "Mutated"
    with pytest.raises(PairingMismatch):
        verify_pairing(model, manifest)


def test_verify_pairing_fails_on_manifest_mutation():
    model, manifest = stamp_pairing(_sample_model(), _sample_manifest())
    manifest["modules"].append({"path": "src/y.py", "functions": []})
    with pytest.raises(PairingMismatch):
        verify_pairing(model, manifest)


def test_verify_pairing_fails_on_missing_pairing_block():
    model, manifest = stamp_pairing(_sample_model(), _sample_manifest())
    del manifest["pairing"]
    with pytest.raises(PairingMismatch, match="missing"):
        verify_pairing(model, manifest)


def test_verify_pairing_fails_on_missing_manifest_digest_meta():
    model, manifest = stamp_pairing(_sample_model(), _sample_manifest())
    del model["meta"]["manifest_digest"]
    with pytest.raises(PairingMismatch, match="missing"):
        verify_pairing(model, manifest)


def test_digest_algo_tag_matches_schema_versions():
    _, manifest = stamp_pairing(_sample_model(), _sample_manifest())
    assert manifest["pairing"]["algo"] == SchemaVersions.DIGEST_ALGO


def test_assert_cross_system_files_returns_empty_when_absent():
    assert assert_cross_system_files({"modules": []}) == []


def test_assert_cross_system_files_returns_list_when_present():
    m = {"cross_system_files": ["src/shared/a.py", "src/shared/b.py"]}
    assert assert_cross_system_files(m) == ["src/shared/a.py", "src/shared/b.py"]


def test_verify_pairing_tolerates_volatile_field_changes():
    model, manifest = stamp_pairing(_sample_model(), _sample_manifest())
    model["meta"]["generated_at"] = "2099-12-31T23:59:59Z"
    model["meta"]["signatures"] = {"author": "changed"}
    manifest["generated_at"] = "2099-12-31T23:59:59Z"
    manifest["signatures"] = {"author": "changed"}
    verify_pairing(model, manifest)


def test_volatile_paths_constants_shape():
    assert MODEL_VOLATILE_PATHS == (("meta", "generated_at"), ("meta", "signatures"))
    assert MANIFEST_VOLATILE_PATHS == (("generated_at",), ("signatures",))
