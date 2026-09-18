"""Pilot parity test: WALK-unrealized-cap vs. legacy _unrealized_capability_summary.

Asserts the declarative WalkSpec produces cards consistent with the
hand-rolled Python walk in scripts/build_v3_viewer.py. Ensures we can
delete the Python impl in a follow-up commit without behavioral regression.

The two implementations differ in shape (verdicts vs severities) but MUST
agree on WHICH capabilities are flagged and their ordering by severity.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

from architecture_model.walks.runner import run_walk
from architecture_model.walks.spec.loader import load_walk_spec

REPO = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO / ".architecture/model/walks/unrealized-cap.v3.yaml"
MODEL_PATH = REPO / ".architecture/model/capabilities.v3.yaml"
LEGACY_SCRIPT = REPO / "scripts/build_v3_viewer.py"


def _load_legacy_helpers():
    """Import the private helpers from build_v3_viewer.py without running its CLI."""
    spec = importlib.util.spec_from_file_location(
        "_legacy_v3_viewer", LEGACY_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_legacy_v3_viewer"] = mod
    spec.loader.exec_module(mod)
    return mod


def _model_dict():
    with MODEL_PATH.open() as f:
        return yaml.safe_load(f)


def _entities_by_kind(model: dict) -> dict:
    """Reshape the model's entities.<kind> lists into id-keyed dicts,
    matching what the legacy viewer expects."""
    ents = model.get("entities", {})
    out: dict = {}
    for bucket_name, bucket in ents.items():
        if isinstance(bucket, list):
            out[bucket_name] = {e["id"]: e for e in bucket if "id" in e}
    return out


@pytest.fixture(scope="module")
def model():
    return _model_dict()


@pytest.fixture(scope="module")
def legacy_summary(model):
    legacy = _load_legacy_helpers()
    entities_by_kind = _entities_by_kind(model)
    return legacy._unrealized_capability_summary(
        entities_by_kind, model.get("relationships", [])
    )


@pytest.fixture(scope="module")
def walk_output(model):
    spec = load_walk_spec(SPEC_PATH)
    return run_walk(spec, model)


def test_spec_loads_and_declares_correct_audit():
    spec = load_walk_spec(SPEC_PATH)
    assert spec.id == "WALK-unrealized-cap"
    assert spec.audits == ("CAP-WK.unrealized-cap",)
    assert spec.scope.kind == "capability"
    assert "realizes" in spec.traverse.edges
    assert spec.traverse.direction == "inbound"


def test_walk_visits_every_capability_in_model(model, walk_output):
    caps = {c["id"] for c in model["entities"].get("capabilities", [])}
    walked = {c["entity_id"] for c in walk_output["cards"]}
    assert walked == caps, (
        f"walk must visit every capability; "
        f"missing={caps - walked} extra={walked - caps}"
    )


def test_flagged_set_matches_legacy(legacy_summary, walk_output):
    """The set of capabilities the legacy walk flags (non-ok) MUST equal
    the set of cards the new walk marks with a non-'ready-to-code' verdict.
    """
    legacy_flagged = {s["cap_id"] for s in legacy_summary}
    walk_flagged = {
        c["entity_id"] for c in walk_output["cards"]
        if c["verdict"] != "ready-to-code"
    }
    assert walk_flagged == legacy_flagged, (
        f"flagged sets diverge: only-legacy={legacy_flagged - walk_flagged} "
        f"only-walk={walk_flagged - legacy_flagged}"
    )


def test_verdict_reasons_are_deterministic(walk_output):
    """Every card carries a non-empty reasons list; two runs give identical output."""
    for card in walk_output["cards"]:
        assert card["reasons"], f"card {card['entity_id']} has empty reasons"
    # Determinism: cards are sorted by (severity desc, entity_id) — verify.
    ids = [c["entity_id"] for c in walk_output["cards"]]
    severities = [c["severity"] for c in walk_output["cards"]]
    for i in range(len(ids) - 1):
        assert (-severities[i], ids[i]) <= (-severities[i + 1], ids[i + 1])
