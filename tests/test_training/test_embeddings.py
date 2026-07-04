"""Tests for Ollama embedding client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from architecture_model.training.embeddings import (
    OllamaEmbedder,
    cosine_similarity,
)


class TestCosineSimilarity:
    def test_identical_vectors(self):
        assert cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_similar_vectors(self):
        sim = cosine_similarity([1.0, 1.0, 0.0], [1.0, 0.9, 0.1])
        assert sim > 0.95

    def test_zero_vector_returns_zero(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


class TestOllamaEmbedder:
    @pytest.mark.asyncio
    async def test_embed_batch(self):
        embedder = OllamaEmbedder()
        embedder._embed_single = AsyncMock(side_effect=[
            [0.1, 0.2], [0.3, 0.4], [0.5, 0.6]
        ])
        result = await embedder.embed(["a", "b", "c"])
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_similarity_matrix(self):
        embedder = OllamaEmbedder()
        embedder._embed_single = AsyncMock(side_effect=[
            [1.0, 0.0], [0.0, 1.0],  # set A
            [0.9, 0.1], [0.1, 0.9],  # set B
        ])
        matrix = await embedder.similarity_matrix(["a", "b"], ["c", "d"])
        assert matrix[0][0] > 0.9  # a vs c
        assert matrix[1][1] > 0.9  # b vs d
        assert matrix[0][1] < 0.3  # a vs d
