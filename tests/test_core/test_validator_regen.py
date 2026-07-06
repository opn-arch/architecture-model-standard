"""Tests for REGEN_READINESS validation rule (Rule 8)."""

from __future__ import annotations

import pytest

from architecture_model.core.types import (
    ArchitectureModel,
    Capability,
    Component,
    Constant,
    Entities,
    FunctionSignature,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
    TestContract,
)
from architecture_model.core.validator import (
    Severity,
    validate_model,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_meta() -> ModelMeta:
    return ModelMeta(
        schema_version="1.3",
        project="test-regen",
        system="test-system",
        generated_at="2024-01-01T00:00:00Z",
        source_artifacts=["functional-architecture"],
    )


def _make_model_with_component(comp: Component) -> ArchitectureModel:
    """Create a minimal valid model containing a single component."""
    cap = Capability(
        id="CAP-1", name="TestCap", status=Status.ACTIVE, f_block="F1"
    )
    return ArchitectureModel(
        meta=_make_meta(),
        entities=Entities(
            capabilities=[cap],
            components=[comp],
        ),
        relationships=[
            Relationship(
                type=RelationType.REALIZES,
                from_id=comp.id,
                to_id="CAP-1",
            )
        ],
    )


# ---------------------------------------------------------------------------
# Test: Components without test_contracts are SKIPPED
# ---------------------------------------------------------------------------


class TestNoTestContracts:
    """Components without test_contracts should produce NO regen issues."""

    def test_no_test_contracts_no_issues(self):
        comp = Component(
            id="COMP-1",
            name="PlainComponent",
            status=Status.ACTIVE,
            constants=[Constant(name="FOO", value="42")],
            signatures=[FunctionSignature(name="do_stuff", params=["self"])],
            # No test_contracts
        )
        model = _make_model_with_component(comp)
        result = validate_model(model)

        regen_issues = [
            i for i in result.issues if i.code.startswith("REGEN_")
        ]
        assert regen_issues == []

    def test_empty_test_contracts_no_issues(self):
        comp = Component(
            id="COMP-1",
            name="PlainComponent",
            status=Status.ACTIVE,
            test_contracts=[],  # Explicitly empty
        )
        model = _make_model_with_component(comp)
        result = validate_model(model)

        regen_issues = [
            i for i in result.issues if i.code.startswith("REGEN_")
        ]
        assert regen_issues == []


# ---------------------------------------------------------------------------
# Test: Constant coverage checks
# ---------------------------------------------------------------------------


class TestConstantCoverage:
    """Test constant coverage detection from test contract assertions."""

    def test_zero_constants_with_references_error(self):
        """Coverage < 0.3 → ERROR with code REGEN_UNREADY."""
        comp = Component(
            id="COMP-1",
            name="ColorModule",
            status=Status.ACTIVE,
            constants=[],  # No constants defined
            test_contracts=[
                TestContract(
                    test_file="test_color.py",
                    test_method="test_black_code",
                    assertion="assert Fore.BLACK == '\\033[30m'",
                ),
                TestContract(
                    test_file="test_color.py",
                    test_method="test_red_code",
                    assertion="assert Fore.RED == '\\033[31m'",
                ),
                TestContract(
                    test_file="test_color.py",
                    test_method="test_green_code",
                    assertion="assert Fore.GREEN == '\\033[32m'",
                ),
            ],
        )
        model = _make_model_with_component(comp)
        result = validate_model(model)

        regen_issues = [
            i for i in result.issues if i.code == "REGEN_UNREADY"
        ]
        assert len(regen_issues) == 1
        assert regen_issues[0].severity == Severity.ERROR
        assert regen_issues[0].entity_id == "COMP-1"

    def test_partial_constants_warning(self):
        """Coverage >= 0.3 but < 0.7 → WARNING with code REGEN_PARTIAL."""
        comp = Component(
            id="COMP-1",
            name="ColorModule",
            status=Status.ACTIVE,
            constants=[
                Constant(name="BLACK", value="\\033[30m"),
                # RED and GREEN not defined
            ],
            test_contracts=[
                TestContract(
                    test_file="test_color.py",
                    test_method="test_black_code",
                    assertion="assert Fore.BLACK == '\\033[30m'",
                ),
                TestContract(
                    test_file="test_color.py",
                    test_method="test_red_code",
                    assertion="assert Fore.RED == '\\033[31m'",
                ),
                TestContract(
                    test_file="test_color.py",
                    test_method="test_green_code",
                    assertion="assert Fore.GREEN == '\\033[32m'",
                ),
            ],
        )
        model = _make_model_with_component(comp)
        result = validate_model(model)

        regen_issues = [
            i for i in result.issues if i.code == "REGEN_PARTIAL"
        ]
        assert len(regen_issues) == 1
        assert regen_issues[0].severity == Severity.WARNING
        assert regen_issues[0].entity_id == "COMP-1"

    def test_full_constants_no_issue(self):
        """Coverage >= 0.7 → no regen constant issue."""
        comp = Component(
            id="COMP-1",
            name="ColorModule",
            status=Status.ACTIVE,
            constants=[
                Constant(name="BLACK", value="\\033[30m"),
                Constant(name="RED", value="\\033[31m"),
                Constant(name="GREEN", value="\\033[32m"),
            ],
            test_contracts=[
                TestContract(
                    test_file="test_color.py",
                    test_method="test_black_code",
                    assertion="assert Fore.BLACK == '\\033[30m'",
                ),
                TestContract(
                    test_file="test_color.py",
                    test_method="test_red_code",
                    assertion="assert Fore.RED == '\\033[31m'",
                ),
                TestContract(
                    test_file="test_color.py",
                    test_method="test_green_code",
                    assertion="assert Fore.GREEN == '\\033[32m'",
                ),
            ],
        )
        model = _make_model_with_component(comp)
        result = validate_model(model)

        regen_issues = [
            i
            for i in result.issues
            if i.code in ("REGEN_UNREADY", "REGEN_PARTIAL")
        ]
        assert regen_issues == []

    def test_no_constant_references_in_assertions(self):
        """If assertions don't reference constants, skip constant check."""
        comp = Component(
            id="COMP-1",
            name="UtilModule",
            status=Status.ACTIVE,
            constants=[],
            test_contracts=[
                TestContract(
                    test_file="test_util.py",
                    test_method="test_add",
                    assertion="assert add(1, 2) == 3",
                ),
            ],
        )
        model = _make_model_with_component(comp)
        result = validate_model(model)

        regen_issues = [
            i
            for i in result.issues
            if i.code in ("REGEN_UNREADY", "REGEN_PARTIAL")
        ]
        assert regen_issues == []


# ---------------------------------------------------------------------------
# Test: Signature coverage checks
# ---------------------------------------------------------------------------


class TestSignatureCoverage:
    """Test signature coverage detection from test contract assertions."""

    def test_low_signature_coverage_warning(self):
        """Coverage < 0.5 → WARNING with code REGEN_LOW_SIG_COVERAGE."""
        comp = Component(
            id="COMP-1",
            name="MathModule",
            status=Status.ACTIVE,
            signatures=[
                FunctionSignature(name="add", params=["a", "b"], returns="int"),
                # multiply and divide not defined
            ],
            test_contracts=[
                TestContract(
                    test_file="test_math.py",
                    test_method="test_add",
                    assertion="assert add(1, 2) == 3",
                ),
                TestContract(
                    test_file="test_math.py",
                    test_method="test_multiply",
                    assertion="assert multiply(3, 4) == 12",
                ),
                TestContract(
                    test_file="test_math.py",
                    test_method="test_divide",
                    assertion="assert divide(10, 2) == 5",
                ),
                TestContract(
                    test_file="test_math.py",
                    test_method="test_add_negative",
                    assertion="assert add(-1, -2) == -3",
                ),
            ],
        )
        model = _make_model_with_component(comp)
        result = validate_model(model)

        regen_issues = [
            i for i in result.issues if i.code == "REGEN_LOW_SIG_COVERAGE"
        ]
        assert len(regen_issues) == 1
        assert regen_issues[0].severity == Severity.WARNING
        assert regen_issues[0].entity_id == "COMP-1"

    def test_good_signature_coverage_no_issue(self):
        """Coverage >= 0.5 → no signature coverage issue."""
        comp = Component(
            id="COMP-1",
            name="MathModule",
            status=Status.ACTIVE,
            signatures=[
                FunctionSignature(name="add", params=["a", "b"], returns="int"),
                FunctionSignature(name="multiply", params=["a", "b"], returns="int"),
            ],
            test_contracts=[
                TestContract(
                    test_file="test_math.py",
                    test_method="test_add",
                    assertion="assert add(1, 2) == 3",
                ),
                TestContract(
                    test_file="test_math.py",
                    test_method="test_multiply",
                    assertion="assert multiply(3, 4) == 12",
                ),
            ],
        )
        model = _make_model_with_component(comp)
        result = validate_model(model)

        regen_issues = [
            i for i in result.issues if i.code == "REGEN_LOW_SIG_COVERAGE"
        ]
        assert regen_issues == []

    def test_no_function_calls_in_assertions(self):
        """If no function calls found, skip signature check."""
        comp = Component(
            id="COMP-1",
            name="ConstModule",
            status=Status.ACTIVE,
            signatures=[],
            test_contracts=[
                TestContract(
                    test_file="test_const.py",
                    test_method="test_value",
                    assertion="assert Obj.VALUE == 42",
                ),
            ],
        )
        model = _make_model_with_component(comp)
        result = validate_model(model)

        regen_issues = [
            i for i in result.issues if i.code == "REGEN_LOW_SIG_COVERAGE"
        ]
        assert regen_issues == []


# ---------------------------------------------------------------------------
# Test: Scoring impact
# ---------------------------------------------------------------------------


class TestScoringImpact:
    """Verify point deductions match spec."""

    def test_error_deducts_10_points(self):
        """REGEN_UNREADY (ERROR) should deduct 10 points."""
        comp = Component(
            id="COMP-1",
            name="ColorModule",
            status=Status.ACTIVE,
            constants=[],  # 0% coverage
            test_contracts=[
                TestContract(
                    test_file="test_color.py",
                    test_method="test_black",
                    assertion="assert Fore.BLACK == '\\033[30m'",
                ),
            ],
        )
        model = _make_model_with_component(comp)
        result = validate_model(model)

        # The model is otherwise perfect (has meta, has relationships)
        # so only the REGEN_UNREADY error should contribute to score loss
        # Baseline is 100, one ERROR = -10
        assert result.score == 90

    def test_warning_deducts_2_points(self):
        """REGEN_PARTIAL (WARNING) should deduct 2 points."""
        # 1 out of 2 constants = 50% coverage → WARNING
        comp = Component(
            id="COMP-1",
            name="ColorModule",
            status=Status.ACTIVE,
            constants=[
                Constant(name="BLACK", value="\\033[30m"),
            ],
            test_contracts=[
                TestContract(
                    test_file="test_color.py",
                    test_method="test_black",
                    assertion="assert Fore.BLACK == '\\033[30m'",
                ),
                TestContract(
                    test_file="test_color.py",
                    test_method="test_red",
                    assertion="assert Fore.RED == '\\033[31m'",
                ),
            ],
        )
        model = _make_model_with_component(comp)
        result = validate_model(model)

        # Baseline 100, one WARNING = -2
        assert result.score == 98

    def test_model_without_test_contracts_unaffected(self):
        """Models without test_contracts should still score 100."""
        comp = Component(
            id="COMP-1",
            name="PlainModule",
            status=Status.ACTIVE,
        )
        model = _make_model_with_component(comp)
        result = validate_model(model)
        assert result.score == 100
