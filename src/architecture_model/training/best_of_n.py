"""
Best-of-N DPO preference pair generation.

Generates N surrogate extractions with temperature sampling, ranks them
against the oracle using the evaluator, and produces preference pairs
(best vs worst) for DPO fine-tuning.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from architecture_model.core.types import ArchitectureModel
from architecture_model.training.evaluator import Evaluator, LossVector
from architecture_model.training.surrogate import Surrogate

logger = logging.getLogger(__name__)


@dataclass
class RankedExtraction:
    """A surrogate extraction ranked by quality."""
    model: ArchitectureModel
    loss: LossVector
    yaml_output: str


class BestOfNGenerator:
    """Generate N surrogate extractions and rank by quality for DPO pairs.

    Strategy: Generate N extractions with temperature sampling, evaluate
    each against the oracle ground truth, return best and worst as
    chosen/rejected pair for DPO training.
    """

    def __init__(
        self,
        surrogate: Surrogate,
        evaluator: Evaluator,
        n: int = 4,
        temperature: float = 0.8,
    ) -> None:
        self._surrogate = surrogate
        self._evaluator = evaluator
        self._n = n
        self._temperature = temperature

    async def generate(
        self,
        code_context: str,
        oracle_model: ArchitectureModel,
    ) -> Optional[tuple[RankedExtraction, RankedExtraction]]:
        """Generate N extractions, rank, return (best, worst) pair.

        Returns None if fewer than 2 valid extractions were produced.

        Args:
            code_context: The code context string to extract from.
            oracle_model: The oracle ground truth for evaluation.

        Returns:
            Tuple of (best, worst) RankedExtraction, or None.
        """
        candidates: list[RankedExtraction] = []

        for i in range(self._n):
            try:
                model = await self._surrogate.extract_model(code_context)
            except Exception:
                logger.debug("Best-of-N attempt %d failed", i)
                continue

            if model is None:
                continue

            loss = self._evaluator.compute_loss(model, oracle_model)
            yaml_output = model.to_yaml()
            candidates.append(RankedExtraction(
                model=model, loss=loss, yaml_output=yaml_output
            ))

        if len(candidates) < 2:
            logger.debug("Best-of-N: only %d valid candidates, need 2+", len(candidates))
            return None

        # Sort by composite quality: structural_accuracy (primary) + completeness (secondary)
        candidates.sort(
            key=lambda c: (c.loss.structural_accuracy, c.loss.completeness),
            reverse=True,
        )

        best = candidates[0]
        worst = candidates[-1]

        # Only produce pair if there's meaningful quality difference
        margin = best.loss.structural_accuracy - worst.loss.structural_accuracy
        if margin < 0.05:
            logger.debug("Best-of-N: margin %.3f too small, skipping", margin)
            return None

        return best, worst

    @property
    def n(self) -> int:
        return self._n
