"""Semantic type round-trip and validation tests."""

from __future__ import annotations

import pytest

from architecture_model.core.semantic_types import (
    FailureMode,
    Likelihood,
    RequirementRef,
    SLO,
    Severity,
    TradeOff,
    TradeOffStatus,
    VerificationRef,
)


def test_failure_mode_round_trip():
    fm = FailureMode(
        id="FM-1",
        cause="Network partition",
        effect="Split brain",
        likelihood=Likelihood.UNLIKELY,
        severity=Severity.MAJOR,
        detection="Health check",
        mitigation="Quorum reads",
        mitigated_by=("COMP-3",),
    )
    d = fm.to_dict()
    assert FailureMode.from_dict(d) == fm


def test_failure_mode_rejects_unknown_likelihood():
    with pytest.raises(ValueError):
        FailureMode.from_dict({
            "id": "FM-1", "cause": "x", "effect": "y",
            "likelihood": "impossible", "severity": "minor",
            "detection": "z", "mitigation": "w",
        })


def test_trade_off_round_trip():
    to = TradeOff(
        id="TO-1",
        decision="Use SQLite",
        alternatives=("PostgreSQL", "DuckDB"),
        rationale="Zero-config for MVP",
        consequences=("Single-writer bottleneck",),
        revisit_when="10k concurrent writers",
        status=TradeOffStatus.ACTIVE,
    )
    assert TradeOff.from_dict(to.to_dict()) == to


def test_slo_round_trip_without_current():
    slo = SLO(metric="p99 latency", target="200ms", window="30d")
    d = slo.to_dict()
    assert "current" not in d  # optional field, omitted when None
    assert SLO.from_dict(d) == slo


def test_slo_round_trip_with_current():
    slo = SLO(metric="availability", target="99.9%", window="30d", current="99.94%")
    assert SLO.from_dict(slo.to_dict()) == slo


def test_requirement_ref_minimal():
    r = RequirementRef(id="REQ-42")
    assert RequirementRef.from_dict(r.to_dict()) == r


def test_verification_ref_with_method():
    v = VerificationRef(id="VER-7", method="pytest", target="test_foo")
    assert VerificationRef.from_dict(v.to_dict()) == v
