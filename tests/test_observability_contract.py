"""Tests for ObservabilityContract on Component."""
from architecture_model.core.types import ObservabilityContract, Component

def test_observability_contract_creation():
    oc = ObservabilityContract(
        function="validate_model",
        log_level="INFO",
        emits_metric="validation_score",
        on_error="ERROR"
    )
    assert oc.function == "validate_model"
    assert oc.log_level == "INFO"
    assert oc.emits_metric == "validation_score"

def test_observability_contract_defaults():
    oc = ObservabilityContract(function="foo", log_level="DEBUG")
    assert oc.emits_metric is None
    assert oc.on_error == "ERROR"

def test_component_has_observability():
    comp = Component(id="C1", name="test", status="ACTIVE",
                     observability=[ObservabilityContract(function="foo", log_level="INFO")])
    assert len(comp.observability) == 1

def test_component_observability_default_empty():
    comp = Component(id="C1", name="test", status="ACTIVE")
    assert comp.observability == []

def test_observability_roundtrip():
    from architecture_model.core.parser import _parse_raw
    raw = {
        "meta": {"project": "test", "schema_version": "1.5"},
        "entities": {
            "components": [{
                "id": "C1", "name": "test", "status": "ACTIVE",
                "observability": [{"function": "foo", "log_level": "INFO", "emits_metric": "bar"}]
            }]
        },
        "relationships": []
    }
    model = _parse_raw(raw)
    comp = model.entities.components[0]
    assert len(comp.observability) == 1
    assert comp.observability[0].emits_metric == "bar"
    d = model.to_dict()
    assert d["entities"]["components"][0]["observability"][0]["function"] == "foo"
