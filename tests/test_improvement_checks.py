"""Tests for improvement opportunity validation checks."""
from architecture_model.core.types import (
    ArchitectureModel, Component, Entities, FunctionSignature, TestContract,
    ObservabilityContract, ModelMeta,
)
from architecture_model.core.validator import validate_model


def _model_with_component(comp):
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.5"),
        entities=Entities(components=[comp]),
        relationships=[],
    )


def test_flags_no_signatures():
    comp = Component(id="C1", name="test", status="ACTIVE", signatures=[])
    result = validate_model(_model_with_component(comp))
    codes = [i.code for i in result.issues]
    assert "IMPROVEMENT_NO_SIGNATURES" in codes


def test_flags_no_test_contracts():
    comp = Component(
        id="C1", name="test", status="ACTIVE",
        signatures=[FunctionSignature(name="foo", params=[], returns="int")],
    )
    result = validate_model(_model_with_component(comp))
    codes = [i.code for i in result.issues]
    assert "IMPROVEMENT_NO_TEST_CONTRACTS" in codes


def test_flags_no_observability():
    comp = Component(
        id="C1", name="test", status="ACTIVE",
        signatures=[FunctionSignature(name="foo", params=[], returns="int")],
        test_contracts=[TestContract(
            test_file="test_foo.py", test_method="test_foo",
            assertion="assert True", contract_type="unit",
        )],
    )
    result = validate_model(_model_with_component(comp))
    codes = [i.code for i in result.issues]
    assert "IMPROVEMENT_NO_OBSERVABILITY" in codes


def test_no_flags_when_fully_specified():
    comp = Component(
        id="C1", name="test", status="ACTIVE",
        signatures=[FunctionSignature(name="foo", params=[], returns="int")],
        test_contracts=[TestContract(
            test_file="test_foo.py", test_method="test_foo",
            assertion="assert True", contract_type="unit",
        )],
        observability=[ObservabilityContract(function="foo", log_level="INFO")],
    )
    result = validate_model(_model_with_component(comp))
    improvement_codes = [i.code for i in result.issues if i.code.startswith("IMPROVEMENT_")]
    assert len(improvement_codes) == 0


def test_improvement_checks_dont_affect_score():
    """Improvement checks are INFO-level and should not reduce the score."""
    comp = Component(id="C1", name="test", status="ACTIVE", signatures=[])
    result = validate_model(_model_with_component(comp))
    improvement_issues = [i for i in result.issues if i.code.startswith("IMPROVEMENT_")]
    assert all(i.severity == "INFO" for i in improvement_issues)


def test_skips_planned_components():
    """PLANNED components should not get improvement flags."""
    comp = Component(id="C1", name="test", status="PLANNED", signatures=[])
    result = validate_model(_model_with_component(comp))
    improvement_codes = [i.code for i in result.issues if i.code.startswith("IMPROVEMENT_")]
    assert len(improvement_codes) == 0
