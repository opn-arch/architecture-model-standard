"""
Semantic similarity matching via local Ollama embeddings.

Uses nomic-embed-text (768-dim) for computing cosine similarity between
entity names, enabling soft matching where names differ but intent is same
(e.g., "UserAuth" ≈ "AuthenticationService").
"""

from __future__ import annotations

import math
from dataclasses import dataclass

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


@dataclass
class SemanticMatch:
    """A semantic match between two names."""

    original: str
    generated: str
    score: float  # cosine similarity (0-1)


class SemanticMatcher:
    """Embedding-based semantic similarity using local Ollama."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        threshold: float = 0.7,
    ) -> None:
        self._host = host
        self._model = model
        self._threshold = threshold

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts. Tries batch /api/embed first, falls back to /api/embeddings.

        Returns list of float vectors (768-dim for nomic-embed-text).
        Raises RuntimeError if aiohttp not installed or Ollama unreachable.
        """
        if not HAS_AIOHTTP:
            raise RuntimeError("aiohttp required for SemanticMatcher")

        async with aiohttp.ClientSession() as session:
            # Try batch endpoint first
            try:
                url = f"{self._host}/api/embed"
                payload = {"model": self._model, "input": texts}
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["embeddings"]
            except Exception:
                pass

            # Fallback: individual embeddings
            embeddings = []
            url = f"{self._host}/api/embeddings"
            for text in texts:
                payload = {"model": self._model, "prompt": text}
                async with session.post(url, json=payload) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    embeddings.append(data["embedding"])
            return embeddings

    async def match_names(
        self,
        original_names: list[str],
        generated_names: list[str],
    ) -> list[SemanticMatch]:
        """Find best semantic matches between two name sets.

        For each original name, finds the best matching generated name
        (by cosine similarity). Only returns matches above threshold.
        Uses greedy one-to-one assignment (each generated matched at most once).

        Args:
            original_names: Names from original code structure.
            generated_names: Names from generated code structure.

        Returns:
            List of SemanticMatch objects (only those above threshold).
        """
        if not original_names or not generated_names:
            return []

        # Embed all names in a single batch
        all_texts = list(original_names) + list(generated_names)
        embeddings = await self.embed(all_texts)

        n_orig = len(original_names)
        orig_embeds = embeddings[:n_orig]
        gen_embeds = embeddings[n_orig:]

        matches = []
        used_gen: set[int] = set()

        for i, (orig_name, orig_vec) in enumerate(zip(original_names, orig_embeds)):
            best_score = -1.0
            best_idx = -1

            for j, (gen_name, gen_vec) in enumerate(zip(generated_names, gen_embeds)):
                if j in used_gen:
                    continue
                sim = self._cosine_similarity(orig_vec, gen_vec)
                if sim > best_score:
                    best_score = sim
                    best_idx = j

            if best_idx >= 0 and best_score >= self._threshold:
                matches.append(SemanticMatch(
                    original=orig_name,
                    generated=generated_names[best_idx],
                    score=best_score,
                ))
                used_gen.add(best_idx)

        return matches

    async def intent_coverage(
        self,
        original_names: list[str],
        generated_names: list[str],
    ) -> float:
        """Fraction of original names that have a semantic match in generated.

        Returns value in [0, 1]. Returns 1.0 if original_names is empty.
        """
        if not original_names:
            return 1.0
        if not generated_names:
            return 0.0

        matches = await self.match_names(original_names, generated_names)
        return len(matches) / len(original_names)

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
