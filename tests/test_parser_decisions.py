"""Tests for DecisionEntry and new SE fields in YAML roundtrip."""

import tempfile
from pathlib import Path

import yaml

from architecture_model.core.parser import _parse_raw, dump_model, load_model, save_model
from architecture_model.core.types import DecisionEntry


def _make_raw(**overrides):
    """Build a minimal raw model dict with overrides merged into a component."""
    base = {
        "meta": {"project": "test", "schema_version": "2.0"},
        "entities": {"components": [{"id": "C1", "name": "Comp1", "status": "ACTIVE"}]},
        "relationships": [],
    }
    for k, v in overrides.items():
        base["entities"]["components"][0][k] = v
    return base


def _make_raw_entity(entity_type, entity_data):
    return {
        "meta": {"project": "test", "schema_version": "2.0"},
        "entities": {entity_type: [{"id": "E1", "name": "Entity1", "status": "ACTIVE", **entity_data}]},
        "relationships": [],
    }


# ---------------------------------------------------------------------------
# DecisionEntry on BaseEntity (via Component)
# ---------------------------------------------------------------------------


class TestDecisionEntryParsing:
    def test_parse_decisions_from_yaml_dict(self):
        raw = _make_raw(decisions=[
            {"date": "2026-01-15", "choice": "Use YAML", "rationale": "Human readable",
             "alternatives": ["JSON", "TOML"], "context": "Config format decision"},
        ])
        model = _parse_raw(raw)
        comp = model.entities.components[0]
        assert len(comp.decisions) == 1
        d = comp.decisions[0]
        assert isinstance(d, DecisionEntry)
        assert d.date == "2026-01-15"
        assert d.choice == "Use YAML"
        assert d.rationale == "Human readable"
        assert d.alternatives == ["JSON", "TOML"]
        assert d.context == "Config format decision"

    def test_parse_decisions_empty(self):
        raw = _make_raw()
        model = _parse_raw(raw)
        assert model.entities.components[0].decisions == []

    def test_dump_preserves_decisions(self):
        raw = _make_raw(decisions=[
            {"date": "2026-01-15", "choice": "Use YAML", "rationale": "Readable",
             "alternatives": ["JSON"], "context": "Format"},
        ])
        model = _parse_raw(raw)
        dumped = dump_model(model)
        decs = dumped["entities"]["components"][0].get("decisions", [])
        assert len(decs) == 1
        assert decs[0]["choice"] == "Use YAML"
        assert decs[0]["alternatives"] == ["JSON"]

    def test_roundtrip_through_file(self, tmp_path):
        raw = _make_raw(decisions=[
            {"date": "2026-06-01", "choice": "Async IO", "rationale": "Perf",
             "alternatives": ["Threads", "Processes"], "context": "Concurrency model"},
        ])
        model = _parse_raw(raw)
        path = tmp_path / "model.yaml"
        save_model(model, path)
        loaded = load_model(path)
        d = loaded.entities.components[0].decisions[0]
        assert isinstance(d, DecisionEntry)
        assert d.choice == "Async IO"
        assert d.alternatives == ["Threads", "Processes"]

    def test_decisions_on_capability(self):
        raw = _make_raw_entity("capabilities", {
            "decisions": [{"date": "2026-01-01", "choice": "MVP first", "rationale": "Speed"}],
        })
        model = _parse_raw(raw)
        assert len(model.entities.capabilities[0].decisions) == 1
        assert isinstance(model.entities.capabilities[0].decisions[0], DecisionEntry)


# ---------------------------------------------------------------------------
# New SE list[str] fields
# ---------------------------------------------------------------------------


class TestCapabilitySEFields:
    def test_parse_goals_trade_offs_failure_modes_monitored(self):
        raw = _make_raw_entity("capabilities", {
            "goals": ["Fast parsing", "Low memory"],
            "trade_offs": ["Speed vs correctness"],
            "failure_modes": ["Corrupt YAML input"],
            "monitored": ["parse_latency_ms"],
            "moes": ["< 100ms parse time"],
        })
        model = _parse_raw(raw)
        cap = model.entities.capabilities[0]
        assert cap.goals == ["Fast parsing", "Low memory"]
        assert cap.trade_offs == ["Speed vs correctness"]
        assert cap.failure_modes == ["Corrupt YAML input"]
        assert cap.monitored == ["parse_latency_ms"]
        assert cap.moes == ["< 100ms parse time"]

    def test_dump_capability_se_fields(self):
        raw = _make_raw_entity("capabilities", {
            "goals": ["G1"], "trade_offs": ["T1"], "failure_modes": ["F1"],
            "monitored": ["M1"], "moes": ["MOE1"],
        })
        model = _parse_raw(raw)
        dumped = dump_model(model)
        cap = dumped["entities"]["capabilities"][0]
        assert cap["goals"] == ["G1"]
        assert cap["trade_offs"] == ["T1"]
        assert cap["failure_modes"] == ["F1"]
        assert cap["monitored"] == ["M1"]
        assert cap["moes"] == ["MOE1"]


