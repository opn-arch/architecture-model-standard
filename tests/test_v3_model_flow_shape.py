"""Part 16c: guard the retrofitted 7-stage pipeline + BEH-mcp-dev-loop composite.

Regression test against ``.architecture/model/capabilities.v3.yaml`` to
ensure the ordered flow substrate stays intact across future edits.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from architecture_model.core.parser import _parse_raw
from architecture_model.core.slicer import slice_by_behavior
from architecture_model.core.types import RelationType
from architecture_model.core.v3_loader import load_v3_model

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def v3_model():
    """Load repo's own v3 model + fragments (self-model regression fixture)."""
    import os
    cwd = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        raw = load_v3_model()
    finally:
        os.chdir(cwd)
    return _parse_raw(raw)


def test_pipeline_has_seven_ordered_stages(v3_model) -> None:
    """BEH-run-pipeline triggers a 1..7 sequenced flow."""
    sub = slice_by_behavior(
        v3_model, "BEH-run-pipeline",
        include_components=False, include_capability=False,
    )
    triggers = sorted(
        [(r.from_id, r.to_id, r.sequence) for r in sub.relationships
         if r.type == RelationType.TRIGGERS and r.sequence is not None],
        key=lambda x: x[2],
    )
    sequences = [t[2] for t in triggers]
    assert sequences == [1, 2, 3, 4, 5, 6, 7], f"expected 1..7, got {sequences}"


def test_pipeline_stage_order_is_canonical(v3_model) -> None:
    """Verify the canonical 7-stage extract chain."""
    sub = slice_by_behavior(
        v3_model, "BEH-run-pipeline",
        include_components=False, include_capability=False,
    )
    triggers = sorted(
        [(r.from_id, r.to_id, r.sequence) for r in sub.relationships
         if r.type == RelationType.TRIGGERS and r.sequence is not None],
        key=lambda x: x[2],
    )
    chain = [t[1] for t in triggers]
    assert chain == [
        "BEH-scan", "BEH-derive-promises", "BEH-cluster",
        "BEH-link", "BEH-containerize", "BEH-verify", "BEH-publish",
    ]


def test_mcp_dev_loop_composite_exists(v3_model) -> None:
    """BEH-mcp-dev-loop composite is contained by CAP-DF."""
    beh_ids = {b.id for b in v3_model.entities.behaviors}
    assert "BEH-mcp-dev-loop" in beh_ids

    contains_edges = [
        r for r in v3_model.relationships
        if r.type == RelationType.CONTAINS
        and r.to_id == "BEH-mcp-dev-loop"
        and r.from_id == "CAP-DF"
    ]
    assert len(contains_edges) == 1


def test_mcp_dev_loop_has_five_ordered_ceremony_steps(v3_model) -> None:
    triggers = [
        (r.to_id, r.sequence)
        for r in v3_model.relationships
        if r.type == RelationType.TRIGGERS
        and r.from_id == "BEH-mcp-dev-loop"
        and r.sequence is not None
    ]
    triggers.sort(key=lambda x: x[1])
    assert [t[1] for t in triggers] == [1, 2, 3, 4, 5]
    assert [t[0] for t in triggers] == [
        "BEH-view-browse", "BEH-view-note", "BEH-view-save",
        "BEH-walk-author", "BEH-run-pipeline",
    ]


def test_composite_slice_expands_transitively(v3_model) -> None:
    """Slicing BEH-mcp-dev-loop pulls in the pipeline via BEH-run-pipeline."""
    sub = slice_by_behavior(
        v3_model, "BEH-mcp-dev-loop",
        include_components=False, include_capability=False,
    )
    kept = {b.id for b in sub.entities.behaviors}
    # Ceremony (5) + pipeline (7 stages) + root = 13.
    assert "BEH-scan" in kept, "transitively pulls in pipeline stages"
    assert "BEH-publish" in kept
    assert "BEH-view-browse" in kept
    assert "BEH-mcp-dev-loop" in kept
