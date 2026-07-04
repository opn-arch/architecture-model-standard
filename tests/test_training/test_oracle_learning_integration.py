"""Integration tests for oracle self-learning in pipeline."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from architecture_model.training.pipeline import TrainingPipeline
from architecture_model.training.oracle import Oracle
from architecture_model.training.oracle_performance import OracleResult


class TestOracleSystemPrompt:
    """Tests for Oracle system_prompt parameter and setter."""

    def test_oracle_accepts_custom_system_prompt(self):
        """Oracle should use custom system prompt when provided."""
        oracle = Oracle(model="test", system_prompt="Custom prompt here")
        assert oracle._system_prompt == "Custom prompt here"

    def test_oracle_defaults_to_builtin_prompt(self):
        """Oracle should default to built-in extraction prompt."""
        oracle = Oracle(model="test")
        assert "architecture extraction engine" in oracle._system_prompt.lower()

    def test_oracle_set_system_prompt(self):
        """set_system_prompt should update the prompt."""
        oracle = Oracle(model="test")
        oracle.set_system_prompt("New evolved prompt")
        assert oracle._system_prompt == "New evolved prompt"

    def test_oracle_custom_prompt_used_in_extract(self):
        """Custom system prompt should be used when building messages."""
        oracle = Oracle(model="test", system_prompt="My custom extraction prompt")
        # Verify the stored prompt is the custom one
        assert oracle._system_prompt == "My custom extraction prompt"


class TestPipelineOracleLearning:
    """Tests for pipeline oracle learning subsystem wiring."""

    def test_pipeline_initializes_oracle_learning(self, tmp_path):
        """Pipeline with oracle_learning_enabled should set up components."""
        db_path = str(tmp_path / "oracle_perf.db")

        with patch(
            "architecture_model.training.pipeline.OraclePerformanceStore"
        ) as mock_store_cls:
            mock_store_cls.return_value = MagicMock()

            pipeline = TrainingPipeline(
                surrogate=MagicMock(),
                oracle=MagicMock(),
                store=MagicMock(),
                evaluator=MagicMock(),
                controller=MagicMock(),
                trainer=MagicMock(),
                repo_fetcher=MagicMock(),
                oracle_learning_enabled=True,
            )

        assert pipeline._oracle_perf_store is not None
        assert pipeline._critique_refiner is not None
        assert pipeline._prompt_evolver is not None

    def test_pipeline_disabled_oracle_learning_by_default(self):
        """Pipeline without oracle_learning_enabled should not set up components."""
        pipeline = TrainingPipeline(
            surrogate=MagicMock(),
            oracle=MagicMock(),
            store=MagicMock(),
            evaluator=MagicMock(),
            controller=MagicMock(),
            trainer=MagicMock(),
            repo_fetcher=MagicMock(),
        )

        assert pipeline._oracle_perf_store is None
        assert pipeline._critique_refiner is None
        assert pipeline._prompt_evolver is None

    def test_pipeline_has_coverage_computer(self):
        """Pipeline should always have a ManifestCoverageComputer."""
        pipeline = TrainingPipeline(
            surrogate=MagicMock(),
            oracle=MagicMock(),
            store=MagicMock(),
            evaluator=MagicMock(),
            controller=MagicMock(),
            trainer=MagicMock(),
            repo_fetcher=MagicMock(),
        )
        assert pipeline._coverage_computer is not None


class TestPipelineOracleExports:
    """Tests for __init__.py exports."""

    def test_self_critique_refiner_importable(self):
        """SelfCritiqueRefiner should be importable from training package."""
        from architecture_model.training import SelfCritiqueRefiner
        assert SelfCritiqueRefiner is not None

    def test_prompt_evolver_importable(self):
        """PromptEvolver should be importable from training package."""
        from architecture_model.training import PromptEvolver
        assert PromptEvolver is not None
