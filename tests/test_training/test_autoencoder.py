"""Tests for RoundTripEvaluator (autoencoder loop)."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    Entities,
    Layer,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
)
from architecture_model.training.autoencoder import RoundTripEvaluator, RoundTripScore
from architecture_model.training.code_structure import (
    ClassInfo,
    FunctionInfo,
    ImportEdge,
    StructuralGraph,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_model() -> ArchitectureModel:
    """Build a minimal ArchitectureModel for testing."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.0", project="test"),
        entities=Entities(
            components=[
                Component(id="comp-1", name="AuthService", status=Status.ACTIVE, layer="services"),
                Component(id="comp-2", name="UserRepo", status=Status.ACTIVE, layer="data"),
            ],
            layers=[
                Layer(id="layer-1", name="services", status=Status.ACTIVE),
                Layer(id="layer-2", name="data", status=Status.ACTIVE),
            ],
        ),
        relationships=[
            Relationship(type=RelationType.DEPENDS_ON, from_id="comp-1", to_id="comp-2"),
        ],
    )


ORIGINAL_CODE_HIGH_OVERLAP = """\
# src/services/auth.py
import os
from typing import Optional

class AuthService:
    \"\"\"Handles authentication.\"\"\"

    def __init__(self, repo):
        self.repo = repo

    def login(self, user: str, password: str) -> bool:
        pass

    def logout(self) -> None:
        pass

# src/data/user_repo.py
from typing import List

class UserRepo:
    \"\"\"Data access for users.\"\"\"

    def __init__(self, db):
        self.db = db

    def find_by_id(self, user_id: str) -> Optional[dict]:
        pass
"""

# Code that the mock surrogate returns (high overlap with original)
GENERATED_CODE_HIGH_OVERLAP = """\
import os
from typing import Optional, List

class AuthService:
    \"\"\"Authentication service component.\"\"\"

    def __init__(self, repo) -> None:
        pass

    def login(self, user: str, password: str) -> bool:
        pass

    def logout(self) -> None:
        pass

class UserRepo:
    \"\"\"User data repository.\"\"\"

    def __init__(self, db) -> None:
        pass

    def find_by_id(self, user_id: str) -> Optional[dict]:
        pass
"""

GENERATED_CODE_NO_OVERLAP = """\
import redis

class CacheManager:
    \"\"\"Manages caching.\"\"\"

    def get(self, key: str) -> str:
        pass

    def set(self, key: str, value: str) -> None:
        pass

class QueueProcessor:
    \"\"\"Processes message queues.\"\"\"

    def enqueue(self, msg: str) -> None:
        pass
"""

GENERATED_CODE_PARTIAL_OVERLAP = """\
import os
from typing import Optional

class AuthService:
    \"\"\"Authentication handler.\"\"\"

    def __init__(self, repo) -> None:
        pass

    def login(self, user: str, password: str) -> bool:
        pass

class NotificationService:
    \"\"\"Sends notifications.\"\"\"

    def send(self, to: str, message: str) -> None:
        pass
"""


def _make_surrogate(generated_code: str) -> MagicMock:
    """Create a mock Surrogate that returns given code from generate_code()."""
    surrogate = MagicMock()
    surrogate.generate_code = AsyncMock(return_value=generated_code)
    return surrogate


# ---------------------------------------------------------------------------
# Tests: Full round-trip evaluation
# ---------------------------------------------------------------------------


class TestRoundTripEvaluatorFullCycle:
    """Test evaluate() end-to-end with mocked surrogate."""

    @pytest.mark.asyncio
    async def test_evaluate_high_overlap(self):
        """Original and generated have same classes/functions → high score."""
        surrogate = _make_surrogate(GENERATED_CODE_HIGH_OVERLAP)
        evaluator = RoundTripEvaluator(surrogate=surrogate)
        model = _make_model()

        score = await evaluator.evaluate(ORIGINAL_CODE_HIGH_OVERLAP, model)

        assert score.class_overlap == 1.0  # Both have AuthService, UserRepo
        assert score.method_overlap > 0.5  # Most methods match
        assert score.overall > 0.5

    @pytest.mark.asyncio
    async def test_evaluate_no_overlap(self):
        """Completely different structures → low score."""
        surrogate = _make_surrogate(GENERATED_CODE_NO_OVERLAP)
        evaluator = RoundTripEvaluator(surrogate=surrogate)
        model = _make_model()

        score = await evaluator.evaluate(ORIGINAL_CODE_HIGH_OVERLAP, model)

        assert score.class_overlap == 0.0  # No common classes
        assert score.method_overlap == 0.0  # No common methods
        assert score.overall < 0.3

    @pytest.mark.asyncio
    async def test_evaluate_partial_overlap(self):
        """Some classes match, some don't → medium score."""
        surrogate = _make_surrogate(GENERATED_CODE_PARTIAL_OVERLAP)
        evaluator = RoundTripEvaluator(surrogate=surrogate)
        model = _make_model()

        score = await evaluator.evaluate(ORIGINAL_CODE_HIGH_OVERLAP, model)

        # AuthService matches, UserRepo/NotificationService don't
        assert 0.0 < score.class_overlap < 1.0
        assert 0.0 < score.overall < 0.8


