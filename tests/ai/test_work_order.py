"""Tests for architecture_model.ai.work_order."""

from __future__ import annotations

import pytest

from architecture_model.ai.work_order import (
    Budget,
    ProposalKind,
    SliceRef,
    WorkOrder,
)
from architecture_model.lifecycle.versions import SchemaVersions


def _valid_kwargs(**overrides):
    kw = dict(
        id="WO-1",
        intent="refine decomposition",
        input_slice_refs=[SliceRef(slice_id="slice-a", model_revision="rev-1")],
        expected_proposal_kinds=[ProposalKind.MODEL_PATCH],
        parameters={"depth": 2},
        budget=Budget(max_tokens=1000, max_wall_seconds=30),
        requested_by="agent://tester",
        created_at="2026-09-03T12:00:00+00:00",
    )
    kw.update(overrides)
    return kw


def test_construct_valid_work_order():
    wo = WorkOrder(**_valid_kwargs())
    assert wo.id == "WO-1"
    assert wo.contract_version == SchemaVersions.WORK_ORDER
    assert wo.intent == "refine decomposition"
    assert wo.input_slice_refs[0].slice_id == "slice-a"
    assert wo.expected_proposal_kinds == [ProposalKind.MODEL_PATCH]
    assert wo.budget.max_tokens == 1000
    assert wo.requested_by == "agent://tester"
    assert wo.created_at == "2026-09-03T12:00:00+00:00"


def test_empty_input_slice_refs_raises():
    with pytest.raises(ValueError, match="input_slice_refs"):
        WorkOrder(**_valid_kwargs(input_slice_refs=[]))


def test_empty_expected_proposal_kinds_raises():
    with pytest.raises(ValueError, match="expected_proposal_kinds"):
        WorkOrder(**_valid_kwargs(expected_proposal_kinds=[]))


def test_duplicate_slice_ids_raises():
    refs = [
        SliceRef(slice_id="dup", model_revision="rev-1"),
        SliceRef(slice_id="dup", model_revision="rev-2"),
    ]
    with pytest.raises(ValueError, match="duplicate"):
        WorkOrder(**_valid_kwargs(input_slice_refs=refs))


def test_to_dict_from_dict_round_trip():
    wo = WorkOrder(**_valid_kwargs())
    d = wo.to_dict()
    wo2 = WorkOrder.from_dict(d)
    assert wo2.to_dict() == d
    assert wo2 == wo


def test_to_dict_deterministic_key_order():
    wo = WorkOrder(**_valid_kwargs())
    a = list(wo.to_dict().keys())
    b = list(wo.to_dict().keys())
    assert a == b
    # Explicit order expected.
    assert a == [
        "id",
        "contract_version",
        "intent",
        "input_slice_refs",
        "expected_proposal_kinds",
        "parameters",
        "budget",
        "requested_by",
        "created_at",
    ]


def test_two_equal_work_orders_have_same_digest():
    wo1 = WorkOrder(**_valid_kwargs())
    wo2 = WorkOrder(**_valid_kwargs())
    assert wo1.digest() == wo2.digest()
    assert wo1.digest().startswith(SchemaVersions.DIGEST_ALGO + ":")


def test_contract_version_pinned():
    wo = WorkOrder(**_valid_kwargs())
    assert wo.contract_version == SchemaVersions.WORK_ORDER == "1.0.0"


def test_validate_schema_returns_empty_for_valid():
    wo = WorkOrder(**_valid_kwargs())
    assert wo.validate_schema() == []


def test_validate_schema_reports_contract_version_mismatch():
    wo = WorkOrder(**_valid_kwargs())
    d = wo.to_dict()
    d["contract_version"] = "9.9.9"
    errors = WorkOrder._validate_dict_against_schema(d)
    assert errors, "expected errors for wrong contract_version"
    assert any("contract_version" in e or "const" in e for e in errors)


