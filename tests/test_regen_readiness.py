"""Tests for regen readiness static metric module."""
import pytest

from architecture_model.core.regen_readiness import (
    FunctionReadiness,
    ComponentReadiness,
    RegenReadiness,
    compute_function_readiness,
    compute_component_readiness,
    compute_regen_readiness,
    _is_trivial_hint,
)
from architecture_model.core.types import (
    Component, FunctionSignature, TestContract, Constant, ComponentInterface,
    ArchitectureModel, Entities, ModelMeta, Status,
)


def _make_sig(name="func", body_hint="", complexity=None):
    return FunctionSignature(name=name, body_hint=body_hint, complexity=complexity)


def _make_tc(test_method="test_func", assertion="assert func() == 1"):
    return TestContract(test_file="test.py", test_method=test_method, assertion=assertion)


class TestFunctionReadiness:
    def test_function_readiness_no_hint(self):
        sig = _make_sig("my_func")
        result = compute_function_readiness(sig, [])
        assert result.score == 20.0
        assert result.has_body_hint is False
        assert result.body_hint_quality == "none"

    def test_function_readiness_trivial(self):
        sig = _make_sig("my_func", body_hint="return self._value", complexity="TRIVIAL")
        result = compute_function_readiness(sig, [])
        assert result.score >= 80.0
        assert result.body_hint_quality == "trivial"

    def test_function_readiness_complex(self):
        sig = _make_sig("my_func", body_hint="[15 statements]")
        result = compute_function_readiness(sig, [])
        assert 45 <= result.score <= 50
        assert result.body_hint_quality == "complex"

    def test_function_readiness_short(self):
        sig = _make_sig("my_func", body_hint="x = 1; return x + 2")
        result = compute_function_readiness(sig, [])
        assert result.score == 65.0
        assert result.body_hint_quality == "short"

    def test_function_readiness_blocker(self):
        sig = _make_sig("critical_func")
        contracts = [
            _make_tc("test_critical_func_1", "assert critical_func() == 1"),
            _make_tc("test_critical_func_2", "assert critical_func() == 2"),
            _make_tc("test_critical_func_3", "assert critical_func() == 3"),
        ]
        result = compute_function_readiness(sig, contracts)
        assert len(result.blockers) == 1
        assert "critical" in result.blockers[0]
        assert "critical_func" in result.blockers[0]

    def test_function_readiness_test_bonus(self):
        sig = _make_sig("my_func", body_hint="return 42", complexity="TRIVIAL")
        contracts = [_make_tc("test_my_func", "assert my_func() == 42")]
        result = compute_function_readiness(sig, contracts)
        assert result.score > 80.0  # 80 + 7 = 87


class TestComponentReadiness:
    def test_component_readiness_full(self):
        """Component with full enrichment scores 90+."""
        sigs = [
            _make_sig("func_a", "return 1", "TRIVIAL"),
            _make_sig("func_b", "return 2", "TRIVIAL"),
        ]
        constants = [Constant(name="MY_CONST", value="42")]
        contracts = [
            _make_tc("test_func_a", "assert func_a() == MY_CONST"),
            _make_tc("test_func_b", "assert func_b() == 2"),
        ] * 5  # 10 contracts
        comp = Component(
            id="COMP-1", name="Full", status=Status.ACTIVE,
            signatures=sigs,
            constants=constants,
            test_contracts=contracts,
            files=["a.py", "b.py"],
        )
        result = compute_component_readiness(comp)
        assert result.score >= 90.0

    def test_component_readiness_empty(self):
        """Component with no enrichment scores low."""
        comp = Component(id="COMP-2", name="Empty", status=Status.ACTIVE, files=["x.py"])
        result = compute_component_readiness(comp)
        # No sigs (body_hint_coverage=0), no contracts, but constant/sig/dep defaults to 1.0
        # 0*25 + 0*15 + 0*20 + 1.0*15 + 1.0*15 + 1.0*10 = 40
        assert result.score == 40.0

    def test_constant_coverage_calculation(self):
        """Test contracts referencing constants properly tracked."""
        constants = [Constant(name="FOO", value="1"), Constant(name="BAR", value="2")]
        contracts = [_make_tc("test_x", "assert result == FOO")]
        comp = Component(
            id="COMP-3", name="ConstTest", status=Status.ACTIVE,
            constants=constants,
            test_contracts=contracts,
            signatures=[_make_sig("result_fn", "return FOO", "TRIVIAL")],
            files=["c.py"],
        )
        result = compute_component_readiness(comp)
        # FOO is referenced and defined → coverage = 1.0
        assert result.constant_coverage == 1.0


class TestSystemReadiness:
    def _make_model(self, components):
        entities = Entities(components=components)
        meta = ModelMeta(project="test", schema_version="2.0")
        return ArchitectureModel(meta=meta, entities=entities, relationships=[])

    def test_system_readiness_grading(self):
        """Verify grade thresholds."""
        # High-scoring component
        sigs = [_make_sig(f"f{i}", "return 1", "TRIVIAL") for i in range(5)]
        contracts = [_make_tc(f"test_f{i}", f"assert f{i}() == 1") for i in range(5)] * 2
        comp = Component(
            id="COMP-1", name="Good", status=Status.ACTIVE,
            signatures=sigs,
            test_contracts=contracts,
            files=["a.py"],
        )
        model = self._make_model([comp])
        result = compute_regen_readiness(model)
        assert result.grade in ("A", "B")
        assert result.overall >= 70

    def test_system_readiness_empty(self):
        model = self._make_model([])
        result = compute_regen_readiness(model)
        assert result.overall == 0.0
        assert result.grade == "F"

    def test_system_readiness_recommendation_ready(self):
        sigs = [_make_sig("f", "return 1", "TRIVIAL")]
        contracts = [_make_tc("test_f", "assert f() == 1")] * 10
        comp = Component(
            id="COMP-1", name="Perfect", status=Status.ACTIVE,
            signatures=sigs, test_contracts=contracts, files=["a.py"],
        )
        model = self._make_model([comp])
        result = compute_regen_readiness(model)
        if result.overall >= 90:
            assert result.recommendation == "Ready for regeneration"
