"""Tests for semantic matcher module."""

import math

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from architecture_model.training.semantic_matcher import (
    SemanticMatcher,
    SemanticMatch,
)


class TestCosineSimilarity:
    """Tests for the static cosine similarity method."""

    def test_identical_vectors(self):
        sim = SemanticMatcher._cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0])
        assert sim == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        sim = SemanticMatcher._cosine_similarity([1.0, 0.0], [0.0, 1.0])
        assert sim == pytest.approx(0.0)

    def test_opposite_vectors(self):
        sim = SemanticMatcher._cosine_similarity([1.0, 0.0], [-1.0, 0.0])
        assert sim == pytest.approx(-1.0)

    def test_zero_vector_returns_zero(self):
        sim = SemanticMatcher._cosine_similarity([0.0, 0.0], [1.0, 1.0])
        assert sim == 0.0


class TestMatchNames:
    """Tests for match_names method with mocked embeddings."""

    @pytest.mark.asyncio
    async def test_match_names_finds_similar(self):
        """Similar embeddings produce a match above threshold."""
        matcher = SemanticMatcher(threshold=0.7)

        # "AuthService" -> [0.9, 0.1, 0.0], "UserAuthentication" -> [0.85, 0.15, 0.0]
        # cosine ~ 0.997 (very similar)
        fake_embeddings = [
            [0.9, 0.1, 0.0],   # AuthService (original)
            [0.85, 0.15, 0.0],  # UserAuthentication (generated)
        ]
        matcher.embed = AsyncMock(return_value=fake_embeddings)

        matches = await matcher.match_names(["AuthService"], ["UserAuthentication"])
        assert len(matches) == 1
        assert matches[0].original == "AuthService"
        assert matches[0].generated == "UserAuthentication"
        assert matches[0].score > 0.9

    @pytest.mark.asyncio
    async def test_match_names_respects_threshold(self):
        """Below-threshold pairs are not returned."""
        matcher = SemanticMatcher(threshold=0.9)

        # Orthogonal vectors: cosine = 0.0
        fake_embeddings = [
            [1.0, 0.0, 0.0],  # original
            [0.0, 1.0, 0.0],  # generated
        ]
        matcher.embed = AsyncMock(return_value=fake_embeddings)

        matches = await matcher.match_names(["Foo"], ["Bar"])
        assert matches == []

    @pytest.mark.asyncio
    async def test_match_names_greedy_one_to_one(self):
        """Each generated name is matched at most once (greedy)."""
        matcher = SemanticMatcher(threshold=0.5)

        # Two originals, one generated. Both originals are similar to the generated.
        # Only the best match should claim it.
        fake_embeddings = [
            [0.9, 0.1, 0.0],  # orig1
            [0.8, 0.2, 0.0],  # orig2
            [0.85, 0.15, 0.0],  # gen1 (similar to both)
        ]
        matcher.embed = AsyncMock(return_value=fake_embeddings)

        matches = await matcher.match_names(["orig1", "orig2"], ["gen1"])
        # Only one match since there's only one generated name
        assert len(matches) == 1
        assert matches[0].generated == "gen1"

    @pytest.mark.asyncio
    async def test_match_names_empty_original(self):
        """Empty original names returns empty matches."""
        matcher = SemanticMatcher(threshold=0.7)
        matches = await matcher.match_names([], ["gen1"])
        assert matches == []

    @pytest.mark.asyncio
    async def test_match_names_empty_generated(self):
        """Empty generated names returns empty matches."""
        matcher = SemanticMatcher(threshold=0.7)
        matches = await matcher.match_names(["orig1"], [])
        assert matches == []


