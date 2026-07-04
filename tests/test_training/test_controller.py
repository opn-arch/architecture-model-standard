"""Tests for MPC controller: active learning decisions, budget management, convergence."""

import pytest

from architecture_model.training.controller import MPCController, MPCState


# ---------------------------------------------------------------------------
# MPCState dataclass tests
# ---------------------------------------------------------------------------


class TestMPCState:
    def test_default_values(self):
        """MPCState initializes with sensible defaults."""
        state = MPCState()
        assert state.iteration == 0
        assert state.total_repos_processed == 0
        assert state.oracle_budget_remaining == 100_000
        assert state.surrogate_accuracy == 0.0
        assert state.convergence_history == []

    def test_custom_values(self):
        """MPCState accepts custom initial values."""
        state = MPCState(
            iteration=5,
            total_repos_processed=50,
            oracle_budget_remaining=80_000,
            surrogate_accuracy=0.85,
            convergence_history=[0.7, 0.8, 0.85],
        )
        assert state.iteration == 5
        assert state.total_repos_processed == 50
        assert state.oracle_budget_remaining == 80_000
        assert state.surrogate_accuracy == 0.85
        assert state.convergence_history == [0.7, 0.8, 0.85]


# ---------------------------------------------------------------------------
# MPCController init tests
# ---------------------------------------------------------------------------


class TestMPCControllerInit:
    def test_init_with_default_state(self):
        """Controller initializes with default MPCState."""
        state = MPCState()
        controller = MPCController(state=state)
        assert controller.state is state
        assert controller.state.oracle_budget_remaining == 100_000

    def test_init_with_custom_budget(self):
        """Controller accepts custom oracle budget that overrides state."""
        state = MPCState()
        controller = MPCController(state=state, oracle_budget=50_000)
        assert controller.state.oracle_budget_remaining == 50_000


# ---------------------------------------------------------------------------
# should_query_oracle tests
# ---------------------------------------------------------------------------


class TestShouldQueryOracle:
    def test_returns_true_for_low_confidence(self):
        """Always query oracle when confidence is below 0.5."""
        state = MPCState()
        controller = MPCController(state=state)
        assert controller.should_query_oracle(
            validator_score=90.0, confidence=0.3, is_novel=False
        ) is True

    def test_returns_true_for_novel_repos(self):
        """Always query oracle for novel patterns (first time seeing this)."""
        state = MPCState()
        controller = MPCController(state=state)
        assert controller.should_query_oracle(
            validator_score=90.0, confidence=0.9, is_novel=True
        ) is True

    def test_returns_true_for_borderline_validator_score(self):
        """Query oracle when validator_score is in borderline range (40-80)."""
        state = MPCState()
        controller = MPCController(state=state)
        assert controller.should_query_oracle(
            validator_score=60.0, confidence=0.7, is_novel=False
        ) is True

    def test_returns_false_when_budget_exhausted(self):
        """Never query oracle when budget is exhausted, regardless of other signals."""
        state = MPCState(oracle_budget_remaining=0)
        controller = MPCController(state=state)
        # Even with low confidence and novel, budget check wins
        assert controller.should_query_oracle(
            validator_score=30.0, confidence=0.1, is_novel=True
        ) is False

    def test_returns_false_for_high_confidence_and_high_score(self):
        """Don't query when confidence is high AND validator_score is high."""
        state = MPCState()
        controller = MPCController(state=state)
        assert controller.should_query_oracle(
            validator_score=95.0, confidence=0.95, is_novel=False
        ) is False

    def test_borderline_lower_bound_inclusive(self):
        """Validator score of exactly 40 is borderline."""
        state = MPCState()
        controller = MPCController(state=state)
        assert controller.should_query_oracle(
            validator_score=40.0, confidence=0.7, is_novel=False
        ) is True

    def test_borderline_upper_bound_inclusive(self):
        """Validator score of exactly 80 is borderline."""
        state = MPCState()
        controller = MPCController(state=state)
        assert controller.should_query_oracle(
            validator_score=80.0, confidence=0.7, is_novel=False
        ) is True


