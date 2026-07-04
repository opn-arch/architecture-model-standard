"""
MPC Controller: active learning decisions, budget management, convergence detection.

The "brain" of the MPC training loop. Decides when to query the expensive
oracle model vs. trusting the local surrogate, tracks agreement rates, and
detects when the surrogate has converged (making further oracle queries
unnecessary).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import stdev

from architecture_model.training.evaluator import LossVector


# ---------------------------------------------------------------------------
# MPCState
# ---------------------------------------------------------------------------


@dataclass
class MPCState:
    """Serializable state for the MPC controller."""

    iteration: int = 0
    total_repos_processed: int = 0
    oracle_budget_remaining: float = 100_000
    surrogate_accuracy: float = 0.0
    convergence_history: list[float] = field(default_factory=list)


# ---------------------------------------------------------------------------
# MPCController
# ---------------------------------------------------------------------------


class MPCController:
    """
    Active learning controller for the MPC training loop.

    Decides whether to query the oracle (expensive frontier model) based on:
    - Confidence of the surrogate's extraction
    - Novelty of the repository pattern
    - Borderline validator scores
    - Remaining oracle budget
    """

    _CONVERGENCE_WINDOW = 5
    _CONVERGENCE_THRESHOLD = 0.02

    def __init__(self, state: MPCState, oracle_budget: float | None = None) -> None:
        self.state = state
        if oracle_budget is not None:
            self.state.oracle_budget_remaining = oracle_budget
        self._agreement_total = 0
        self._agreement_count = 0
        self._pareto_front: list[LossVector] = []

    def should_query_oracle(
        self, validator_score: float, confidence: float, is_novel: bool
    ) -> bool:
        """
        Decide whether a specific extraction needs oracle verification.

        Priority of checks:
        1. Budget exhausted → never query
        2. Low confidence (< 0.5) → always query
        3. Novel pattern → always query
        4. Borderline validator score (40-80) → query
        5. High confidence AND high validator score → don't query
        """
        # Budget check first — can't query with no budget
        if self.state.oracle_budget_remaining <= 0:
            return False

        # Low confidence → always query
        if confidence < 0.5:
            return True

        # Novel pattern → always query
        if is_novel:
            return True

        # Borderline validator score → query
        if 40 <= validator_score <= 80:
            return True

        # High confidence AND high score → don't query
        if confidence >= 0.5 and validator_score > 80:
            return False

        return True

    def record_agreement(self, agreed: bool) -> None:
        """
        Track whether surrogate agreed with oracle on this extraction.

        Updates running surrogate_accuracy as the fraction of agreements.
        """
        self._agreement_total += 1
        if agreed:
            self._agreement_count += 1

        self.state.surrogate_accuracy = self._agreement_count / self._agreement_total

    def record_loss(self, loss: LossVector) -> bool:
        """Check if loss is competitive with Pareto front.

        Returns True if the loss is non-dominated (competitive with best seen).
        Returns False if dominated (strictly worse than something on the front).

        Also updates the Pareto front and convergence history.
        """
        # Check if new loss is dominated by any current front member
        dominated = any(f.dominates(loss) for f in self._pareto_front)
        agreed = not dominated

        # Update Pareto front: add candidate, then prune dominated entries
        candidates = self._pareto_front + [loss]
        self._pareto_front = [
            c for c in candidates
            if not any(o.dominates(c) for o in candidates if o is not c)
        ]

        # Track in convergence history
        self.state.convergence_history.append(1.0 if agreed else 0.0)

        # Update agreement tracking for backward compatibility
        self._agreement_total += 1
        if agreed:
            self._agreement_count += 1
        self.state.surrogate_accuracy = self._agreement_count / self._agreement_total

        return agreed

    def is_converged(self) -> bool:
        """
        Check if training has converged.

        Convergence = 80%+ of recent loss vectors are non-dominated
        (competitive with the Pareto front). Requires at least
        CONVERGENCE_WINDOW values in history.
        """
        history = self.state.convergence_history
        if len(history) < self._CONVERGENCE_WINDOW:
            return False

        recent = history[-self._CONVERGENCE_WINDOW:]
        return sum(recent) / len(recent) >= 0.8

    def next_iteration(self) -> None:
        """
        Advance to the next iteration.

        - Increments iteration counter
        - Increments total_repos_processed
        - Records current surrogate_accuracy in convergence_history
        """
        self.state.iteration += 1
        self.state.total_repos_processed += 1
        self.state.convergence_history.append(self.state.surrogate_accuracy)
