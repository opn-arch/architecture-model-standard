"""Tests for TrainingPipeline.record_test_guided_signal integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from architecture_model.training.pipeline import TrainingPipeline
from architecture_model.training.test_guided_generator import (
    GenerationAttempt,
    TestGuidedResult,
)
from architecture_model.training.failure_parser import FailureReport


def _make_attempt(iteration: int, code: str, pass_rate: float) -> GenerationAttempt:
    """Helper to create a GenerationAttempt with minimal required fields."""
    return GenerationAttempt(
        iteration=iteration,
        code=code,
        pass_rate=pass_rate,
        failures=FailureReport(
            total_collected=10,
            total_passed=int(10 * pass_rate),
            total_failed=10 - int(10 * pass_rate),
            pass_rate=pass_rate,
        ),
        time_seconds=1.0,
        components_regenerated=[],
    )


def _make_pipeline() -> TrainingPipeline:
    """Create a TrainingPipeline with mocked dependencies."""
    surrogate = MagicMock()
    oracle = MagicMock()
    store = MagicMock()
    evaluator = MagicMock()
    controller = MagicMock()
    controller.state.iteration = 5
    trainer = MagicMock()
    repo_fetcher = MagicMock()

    pipeline = TrainingPipeline(
        surrogate=surrogate,
        oracle=oracle,
        store=store,
        evaluator=evaluator,
        controller=controller,
        trainer=trainer,
        repo_fetcher=repo_fetcher,
    )
    return pipeline


class TestRecordTestGuidedSignal:
    """Tests for TrainingPipeline.record_test_guided_signal."""

    def test_returns_correct_loss_vector_entries(self):
        """Should return dict with test_pass_rate and test_iterations."""
        pipeline = _make_pipeline()
        result = TestGuidedResult(
            final_code="def foo(): pass",
            final_pass_rate=0.85,
            iterations=3,
            attempts=[],
            converged=True,
            structural_score=0.9,
        )

        signal = pipeline.record_test_guided_signal(
            result=result,
            model_yaml="components:\n  - id: foo",
        )

        assert signal["test_pass_rate"] == 0.85
        assert signal["test_iterations"] == 3

    def test_dpo_pairs_generated_on_improvement(self):
        """Should generate DPO pairs when pass_rate improves between attempts."""
        pipeline = _make_pipeline()
        attempts = [
            _make_attempt(0, "code_v0", 0.4),
            _make_attempt(1, "code_v1", 0.7),
            _make_attempt(2, "code_v2", 0.9),
        ]
        result = TestGuidedResult(
            final_code="code_v2",
            final_pass_rate=0.9,
            iterations=3,
            attempts=attempts,
            converged=True,
        )
        model_yaml = "components:\n  - id: foo"

        signal = pipeline.record_test_guided_signal(
            result=result,
            model_yaml=model_yaml,
        )

        assert signal["dpo_pairs_generated"] == 2
        assert pipeline.store.save_preference.call_count == 2

        # First pair: attempt[1] chosen over attempt[0]
        call_args_0 = pipeline.store.save_preference.call_args_list[0]
        assert call_args_0.kwargs["prompt"] == model_yaml
        assert call_args_0.kwargs["chosen"] == "code_v1"
        assert call_args_0.kwargs["rejected"] == "code_v0"
        assert call_args_0.kwargs["margin"] == pytest.approx(0.3)

        # Second pair: attempt[2] chosen over attempt[1]
        call_args_1 = pipeline.store.save_preference.call_args_list[1]
        assert call_args_1.kwargs["prompt"] == model_yaml
        assert call_args_1.kwargs["chosen"] == "code_v2"
        assert call_args_1.kwargs["rejected"] == "code_v1"
        assert call_args_1.kwargs["margin"] == pytest.approx(0.2)

    def test_no_dpo_pairs_when_pass_rate_stays_same(self):
        """Should not generate DPO pairs when pass_rate doesn't improve."""
        pipeline = _make_pipeline()
        attempts = [
            _make_attempt(0, "code_v0", 0.5),
            _make_attempt(1, "code_v1", 0.5),
            _make_attempt(2, "code_v2", 0.5),
        ]
        result = TestGuidedResult(
            final_code="code_v2",
            final_pass_rate=0.5,
            iterations=3,
            attempts=attempts,
        )

        signal = pipeline.record_test_guided_signal(
            result=result,
            model_yaml="components:\n  - id: foo",
        )

        assert signal["dpo_pairs_generated"] == 0
        pipeline.store.save_preference.assert_not_called()

    def test_no_dpo_pairs_when_pass_rate_decreases(self):
        """Should not generate DPO pairs when pass_rate decreases."""
        pipeline = _make_pipeline()
        attempts = [
            _make_attempt(0, "code_v0", 0.8),
            _make_attempt(1, "code_v1", 0.6),
            _make_attempt(2, "code_v2", 0.4),
        ]
        result = TestGuidedResult(
            final_code="code_v2",
            final_pass_rate=0.4,
            iterations=3,
            attempts=attempts,
        )

        signal = pipeline.record_test_guided_signal(
            result=result,
            model_yaml="components:\n  - id: foo",
        )

        assert signal["dpo_pairs_generated"] == 0
        pipeline.store.save_preference.assert_not_called()

    def test_empty_attempts_list(self):
        """Should handle empty attempts list gracefully."""
        pipeline = _make_pipeline()
        result = TestGuidedResult(
            final_code="def foo(): pass",
            final_pass_rate=1.0,
            iterations=0,
            attempts=[],
        )

        signal = pipeline.record_test_guided_signal(
            result=result,
            model_yaml="components:\n  - id: foo",
        )

        assert signal["test_pass_rate"] == 1.0
        assert signal["test_iterations"] == 0
        assert signal["dpo_pairs_generated"] == 0
        pipeline.store.save_preference.assert_not_called()

    def test_single_attempt_no_pairs(self):
        """Should produce no DPO pairs with only one attempt."""
        pipeline = _make_pipeline()
        attempts = [_make_attempt(0, "code_v0", 0.9)]
        result = TestGuidedResult(
            final_code="code_v0",
            final_pass_rate=0.9,
            iterations=1,
            attempts=attempts,
        )

        signal = pipeline.record_test_guided_signal(
            result=result,
            model_yaml="components:\n  - id: foo",
        )

        assert signal["test_pass_rate"] == 0.9
        assert signal["test_iterations"] == 1
        assert signal["dpo_pairs_generated"] == 0
        pipeline.store.save_preference.assert_not_called()

    def test_margin_calculation_is_correct(self):
        """Margin should be exactly the pass_rate delta between consecutive attempts."""
        pipeline = _make_pipeline()
        attempts = [
            _make_attempt(0, "code_v0", 0.1),
            _make_attempt(1, "code_v1", 0.55),
        ]
        result = TestGuidedResult(
            final_code="code_v1",
            final_pass_rate=0.55,
            iterations=2,
            attempts=attempts,
        )

        pipeline.record_test_guided_signal(
            result=result,
            model_yaml="model_yaml_content",
        )

        call_kwargs = pipeline.store.save_preference.call_args.kwargs
        assert call_kwargs["margin"] == pytest.approx(0.45)

    def test_uses_controller_iteration_when_not_provided(self):
        """Should use controller.state.iteration when iteration param is None."""
        pipeline = _make_pipeline()
        pipeline.controller.state.iteration = 7
        attempts = [
            _make_attempt(0, "code_v0", 0.3),
            _make_attempt(1, "code_v1", 0.8),
        ]
        result = TestGuidedResult(
            final_code="code_v1",
            final_pass_rate=0.8,
            iterations=2,
            attempts=attempts,
        )

        pipeline.record_test_guided_signal(
            result=result,
            model_yaml="model_yaml_content",
        )

        call_kwargs = pipeline.store.save_preference.call_args.kwargs
        assert call_kwargs["iteration"] == 7

    def test_uses_explicit_iteration_when_provided(self):
        """Should use the explicit iteration parameter over controller state."""
        pipeline = _make_pipeline()
        pipeline.controller.state.iteration = 7
        attempts = [
            _make_attempt(0, "code_v0", 0.3),
            _make_attempt(1, "code_v1", 0.8),
        ]
        result = TestGuidedResult(
            final_code="code_v1",
            final_pass_rate=0.8,
            iterations=2,
            attempts=attempts,
        )

        pipeline.record_test_guided_signal(
            result=result,
            model_yaml="model_yaml_content",
            iteration=42,
        )

        call_kwargs = pipeline.store.save_preference.call_args.kwargs
        assert call_kwargs["iteration"] == 42

    def test_mixed_improvement_and_regression(self):
        """Should only generate DPO pairs for improvements, not regressions."""
        pipeline = _make_pipeline()
        attempts = [
            _make_attempt(0, "code_v0", 0.3),
            _make_attempt(1, "code_v1", 0.6),  # improvement
            _make_attempt(2, "code_v2", 0.5),  # regression - no pair
            _make_attempt(3, "code_v3", 0.8),  # improvement
        ]
        result = TestGuidedResult(
            final_code="code_v3",
            final_pass_rate=0.8,
            iterations=4,
            attempts=attempts,
        )

        signal = pipeline.record_test_guided_signal(
            result=result,
            model_yaml="model_yaml_content",
        )

        # Only pairs where pass_rate improved: (0→1) and (2→3)
        assert signal["dpo_pairs_generated"] == 2
        assert pipeline.store.save_preference.call_count == 2

        # Verify the correct pairs were saved
        calls = pipeline.store.save_preference.call_args_list
        # First pair: code_v1 chosen over code_v0
        assert calls[0].kwargs["chosen"] == "code_v1"
        assert calls[0].kwargs["rejected"] == "code_v0"
        assert calls[0].kwargs["margin"] == pytest.approx(0.3)
        # Second pair: code_v3 chosen over code_v2
        assert calls[1].kwargs["chosen"] == "code_v3"
        assert calls[1].kwargs["rejected"] == "code_v2"
        assert calls[1].kwargs["margin"] == pytest.approx(0.3)
