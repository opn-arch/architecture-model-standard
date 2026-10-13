"""Phase 9 — v3 slicer tests.

Covers component-scoped and promise-scoped slicing over the v3 model
shape (``entities.components[].promises[]`` + ``relationships[]``).
Slicing is used to produce token-budgeted focused views for downstream
LLM consumers and for docs/rendering pipelines.
"""

from __future__ import annotations

import pytest
import yaml

from architecture_model.pipeline_v3.slice import (
    SliceError,
    slice_by_component,
    slice_by_promise,
)


@pytest.fixture()
def model() -> dict:
    return {
        "meta": {
            "schema_version": "3.0",
            "project": "test",
            "generated_by": "pipeline_v3",
            "generated_at": "2026-09-14T00:00:00Z",
            "source_root": ".",
        },
        "entities": {
            "components": [
                {
                    "id": "COMP-a",
                    "name": "a",
                    "root_prefix": "pkg.a",
                    "module_names": ["pkg.a"],
                    "promises": [
                        {
                            "id": "PR-aaaa",
                            "attribute": "delivers",
                            "content": ["fn_a"],
                            "owner_entity": "COMP-a",
                            "delivered_from": None,
                            "verified_by": [],
                            "status": "open",
                            "gap_type": None,
                            "provenance": "test",
                        },
                        {
                            "id": "PR-aaab",
                            "attribute": "intent",
                            "content": ["a intent"],
                            "owner_entity": "COMP-a",
                            "delivered_from": None,
                            "verified_by": [],
                            "status": "open",
                            "gap_type": None,
                            "provenance": "test",
                        },
                    ],
                },
                {
                    "id": "COMP-b",
                    "name": "b",
                    "root_prefix": "pkg.b",
                    "module_names": ["pkg.b"],
                    "promises": [
                        {
                            "id": "PR-bbbb",
                            "attribute": "delivers",
                            "content": ["fn_b"],
                            "owner_entity": "COMP-b",
                            "delivered_from": None,
                            "verified_by": [],
                            "status": "open",
                            "gap_type": None,
                            "provenance": "test",
                        },
                    ],
                },
                {
                    "id": "COMP-c",
                    "name": "c",
                    "root_prefix": "pkg.c",
                    "module_names": ["pkg.c"],
                    "promises": [],
                },
            ],
        },
        "relationships": [
            {"from": "COMP-a", "to": "COMP-b", "type": "depends-on"},
            {"from": "COMP-b", "to": "COMP-c", "type": "depends-on"},
        ],
    }


def test_slice_by_component_returns_target_and_neighbors(model: dict) -> None:
    out = slice_by_component(model, "COMP-a")
    ids = {c["id"] for c in out["entities"]["components"]}
    assert ids == {"COMP-a", "COMP-b"}  # a + its neighbor b


def test_slice_by_component_no_neighbors(model: dict) -> None:
    out = slice_by_component(model, "COMP-a", include_neighbors=False)
    ids = {c["id"] for c in out["entities"]["components"]}
    assert ids == {"COMP-a"}


def test_slice_by_component_unknown_raises(model: dict) -> None:
    with pytest.raises(SliceError):
        slice_by_component(model, "COMP-nope")


def test_slice_by_component_preserves_schema_version(model: dict) -> None:
    out = slice_by_component(model, "COMP-a")
    assert out["meta"]["schema_version"] == "3.0"


def test_slice_by_component_stamps_slice_meta(model: dict) -> None:
    out = slice_by_component(model, "COMP-a")
    assert out["meta"]["sliced_from"] == "test"
    assert out["meta"]["slice_spec"]["kind"] == "component"
    assert out["meta"]["slice_spec"]["target"] == "COMP-a"


def test_slice_by_component_filters_relationships(model: dict) -> None:
    out = slice_by_component(model, "COMP-a")
    # Only a→b kept; b→c dropped because c not in slice
    kinds = [(r["from"], r["to"]) for r in out["relationships"]]
    assert kinds == [("COMP-a", "COMP-b")]


def test_slice_by_component_neighbors_via_inbound_edge(model: dict) -> None:
    # COMP-b is depended-on by COMP-a; slicing on b should pull a in too
    out = slice_by_component(model, "COMP-b")
    ids = {c["id"] for c in out["entities"]["components"]}
    assert ids == {"COMP-a", "COMP-b", "COMP-c"}  # a→b and b→c


def test_slice_by_component_deterministic(model: dict) -> None:
    a = yaml.safe_dump(slice_by_component(model, "COMP-a"), sort_keys=False)
    b = yaml.safe_dump(slice_by_component(model, "COMP-a"), sort_keys=False)
    assert a == b


def test_slice_by_promise_returns_owner_with_single_promise(model: dict) -> None:
    out = slice_by_promise(model, "PR-aaaa")
    comps = out["entities"]["components"]
    assert len(comps) == 1
    assert comps[0]["id"] == "COMP-a"
    assert [p["id"] for p in comps[0]["promises"]] == ["PR-aaaa"]


def test_slice_by_promise_unknown_raises(model: dict) -> None:
    with pytest.raises(SliceError):
        slice_by_promise(model, "PR-nope")


