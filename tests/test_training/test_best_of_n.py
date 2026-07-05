"""Tests for Best-of-N DPO preference pair generation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from architecture_model.training.best_of_n import BestOfNGenerator, RankedExtraction
from architecture_model.training.evaluator import Evaluator, LossVector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_model(name: str = "test"):
    """Create a minimal mock ArchitectureModel."""
    model = MagicMock()
    model.entity_count = 5
    model.to_yaml = MagicMock(return_value=f"entities: {name}\nrelationships: []\n")
    model.entities = MagicMock()
    model.relationships = []
    for attr in ['actors', 'capabilities', 'behaviors', 'interfaces', 'constraints', 'layers', 'components']:
        setattr(model.entities, attr, [])
    return model


def _make_surrogate(models: list):
    """Create a surrogate mock that returns models in sequence."""
    s = MagicMock()
    s.extract_model = AsyncMock(side_effect=models)
    return s


def _make_evaluator(losses: list[LossVector]):
    """Create an evaluator mock that returns losses in sequence."""
    ev = MagicMock(spec=Evaluator)
    ev.compute_loss = MagicMock(side_effect=losses)
    return ev


# ---------------------------------------------------------------------------
# Tests: generate returns best/worst pair
# ---------------------------------------------------------------------------


class TestGenerateReturnsBestWorstPair:
    @pytest.mark.asyncio
    async def test_generate_returns_best_worst_pair(self):
        """Mock surrogate returns different models, verify ranking."""
        models = [_make_model(f"m{i}") for i in range(4)]
        surrogate = _make_surrogate(models)

        # Different quality levels
        losses = [
            LossVector(structural_accuracy=0.9, completeness=0.8, validator_score=90),
            LossVector(structural_accuracy=0.5, completeness=0.6, validator_score=70),
            LossVector(structural_accuracy=0.7, completeness=0.7, validator_score=80),
            LossVector(structural_accuracy=0.3, completeness=0.4, validator_score=60),
        ]
        evaluator = _make_evaluator(losses)

        oracle_model = _make_model("oracle")
        gen = BestOfNGenerator(surrogate=surrogate, evaluator=evaluator, n=4)

        result = await gen.generate("code context", oracle_model)

        assert result is not None
        best, worst = result
        # Best should have highest structural_accuracy (0.9)
        assert best.loss.structural_accuracy == 0.9
        # Worst should have lowest structural_accuracy (0.3)
        assert worst.loss.structural_accuracy == 0.3

    @pytest.mark.asyncio
    async def test_generate_returns_yaml_output(self):
        """Verify that yaml_output is populated from model.to_yaml()."""
        models = [_make_model(f"m{i}") for i in range(4)]
        surrogate = _make_surrogate(models)

        losses = [
            LossVector(structural_accuracy=0.9, completeness=0.8, validator_score=90),
            LossVector(structural_accuracy=0.3, completeness=0.4, validator_score=60),
            LossVector(structural_accuracy=0.6, completeness=0.5, validator_score=70),
            LossVector(structural_accuracy=0.5, completeness=0.6, validator_score=65),
        ]
        evaluator = _make_evaluator(losses)

        oracle_model = _make_model("oracle")
        gen = BestOfNGenerator(surrogate=surrogate, evaluator=evaluator, n=4)

        result = await gen.generate("code context", oracle_model)

        assert result is not None
        best, worst = result
        assert "entities:" in best.yaml_output
        assert "entities:" in worst.yaml_output


# ---------------------------------------------------------------------------
# Tests: generate returns None on insufficient candidates
# ---------------------------------------------------------------------------


class TestGenerateReturnsNoneOnInsufficientCandidates:
    @pytest.mark.asyncio
    async def test_generate_returns_none_on_insufficient_candidates(self):
        """Mock surrogate returns None most times → fewer than 2 candidates."""
        # Only 1 valid model out of 4 attempts
        models = [None, None, _make_model("single"), None]
        surrogate = _make_surrogate(models)

        losses = [LossVector(structural_accuracy=0.7, completeness=0.7, validator_score=80)]
        evaluator = _make_evaluator(losses)

        oracle_model = _make_model("oracle")
        gen = BestOfNGenerator(surrogate=surrogate, evaluator=evaluator, n=4)

        result = await gen.generate("code context", oracle_model)

        assert result is None

    @pytest.mark.asyncio
    async def test_generate_returns_none_when_all_fail(self):
        """All surrogate calls return None."""
        models = [None, None, None, None]
        surrogate = _make_surrogate(models)

        evaluator = MagicMock(spec=Evaluator)
        oracle_model = _make_model("oracle")
        gen = BestOfNGenerator(surrogate=surrogate, evaluator=evaluator, n=4)

        result = await gen.generate("code context", oracle_model)

        assert result is None


# ---------------------------------------------------------------------------
# Tests: generate returns None on small margin
# ---------------------------------------------------------------------------


class TestGenerateReturnsNoneOnSmallMargin:
    @pytest.mark.asyncio
    async def test_generate_returns_none_on_small_margin(self):
        """Models with similar quality → margin < 0.05 → returns None."""
        models = [_make_model(f"m{i}") for i in range(4)]
        surrogate = _make_surrogate(models)

        # All models have very similar structural_accuracy
        losses = [
            LossVector(structural_accuracy=0.72, completeness=0.7, validator_score=80),
            LossVector(structural_accuracy=0.70, completeness=0.65, validator_score=78),
            LossVector(structural_accuracy=0.71, completeness=0.68, validator_score=79),
            LossVector(structural_accuracy=0.73, completeness=0.72, validator_score=81),
        ]
        evaluator = _make_evaluator(losses)

        oracle_model = _make_model("oracle")
        gen = BestOfNGenerator(surrogate=surrogate, evaluator=evaluator, n=4)

        result = await gen.generate("code context", oracle_model)

        # margin = 0.73 - 0.70 = 0.03 < 0.05, so returns None
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_returns_pair_at_threshold(self):
        """Models with margin exactly at 0.05 → returns None (< not <=)."""
        models = [_make_model(f"m{i}") for i in range(4)]
        surrogate = _make_surrogate(models)

        # margin = 0.75 - 0.70 = 0.05, which is NOT < 0.05
        losses = [
            LossVector(structural_accuracy=0.75, completeness=0.7, validator_score=80),
            LossVector(structural_accuracy=0.70, completeness=0.65, validator_score=78),
            LossVector(structural_accuracy=0.72, completeness=0.68, validator_score=79),
            LossVector(structural_accuracy=0.71, completeness=0.66, validator_score=77),
        ]
        evaluator = _make_evaluator(losses)

        oracle_model = _make_model("oracle")
        gen = BestOfNGenerator(surrogate=surrogate, evaluator=evaluator, n=4)

        result = await gen.generate("code context", oracle_model)

        # margin = 0.75 - 0.70 = 0.05, which is NOT < 0.05, so pair IS returned
        assert result is not None


# ---------------------------------------------------------------------------
# Tests: generate handles extraction errors
# ---------------------------------------------------------------------------


class TestGenerateHandlesExtractionErrors:
    @pytest.mark.asyncio
    async def test_generate_handles_extraction_errors(self):
        """Surrogate raises Exception on some calls, still produces valid pair."""
        # 2 succeed, 2 throw exceptions
        model_a = _make_model("a")
        model_b = _make_model("b")

        surrogate = MagicMock()
        surrogate.extract_model = AsyncMock(
            side_effect=[
                RuntimeError("network error"),
                model_a,
                ValueError("parse failure"),
                model_b,
            ]
        )

        losses = [
            LossVector(structural_accuracy=0.9, completeness=0.8, validator_score=90),
            LossVector(structural_accuracy=0.4, completeness=0.5, validator_score=65),
        ]
        evaluator = _make_evaluator(losses)

        oracle_model = _make_model("oracle")
        gen = BestOfNGenerator(surrogate=surrogate, evaluator=evaluator, n=4)

        result = await gen.generate("code context", oracle_model)

        assert result is not None
        best, worst = result
        assert best.loss.structural_accuracy == 0.9
        assert worst.loss.structural_accuracy == 0.4

    @pytest.mark.asyncio
    async def test_generate_returns_none_when_errors_leave_too_few(self):
        """All but one call raises → only 1 candidate → returns None."""
        model_a = _make_model("a")
        surrogate = MagicMock()
        surrogate.extract_model = AsyncMock(
            side_effect=[
                RuntimeError("fail"),
                RuntimeError("fail"),
                model_a,
                RuntimeError("fail"),
            ]
        )

        losses = [LossVector(structural_accuracy=0.7, completeness=0.7, validator_score=80)]
        evaluator = _make_evaluator(losses)

        oracle_model = _make_model("oracle")
        gen = BestOfNGenerator(surrogate=surrogate, evaluator=evaluator, n=4)

        result = await gen.generate("code context", oracle_model)

        assert result is None


# ---------------------------------------------------------------------------
# Tests: ranking uses structural_accuracy as primary sort key
# ---------------------------------------------------------------------------


class TestRankingUsesStructuralAccuracyPrimary:
    @pytest.mark.asyncio
    async def test_ranking_uses_structural_accuracy_primary(self):
        """Verify sort order: structural_accuracy is primary, completeness is secondary."""
        models = [_make_model(f"m{i}") for i in range(4)]
        surrogate = _make_surrogate(models)

        # Model with lower structural_accuracy but higher completeness should rank LOWER
        losses = [
            LossVector(structural_accuracy=0.6, completeness=0.99, validator_score=90),
            LossVector(structural_accuracy=0.9, completeness=0.3, validator_score=70),
            LossVector(structural_accuracy=0.7, completeness=0.8, validator_score=80),
            LossVector(structural_accuracy=0.4, completeness=0.95, validator_score=85),
        ]
        evaluator = _make_evaluator(losses)

        oracle_model = _make_model("oracle")
        gen = BestOfNGenerator(surrogate=surrogate, evaluator=evaluator, n=4)

        result = await gen.generate("code context", oracle_model)

        assert result is not None
        best, worst = result
        # Best by structural_accuracy = 0.9 (even though completeness is only 0.3)
        assert best.loss.structural_accuracy == 0.9
        # Worst by structural_accuracy = 0.4
        assert worst.loss.structural_accuracy == 0.4

    @pytest.mark.asyncio
    async def test_completeness_breaks_ties(self):
        """When structural_accuracy ties, completeness is the tiebreaker."""
        models = [_make_model(f"m{i}") for i in range(3)]
        surrogate = _make_surrogate(models)

        # Two models tie on structural_accuracy, differ on completeness
        losses = [
            LossVector(structural_accuracy=0.8, completeness=0.9, validator_score=85),
            LossVector(structural_accuracy=0.8, completeness=0.3, validator_score=80),
            LossVector(structural_accuracy=0.2, completeness=0.5, validator_score=60),
        ]
        evaluator = _make_evaluator(losses)

        oracle_model = _make_model("oracle")
        gen = BestOfNGenerator(surrogate=surrogate, evaluator=evaluator, n=3)

        result = await gen.generate("code context", oracle_model)

        assert result is not None
        best, worst = result
        # Best: structural_accuracy=0.8, completeness=0.9 (wins tie)
        assert best.loss.structural_accuracy == 0.8
        assert best.loss.completeness == 0.9
        # Worst: structural_accuracy=0.2
        assert worst.loss.structural_accuracy == 0.2


# ---------------------------------------------------------------------------
# Tests: pipeline integration with Best-of-N
# ---------------------------------------------------------------------------


class TestPipelineUsesBestOfN:
    @pytest.mark.asyncio
    async def test_pipeline_uses_best_of_n(self):
        """Integration: pipeline uses BestOfNGenerator when loss < 0.8."""
        from architecture_model.training.pipeline import TrainingPipeline
        from architecture_model.training.controller import MPCController, MPCState

        mock_model = _make_model("local")
        mock_oracle_model = _make_model("oracle")

        surrogate = MagicMock()
        surrogate.confidence = MagicMock(return_value=0.8)
        oracle = MagicMock()
        oracle.extract_model = AsyncMock(return_value=mock_oracle_model)
        store = MagicMock()
        # Low structural_accuracy → triggers Best-of-N
        loss_vec = LossVector(0.5, 0.6, 75)
        evaluator = MagicMock()
        evaluator.compute_loss = MagicMock(return_value=loss_vec)
        controller = MPCController(MPCState())
        controller.should_query_oracle = MagicMock(return_value=True)
        trainer = MagicMock()
        repo_fetcher = MagicMock()
        repo_fetcher.clone = MagicMock(return_value=Path("/tmp/test"))

        pipeline = TrainingPipeline(
            surrogate=surrogate, oracle=oracle, store=store,
            evaluator=evaluator, controller=controller,
            trainer=trainer, repo_fetcher=repo_fetcher,
        )
        pipeline.enhanced_extract = AsyncMock(return_value=(mock_model, 0.8))
        pipeline._read_code_context = MagicMock(return_value="# code")

        # Mock the BestOfNGenerator to return a pair
        best = RankedExtraction(
            model=_make_model("best"),
            loss=LossVector(0.8, 0.7, 85),
            yaml_output="best_yaml",
        )
        worst = RankedExtraction(
            model=_make_model("worst"),
            loss=LossVector(0.3, 0.4, 60),
            yaml_output="worst_yaml",
        )
        pipeline._best_of_n = MagicMock()
        pipeline._best_of_n.generate = AsyncMock(return_value=(best, worst))

        with patch('architecture_model.training.pipeline.validate_model') as mock_validate:
            mock_validate.return_value = MagicMock(score=75)
            repo = MagicMock()
            repo.url = "https://github.com/test/test"
            repo.default_branch = "main"
            await pipeline._process_repo(repo)

        # Verify BestOfN was called
        pipeline._best_of_n.generate.assert_called_once()

        # Verify save_preference was called with Best-of-N outputs
        store.save_preference.assert_called_once()
        call_kwargs = store.save_preference.call_args[1]
        assert call_kwargs["chosen"] == "best_yaml"
        assert call_kwargs["rejected"] == "worst_yaml"
        assert call_kwargs["margin"] == pytest.approx(0.5)  # 0.8 - 0.3

    @pytest.mark.asyncio
    async def test_pipeline_no_dpo_when_accuracy_high(self):
        """No Best-of-N DPO when structural_accuracy >= 0.8."""
        from architecture_model.training.pipeline import TrainingPipeline
        from architecture_model.training.controller import MPCController, MPCState

        mock_model = _make_model("local")
        mock_oracle_model = _make_model("oracle")

        surrogate = MagicMock()
        surrogate.confidence = MagicMock(return_value=0.8)
        oracle = MagicMock()
        oracle.extract_model = AsyncMock(return_value=mock_oracle_model)
        store = MagicMock()
        # High structural_accuracy → should NOT trigger Best-of-N
        loss_vec = LossVector(0.85, 0.9, 95)
        evaluator = MagicMock()
        evaluator.compute_loss = MagicMock(return_value=loss_vec)
        controller = MPCController(MPCState())
        controller.should_query_oracle = MagicMock(return_value=True)
        trainer = MagicMock()
        repo_fetcher = MagicMock()
        repo_fetcher.clone = MagicMock(return_value=Path("/tmp/test"))

        pipeline = TrainingPipeline(
            surrogate=surrogate, oracle=oracle, store=store,
            evaluator=evaluator, controller=controller,
            trainer=trainer, repo_fetcher=repo_fetcher,
        )
        pipeline.enhanced_extract = AsyncMock(return_value=(mock_model, 0.8))
        pipeline._read_code_context = MagicMock(return_value="# code")
        pipeline._best_of_n = MagicMock()

        with patch('architecture_model.training.pipeline.validate_model') as mock_validate:
            mock_validate.return_value = MagicMock(score=95)
            repo = MagicMock()
            repo.url = "https://github.com/test/test"
            repo.default_branch = "main"
            await pipeline._process_repo(repo)

        # BestOfN should NOT have been called
        pipeline._best_of_n.generate.assert_not_called()
        store.save_preference.assert_not_called()

    @pytest.mark.asyncio
    async def test_pipeline_no_save_when_best_of_n_returns_none(self):
        """When BestOfN returns None (small margin), no preference saved."""
        from architecture_model.training.pipeline import TrainingPipeline
        from architecture_model.training.controller import MPCController, MPCState

        mock_model = _make_model("local")
        mock_oracle_model = _make_model("oracle")

        surrogate = MagicMock()
        surrogate.confidence = MagicMock(return_value=0.8)
        oracle = MagicMock()
        oracle.extract_model = AsyncMock(return_value=mock_oracle_model)
        store = MagicMock()
        loss_vec = LossVector(0.5, 0.6, 75)
        evaluator = MagicMock()
        evaluator.compute_loss = MagicMock(return_value=loss_vec)
        controller = MPCController(MPCState())
        controller.should_query_oracle = MagicMock(return_value=True)
        trainer = MagicMock()
        repo_fetcher = MagicMock()
        repo_fetcher.clone = MagicMock(return_value=Path("/tmp/test"))

        pipeline = TrainingPipeline(
            surrogate=surrogate, oracle=oracle, store=store,
            evaluator=evaluator, controller=controller,
            trainer=trainer, repo_fetcher=repo_fetcher,
        )
        pipeline.enhanced_extract = AsyncMock(return_value=(mock_model, 0.8))
        pipeline._read_code_context = MagicMock(return_value="# code")

        # BestOfN returns None (insufficient margin)
        pipeline._best_of_n = MagicMock()
        pipeline._best_of_n.generate = AsyncMock(return_value=None)

        with patch('architecture_model.training.pipeline.validate_model') as mock_validate:
            mock_validate.return_value = MagicMock(score=75)
            repo = MagicMock()
            repo.url = "https://github.com/test/test"
            repo.default_branch = "main"
            await pipeline._process_repo(repo)

        # BestOfN was called but returned None
        pipeline._best_of_n.generate.assert_called_once()
        # No preference saved
        store.save_preference.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: BestOfNGenerator properties
# ---------------------------------------------------------------------------


class TestBestOfNProperties:
    def test_n_property(self):
        """Verify n property returns configured value."""
        surrogate = MagicMock()
        evaluator = MagicMock()
        gen = BestOfNGenerator(surrogate=surrogate, evaluator=evaluator, n=8)
        assert gen.n == 8

    def test_default_n(self):
        """Default n is 4."""
        surrogate = MagicMock()
        evaluator = MagicMock()
        gen = BestOfNGenerator(surrogate=surrogate, evaluator=evaluator)
        assert gen.n == 4