# ---------------------------------------------------------------------------
# Tests: Jaccard similarity
# ---------------------------------------------------------------------------


class TestJaccard:
    """Test _jaccard static method."""

    def test_jaccard_identical_sets(self):
        result = RoundTripEvaluator._jaccard({"A", "B", "C"}, {"A", "B", "C"})
        assert result == 1.0

    def test_jaccard_disjoint_sets(self):
        result = RoundTripEvaluator._jaccard({"A", "B"}, {"C", "D"})
        assert result == 0.0

    def test_jaccard_partial_overlap(self):
        # {a, b, c} & {b, c, d} = {b, c}, union = {a, b, c, d}
        result = RoundTripEvaluator._jaccard({"A", "B", "C"}, {"B", "C", "D"})
        assert result == pytest.approx(2 / 4)

    def test_jaccard_empty_both(self):
        result = RoundTripEvaluator._jaccard(set(), set())
        assert result == 1.0

    def test_jaccard_empty_one(self):
        result = RoundTripEvaluator._jaccard({"A"}, set())
        assert result == 0.0

    def test_jaccard_case_insensitive(self):
        result = RoundTripEvaluator._jaccard({"AuthService"}, {"authservice"})
        assert result == 1.0


# ---------------------------------------------------------------------------
# Tests: Module ratio
# ---------------------------------------------------------------------------


class TestModuleRatio:
    """Test _module_ratio static method."""

    def test_module_ratio_same_count(self):
        g1 = StructuralGraph(modules=["a", "b", "c"])
        g2 = StructuralGraph(modules=["x", "y", "z"])
        assert RoundTripEvaluator._module_ratio(g1, g2) == 1.0

    def test_module_ratio_different_count(self):
        g1 = StructuralGraph(modules=["a", "b"])
        g2 = StructuralGraph(modules=["x", "y", "z", "w"])
        # min(2, 4) / max(2, 4) = 0.5
        assert RoundTripEvaluator._module_ratio(g1, g2) == 0.5

    def test_module_ratio_empty_uses_floor_of_one(self):
        g1 = StructuralGraph(modules=[])
        g2 = StructuralGraph(modules=["x", "y"])
        # max(0, 1) = 1 for empty, so min(1, 2) / max(1, 2) = 0.5
        assert RoundTripEvaluator._module_ratio(g1, g2) == 0.5


# ---------------------------------------------------------------------------
# Tests: Import overlap
# ---------------------------------------------------------------------------


class TestImportOverlap:
    """Test _import_overlap static method."""

    def test_import_overlap_full_match(self):
        g1 = StructuralGraph(imports=[
            ImportEdge(from_module="app", to_module="os"),
            ImportEdge(from_module="app", to_module="sys"),
        ])
        g2 = StructuralGraph(imports=[
            ImportEdge(from_module="gen", to_module="os"),
            ImportEdge(from_module="gen", to_module="sys"),
        ])
        assert RoundTripEvaluator._import_overlap(g1, g2) == 1.0

    def test_import_overlap_partial_match(self):
        # Original imports os, sys, typing; generated only has os
        g1 = StructuralGraph(imports=[
            ImportEdge(from_module="app", to_module="os"),
            ImportEdge(from_module="app", to_module="sys"),
            ImportEdge(from_module="app", to_module="typing"),
        ])
        g2 = StructuralGraph(imports=[
            ImportEdge(from_module="gen", to_module="os"),
        ])
        assert RoundTripEvaluator._import_overlap(g1, g2) == pytest.approx(1 / 3)

    def test_import_overlap_suffix_match(self):
        """Partial module name matching: 'auth.service' matches 'service'."""
        g1 = StructuralGraph(imports=[
            ImportEdge(from_module="app", to_module="auth.service"),
        ])
        g2 = StructuralGraph(imports=[
            ImportEdge(from_module="gen", to_module="service"),
        ])
        assert RoundTripEvaluator._import_overlap(g1, g2) == 1.0

    def test_import_overlap_empty_original(self):
        g1 = StructuralGraph(imports=[])
        g2 = StructuralGraph(imports=[
            ImportEdge(from_module="gen", to_module="os"),
        ])
        assert RoundTripEvaluator._import_overlap(g1, g2) == 1.0

    def test_import_overlap_empty_generated(self):
        g1 = StructuralGraph(imports=[
            ImportEdge(from_module="app", to_module="os"),
        ])
        g2 = StructuralGraph(imports=[])
        assert RoundTripEvaluator._import_overlap(g1, g2) == 0.0


# ---------------------------------------------------------------------------
# Tests: Semantic matcher integration
# ---------------------------------------------------------------------------


