"""End-to-end integration test for surrogate training plumbing.

Exercises the full training pipeline with mocked LLM calls but real
DatasetStore, Evaluator, Controller, and BestOfNGenerator logic.
Proves the plumbing fixes from Tasks 1-7 work end-to-end.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    Entities,
    Layer,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
    Strength,
)
from architecture_model.training.best_of_n import BestOfNGenerator, RankedExtraction
from architecture_model.training.controller import MPCController, MPCState
from architecture_model.training.dataset import DatasetStore
from architecture_model.training.evaluator import Evaluator, LossVector
from architecture_model.training.pipeline import TrainingPipeline
from architecture_model.training.repo_fetcher import RepoFetcher, RepoInfo


# ---------------------------------------------------------------------------
# Model fixtures
# ---------------------------------------------------------------------------


def _make_surrogate_model() -> ArchitectureModel:
    """Surrogate's extraction — fewer entities, some missing."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.0", project="test-project"),
        entities=Entities(
            layers=[
                Layer(id="layer-core", name="Core Layer", status=Status.ACTIVE),
                Layer(id="layer-api", name="API Layer", status=Status.ACTIVE),
            ],
            components=[
                Component(
                    id="comp-auth",
                    name="Auth Service",
                    status=Status.ACTIVE,
                    layer="layer-core",
                ),
                Component(
                    id="comp-users",
                    name="User Service",
                    status=Status.ACTIVE,
                    layer="layer-core",
                ),
                Component(
                    id="comp-api",
                    name="API Gateway",
                    status=Status.ACTIVE,
                    layer="layer-api",
                ),
            ],
        ),
        relationships=[
            Relationship(
                type=RelationType.CONTAINS, from_id="layer-core", to_id="comp-auth"
            ),
            Relationship(
                type=RelationType.CONTAINS, from_id="layer-core", to_id="comp-users"
            ),
            Relationship(
                type=RelationType.DEPENDS_ON, from_id="comp-api", to_id="comp-auth"
            ),
        ],
    )


