"""Parity + integration tests for architecture_model.walks.meta.direction_lint.

Confirms the meta-walk produces byte-identical output to the legacy
``_lint_edge_note_directions`` helper in ``scripts/build_v3_viewer.py``.
After this test lands green, the legacy helper can be deleted and its
caller updated to import from the meta module.

Realizes CAP-WK.direction-lint parity discipline.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

from architecture_model.walks.meta import lint_edge_note_directions
from architecture_model.walks.meta.direction_lint import (
    DirectionLintCard,
    DirectionLintReport,
    audit_edge_note_directions,
)

REPO = Path(__file__).resolve().parents[2]
MODEL_PATH = REPO / ".architecture/model/capabilities.v3.yaml"
LEGACY_SCRIPT = REPO / "scripts/build_v3_viewer.py"


@pytest.fixture(scope="module")
def real_relationships() -> list:
    with MODEL_PATH.open() as f:
        model = yaml.safe_load(f)
    return model.get("relationships", []) or []


# ---------- unit tests: each of the four rules -----------------------------


def test_realizes_reversed_note_flagged():
    rels = [
        {
            "from": "CAP-A",
            "to": "COMP-1",
            "type": "realizes",
            "note": "CAP-A is realized by COMP-1",
        }
    ]
    result = lint_edge_note_directions(rels)
    assert len(result) == 1
    assert result[0]["type"] == "realizes"
    assert "reversed" in result[0]["warning"]
    assert "expected COMP-1->CAP-A" in result[0]["warning"]


def test_realizes_correct_direction_note_passes():
    rels = [
        {
            "from": "COMP-1",
            "to": "CAP-A",
            "type": "realizes",
            "note": "COMP-1 realizes CAP-A",
        }
    ]
    assert lint_edge_note_directions(rels) == []


def test_depends_on_reversed_note_flagged():
    # Correct direction: X -> depends-on -> Y means "X depends on Y".
    # A note saying "Y depends on X" on an X->depends-on->Y edge is reversed.
    rels = [
        {
            "from": "COMP-X",
            "to": "COMP-Y",
            "type": "depends-on",
            "note": "COMP-Y depends on COMP-X",
        }
    ]
    result = lint_edge_note_directions(rels)
    assert len(result) == 1
    assert "reversed" in result[0]["warning"]


def test_contains_reversed_note_flagged():
    rels = [
        {
            "from": "CAP-A",
            "to": "CAP-A.sub",
            "type": "contains",
            "note": "CAP-A is contained in CAP-A.sub",
        }
    ]
    result = lint_edge_note_directions(rels)
    assert len(result) == 1
    assert result[0]["type"] == "contains"


def test_exposes_reversed_note_flagged():
    # Correct direction: X -> exposes -> Y means "X exposes Y".
    # "Y exposes X" on X->exposes->Y is reversed.
    rels = [
        {
            "from": "COMP-A",
            "to": "IF-1",
            "type": "exposes",
            "note": "IF-1 exposes COMP-A",
        }
    ]
    result = lint_edge_note_directions(rels)
    assert len(result) == 1
    assert result[0]["type"] == "exposes"


def test_no_note_field_skipped():
    rels = [{"from": "A", "to": "B", "type": "realizes"}]
    assert lint_edge_note_directions(rels) == []


def test_empty_note_skipped():
    rels = [{"from": "A", "to": "B", "type": "realizes", "note": ""}]
    assert lint_edge_note_directions(rels) == []


def test_output_sorted_deterministically():
    rels = [
        {
            "from": "Z",
            "to": "Y",
            "type": "realizes",
            "note": "Z is realized by Y",
        },
        {
            "from": "A",
            "to": "B",
            "type": "contains",
            "note": "A is contained in B",
        },
        {
            "from": "M",
            "to": "N",
            "type": "realizes",
            "note": "M is realized by N",
        },
    ]
    result = lint_edge_note_directions(rels)
    # Sort key: (type, from, to). contains < realizes alphabetically.
    types = [w["type"] for w in result]
    assert types == ["contains", "realizes", "realizes"]
    # Within realizes: from M sorts before from Z.
    assert result[1]["from"] == "M"
    assert result[2]["from"] == "Z"


def test_correct_note_wins_over_reversed_pattern():
    """A note containing both patterns must NOT be flagged (right_pattern present)."""
    rels = [
        {
            "from": "COMP-1",
            "to": "CAP-A",
            "type": "realizes",
            "note": "COMP-1 realizes CAP-A (CAP-A is realized by COMP-1)",
        }
    ]
    assert lint_edge_note_directions(rels) == []


# ---------- parity test against legacy viewer helper -----------------------


def _load_legacy_helper():
    spec = importlib.util.spec_from_file_location("_legacy_v3", LEGACY_SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_legacy_v3"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_parity_with_legacy_viewer_helper(real_relationships):
    """Byte-identical output on the real repo relationships list.

    After this test lands green, the legacy helper
    ``scripts.build_v3_viewer._lint_edge_note_directions`` can be deleted
    and its caller updated to import from the meta module.
    """
    try:
        legacy = _load_legacy_helper()
    except AttributeError:
        # Legacy helper already deleted — parity is trivially satisfied.
        pytest.skip("legacy helper already deleted; parity check no longer meaningful")
        return
    if not hasattr(legacy, "_lint_edge_note_directions"):
        pytest.skip("legacy helper already deleted; parity check no longer meaningful")
        return
    legacy_out = legacy._lint_edge_note_directions(real_relationships)
    new_out = lint_edge_note_directions(real_relationships)
    assert legacy_out == new_out


def test_real_model_clean(real_relationships):
    """The real model should have no direction-vs-note contradictions
    (L9 fix cleared all)."""
    warnings = lint_edge_note_directions(real_relationships)
    assert warnings == [], (
        f"unexpected direction-lint warnings: {warnings}"
    )


# ---------- report-shape API (R2) ------------------------------------------


def test_audit_returns_direction_lint_report():
    """audit_edge_note_directions returns a DirectionLintReport dataclass
    with .cards and .counts, matching the shape of other meta-walks
    (walk_coverage, llm_endpoint_inventory, prompt_refiner).
    """
    rels = [
        {"from": "CAP-A", "to": "COMP-1", "type": "realizes",
         "note": "CAP-A is realized by COMP-1"},
    ]
    report = audit_edge_note_directions(rels)
    assert isinstance(report, DirectionLintReport)
    assert isinstance(report.cards, tuple)
    assert len(report.cards) == 1
    assert isinstance(report.cards[0], DirectionLintCard)
    assert report.counts == {"reversed-note": 1}


def test_audit_clean_report_empty_cards():
    """Clean input → empty cards tuple and counts dict."""
    rels = [{"from": "COMP-1", "to": "CAP-A", "type": "realizes",
             "note": "COMP-1 realizes CAP-A"}]
    report = audit_edge_note_directions(rels)
    assert report.cards == ()
    assert report.counts == {}


def test_audit_card_preserves_edge_fields():
    """DirectionLintCard exposes from/to/type/note/warning."""
    rels = [
        {"from": "CAP-A", "to": "COMP-1", "type": "realizes",
         "note": "CAP-A is realized by COMP-1"},
    ]
    card = audit_edge_note_directions(rels).cards[0]
    assert card.from_id == "CAP-A"
    assert card.to_id == "COMP-1"
    assert card.edge_type == "realizes"
    assert card.note == "CAP-A is realized by COMP-1"
    assert "reversed" in card.warning


def test_audit_deterministic_sort():
    """Cards sorted by (edge_type, from_id, to_id) — same as legacy."""
    rels = [
        {"from": "Z", "to": "Y", "type": "realizes",
         "note": "Z is realized by Y"},
        {"from": "A", "to": "B", "type": "contains",
         "note": "A is contained in B"},
        {"from": "M", "to": "N", "type": "realizes",
         "note": "M is realized by N"},
    ]
    report = audit_edge_note_directions(rels)
    types = [c.edge_type for c in report.cards]
    assert types == ["contains", "realizes", "realizes"]
    assert report.cards[1].from_id == "M"
    assert report.cards[2].from_id == "Z"
    assert report.counts == {"reversed-note": 3}


def test_shim_and_audit_agree_on_real_model(real_relationships):
    """Legacy shim and new audit produce the same underlying findings."""
    legacy = lint_edge_note_directions(real_relationships)
    report = audit_edge_note_directions(real_relationships)
    assert len(legacy) == len(report.cards)
    for l, c in zip(legacy, report.cards):
        assert l["from"] == c.from_id
        assert l["to"] == c.to_id
        assert l["type"] == c.edge_type
        assert l["warning"] == c.warning
