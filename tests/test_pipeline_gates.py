"""Tests for pipeline quality gates."""

from architecture_model.pipeline.gates import DEFAULT_GATES, get_gates_for_stage
from architecture_model.pipeline.protocol import GateSeverity


class TestDefaultGates:
    def test_observe_has_hard_parse_gate(self):
        gates = get_gates_for_stage("observe")
        parse_gate = next(g for g in gates if g.metric == "parse_success_rate")
        assert parse_gate.severity == GateSeverity.HARD
        assert parse_gate.threshold == 90.0

    def test_allocate_has_soft_coherence_gate(self):
        gates = get_gates_for_stage("allocate")
        coherence_gate = next(g for g in gates if g.metric == "boundary_coherence")
        assert coherence_gate.severity == GateSeverity.SOFT

    def test_validate_error_gate_is_lte(self):
        gates = get_gates_for_stage("validate")
        error_gate = next(g for g in gates if g.metric == "error_count")
        assert error_gate.direction == "lte"
        assert error_gate.severity == GateSeverity.HARD

    def test_unknown_stage_returns_empty(self):
        assert get_gates_for_stage("nonexistent") == []

    def test_all_stages_have_valid_gates(self):
        for stage, gates in DEFAULT_GATES.items():
            for gate in gates:
                assert gate.metric
                assert gate.threshold >= 0
                assert gate.severity in (GateSeverity.HARD, GateSeverity.SOFT)
