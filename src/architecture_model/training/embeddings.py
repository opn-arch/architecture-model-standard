"""Ollama embedding client for semantic entity matching."""

from __future__ import annotations

import math
from typing import Optional

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class OllamaEmbedder:
    """Generates embeddings via Ollama's /api/embeddings endpoint."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        host: str = "http://localhost:11434",
    ) -> None:
        self._model = model
        self._host = host

    async def _embed_single(self, text: str) -> list[float]:
        """Embed a single text string."""
        if not HAS_AIOHTTP:
            raise RuntimeError("aiohttp required for embeddings")

        url = f"{self._host}/api/embeddings"
        payload = {"model": self._model, "prompt": text}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["embedding"]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""
        results = []
        for text in texts:
            vec = await self._embed_single(text)
            results.append(vec)
        return results

    async def similarity_matrix(
        self, texts_a: list[str], texts_b: list[str]
    ) -> list[list[float]]:
        """Compute NxM similarity matrix between two text lists."""
        vecs_a = await self.embed(texts_a)
        vecs_b = await self.embed(texts_b)

        matrix = []
        for va in vecs_a:
            row = [cosine_similarity(va, vb) for vb in vecs_b]
            matrix.append(row)
        return matrix