class TestBehaviorSEFields:
    def test_parse_goals_moes_failure_modes(self):
        raw = _make_raw_entity("behaviors", {
            "goals": ["Reliable processing"],
            "moes": ["99.9% success rate"],
            "failure_modes": ["Timeout on slow network"],
        })
        model = _parse_raw(raw)
        beh = model.entities.behaviors[0]
        assert beh.goals == ["Reliable processing"]
        assert beh.moes == ["99.9% success rate"]
        assert beh.failure_modes == ["Timeout on slow network"]

    def test_dump_behavior_se_fields(self):
        raw = _make_raw_entity("behaviors", {
            "goals": ["G1"], "moes": ["M1"], "failure_modes": ["F1"],
        })
        model = _parse_raw(raw)
        dumped = dump_model(model)
        beh = dumped["entities"]["behaviors"][0]
        assert beh["goals"] == ["G1"]
        assert beh["moes"] == ["M1"]
        assert beh["failure_modes"] == ["F1"]


class TestSystemSEFields:
    def test_parse_system_se_fields(self):
        raw = _make_raw_entity("systems", {
            "goals": ["Scalable"], "trade_offs": ["Cost vs perf"],
            "failure_modes": ["OOM"], "monitored": ["cpu_usage"],
        })
        model = _parse_raw(raw)
        sys = model.entities.systems[0]
        assert sys.goals == ["Scalable"]
        assert sys.trade_offs == ["Cost vs perf"]
        assert sys.failure_modes == ["OOM"]
        assert sys.monitored == ["cpu_usage"]

    def test_dump_system_se_fields(self):
        raw = _make_raw_entity("systems", {
            "goals": ["G1"], "trade_offs": ["T1"],
            "failure_modes": ["F1"], "monitored": ["M1"],
        })
        model = _parse_raw(raw)
        dumped = dump_model(model)
        sys = dumped["entities"]["systems"][0]
        assert sys["goals"] == ["G1"]
        assert sys["trade_offs"] == ["T1"]
        assert sys["failure_modes"] == ["F1"]
        assert sys["monitored"] == ["M1"]


class TestRequirementSEFields:
    def test_parse_requirement_se_fields(self):
        raw = _make_raw_entity("requirements", {
            "value_function": "minimize_latency",
            "moes": ["p99 < 200ms"],
            "failure_modes": ["Stale cache"],
            "monitored": ["cache_hit_ratio"],
        })
        model = _parse_raw(raw)
        req = model.entities.requirements[0]
        assert req.value_function == "minimize_latency"
        assert req.moes == ["p99 < 200ms"]
        assert req.failure_modes == ["Stale cache"]
        assert req.monitored == ["cache_hit_ratio"]

    def test_dump_requirement_se_fields(self):
        raw = _make_raw_entity("requirements", {
            "value_function": "VF", "moes": ["M1"],
            "failure_modes": ["F1"], "monitored": ["Mon1"],
            "rationale": "R", "priority": "high", "moe": "legacy_moe",
        })
        model = _parse_raw(raw)
        dumped = dump_model(model)
        req = dumped["entities"]["requirements"][0]
        assert req["value_function"] == "VF"
        assert req["moes"] == ["M1"]
        assert req["failure_modes"] == ["F1"]
        assert req["monitored"] == ["Mon1"]
        assert req["rationale"] == "R"
        assert req["priority"] == "high"
        assert req["moe"] == "legacy_moe"


class TestComponentMonitored:
    def test_parse_component_monitored(self):
        raw = _make_raw(monitored=["error_rate", "latency_p99"])
        model = _parse_raw(raw)
        assert model.entities.components[0].monitored == ["error_rate", "latency_p99"]

    def test_dump_component_monitored(self):
        raw = _make_raw(monitored=["m1"])
        model = _parse_raw(raw)
        dumped = dump_model(model)
        assert dumped["entities"]["components"][0]["monitored"] == ["m1"]