def test_slice_by_promise_stamps_slice_meta(model: dict) -> None:
    out = slice_by_promise(model, "PR-aaaa")
    assert out["meta"]["slice_spec"]["kind"] == "promise"
    assert out["meta"]["slice_spec"]["target"] == "PR-aaaa"


def test_slice_by_promise_drops_relationships(model: dict) -> None:
    out = slice_by_promise(model, "PR-aaaa")
    assert out["relationships"] == []


def test_slice_output_yaml_serializable(model: dict) -> None:
    out = slice_by_component(model, "COMP-a")
    txt = yaml.safe_dump(out, sort_keys=False)
    assert "COMP-a" in txt
    reload = yaml.safe_load(txt)
    assert reload["meta"]["slice_spec"]["target"] == "COMP-a"


def test_slice_by_component_original_model_unchanged(model: dict) -> None:
    orig_ids = {c["id"] for c in model["entities"]["components"]}
    slice_by_component(model, "COMP-a")
    still_ids = {c["id"] for c in model["entities"]["components"]}
    assert orig_ids == still_ids


# ---------------------------------------------------------------------------
# L16 fix: cross-kind neighborhood retention.
# ---------------------------------------------------------------------------

@pytest.fixture()
def multi_kind_model() -> dict:
    """Model with one component and one neighbor of every other kind."""
    return {
        "meta": {"schema_version": "3.0", "project": "mk"},
        "entities": {
            "components": [
                {"id": "COMP-x", "name": "X", "promises": []},
                {"id": "COMP-far", "name": "Far", "promises": []},  # not neighbor
            ],
            "capabilities": [
                {"id": "CAP-1", "name": "Cap1"},
                {"id": "CAP-far", "name": "CapFar"},  # not neighbor
            ],
            "behaviors": [{"id": "BEH-1", "name": "Beh1"}],
            "interfaces": [{"id": "IF-1", "name": "If1"}],
            "constraints": [{"id": "CONS-1", "name": "Cons1"}],
            "layers": [{"id": "LAY-1", "name": "Lay1"}],
            "actors": [{"id": "ACT-1", "name": "Act1"}],
        },
        "relationships": [
            {"from": "COMP-x", "to": "CAP-1", "type": "realizes"},
            {"from": "COMP-x", "to": "IF-1", "type": "exposes"},
            {"from": "COMP-x", "to": "BEH-1", "type": "traces-to"},
            {"from": "COMP-x", "to": "CONS-1", "type": "constrained-by"},
            {"from": "LAY-1", "to": "COMP-x", "type": "contains"},
            {"from": "ACT-1", "to": "BEH-1", "type": "triggers"},   # not touching x
            {"from": "COMP-far", "to": "CAP-far", "type": "realizes"},  # not touching x
        ],
    }


def test_slice_by_component_retains_cross_kind_neighbors(multi_kind_model: dict) -> None:
    """L16 gap closure: slice on COMP-x pulls in every neighbor kind."""
    out = slice_by_component(multi_kind_model, "COMP-x")
    ents = out["entities"]
    assert {c["id"] for c in ents["components"]} == {"COMP-x"}
    assert {c["id"] for c in ents["capabilities"]} == {"CAP-1"}
    assert {c["id"] for c in ents["behaviors"]} == {"BEH-1"}
    assert {c["id"] for c in ents["interfaces"]} == {"IF-1"}
    assert {c["id"] for c in ents["constraints"]} == {"CONS-1"}
    assert {c["id"] for c in ents["layers"]} == {"LAY-1"}
    # ACT-1 is not a 1-hop neighbor of COMP-x → excluded.
    assert "actors" not in ents


def test_slice_by_component_no_neighbors_drops_other_kinds(multi_kind_model: dict) -> None:
    out = slice_by_component(multi_kind_model, "COMP-x", include_neighbors=False)
    ents = out["entities"]
    assert {c["id"] for c in ents["components"]} == {"COMP-x"}
    # No other kind buckets — only the target.
    assert set(ents.keys()) == {"components"}


def test_slice_by_component_retains_cross_kind_edges(multi_kind_model: dict) -> None:
    """All 5 edges touching COMP-x must be in the sliced relationships."""
    out = slice_by_component(multi_kind_model, "COMP-x")
    edges = {(r["from"], r["to"], r["type"]) for r in out["relationships"]}
    assert ("COMP-x", "CAP-1", "realizes") in edges
    assert ("COMP-x", "IF-1", "exposes") in edges
    assert ("COMP-x", "BEH-1", "traces-to") in edges
    assert ("COMP-x", "CONS-1", "constrained-by") in edges
    assert ("LAY-1", "COMP-x", "contains") in edges
    # Distant edges must NOT be present.
    assert ("ACT-1", "BEH-1", "triggers") not in edges
    assert ("COMP-far", "CAP-far", "realizes") not in edges


def test_slice_by_component_multi_kind_deterministic(multi_kind_model: dict) -> None:
    a = yaml.safe_dump(slice_by_component(multi_kind_model, "COMP-x"), sort_keys=False)
    b = yaml.safe_dump(slice_by_component(multi_kind_model, "COMP-x"), sort_keys=False)
    assert a == b