def _make_oracle_model() -> ArchitectureModel:
    """Oracle's ground truth — more complete, with additional entities."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.0", project="test-project"),
        entities=Entities(
            layers=[
                Layer(id="layer-core", name="Core Layer", status=Status.ACTIVE),
                Layer(id="layer-api", name="API Layer", status=Status.ACTIVE),
                Layer(id="layer-data", name="Data Layer", status=Status.ACTIVE),
            ],
            components=[
                Component(
                    id="comp-auth",
                    name="Auth Service",
                    status=Status.ACTIVE,
                    layer="layer-core",
                ),
                Component(
                    id="comp-users",
                    name="User Service",
                    status=Status.ACTIVE,
                    layer="layer-core",
                ),
                Component(
                    id="comp-api",
                    name="API Gateway",
                    status=Status.ACTIVE,
                    layer="layer-api",
                ),
                Component(
                    id="comp-db",
                    name="Database",
                    status=Status.ACTIVE,
                    layer="layer-data",
                ),
            ],
        ),
        relationships=[
            Relationship(
                type=RelationType.CONTAINS, from_id="layer-core", to_id="comp-auth"
            ),
            Relationship(
                type=RelationType.CONTAINS, from_id="layer-core", to_id="comp-users"
            ),
            Relationship(
                type=RelationType.CONTAINS, from_id="layer-api", to_id="comp-api"
            ),
            Relationship(
                type=RelationType.CONTAINS, from_id="layer-data", to_id="comp-db"
            ),
            Relationship(
                type=RelationType.DEPENDS_ON, from_id="comp-api", to_id="comp-auth"
            ),
            Relationship(
                type=RelationType.DEPENDS_ON,
                from_id="comp-users",
                to_id="comp-db",
            ),
        ],
    )


def _make_repo_info() -> RepoInfo:
    return RepoInfo(
        url="https://github.com/test/repo",
        full_name="test/repo",
        stars=100,
        language="python",
        default_branch="main",
        has_ci=True,
        size_kb=2000,
    )


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestPlumbingE2E:
    """Integration tests verifying all plumbing fixes work together."""

    @pytest.fixture
    def pipeline_components(self, tmp_path):
        """Set up pipeline with mocked LLM but real logic components."""
        # Real components
        db_path = str(tmp_path / "test_training.db")
        store = DatasetStore(db_path)
        evaluator = Evaluator()
        state = MPCState(oracle_budget_remaining=100)
        controller = MPCController(state)

        # Mocked LLM components
        surrogate = MagicMock()
        surrogate.extract_model = AsyncMock(return_value=_make_surrogate_model())
        surrogate.confidence = MagicMock(return_value=0.4)  # Low → triggers oracle

        oracle = MagicMock()
        oracle.extract_model = AsyncMock(return_value=_make_oracle_model())

        trainer = MagicMock()
        trainer.needs_retrain = False

        repo_fetcher = MagicMock()
        repo_fetcher.discover = AsyncMock(return_value=[_make_repo_info()])
        repo_fetcher.clone = MagicMock(return_value=tmp_path / "repo")

        # Create fake repo directory with a Python file
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "main.py").write_text("class App:\n    pass\n")

        return {
            "store": store,
            "evaluator": evaluator,
            "controller": controller,
            "surrogate": surrogate,
            "oracle": oracle,
            "trainer": trainer,
            "repo_fetcher": repo_fetcher,
            "state": state,
            "tmp_path": tmp_path,
        }

    def _build_pipeline(self, components):
        """Build a TrainingPipeline and patch enhanced_extract."""
        pipeline = TrainingPipeline(
            surrogate=components["surrogate"],
            oracle=components["oracle"],
            store=components["store"],
            evaluator=components["evaluator"],
            controller=components["controller"],
            trainer=components["trainer"],
            repo_fetcher=components["repo_fetcher"],
            oracle_learning_enabled=False,
        )
        # Patch enhanced_extract to return surrogate model + low confidence
        # This bypasses ContextBuilder/MultiPass/Refiner filesystem dependencies
        pipeline.enhanced_extract = AsyncMock(
            return_value=(_make_surrogate_model(), 0.4)
        )
        return pipeline

    async def _run_one_repo(self, pipeline):
        """Run a single iteration processing one repo."""
        await pipeline.run_iteration(n_repos=1)

    @pytest.mark.asyncio
    async def test_full_pipeline_stores_valid_yaml(self, pipeline_components):
        """After processing a repo, stored oracle/local output is valid YAML."""
        pipeline = self._build_pipeline(pipeline_components)
        await self._run_one_repo(pipeline)

        store = pipeline_components["store"]
        examples = store.query(has_oracle=True)
        assert len(examples) >= 1, "Expected at least one oracle-validated example"

        for ex in examples:
            # oracle_output must be valid YAML (not Python repr)
            assert ex.oracle_output is not None
            parsed_oracle = yaml.safe_load(ex.oracle_output)
            assert isinstance(parsed_oracle, dict), (
                f"oracle_output should parse to dict, got {type(parsed_oracle)}"
            )
            assert "meta" in parsed_oracle or "entities" in parsed_oracle

            # local_output must be valid YAML (not Python repr)
            parsed_local = yaml.safe_load(ex.local_output)
            assert isinstance(parsed_local, dict), (
                f"local_output should parse to dict, got {type(parsed_local)}"
            )
            assert "meta" in parsed_local or "entities" in parsed_local

    @pytest.mark.asyncio
    async def test_export_for_training_returns_data(self, pipeline_components):
        """export_for_training() returns non-empty after pipeline processes a repo."""
        pipeline = self._build_pipeline(pipeline_components)
        await self._run_one_repo(pipeline)

        store = pipeline_components["store"]
        exported = store.export_for_training()
        assert len(exported) > 0, "export_for_training() should return non-empty list"
        # Each entry has instruction/input/output fields
        for entry in exported:
            assert "instruction" in entry
            assert "input" in entry
            assert "output" in entry
            # output should be valid YAML
            parsed = yaml.safe_load(entry["output"])
            assert isinstance(parsed, dict)

    @pytest.mark.asyncio
    async def test_budget_decremented_after_oracle_query(self, pipeline_components):
        """oracle_budget_remaining decreases after oracle query."""
        initial_budget = pipeline_components["state"].oracle_budget_remaining
        assert initial_budget == 100

        pipeline = self._build_pipeline(pipeline_components)
        await self._run_one_repo(pipeline)

        final_budget = pipeline_components["state"].oracle_budget_remaining
        assert final_budget < initial_budget, (
            f"Budget should decrease: was {initial_budget}, now {final_budget}"
        )

    @pytest.mark.asyncio
    async def test_convergence_history_only_pareto_values(self, pipeline_components):
        """convergence_history only contains 0.0 or 1.0 (Pareto dominance)."""
        pipeline = self._build_pipeline(pipeline_components)
        await self._run_one_repo(pipeline)

        history = pipeline_components["state"].convergence_history
        assert len(history) > 0, "convergence_history should have entries"
        for value in history:
            assert value in (0.0, 1.0), (
                f"convergence_history should only have 0.0 or 1.0, got {value}"
            )

    @pytest.mark.asyncio
    async def test_best_of_n_generates_preferences(self, pipeline_components):
        """Best-of-N generates DPO preference pairs when accuracy is low."""
        # The surrogate model is intentionally less complete than oracle,
        # so structural_accuracy should be < 0.8, triggering Best-of-N.
        # We need to mock the BestOfNGenerator.generate to return a valid pair
        # because the real one calls surrogate.extract_model which returns our
        # fixed mock (no variation → margin < 0.05 → returns None).
        pipeline = self._build_pipeline(pipeline_components)

        # Create a mock best_of_n that returns a valid preference pair
        best = RankedExtraction(
            model=_make_oracle_model(),
            loss=LossVector(0.9, 0.85, 95.0),
            yaml_output=_make_oracle_model().to_yaml(),
        )
        worst = RankedExtraction(
            model=_make_surrogate_model(),
            loss=LossVector(0.3, 0.4, 60.0),
            yaml_output=_make_surrogate_model().to_yaml(),
        )
        pipeline._best_of_n = MagicMock()
        pipeline._best_of_n.generate = AsyncMock(return_value=(best, worst))

        await self._run_one_repo(pipeline)

        store = pipeline_components["store"]
        prefs = store.export_preferences()
        assert len(prefs) > 0, "export_preferences() should return entries"
        for pref in prefs:
            assert "prompt" in pref
            assert "chosen" in pref
            assert "rejected" in pref
            # chosen and rejected should be valid YAML
            assert isinstance(yaml.safe_load(pref["chosen"]), dict)
            assert isinstance(yaml.safe_load(pref["rejected"]), dict)

    @pytest.mark.asyncio
    async def test_loss_vector_has_enriched_values(self, pipeline_components):
        """Stored loss_vector reflects enriched Pareto objectives."""
        pipeline = self._build_pipeline(pipeline_components)
        await self._run_one_repo(pipeline)

        store = pipeline_components["store"]
        examples = store.query(has_oracle=True)
        assert len(examples) >= 1

        for ex in examples:
            assert ex.loss_vector is not None, "loss_vector should be stored"
            assert "structural_accuracy" in ex.loss_vector
            assert "completeness" in ex.loss_vector
            assert "validator_score" in ex.loss_vector
            # Values should be reasonable (0-1 for accuracy/completeness, 0-100 for validator)
            assert 0.0 <= ex.loss_vector["structural_accuracy"] <= 1.0
            assert 0.0 <= ex.loss_vector["completeness"] <= 1.0
            assert 0.0 <= ex.loss_vector["validator_score"] <= 100.0

    @pytest.mark.asyncio
    async def test_to_yaml_produces_parseable_output(self, pipeline_components):
        """Verify to_yaml() on real ArchitectureModel produces valid YAML (Task 1)."""
        surrogate_model = _make_surrogate_model()
        oracle_model = _make_oracle_model()

        # Both should produce valid YAML with proper structure
        for label, model in [("surrogate", surrogate_model), ("oracle", oracle_model)]:
            yaml_str = model.to_yaml()
            parsed = yaml.safe_load(yaml_str)
            assert isinstance(parsed, dict), f"{label}.to_yaml() didn't produce a dict"
            assert "meta" in parsed, f"{label} YAML missing 'meta'"
            assert "entities" in parsed, f"{label} YAML missing 'entities'"
            assert "relationships" in parsed, f"{label} YAML missing 'relationships'"
            # Relationships should be a list of dicts, not Python repr
            for rel in parsed["relationships"]:
                assert isinstance(rel, dict), (
                    f"{label} relationship is {type(rel)}, not dict"
                )
                assert "type" in rel
                assert "from" in rel
                assert "to" in rel

    @pytest.mark.asyncio
    async def test_evaluator_computes_real_loss(self, pipeline_components):
        """Evaluator produces meaningful loss between surrogate and oracle models."""
        evaluator = pipeline_components["evaluator"]
        local_model = _make_surrogate_model()
        oracle_model = _make_oracle_model()

        loss = evaluator.compute_loss(local_model, oracle_model)

        # Surrogate is incomplete (missing layer-data, comp-db, some rels)
        # so accuracy and completeness should be < 1.0 but > 0
        assert 0.0 < loss.structural_accuracy < 1.0
        assert 0.0 < loss.completeness < 1.0
        assert loss.validator_score > 0.0
