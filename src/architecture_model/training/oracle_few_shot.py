"""Few-shot retrieval for oracle prompts.

Retrieves high-scoring past extractions as examples, ranked by
manifest similarity (module count, LOC distribution).
"""

from __future__ import annotations

from typing import Any


class FewShotRetriever:
    """Retrieves similar high-quality past extractions as few-shot examples."""

    def __init__(self, performance_store: Any) -> None:
        self._store = performance_store

    def retrieve(self, manifest: dict, k: int = 3) -> list[dict]:
        """Retrieve top-k similar high-scoring examples.

        Similarity is based on manifest characteristics (module count).
        Returns list of dicts with keys: code_context, oracle_output, coverage_score.
        """
        candidates = self._store.get_high_scoring(threshold=0.8, limit=20)
        if not candidates:
            return []

        # Score by similarity to current manifest
        target_modules = len(manifest.get("modules", []))
        scored = []
        for c in candidates:
            c_modules = c.get("modules", 0)
            # Prefer similar-sized projects
            size_diff = abs(target_modules - c_modules)
            similarity = 1.0 / (1.0 + size_diff * 0.1)
            scored.append((similarity, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:k]]

    def format_section(self, manifest: dict, k: int = 3) -> str:
        """Format few-shot examples as a prompt section."""
        examples = self.retrieve(manifest, k=k)
        if not examples:
            return ""

        lines = ["\n## Few-Shot Examples (high-scoring past extractions)\n"]
        for i, ex in enumerate(examples, 1):
            context_preview = ex.get("code_context", "")[:500]
            output = ex.get("oracle_output", "")[:1000]
            lines.append(f"### Example {i} (coverage: {ex.get('coverage_score', '?')})")
            lines.append(f"Input (abbreviated):\n```\n{context_preview}\n```")
            lines.append(f"Output:\n```yaml\n{output}\n```\n")

        return "\n".join(lines)