class TestSemanticMatcherIntegration:
    """Test that semantic matcher is called and scores are used."""

    @pytest.mark.asyncio
    async def test_semantic_matcher_integrated(self):
        """Mock semantic matcher, verify it's called and scores used."""

        @dataclass
        class FakeMatch:
            original: str
            generated: str
            score: float

        mock_matcher = MagicMock()
        mock_matcher.match_names = AsyncMock(return_value=[
            FakeMatch(original="AuthService", generated="AuthService", score=0.95),
            FakeMatch(original="UserRepo", generated="UserRepository", score=0.85),
        ])
        mock_matcher.intent_coverage = AsyncMock(return_value=0.8)

        surrogate = _make_surrogate(GENERATED_CODE_HIGH_OVERLAP)
        evaluator = RoundTripEvaluator(surrogate=surrogate, semantic_matcher=mock_matcher)
        model = _make_model()

        score = await evaluator.evaluate(ORIGINAL_CODE_HIGH_OVERLAP, model)

        # Semantic matcher was called
        mock_matcher.match_names.assert_called_once()
        mock_matcher.intent_coverage.assert_called_once()

        # Scores should incorporate semantic results
        assert score.semantic_class_match > 0.0
        assert score.intent_coverage == 0.8
        assert score.overall > 0.5

    @pytest.mark.asyncio
    async def test_semantic_matcher_failure_graceful(self):
        """Matcher raises, doesn't crash evaluator — falls back to 0.0."""
        mock_matcher = MagicMock()
        mock_matcher.match_names = AsyncMock(side_effect=RuntimeError("Connection refused"))
        mock_matcher.intent_coverage = AsyncMock(side_effect=RuntimeError("Connection refused"))

        surrogate = _make_surrogate(GENERATED_CODE_HIGH_OVERLAP)
        evaluator = RoundTripEvaluator(surrogate=surrogate, semantic_matcher=mock_matcher)
        model = _make_model()

        # Should NOT raise
        score = await evaluator.evaluate(ORIGINAL_CODE_HIGH_OVERLAP, model)

        # Gracefully degraded to 0.0 for soft metrics
        assert score.semantic_class_match == 0.0
        assert score.intent_coverage == 0.0
        # Hard metrics still work
        assert score.class_overlap == 1.0

    @pytest.mark.asyncio
    async def test_no_semantic_matcher_skips_soft_metrics(self):
        """Without semantic matcher, soft metrics stay at 0."""
        surrogate = _make_surrogate(GENERATED_CODE_HIGH_OVERLAP)
        evaluator = RoundTripEvaluator(surrogate=surrogate, semantic_matcher=None)
        model = _make_model()

        score = await evaluator.evaluate(ORIGINAL_CODE_HIGH_OVERLAP, model)

        assert score.semantic_class_match == 0.0
        assert score.intent_coverage == 0.0


# ---------------------------------------------------------------------------
# Tests: Overall score weighting
# ---------------------------------------------------------------------------


class TestOverallScoreWeighting:
    """Verify compute_overall formula."""

    def test_overall_weighted_correctly(self):
        """Verify the weight formula sums correctly."""
        result = RoundTripScore.compute_overall(
            class_overlap=1.0,
            method_overlap=1.0,
            function_overlap=1.0,
            import_similarity=1.0,
            module_ratio=1.0,
            semantic_class_match=1.0,
            intent_coverage=1.0,
        )
        # All 1.0 → weights sum to 1.0
        assert result == pytest.approx(1.0)

    def test_overall_all_zero(self):
        result = RoundTripScore.compute_overall(
            class_overlap=0.0,
            method_overlap=0.0,
            function_overlap=0.0,
            import_similarity=0.0,
            module_ratio=0.0,
            semantic_class_match=0.0,
            intent_coverage=0.0,
        )
        assert result == 0.0

    def test_overall_partial_values(self):
        """Verify specific weight contributions."""
        # Only class_overlap = 1.0 (weight 0.20)
        result = RoundTripScore.compute_overall(
            class_overlap=1.0,
            method_overlap=0.0,
            function_overlap=0.0,
            import_similarity=0.0,
            module_ratio=0.0,
            semantic_class_match=0.0,
            intent_coverage=0.0,
        )
        assert result == pytest.approx(0.20)

        # Only intent_coverage = 1.0 (weight 0.20)
        result = RoundTripScore.compute_overall(
            class_overlap=0.0,
            method_overlap=0.0,
            function_overlap=0.0,
            import_similarity=0.0,
            module_ratio=0.0,
            semantic_class_match=0.0,
            intent_coverage=1.0,
        )
        assert result == pytest.approx(0.20)

    def test_weights_sum_to_one(self):
        """Confirm that the weights add up to 1.0."""
        weights = [0.20, 0.15, 0.10, 0.10, 0.10, 0.15, 0.20]
        assert sum(weights) == pytest.approx(1.0)
