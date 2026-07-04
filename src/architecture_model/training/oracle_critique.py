"""Self-critique refinement loop for oracle extractions.

After initial extraction, checks manifest coverage. If gaps exist,
builds a targeted critique and asks oracle to re-extract with gap awareness.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from architecture_model.core.types import ArchitectureModel
from architecture_model.training.oracle_coverage import ManifestCoverageComputer, CoverageResult

if TYPE_CHECKING:
    from architecture_model.training.oracle import Oracle


class SelfCritiqueRefiner:
    """Iterative self-critique loop for oracle extraction quality."""

    def __init__(
        self,
        oracle: "Oracle",
        coverage_computer: ManifestCoverageComputer,
        threshold: float = 0.85,
        max_rounds: int = 3,
    ) -> None:
        self._oracle = oracle
        self._coverage = coverage_computer
        self._threshold = threshold
        self._max_rounds = max_rounds

    async def refine(
        self,
        model: ArchitectureModel,
        manifest: dict,
        context: str,
    ) -> ArchitectureModel:
        """Refine oracle extraction via self-critique.

        If coverage is already above threshold, returns immediately.
        Otherwise, builds critique from gaps and re-extracts.

        Args:
            model: Initial oracle extraction.
            manifest: Reality Manifest for the repo.
            context: Code context string.

        Returns:
            Best model achieved (original or improved).
        """
        best_model = model

        for round_num in range(self._max_rounds):
            coverage = self._coverage.compute(manifest, best_model)

            if coverage.overall >= self._threshold:
                return best_model

            # Build critique from gaps
            critique = self._build_critique(coverage)

            # Re-extract with critique appended to context
            augmented_context = f"{context}\n\n{critique}"
            new_model = await self._oracle.extract_model(augmented_context)

            if new_model is not None:
                best_model = new_model

        return best_model

    def _build_critique(self, coverage: CoverageResult) -> str:
        """Build a critique prompt from coverage gaps."""
        lines = ["## Self-Critique — Gaps Identified\n"]
        lines.append(f"Coverage score: {coverage.overall:.2f} (target: {self._threshold})\n")

        if coverage.uncovered_modules:
            lines.append("### Uncovered Modules (must add components for these):")
            for mod in coverage.uncovered_modules[:10]:
                lines.append(f"- `{mod}`")

        if coverage.uncovered_interfaces:
            lines.append("\n### Uncovered Import Edges (must add relationships):")
            for src, tgt in coverage.uncovered_interfaces[:10]:
                lines.append(f"- `{src}` → `{tgt}`")

        lines.append("\n**Re-extract the architecture model, ensuring these modules and")
        lines.append("interfaces are represented as components and relationships.**")

        return "\n".join(lines)
