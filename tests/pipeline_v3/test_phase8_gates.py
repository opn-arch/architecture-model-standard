"""Phase 8 quality gates for pipeline_v3 self-model (T0.14).

Regression harness: running pipeline_v3 against the repo must produce a
structurally valid v3 model and be byte-identical across two runs under
a pinned AMS_DETERMINISTIC_NOW.

These gates run every CI cycle. They do NOT require chain-closure to
reach 100% (evidence binding is a separate progression) — they only
require that the model produced is coherent and deterministic.

Kept in tests/pipeline_v3/ so they share the pipeline_v3 test tree.
Deliberately isolated from `test_orchestrator.py` (which uses tiny
synthetic repos) — this file exercises the *real* AMS tree.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from architecture_model.core.promise import Promise, compute_promise_id
from architecture_model.pipeline_v3.orchestrator import run_pipeline

REPO_ROOT = Path(__file__).resolve().parents[2]
PINNED_NOW = "2026-09-14T00:00:00Z"


@pytest.fixture(scope="module")
def self_model(tmp_path_factory) -> dict:
    """Run pipeline_v3 on the repo root and return the parsed YAML doc."""
    out = tmp_path_factory.mktemp("phase8") / "arch.yaml"
    env_prev = os.environ.get("AMS_DETERMINISTIC_NOW")
    os.environ["AMS_DETERMINISTIC_NOW"] = PINNED_NOW
    try:
        run_pipeline(
            REPO_ROOT,
            out_path=out,
            project_name="architecture-model-standard",
            cluster_depth=3,
        )
        return yaml.safe_load(out.read_text())
    finally:
        if env_prev is None:
            os.environ.pop("AMS_DETERMINISTIC_NOW", None)
        else:
            os.environ["AMS_DETERMINISTIC_NOW"] = env_prev


# ---------------------------------------------------------------------------
# Structural gates
# ---------------------------------------------------------------------------


def test_self_model_has_v3_schema_version(self_model):
    assert self_model["meta"]["schema_version"] == "3.0"


def test_self_model_has_expected_top_level_keys(self_model):
    assert set(self_model) >= {"meta", "entities", "relationships"}


def test_self_model_meta_stamps_pipeline_v3(self_model):
    assert self_model["meta"]["generated_by"] == "pipeline_v3"


def test_self_model_has_at_least_one_component(self_model):
    assert len(self_model["entities"]["components"]) >= 1


def test_self_model_component_has_required_fields(self_model):
    for comp in self_model["entities"]["components"]:
        assert set(comp) >= {"id", "name", "root_prefix", "module_names", "promises"}
        assert comp["id"].startswith("COMP-")


def test_self_model_promise_ids_are_deterministic(self_model):
    """Every Promise's id must match compute_promise_id(attribute, content, owner)."""
    for comp in self_model["entities"]["components"]:
        for p in comp["promises"]:
            expected = compute_promise_id(p["attribute"], p["content"], p["owner_entity"])
            assert p["id"] == expected, (
                f"Promise id mismatch: got {p['id']!r} expected {expected!r} "
                f"for attribute={p['attribute']!r} owner={p['owner_entity']!r}"
            )


def test_self_model_promise_owner_matches_containing_component(self_model):
    for comp in self_model["entities"]["components"]:
        for p in comp["promises"]:
            assert p["owner_entity"] == comp["id"], (
                f"Promise {p['id']} owner_entity={p['owner_entity']!r} "
                f"does not match containing component {comp['id']!r}"
            )


def test_self_model_promise_ids_are_globally_unique(self_model):
    seen = set()
    for comp in self_model["entities"]["components"]:
        for p in comp["promises"]:
            assert p["id"] not in seen, f"Duplicate Promise id: {p['id']}"
            seen.add(p["id"])


def test_self_model_component_ids_are_globally_unique(self_model):
    ids = [c["id"] for c in self_model["entities"]["components"]]
    assert len(ids) == len(set(ids))


def test_self_model_relationships_reference_known_components(self_model):
    known = {c["id"] for c in self_model["entities"]["components"]}
    for r in self_model["relationships"]:
        assert r["from"] in known, f"relationship from unknown component {r['from']!r}"
        assert r["to"] in known, f"relationship to unknown component {r['to']!r}"


def test_self_model_relationships_use_valid_kind(self_model):
    for r in self_model["relationships"]:
        assert r["type"] in {"depends-on"}  # only kind emitted by link stage


def test_self_model_promise_status_values_are_recognized(self_model):
    valid = {"open", "delivered", "verified", "typed-gap"}
    for comp in self_model["entities"]["components"]:
        for p in comp["promises"]:
            assert p["status"] in valid, f"Unknown status: {p['status']!r}"


def test_self_model_typed_gap_carries_gap_type(self_model):
    for comp in self_model["entities"]["components"]:
        for p in comp["promises"]:
            if p["status"] == "typed-gap":
                assert p["gap_type"], (
                    f"typed-gap Promise {p['id']} missing gap_type"
                )
            else:
                assert p["gap_type"] is None, (
                    f"non-typed-gap Promise {p['id']} has stray gap_type={p['gap_type']!r}"
                )


# ---------------------------------------------------------------------------
# Determinism gate
# ---------------------------------------------------------------------------


def test_pipeline_v3_is_byte_deterministic_under_pinned_now(tmp_path, monkeypatch):
    monkeypatch.setenv("AMS_DETERMINISTIC_NOW", PINNED_NOW)
    out_a = tmp_path / "a.yaml"
    out_b = tmp_path / "b.yaml"
    run_pipeline(REPO_ROOT, out_path=out_a, project_name="p", cluster_depth=3)
    run_pipeline(REPO_ROOT, out_path=out_b, project_name="p", cluster_depth=3)
    assert out_a.read_bytes() == out_b.read_bytes()


# ---------------------------------------------------------------------------
# Round-trip: Promise objects reconstitute from YAML dicts
# ---------------------------------------------------------------------------


def test_self_model_promises_round_trip_through_promise_from_dict(self_model):
    for comp in self_model["entities"]["components"]:
        for p_dict in comp["promises"]:
            p = Promise.from_dict(p_dict)
            assert p.id == p_dict["id"]
            assert p.owner_entity == p_dict["owner_entity"]
            assert p.attribute == p_dict["attribute"]
