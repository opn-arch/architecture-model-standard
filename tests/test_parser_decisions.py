"""Tests for DecisionEntry and new SE fields in YAML roundtrip."""

import tempfile
from pathlib import Path

import yaml
import pytest

from architecture_model.core.parser import _parse_raw, dump_model, load_model, save_model, validate_model_data
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


@pytest.mark.parametrize(("entity_type", "se_fields"), [
    ("capabilities", {
        "goals": ["Deliver value"], "moes": ["99% success"],
        "requirements": ["REQ-1"], "trade_offs": ["Speed vs cost"],
        "failure_modes": ["Timeout"], "monitored": ["success_rate"],
    }),
    ("behaviors", {
        "goals": ["Complete workflow"], "moes": ["< 1s"],
        "failure_modes": ["Invalid input"], "steps": ["Validate", "Persist"],
    }),
    ("components", {
        "goals": ["Process requests"], "moes": ["p99 < 100ms"],
        "trade_offs": ["Memory vs latency"], "failure_modes": ["Overload"],
        "monitored": ["latency_p99"], "files": ["src/service.py"],
    }),
    ("systems", {
        "goals": ["Serve users"], "trade_offs": ["Cost vs availability"],
        "failure_modes": ["Region outage"], "monitored": ["availability"],
        "component_ids": ["COMP-1"],
    }),
    ("requirements", {
        "rationale": "User need", "priority": "must", "moe": "Legacy measure",
        "value_function": "minimize(latency)", "moes": ["p99 < 100ms"],
        "failure_modes": ["Unmet target"], "monitored": ["latency_p99"],
    }),
])
def test_to_dict_and_yaml_preserve_intent_decisions_and_se_fields(entity_type, se_fields):
    decision = {
        "choice": "Use explicit serialization",
        "date": "2026-09-01",
        "rationale": "Preserve model semantics",
        "alternatives": ["Implicit conversion"],
        "context": "ArchitectureModel.to_dict",
    }
    raw = _make_raw_entity(entity_type, {
        "intent": "Preserve architectural intent",
        "decisions": [decision],
        **se_fields,
    })
    model = _parse_raw(raw)

    dumped = model.to_dict()["entities"][entity_type][0]
    loaded = _parse_raw(yaml.safe_load(model.to_yaml()))
    entity = getattr(loaded.entities, entity_type)[0]

    assert dumped["intent"] == "Preserve architectural intent"
    assert dumped["decisions"] == [decision]
    for field, value in se_fields.items():
        assert dumped[field] == value
        assert getattr(entity, field) == value
    assert entity.intent == "Preserve architectural intent"
    assert entity.decisions == [DecisionEntry(**decision)]


# ---------------------------------------------------------------------------
# DecisionEntry on BaseEntity (via Component)
# ---------------------------------------------------------------------------


class TestDecisionEntryParsing:
    def test_choice_is_required_and_date_defaults_empty(self):
        decision = DecisionEntry(choice="Use YAML")

        assert decision.choice == "Use YAML"
        assert decision.date == ""

        with pytest.raises(TypeError):
            DecisionEntry()

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

    def test_parse_decision_requires_choice(self):
        with pytest.raises(KeyError):
            _parse_raw(_make_raw(decisions=[{"date": "2026-01-15"}]))

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

    def test_intent_roundtrip_through_file(self, tmp_path):
        model = _parse_raw(_make_raw(intent="Keep architecture intent durable"))
        path = tmp_path / "model.yaml"

        save_model(model, path)
        loaded = load_model(path)

        assert loaded.entities.components[0].intent == "Keep architecture intent durable"

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

    def test_to_dict_and_yaml_roundtrip_all_requirement_se_fields(self):
        model = _parse_raw(_make_raw_entity("requirements", {
            "rationale": "Optimize user experience",
            "priority": "must",
            "moe": "Legacy measure",
            "value_function": r"J = \sum_t latency_t",
            "moes": ["p99 < 200ms"],
            "failure_modes": ["Timeout"],
            "monitored": ["latency_p99"],
        }))

        requirement = model.to_dict()["entities"]["requirements"][0]
        loaded = _parse_raw(yaml.safe_load(model.to_yaml())).entities.requirements[0]

        assert requirement["value_function"] == r"J = \sum_t latency_t"
        assert requirement["moes"] == ["p99 < 200ms"]
        assert requirement["failure_modes"] == ["Timeout"]
        assert requirement["monitored"] == ["latency_p99"]
        assert loaded.value_function == r"J = \sum_t latency_t"
        assert loaded.moes == ["p99 < 200ms"]
        assert loaded.failure_modes == ["Timeout"]
        assert loaded.monitored == ["latency_p99"]


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


class TestExternalSystemRoundtrip:
    def test_parser_and_typed_serializers_preserve_external_system(self, tmp_path):
        decision = {
            "choice": "Use vendor API",
            "date": "2026-09-01",
            "rationale": "Required integration",
            "alternatives": ["Build internally"],
            "context": "Payment processing",
        }
        raw = _make_raw_entity("external_systems", {
            "intent": "Process payments through a trusted provider",
            "decisions": [decision],
            "url": "https://payments.example.test",
            "auth_method": "OAuth2",
            "api_type": "REST",
            "provider": "Example Payments",
            "sla": "99.99%",
        })

        model = _parse_raw(raw)
        parser_dump = dump_model(model)["entities"]["external_systems"][0]
        typed_dump = model.to_dict()["entities"]["external_systems"][0]
        yaml_loaded = _parse_raw(yaml.safe_load(model.to_yaml())).entities.external_systems[0]
        path = tmp_path / "model.yaml"
        save_model(model, path)
        file_loaded = load_model(path).entities.external_systems[0]

        assert parser_dump == typed_dump
        assert typed_dump["intent"] == "Process payments through a trusted provider"
        assert typed_dump["decisions"] == [decision]
        assert typed_dump["url"] == "https://payments.example.test"
        assert yaml_loaded.decisions == [DecisionEntry(**decision)]
        assert yaml_loaded.intent == "Process payments through a trusted provider"
        assert file_loaded.provider == "Example Payments"
        assert file_loaded.sla == "99.99%"

    def test_external_system_roundtrip_passes_json_schema(self):
        raw = _make_raw_entity("external_systems", {
            "url": "https://vendor.example.test",
            "auth_method": "mTLS",
            "api_type": "REST",
            "provider": "Vendor",
            "sla": "99.9%",
        })
        raw["entities"]["external_systems"][0]["id"] = "EXT-1"
        raw["meta"]["schema_version"] = "2.1.0"

        dumped = dump_model(_parse_raw(raw))

        assert validate_model_data(dumped) == []


class TestPublicSerializerEquivalence:
    def test_non_default_metadata_and_relationship_fields_are_equivalent(self):
        raw = _make_raw()
        raw["meta"].update({
            "source_language": "python",
            "domain_profile": "controls",
            "lifecycle_phase": "concept",
        })
        raw["relationships"] = [{
            "type": "depends-on",
            "from": "COMP-1",
            "to": "COMP-1",
            "imports": ["architecture_model.core.types"],
            "import_count": 7,
            "weight": 2.5,
        }]

        model = _parse_raw(raw)

        assert dump_model(model) == model.to_dict()
        assert model.to_dict()["meta"] | {
            "source_language": "python",
            "domain_profile": "controls",
            "lifecycle_phase": "concept",
        } == model.to_dict()["meta"]
        assert model.to_dict()["relationships"][0] | {
            "imports": ["architecture_model.core.types"],
            "import_count": 7,
            "weight": 2.5,
        } == model.to_dict()["relationships"][0]