class TestIntentCoverage:
    """Tests for intent_coverage method."""

    @pytest.mark.asyncio
    async def test_intent_coverage_full_match(self):
        """All originals have matches -> 1.0."""
        matcher = SemanticMatcher(threshold=0.7)

        # Two originals, two generated, all similar
        fake_embeddings = [
            [0.9, 0.1, 0.0],  # orig1
            [0.1, 0.9, 0.0],  # orig2
            [0.85, 0.15, 0.0],  # gen1 (matches orig1)
            [0.15, 0.85, 0.0],  # gen2 (matches orig2)
        ]
        matcher.embed = AsyncMock(return_value=fake_embeddings)

        coverage = await matcher.intent_coverage(["a", "b"], ["c", "d"])
        assert coverage == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_intent_coverage_partial(self):
        """Half originals match -> 0.5."""
        matcher = SemanticMatcher(threshold=0.7)

        # Two originals, two generated, only one pair similar
        fake_embeddings = [
            [0.9, 0.1, 0.0],  # orig1
            [0.1, 0.9, 0.0],  # orig2
            [0.85, 0.15, 0.0],  # gen1 (matches orig1)
            [0.85, 0.14, 0.01],  # gen2 (also matches orig1, NOT orig2)
        ]
        matcher.embed = AsyncMock(return_value=fake_embeddings)

        coverage = await matcher.intent_coverage(["a", "b"], ["c", "d"])
        # orig1 matches gen1, orig2 tries gen2 but cosine([0.1,0.9,0],[0.85,0.14,0.01]) is low
        assert coverage == pytest.approx(0.5)

    @pytest.mark.asyncio
    async def test_intent_coverage_empty_original(self):
        """Empty original -> 1.0 (vacuously true)."""
        matcher = SemanticMatcher(threshold=0.7)
        coverage = await matcher.intent_coverage([], ["gen1"])
        assert coverage == 1.0

    @pytest.mark.asyncio
    async def test_intent_coverage_empty_generated(self):
        """Empty generated -> 0.0."""
        matcher = SemanticMatcher(threshold=0.7)
        coverage = await matcher.intent_coverage(["orig1"], [])
        assert coverage == 0.0


class TestEmbedEndpoint:
    """Tests for embed method with mocked HTTP calls."""

    @pytest.mark.asyncio
    async def test_embed_uses_batch_endpoint(self):
        """Verifies /api/embed is called first."""
        matcher = SemanticMatcher(host="http://localhost:11434")

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={
            "embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        })
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("architecture_model.training.semantic_matcher.aiohttp") as mock_aiohttp:
            mock_aiohttp.ClientSession = MagicMock(return_value=mock_session)

            result = await matcher.embed(["hello", "world"])

        assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_session.post.assert_called_once_with(
            "http://localhost:11434/api/embed",
            json={"model": "nomic-embed-text", "input": ["hello", "world"]},
        )

    @pytest.mark.asyncio
    async def test_embed_fallback_to_individual(self):
        """Falls back to /api/embeddings when batch endpoint fails."""
        matcher = SemanticMatcher(host="http://localhost:11434")

        # Batch endpoint fails
        batch_resp = AsyncMock()
        batch_resp.status = 404
        batch_resp.__aenter__ = AsyncMock(return_value=batch_resp)
        batch_resp.__aexit__ = AsyncMock(return_value=False)

        # Individual endpoint succeeds
        ind_resp1 = AsyncMock()
        ind_resp1.status = 200
        ind_resp1.raise_for_status = MagicMock()
        ind_resp1.json = AsyncMock(return_value={"embedding": [0.1, 0.2]})
        ind_resp1.__aenter__ = AsyncMock(return_value=ind_resp1)
        ind_resp1.__aexit__ = AsyncMock(return_value=False)

        ind_resp2 = AsyncMock()
        ind_resp2.status = 200
        ind_resp2.raise_for_status = MagicMock()
        ind_resp2.json = AsyncMock(return_value={"embedding": [0.3, 0.4]})
        ind_resp2.__aenter__ = AsyncMock(return_value=ind_resp2)
        ind_resp2.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        # First call is batch (fails with 404), then two individual calls
        mock_session.post = MagicMock(side_effect=[batch_resp, ind_resp1, ind_resp2])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("architecture_model.training.semantic_matcher.aiohttp") as mock_aiohttp:
            mock_aiohttp.ClientSession = MagicMock(return_value=mock_session)

            result = await matcher.embed(["hello", "world"])

        assert result == [[0.1, 0.2], [0.3, 0.4]]
