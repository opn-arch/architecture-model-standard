"""Tests for SE fields added to entity types."""

from architecture_model.core.types import (
    Capability, Behavior, Requirement, System, Component, Status,
)


# --- Capability: goals, trade_offs, failure_modes, monitored ---

def test_capability_goals_default():
    c = Capability(id="CAP-1", name="C", status=Status.ACTIVE)
    assert c.goals == []


def test_capability_goals_set():
    c = Capability(id="CAP-1", name="C", status=Status.ACTIVE, goals=["fast"])
    assert c.goals == ["fast"]


def test_capability_trade_offs():
    c = Capability(id="CAP-1", name="C", status=Status.ACTIVE, trade_offs=["speed vs safety"])
    assert c.trade_offs == ["speed vs safety"]


def test_capability_failure_modes():
    c = Capability(id="CAP-1", name="C", status=Status.ACTIVE, failure_modes=["timeout"])
    assert c.failure_modes == ["timeout"]


def test_capability_monitored():
    c = Capability(id="CAP-1", name="C", status=Status.ACTIVE, monitored=["latency"])
    assert c.monitored == ["latency"]


# --- Behavior: goals, moes, failure_modes ---

def test_behavior_goals():
    b = Behavior(id="B-1", name="B", status=Status.ACTIVE, goals=["reliability"])
    assert b.goals == ["reliability"]


def test_behavior_moes():
    b = Behavior(id="B-1", name="B", status=Status.ACTIVE, moes=["99.9% uptime"])
    assert b.moes == ["99.9% uptime"]


def test_behavior_failure_modes():
    b = Behavior(id="B-1", name="B", status=Status.ACTIVE, failure_modes=["crash"])
    assert b.failure_modes == ["crash"]


# --- Requirement: value_function, moes, failure_modes, monitored ---

def test_requirement_value_function():
    r = Requirement(id="REQ-1", name="R", status=Status.ACTIVE, value_function="minimize latency")
    assert r.value_function == "minimize latency"


def test_requirement_moes():
    r = Requirement(id="REQ-1", name="R", status=Status.ACTIVE, moes=["p99 < 100ms"])
    assert r.moes == ["p99 < 100ms"]


def test_requirement_failure_modes():
    r = Requirement(id="REQ-1", name="R", status=Status.ACTIVE, failure_modes=["data loss"])
    assert r.failure_modes == ["data loss"]


def test_requirement_monitored():
    r = Requirement(id="REQ-1", name="R", status=Status.ACTIVE, monitored=["error_rate"])
    assert r.monitored == ["error_rate"]


# --- System: goals, trade_offs, failure_modes, monitored ---

def test_system_goals():
    s = System(id="SYS-1", name="S", status=Status.ACTIVE, goals=["scalable"])
    assert s.goals == ["scalable"]


def test_system_trade_offs():
    s = System(id="SYS-1", name="S", status=Status.ACTIVE, trade_offs=["cost vs perf"])
    assert s.trade_offs == ["cost vs perf"]


def test_system_failure_modes():
    s = System(id="SYS-1", name="S", status=Status.ACTIVE, failure_modes=["network partition"])
    assert s.failure_modes == ["network partition"]


def test_system_monitored():
    s = System(id="SYS-1", name="S", status=Status.ACTIVE, monitored=["cpu_usage"])
    assert s.monitored == ["cpu_usage"]


# --- Component: monitored (only new field) ---

def test_component_monitored():
    c = Component(id="COMP-1", name="C", status=Status.ACTIVE, monitored=["memory"])
    assert c.monitored == ["memory"]


def test_component_still_has_existing_fields():
    c = Component(
        id="COMP-1", name="C", status=Status.ACTIVE,
        goals=["fast"], moes=["p99"], trade_offs=["x"], failure_modes=["y"],
    )
    assert c.goals == ["fast"]
    assert c.moes == ["p99"]
    assert c.trade_offs == ["x"]
    assert c.failure_modes == ["y"]
