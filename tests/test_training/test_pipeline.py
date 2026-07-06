"""Tests for Pipeline Orchestrator: MPC training loop coordination."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from architecture_model.training.pipeline import TrainingPipeline
from architecture_model.training.controller import MPCController, MPCState
from architecture_model.training.repo_fetcher import RepoInfo


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_repo_info(name: str = "owner/repo") -> RepoInfo:
    return RepoInfo(
        url=f"https://github.com/{name}",
        full_name=name,
        stars=500,
        language="python",
        default_branch="main",
        has_ci=True,
        size_kb=5000,
    )


def _make_architecture_model():
    """Create a minimal mock ArchitectureModel."""
    model = MagicMock()
    model.entity_count = 5
    model.to_yaml = MagicMock(return_value="entities: {}\nrelationships: []\n")
    return model


@pytest.fixture
def mock_surrogate():
    s = MagicMock()
    s.extract_model = AsyncMock(return_value=_make_architecture_model())
    s.confidence = MagicMock(return_value=0.8)
    return s


@pytest.fixture
def mock_oracle():
    o = MagicMock()
    o.extract_model = AsyncMock(return_value=_make_architecture_model())
    return o


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.save = MagicMock(return_value=1)
    store.new_examples_since_last_train = MagicMock(return_value=10)
    store.count_preferences = MagicMock(return_value=0)
    return store


@pytest.fixture
def mock_evaluator():
    ev = MagicMock()
    loss = MagicMock()
    loss.structural_accuracy = 0.9
    loss.completeness = 0.85
    loss.validator_score = 90.0
    ev.compute_loss = MagicMock(return_value=loss)
    return ev


@pytest.fixture
def mock_controller():
    state = MPCState()
    ctrl = MagicMock(spec=MPCController)
    ctrl.state = state
    ctrl.should_query_oracle = MagicMock(return_value=True)
    ctrl.is_converged = MagicMock(return_value=False)
    ctrl.next_iteration = MagicMock()
    ctrl.record_agreement = MagicMock()
    return ctrl


@pytest.fixture
def mock_trainer():
    t = MagicMock()
    t.prepare_dataset = MagicMock(return_value=MagicMock())
    t.train = MagicMock(return_value=Path("/tmp/lora_adapter"))
    return t


@pytest.fixture
def mock_repo_fetcher():
    rf = MagicMock()
    rf.discover = AsyncMock(return_value=[_make_repo_info("org/repo1"), _make_repo_info("org/repo2")])
    rf.clone = MagicMock(return_value=Path("/tmp/clones/org/repo1"))
    return rf


@pytest.fixture
def pipeline(
    mock_surrogate,
    mock_oracle,
    mock_store,
    mock_evaluator,
    mock_controller,
    mock_trainer,
    mock_repo_fetcher,
):
    p = TrainingPipeline(
        surrogate=mock_surrogate,
        oracle=mock_oracle,
        store=mock_store,
        evaluator=mock_evaluator,
        controller=mock_controller,
        trainer=mock_trainer,
        repo_fetcher=mock_repo_fetcher,
    )
    # Mock enhanced_extract to return a valid model + confidence
    p.enhanced_extract = AsyncMock(return_value=(_make_architecture_model(), 0.8))
    # Mock _read_code_context so it doesn't try to scan filesystem
    p._read_code_context = MagicMock(return_value="# mock code context")
    return p


# ---------------------------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------------------------


class TestTrainingPipelineInit:
    def test_accepts_all_components(self, pipeline, mock_surrogate, mock_oracle, mock_store):
        """TrainingPipeline stores all injected components."""
        assert pipeline.surrogate is mock_surrogate
        assert pipeline.oracle is mock_oracle
        assert pipeline.store is mock_store


# ---------------------------------------------------------------------------
# run_iteration tests
# ---------------------------------------------------------------------------


class TestRunIteration:
    @pytest.mark.asyncio
    async def test_discovers_repos(self, pipeline, mock_repo_fetcher):
        """run_iteration discovers repos via repo_fetcher."""
        await pipeline.run_iteration(n_repos=5)
        mock_repo_fetcher.discover.assert_called_once_with(5)

    @pytest.mark.asyncio
    async def test_calls_enhanced_extract_for_each_repo(self, pipeline, mock_repo_fetcher):
        """run_iteration runs enhanced_extract for each discovered repo."""
        repos = [_make_repo_info("a/b"), _make_repo_info("c/d"), _make_repo_info("e/f")]
        mock_repo_fetcher.discover = AsyncMock(return_value=repos)

        await pipeline.run_iteration(n_repos=3)

        assert pipeline.enhanced_extract.call_count == 3

    @pytest.mark.asyncio
    async def test_queries_oracle_when_controller_says_yes(
        self, pipeline, mock_controller, mock_oracle
    ):
        """run_iteration queries oracle when should_query_oracle returns True."""
        mock_controller.should_query_oracle.return_value = True

        await pipeline.run_iteration(n_repos=2)

        assert mock_oracle.extract_model.call_count == 2

    @pytest.mark.asyncio
    async def test_skips_oracle_when_controller_says_no(
        self, pipeline, mock_controller, mock_oracle
    ):
        """run_iteration does NOT query oracle when should_query_oracle returns False."""
        mock_controller.should_query_oracle.return_value = False

        await pipeline.run_iteration(n_repos=2)

        mock_oracle.extract_model.assert_not_called()

    @pytest.mark.asyncio
    async def test_saves_examples_to_store(self, pipeline, mock_store, mock_repo_fetcher):
        """run_iteration saves a TrainingExample for each repo processed."""
        repos = [_make_repo_info("x/y"), _make_repo_info("a/b")]
        mock_repo_fetcher.discover = AsyncMock(return_value=repos)

        await pipeline.run_iteration(n_repos=2)

        assert mock_store.save.call_count == 2

    @pytest.mark.asyncio
    async def test_triggers_training_at_threshold(
        self, pipeline, mock_store, mock_trainer
    ):
        """run_iteration triggers trainer when new_examples >= 50."""
        mock_store.new_examples_since_last_train.return_value = 55

        await pipeline.run_iteration(n_repos=2)

        mock_trainer.prepare_dataset.assert_called_once_with(mock_store)
        mock_trainer.train.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_training_below_threshold(
        self, pipeline, mock_store, mock_trainer
    ):
        """run_iteration does NOT trigger training when new_examples < 50."""
        mock_store.new_examples_since_last_train.return_value = 10

        await pipeline.run_iteration(n_repos=2)

        mock_trainer.prepare_dataset.assert_not_called()
        mock_trainer.train.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_updated_state(self, pipeline, mock_controller):
        """run_iteration calls controller.next_iteration and returns state."""
        result = await pipeline.run_iteration(n_repos=2)

        mock_controller.next_iteration.assert_called_once()
        assert result is mock_controller.state

    @pytest.mark.asyncio
    async def test_computes_loss_when_oracle_queried(
        self, pipeline, mock_controller, mock_evaluator
    ):
        """run_iteration computes loss comparing surrogate vs oracle output."""
        mock_controller.should_query_oracle.return_value = True

        await pipeline.run_iteration(n_repos=2)

        assert mock_evaluator.compute_loss.call_count == 2


# ---------------------------------------------------------------------------
# run_loop tests
# ---------------------------------------------------------------------------


class TestRunLoop:
    @pytest.mark.asyncio
    async def test_exits_on_convergence(self, pipeline, mock_controller):
        """run_loop stops early when controller reports convergence."""
        call_count = 0

        def side_effect():
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                mock_controller.is_converged.return_value = True

        mock_controller.next_iteration.side_effect = side_effect

        result = await pipeline.run_loop(max_iterations=100)

        assert result is mock_controller.state
        # Should have run 3 iterations, not 100
        assert mock_controller.next_iteration.call_count == 3

    @pytest.mark.asyncio
    async def test_exits_on_max_iterations(self, pipeline, mock_controller):
        """run_loop stops after max_iterations even without convergence."""
        mock_controller.is_converged.return_value = False

        result = await pipeline.run_loop(max_iterations=5)

        assert result is mock_controller.state
        assert mock_controller.next_iteration.call_count == 5

    @pytest.mark.asyncio
    async def test_exits_on_budget_exhaustion(self, pipeline, mock_controller):
        """run_loop stops when oracle budget is exhausted."""
        call_count = 0

        def side_effect():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                mock_controller.state.oracle_budget_remaining = 0

        mock_controller.next_iteration.side_effect = side_effect

        result = await pipeline.run_loop(max_iterations=100)

        assert result is mock_controller.state
        # Should stop at 2, not continue to 100
        assert mock_controller.next_iteration.call_count == 2


# ---------------------------------------------------------------------------
# Enhanced _process_repo tests
# ---------------------------------------------------------------------------


class TestProcessRepoEnhanced:
    @pytest.mark.asyncio
    async def test_process_repo_uses_enhanced_extract(self):
        """_process_repo should use enhanced_extract, not raw extract_model."""
        from architecture_model.training.evaluator import LossVector

        mock_model = MagicMock()
        mock_model.relationships = []
        mock_model.entities = MagicMock()
        for attr in ['actors', 'capabilities', 'behaviors', 'interfaces', 'constraints', 'layers', 'components']:
            setattr(mock_model.entities, attr, [])

        surrogate = MagicMock()
        surrogate.confidence = MagicMock(return_value=0.8)
        oracle = MagicMock()
        oracle.extract_model = AsyncMock(return_value=mock_model)
        store = MagicMock()
        evaluator = MagicMock()
        evaluator.compute_loss = MagicMock(return_value=LossVector(0.7, 0.8, 90))
        controller = MPCController(MPCState())
        controller.should_query_oracle = MagicMock(return_value=True)
        trainer = MagicMock()
        repo_fetcher = MagicMock()
        repo_fetcher.clone = MagicMock(return_value=Path("/tmp/test"))

        pipeline = TrainingPipeline(
            surrogate=surrogate,
            oracle=oracle,
            store=store,
            evaluator=evaluator,
            controller=controller,
            trainer=trainer,
            repo_fetcher=repo_fetcher,
        )

        # Mock enhanced_extract to return our model
        pipeline.enhanced_extract = AsyncMock(return_value=(mock_model, 0.8))
        pipeline._read_code_context = MagicMock(return_value="# code")
        # Mock Best-of-N to prevent surrogate calls from BestOfNGenerator
        pipeline._best_of_n = MagicMock()
        pipeline._best_of_n.generate = AsyncMock(return_value=None)

        with patch('architecture_model.training.pipeline.validate_model') as mock_validate:
            mock_validate.return_value = MagicMock(score=90)

            repo = MagicMock()
            repo.url = "https://github.com/test/test"
            repo.default_branch = "main"

            await pipeline._process_repo(repo)

        # Verify enhanced_extract was called (not surrogate.extract_model directly)
        pipeline.enhanced_extract.assert_called_once()
        # surrogate.extract_model should NOT have been called directly by _process_repo
        surrogate.extract_model.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_repo_records_loss(self):
        """_process_repo should call controller.record_loss() with LossVector."""
        from architecture_model.training.evaluator import LossVector

        mock_model = MagicMock()
        mock_model.relationships = []
        mock_model.entities = MagicMock()
        for attr in ['actors', 'capabilities', 'behaviors', 'interfaces', 'constraints', 'layers', 'components']:
            setattr(mock_model.entities, attr, [])

        surrogate = MagicMock()
        surrogate.confidence = MagicMock(return_value=0.8)
        oracle = MagicMock()
        oracle.extract_model = AsyncMock(return_value=mock_model)
        store = MagicMock()
        loss_vec = LossVector(0.7, 0.8, 90)
        evaluator = MagicMock()
        evaluator.compute_loss = MagicMock(return_value=loss_vec)
        state = MPCState()
        controller = MPCController(state)
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

        with patch('architecture_model.training.pipeline.validate_model') as mock_validate:
            mock_validate.return_value = MagicMock(score=90)
            repo = MagicMock()
            repo.url = "https://github.com/test/test"
            repo.default_branch = "main"
            await pipeline._process_repo(repo)

        # Verify record_loss was called (convergence_history gets an entry)
        assert len(state.convergence_history) == 1
        assert state.convergence_history[0] == 1.0  # non-dominated (first entry)

    @pytest.mark.asyncio
    async def test_process_repo_saves_dpo_preference_on_low_accuracy(self):
        """When structural_accuracy < 0.8, Best-of-N generates DPO preference pair."""
        from architecture_model.training.evaluator import LossVector
        from architecture_model.training.best_of_n import RankedExtraction

        mock_model = MagicMock()
        mock_model.relationships = []
        mock_model.entities = MagicMock()
        for attr in ['actors', 'capabilities', 'behaviors', 'interfaces', 'constraints', 'layers', 'components']:
            setattr(mock_model.entities, attr, [])
        mock_model.to_yaml = MagicMock(return_value="local_yaml")

        mock_oracle_model = MagicMock()
        mock_oracle_model.relationships = []
        mock_oracle_model.entities = MagicMock()
        for attr in ['actors', 'capabilities', 'behaviors', 'interfaces', 'constraints', 'layers', 'components']:
            setattr(mock_oracle_model.entities, attr, [])
        mock_oracle_model.to_yaml = MagicMock(return_value="oracle_yaml")

        surrogate = MagicMock()
        surrogate.confidence = MagicMock(return_value=0.8)
        oracle = MagicMock()
        oracle.extract_model = AsyncMock(return_value=mock_oracle_model)
        store = MagicMock()
        # Low structural_accuracy → should trigger Best-of-N DPO preference save
        loss_vec = LossVector(0.3, 0.5, 70)
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

        # Mock Best-of-N to return a valid pair
        best = RankedExtraction(
            model=MagicMock(), loss=LossVector(0.7, 0.6, 80), yaml_output="best_yaml"
        )
        worst = RankedExtraction(
            model=MagicMock(), loss=LossVector(0.2, 0.3, 55), yaml_output="worst_yaml"
        )
        pipeline._best_of_n = MagicMock()
        pipeline._best_of_n.generate = AsyncMock(return_value=(best, worst))

        with patch('architecture_model.training.pipeline.validate_model') as mock_validate:
            mock_validate.return_value = MagicMock(score=70)

            repo = MagicMock()
            repo.url = "https://github.com/test/test"
            repo.default_branch = "main"

            await pipeline._process_repo(repo)

        # Verify save_preference was called with Best-of-N outputs
        store.save_preference.assert_called_once()
        call_kwargs = store.save_preference.call_args[1]
        assert call_kwargs["chosen"] == "best_yaml"
        assert call_kwargs["rejected"] == "worst_yaml"
        assert call_kwargs["margin"] == pytest.approx(0.5)  # 0.7 - 0.2

    @pytest.mark.asyncio
    async def test_process_repo_no_dpo_when_accuracy_high(self):
        """When structural_accuracy >= 0.8, NO DPO preference pair saved."""
        from architecture_model.training.evaluator import LossVector

        mock_model = MagicMock()
        mock_model.relationships = []
        mock_model.entities = MagicMock()
        for attr in ['actors', 'capabilities', 'behaviors', 'interfaces', 'constraints', 'layers', 'components']:
            setattr(mock_model.entities, attr, [])

        surrogate = MagicMock()
        surrogate.confidence = MagicMock(return_value=0.8)
        oracle = MagicMock()
        oracle.extract_model = AsyncMock(return_value=mock_model)
        store = MagicMock()
        # High structural_accuracy → should NOT trigger Best-of-N DPO
        loss_vec = LossVector(0.8, 0.9, 95)
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
        # Mock _best_of_n to verify it's NOT called
        pipeline._best_of_n = MagicMock()

        with patch('architecture_model.training.pipeline.validate_model') as mock_validate:
            mock_validate.return_value = MagicMock(score=95)
            repo = MagicMock()
            repo.url = "https://github.com/test/test"
            repo.default_branch = "main"
            await pipeline._process_repo(repo)

        # save_preference should NOT have been called
        store.save_preference.assert_not_called()
        # Best-of-N should NOT have been called
        pipeline._best_of_n.generate.assert_not_called()


# ---------------------------------------------------------------------------
# Round-trip evaluator integration tests
# ---------------------------------------------------------------------------


class TestRoundTripIntegration:
    """Tests for round-trip evaluator integration in pipeline."""

    @pytest.mark.asyncio
    async def test_round_trip_evaluator_called_when_configured(self):
        """RoundTripEvaluator.evaluate() is called during _process_repo."""
        from architecture_model.training.autoencoder import RoundTripScore

        mock_model = _make_architecture_model()
        mock_rt = AsyncMock()
        mock_rt.evaluate = AsyncMock(return_value=RoundTripScore(
            class_overlap=0.7,
            method_overlap=0.5,
            function_overlap=0.6,
            import_similarity=0.4,
            module_ratio=0.8,
            semantic_class_match=0.6,
            intent_coverage=0.5,
            overall=0.58,
        ))

        surrogate = MagicMock()
        oracle = MagicMock()
        oracle.extract_model = AsyncMock(return_value=None)
        store = MagicMock()
        store.save = MagicMock(return_value=1)
        store.count_preferences = MagicMock(return_value=0)
        evaluator = MagicMock()
        controller = MagicMock()
        controller.state = MPCState()
        controller.should_query_oracle = MagicMock(return_value=False)
        trainer = MagicMock()
        repo_fetcher = MagicMock()
        repo_fetcher.clone = MagicMock(return_value=Path("/tmp/test"))

        pipeline = TrainingPipeline(
            surrogate=surrogate, oracle=oracle, store=store,
            evaluator=evaluator, controller=controller,
            trainer=trainer, repo_fetcher=repo_fetcher,
            round_trip_evaluator=mock_rt,
        )
        pipeline.enhanced_extract = AsyncMock(return_value=(mock_model, 0.8))
        pipeline._read_code_context = MagicMock(return_value="class Foo:\n    pass")

        with patch('architecture_model.training.pipeline.validate_model') as mock_validate:
            mock_validate.return_value = MagicMock(score=90)
            repo = MagicMock()
            repo.url = "https://github.com/test/test"
            repo.default_branch = "main"
            await pipeline._process_repo(repo)

        # Round-trip evaluator was called with the code and model
        mock_rt.evaluate.assert_called_once_with(
            original_code="class Foo:\n    pass",
            model=mock_model,
        )

    @pytest.mark.asyncio
    async def test_round_trip_modulates_confidence(self):
        """Low round-trip score reduces effective confidence."""
        from architecture_model.training.autoencoder import RoundTripScore

        mock_model = _make_architecture_model()
        # Low round-trip score (0.3 overall)
        mock_rt = AsyncMock()
        mock_rt.evaluate = AsyncMock(return_value=RoundTripScore(
            class_overlap=0.2,
            method_overlap=0.3,
            function_overlap=0.1,
            import_similarity=0.3,
            module_ratio=0.5,
            semantic_class_match=0.2,
            intent_coverage=0.3,
            overall=0.3,
        ))

        store = MagicMock()
        store.save = MagicMock(return_value=1)
        store.count_preferences = MagicMock(return_value=0)
        controller = MagicMock()
        controller.state = MPCState()
        controller.should_query_oracle = MagicMock(return_value=False)
        repo_fetcher = MagicMock()
        repo_fetcher.clone = MagicMock(return_value=Path("/tmp/test"))

        pipeline = TrainingPipeline(
            surrogate=MagicMock(), oracle=MagicMock(), store=store,
            evaluator=MagicMock(), controller=controller,
            trainer=MagicMock(), repo_fetcher=repo_fetcher,
            round_trip_evaluator=mock_rt,
        )
        pipeline.enhanced_extract = AsyncMock(return_value=(mock_model, 0.9))
        pipeline._read_code_context = MagicMock(return_value="class Foo:\n    pass")

        with patch('architecture_model.training.pipeline.validate_model') as mock_validate:
            mock_validate.return_value = MagicMock(score=90)
            repo = MagicMock()
            repo.url = "https://github.com/test/test"
            repo.default_branch = "main"
            await pipeline._process_repo(repo)

        # Confidence passed to should_query_oracle:
        # Original confidence = 0.9, round_trip = 0.3
        # Modulated = 0.6 * 0.9 + 0.4 * 0.3 = 0.54 + 0.12 = 0.66
        call_kwargs = controller.should_query_oracle.call_args[1]
        assert abs(call_kwargs["confidence"] - 0.66) < 0.01

    @pytest.mark.asyncio
    async def test_round_trip_score_stored_in_metadata(self):
        """Round-trip score is persisted in training example metadata."""
        from architecture_model.training.autoencoder import RoundTripScore

        mock_model = _make_architecture_model()
        mock_rt = AsyncMock()
        mock_rt.evaluate = AsyncMock(return_value=RoundTripScore(
            class_overlap=0.8,
            method_overlap=0.6,
            function_overlap=0.7,
            import_similarity=0.5,
            module_ratio=0.9,
            semantic_class_match=0.7,
            intent_coverage=0.6,
            overall=0.69,
        ))

        store = MagicMock()
        store.save = MagicMock(return_value=1)
        store.count_preferences = MagicMock(return_value=0)
        controller = MagicMock()
        controller.state = MPCState()
        controller.should_query_oracle = MagicMock(return_value=False)
        repo_fetcher = MagicMock()
        repo_fetcher.clone = MagicMock(return_value=Path("/tmp/test"))

        pipeline = TrainingPipeline(
            surrogate=MagicMock(), oracle=MagicMock(), store=store,
            evaluator=MagicMock(), controller=controller,
            trainer=MagicMock(), repo_fetcher=repo_fetcher,
            round_trip_evaluator=mock_rt,
        )
        pipeline.enhanced_extract = AsyncMock(return_value=(mock_model, 0.8))
        pipeline._read_code_context = MagicMock(return_value="class Foo:\n    pass")

        with patch('architecture_model.training.pipeline.validate_model') as mock_validate:
            mock_validate.return_value = MagicMock(score=90)
            repo = MagicMock()
            repo.url = "https://github.com/test/test"
            repo.default_branch = "main"
            await pipeline._process_repo(repo)

        # Check metadata in saved example
        saved_example = store.save.call_args[0][0]
        assert "round_trip" in saved_example.metadata
        assert saved_example.metadata["round_trip"]["overall"] == 0.69
        assert saved_example.metadata["round_trip"]["class_overlap"] == 0.8

    @pytest.mark.asyncio
    async def test_no_round_trip_when_evaluator_not_configured(self):
        """Without round_trip_evaluator, pipeline works normally."""
        mock_model = _make_architecture_model()

        store = MagicMock()
        store.save = MagicMock(return_value=1)
        store.count_preferences = MagicMock(return_value=0)
        controller = MagicMock()
        controller.state = MPCState()
        controller.should_query_oracle = MagicMock(return_value=False)
        repo_fetcher = MagicMock()
        repo_fetcher.clone = MagicMock(return_value=Path("/tmp/test"))

        pipeline = TrainingPipeline(
            surrogate=MagicMock(), oracle=MagicMock(), store=store,
            evaluator=MagicMock(), controller=controller,
            trainer=MagicMock(), repo_fetcher=repo_fetcher,
            # No round_trip_evaluator
        )
        pipeline.enhanced_extract = AsyncMock(return_value=(mock_model, 0.8))
        pipeline._read_code_context = MagicMock(return_value="class Foo:\n    pass")

        with patch('architecture_model.training.pipeline.validate_model') as mock_validate:
            mock_validate.return_value = MagicMock(score=90)
            repo = MagicMock()
            repo.url = "https://github.com/test/test"
            repo.default_branch = "main"
            await pipeline._process_repo(repo)

        # Confidence should not be modulated (original 0.8 passed through)
        call_kwargs = controller.should_query_oracle.call_args[1]
        assert call_kwargs["confidence"] == 0.8

        # Metadata should be empty
        saved_example = store.save.call_args[0][0]
        assert saved_example.metadata == {}

    @pytest.mark.asyncio
    async def test_round_trip_failure_does_not_crash_pipeline(self):
        """If round-trip evaluator throws, pipeline continues gracefully."""
        mock_model = _make_architecture_model()
        mock_rt = AsyncMock()
        mock_rt.evaluate = AsyncMock(side_effect=RuntimeError("Ollama down"))

        store = MagicMock()
        store.save = MagicMock(return_value=1)
        store.count_preferences = MagicMock(return_value=0)
        controller = MagicMock()
        controller.state = MPCState()
        controller.should_query_oracle = MagicMock(return_value=False)
        repo_fetcher = MagicMock()
        repo_fetcher.clone = MagicMock(return_value=Path("/tmp/test"))

        pipeline = TrainingPipeline(
            surrogate=MagicMock(), oracle=MagicMock(), store=store,
            evaluator=MagicMock(), controller=controller,
            trainer=MagicMock(), repo_fetcher=repo_fetcher,
            round_trip_evaluator=mock_rt,
        )
        pipeline.enhanced_extract = AsyncMock(return_value=(mock_model, 0.8))
        pipeline._read_code_context = MagicMock(return_value="class Foo:\n    pass")

        with patch('architecture_model.training.pipeline.validate_model') as mock_validate:
            mock_validate.return_value = MagicMock(score=90)
            repo = MagicMock()
            repo.url = "https://github.com/test/test"
            repo.default_branch = "main"
            # Should NOT raise
            await pipeline._process_repo(repo)

        # Pipeline continued — example was still saved
        store.save.assert_called_once()
        # Confidence unchanged (exception caught)
        call_kwargs = controller.should_query_oracle.call_args[1]
        assert call_kwargs["confidence"] == 0.8