def test_validate_schema_rejects_unknown_proposal_kind():
    wo = WorkOrder(**_valid_kwargs())
    d = wo.to_dict()
    d["expected_proposal_kinds"] = ["not-a-real-kind"]
    errors = WorkOrder._validate_dict_against_schema(d)
    assert errors


def test_created_at_iso8601_with_T_separator():
    with pytest.raises(ValueError, match="ISO-8601"):
        WorkOrder(**_valid_kwargs(created_at="2026-09-03 12:00:00+00:00"))
    with pytest.raises(ValueError, match="ISO-8601"):
        WorkOrder(**_valid_kwargs(created_at="not a date"))


def test_budget_positive_ints():
    with pytest.raises(ValueError, match="max_tokens"):
        WorkOrder(**_valid_kwargs(budget=Budget(max_tokens=0, max_wall_seconds=1)))
    with pytest.raises(ValueError, match="max_wall_seconds"):
        WorkOrder(**_valid_kwargs(budget=Budget(max_tokens=1, max_wall_seconds=-5)))


def test_from_dict_accepts_string_kind_values():
    wo = WorkOrder(**_valid_kwargs())
    d = wo.to_dict()
    # kinds are serialized as raw strings; from_dict must accept them.
    assert d["expected_proposal_kinds"] == ["model-patch"]
    wo2 = WorkOrder.from_dict(d)
    assert wo2.expected_proposal_kinds == [ProposalKind.MODEL_PATCH]


def test_workorder_build_minimal():
    wo = WorkOrder.build(
        intent="patch model",
        slices=[("slice-a", "rev-1")],
        accepts=["model-patch"],
        requested_by="test",
        max_tokens=1000,
        max_wall_seconds=30,
    )
    assert wo.intent == "patch model"
    assert wo.id.startswith("sha256-v1:")
    assert wo.created_at
    assert wo.input_slice_refs[0].slice_id == "slice-a"
    assert wo.input_slice_refs[0].model_revision == "rev-1"


def test_workorder_build_accepts_datetime_created_at():
    from datetime import datetime, timezone

    dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
    wo = WorkOrder.build(
        intent="x",
        slices=[("s", "r")],
        accepts=["model-patch"],
        requested_by="t",
        max_tokens=1,
        max_wall_seconds=1,
        created_at=dt,
    )
    assert wo.created_at == dt.isoformat()


def test_workorder_build_deterministic_id():
    kwargs = dict(
        intent="x",
        slices=[("s", "r")],
        accepts=["model-patch"],
        requested_by="t",
        max_tokens=1,
        max_wall_seconds=1,
        created_at="2026-01-01T00:00:00+00:00",
    )
    w1 = WorkOrder.build(**kwargs)
    w2 = WorkOrder.build(**kwargs)
    assert w1.id == w2.id


def test_workorder_build_accepts_supplied_id():
    wo = WorkOrder.build(
        intent="x",
        slices=[("s", "r")],
        accepts=["model-patch"],
        requested_by="t",
        max_tokens=1,
        max_wall_seconds=1,
        created_at="2026-01-01T00:00:00+00:00",
        id="WO-custom",
    )
    assert wo.id == "WO-custom"


def test_workorder_build_normalizes_string_proposal_kinds():
    wo = WorkOrder.build(
        intent="x",
        slices=[("s", "r")],
        accepts=["model-patch"],
        requested_by="t",
        max_tokens=1,
        max_wall_seconds=1,
    )
    assert wo.expected_proposal_kinds[0] == ProposalKind("model-patch")


def test_workorder_build_accepts_sliceref_directly():
    ref = SliceRef(slice_id="s", model_revision="r")
    wo = WorkOrder.build(
        intent="x",
        slices=[ref],
        accepts=["model-patch"],
        requested_by="t",
        max_tokens=1,
        max_wall_seconds=1,
    )
    assert wo.input_slice_refs[0] is ref
