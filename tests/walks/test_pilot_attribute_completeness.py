"""Pilot test: WALK-attribute-completeness — promise coverage meta-walk.

Verifies the declarative WalkSpec parses, runs, and produces sensible
buckets on both synthetic entities and the real repo model. This is
purely a WalkSpec (no legacy hand-rolled counterpart to compare against)
— it exercises the classify DSL's promise_status_count atoms on real data.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from architecture_model.walks.runner import run_walk
from architecture_model.walks.spec.loader import load_walk_spec

REPO = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO / ".architecture/model/walks/attribute-completeness.v3.yaml"
MODEL_PATH = REPO / ".architecture/model/capabilities.v3.yaml"


@pytest.fixture(scope="module")
def real_model() -> dict:
    with MODEL_PATH.open() as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def spec():
    return load_walk_spec(SPEC_PATH)


# ---------- spec parses correctly ------------------------------------------


def test_spec_id_and_audits(spec):
    assert spec.id == "WALK-attribute-completeness"
    assert spec.audits == ("CAP-WK.attribute-completeness",)


def test_scope_is_any_kind(spec):
    assert spec.scope.kind == "any"


def test_classify_uses_promise_status_atoms(spec):
    predicates = " ".join(v.when for v in spec.classify.verdicts)
    assert "promise_status_count:verified" in predicates
    assert "promise_status_count:open" in predicates
    assert "count:promises" in predicates


def test_rollup_is_worst_child_via_contains(spec):
    assert spec.rollup is not None
    assert spec.rollup.via == "contains"
    assert spec.rollup.strategy == "worst-child"


# ---------- synthetic bucketing --------------------------------------------


def _entity(id: str, promises: list[dict]) -> dict:
    return {"id": id, "name": id, "promises": promises}


def _promise(status: str) -> dict:
    return {"id": f"PR-{status}", "attribute": "intent", "status": status}


def test_bare_entity_flagged_needs_enrichment(spec):
    model = {
        "entities": {
            "capabilities": [_entity("CAP-empty", [])],
        },
        "relationships": [],
    }
    out = run_walk(spec, model)
    cards_by_id = {c["entity_id"]: c for c in out["cards"]}
    assert cards_by_id["CAP-empty"]["verdict"] == "needs-enrichment"


def test_fully_verified_entity_ready_to_code(spec):
    model = {
        "entities": {
            "capabilities": [
                _entity(
                    "CAP-gold",
                    [_promise("verified"), _promise("verified"), _promise("verified")],
                )
            ],
        },
        "relationships": [],
    }
    out = run_walk(spec, model)
    cards_by_id = {c["entity_id"]: c for c in out["cards"]}
    assert cards_by_id["CAP-gold"]["verdict"] == "ready-to-code"


def test_partial_open_gap_needs_validation(spec):
    model = {
        "entities": {
            "capabilities": [
                _entity(
                    "CAP-partial",
                    [_promise("verified"), _promise("open")],
                )
            ],
        },
        "relationships": [],
    }
    out = run_walk(spec, model)
    cards_by_id = {c["entity_id"]: c for c in out["cards"]}
    assert cards_by_id["CAP-partial"]["verdict"] == "needs-validation"


def test_unverified_only_needs_validation(spec):
    model = {
        "entities": {
            "capabilities": [
                _entity("CAP-raw", [_promise("proposed"), _promise("proposed")]),
            ],
        },
        "relationships": [],
    }
    out = run_walk(spec, model)
    cards_by_id = {c["entity_id"]: c for c in out["cards"]}
    assert cards_by_id["CAP-raw"]["verdict"] == "needs-validation"


# ---------- integration against real repo model ----------------------------


def test_real_model_produces_cards(spec, real_model):
    out = run_walk(spec, real_model)
    assert out["walk_id"] == "WALK-attribute-completeness"
    assert len(out["cards"]) > 0


def test_real_model_verdicts_are_known(spec, real_model):
    out = run_walk(spec, real_model)
    known = {"ready-to-code", "needs-validation", "needs-enrichment"}
    for card in out["cards"]:
        assert card["verdict"] in known, (
            f"unexpected verdict {card['verdict']!r} on {card['entity_id']!r}"
        )


def test_real_model_flags_bare_entities(spec, real_model):
    """Any entity carrying zero promises must land in needs-enrichment."""
    out = run_walk(spec, real_model)
    bare = [
        c
        for c in out["cards"]
        if not (c["entity"].get("promises") or [])
    ]
    for card in bare:
        assert card["verdict"] == "needs-enrichment"
