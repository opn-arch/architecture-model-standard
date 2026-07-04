"""Tests for oracle self-critique refinement loop."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from architecture_model.training.oracle_critique import SelfCritiqueRefiner
from architecture_model.training.oracle_coverage import CoverageResult
from architecture_model.core.types import (
    ArchitectureModel, Entities, Component, Layer, Status, ModelMeta,
)


def _make_model(n_components=1):
    meta = ModelMeta(schema_version="1.0", project="test")
    return ArchitectureModel(
        meta=meta,
        entities=Entities(
            actors=[], behaviors=[], interfaces=[], constraints=[],
            capabilities=[], layers=[Layer(id="L1", name="core", status=Status.ACTIVE)],
            components=[
                Component(id=f"C{i}", name=f"Component {i}", layer="L1", status=Status.ACTIVE)
                for i in range(n_components)
            ],
        ),
        relationships=[],
    )


class TestSelfCritiqueRefiner:
    @pytest.mark.asyncio
    async def test_returns_immediately_if_coverage_high(self):
        oracle = MagicMock()
        coverage_computer = MagicMock()
        coverage_computer.compute = MagicMock(return_value=CoverageResult(
            module_coverage=0.9, interface_coverage=0.9, block_coverage=1.0,
            overall=0.9, uncovered_modules=[], uncovered_interfaces=[],
        ))

        refiner = SelfCritiqueRefiner(oracle, coverage_computer, threshold=0.85)
        model = _make_model(3)
        result = await refiner.refine(model, manifest={}, context="# code")
        # Should not call oracle again (already good)
        assert result is model
        oracle.extract_model.assert_not_called()

    @pytest.mark.asyncio
    async def test_retries_on_low_coverage(self):
        improved_model = _make_model(5)

        oracle = MagicMock()
        oracle.extract_model = AsyncMock(return_value=improved_model)

        coverage_computer = MagicMock()
        # First call: low coverage, second: high
        coverage_computer.compute = MagicMock(side_effect=[
            CoverageResult(0.5, 0.3, 0.5, 0.45,
                          uncovered_modules=["src/missed.py"],
                          uncovered_interfaces=[("a.py", "b.py")]),
            CoverageResult(0.9, 0.9, 1.0, 0.92,
                          uncovered_modules=[], uncovered_interfaces=[]),
        ])

        refiner = SelfCritiqueRefiner(oracle, coverage_computer, threshold=0.85, max_rounds=3)
        model = _make_model(1)
        result = await refiner.refine(model, manifest={}, context="# code")

        assert result is improved_model
        oracle.extract_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_rounds_respected(self):
        oracle = MagicMock()
        oracle.extract_model = AsyncMock(return_value=_make_model(2))

        coverage_computer = MagicMock()
        # Always low coverage
        coverage_computer.compute = MagicMock(return_value=CoverageResult(
            0.3, 0.2, 0.0, 0.25,
            uncovered_modules=["x.py"], uncovered_interfaces=[],
        ))

        refiner = SelfCritiqueRefiner(oracle, coverage_computer, threshold=0.85, max_rounds=2)
        model = _make_model(1)
        result = await refiner.refine(model, manifest={}, context="# code")

        # Should have called extract_model exactly max_rounds times
        assert oracle.extract_model.call_count == 2