# ---------------------------------------------------------------------------
# record_agreement tests
# ---------------------------------------------------------------------------


class TestRecordAgreement:
    def test_updates_surrogate_accuracy(self):
        """Recording agreements updates the running surrogate accuracy."""
        state = MPCState()
        controller = MPCController(state=state)

        controller.record_agreement(agreed=True)
        controller.record_agreement(agreed=True)
        controller.record_agreement(agreed=False)

        # 2 out of 3 agreed → accuracy = 2/3 ≈ 0.667
        assert abs(controller.state.surrogate_accuracy - 2 / 3) < 0.01

    def test_all_agreements(self):
        """All agreements produce accuracy of 1.0."""
        state = MPCState()
        controller = MPCController(state=state)

        for _ in range(5):
            controller.record_agreement(agreed=True)

        assert controller.state.surrogate_accuracy == 1.0

    def test_no_agreements(self):
        """No agreements produce accuracy of 0.0."""
        state = MPCState()
        controller = MPCController(state=state)

        for _ in range(5):
            controller.record_agreement(agreed=False)

        assert controller.state.surrogate_accuracy == 0.0


# ---------------------------------------------------------------------------
# is_converged tests
# ---------------------------------------------------------------------------


class TestIsConverged:
    def test_returns_false_with_insufficient_history(self):
        """Cannot converge with fewer than 5 data points."""
        state = MPCState(convergence_history=[0.9, 0.9, 0.9])
        controller = MPCController(state=state)
        assert controller.is_converged() is False

    def test_returns_false_with_unstable_history(self):
        """Not converged when recent history has high variance."""
        state = MPCState(convergence_history=[0.5, 0.7, 0.9, 0.6, 0.8])
        controller = MPCController(state=state)
        assert controller.is_converged() is False

    def test_returns_true_with_stable_history(self):
        """Converged when last 5 values have std < 0.02."""
        state = MPCState(convergence_history=[0.90, 0.91, 0.90, 0.91, 0.90])
        controller = MPCController(state=state)
        assert controller.is_converged() is True

    def test_only_considers_last_five_values(self):
        """Convergence only looks at the last 5 values, ignoring older history."""
        # Older values are unstable, but last 5 are stable
        state = MPCState(
            convergence_history=[0.1, 0.3, 0.5, 0.7, 0.90, 0.91, 0.90, 0.91, 0.90]
        )
        controller = MPCController(state=state)
        assert controller.is_converged() is True


# ---------------------------------------------------------------------------
# next_iteration tests
# ---------------------------------------------------------------------------


class TestNextIteration:
    def test_increments_iteration(self):
        """next_iteration increments the iteration counter."""
        state = MPCState()
        controller = MPCController(state=state)

        controller.next_iteration()

        assert controller.state.iteration == 1

    def test_increments_repos_processed(self):
        """next_iteration increments total_repos_processed."""
        state = MPCState()
        controller = MPCController(state=state)

        controller.next_iteration()

        assert controller.state.total_repos_processed == 1

    def test_appends_accuracy_to_convergence_history(self):
        """next_iteration records current surrogate_accuracy in convergence_history."""
        state = MPCState(surrogate_accuracy=0.85)
        controller = MPCController(state=state)

        controller.next_iteration()

        assert controller.state.convergence_history == [0.85]

    def test_multiple_iterations(self):
        """Multiple iterations accumulate correctly."""
        state = MPCState()
        controller = MPCController(state=state)

        controller.next_iteration()
        controller.state.surrogate_accuracy = 0.7
        controller.next_iteration()
        controller.state.surrogate_accuracy = 0.8
        controller.next_iteration()

        assert controller.state.iteration == 3
        assert controller.state.total_repos_processed == 3
        assert len(controller.state.convergence_history) == 3
