"""Tests for self-reflective prompt evolution."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from architecture_model.training.oracle_evolution import PromptEvolver
from architecture_model.training.oracle_performance import OracleResult


class TestPromptEvolver:
    def test_should_evolve_after_batch_size(self):
        store = MagicMock()
        store.count_since_iteration = MagicMock(return_value=10)
        store.get_average_coverage = MagicMock(return_value=0.8)
        evolver = PromptEvolver(store, batch_size=10)
        assert evolver.should_evolve(current_iteration=5) is True

    def test_should_evolve_on_quality_drop(self):
        store = MagicMock()
        store.count_since_iteration = MagicMock(return_value=3)  # under batch size
        store.get_average_coverage = MagicMock(return_value=0.5)  # but quality dropped
        evolver = PromptEvolver(store, batch_size=10, quality_threshold=0.7)
        assert evolver.should_evolve(current_iteration=5) is True

    def test_should_not_evolve_when_fine(self):
        store = MagicMock()
        store.count_since_iteration = MagicMock(return_value=3)
        store.get_average_coverage = MagicMock(return_value=0.85)
        evolver = PromptEvolver(store, batch_size=10, quality_threshold=0.7)
        assert evolver.should_evolve(current_iteration=5) is False

    def test_get_current_prompt_returns_base(self):
        store = MagicMock()
        evolver = PromptEvolver(store)
        prompt = evolver.get_current_prompt()
        assert "architecture extraction engine" in prompt.lower() or "UAM" in prompt

    @pytest.mark.asyncio
    async def test_evolve_updates_prompt(self):
        store = MagicMock()
        store.get_poor_extractions = MagicMock(return_value=[
            OracleResult("repo-a", "v1", 0.3, 60.0, 1,
                        uncovered_modules='["x.py"]', uncovered_interfaces='[]'),
        ])

        oracle = MagicMock()
        oracle._completion = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content="""
analysis:
  - pattern: "missed utility modules"
    reason: "prompt does not emphasize small helper modules"
prompt_additions:
  - "Include ALL modules with >10 LOC as components, even utilities"
prompt_removals: []
"""))],
            usage=MagicMock(total_tokens=100),
        ))

        evolver = PromptEvolver(store)
        old_prompt = evolver.get_current_prompt()
        await evolver.evolve(oracle)
        new_prompt = evolver.get_current_prompt()

        # New prompt should contain the addition
        assert "utility" in new_prompt.lower() or "modules" in new_prompt.lower()
        assert new_prompt != old_prompt
