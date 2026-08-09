"""Project-local learning persistence.

Stores corrections, resolution outcomes, calibration overrides,
and quality history for cross-session learning (Loop 2).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import json

from .protocol import Evidence, Uncertainty


@dataclass
class Correction:
    """A user correction to a module's output."""
    timestamp: str
    module: str
    entity_id: str
    correction_type: str  # rename | split | merge | remove | add | reclassify | reassign
    before: dict[str, Any]
    after: dict[str, Any]
    reason: str


@dataclass
class ResolutionOutcome:
    """Record of how an uncertainty was resolved."""
    uncertainty: Uncertainty
    resolution: Evidence
    method: str       # llm | search | user | escalation
    attempts: int
    duration_ms: int


@dataclass
class Calibration:
    """A project-specific threshold override."""
    module: str
    parameter: str
    value: float
    reason: str
    date: str = ""


@dataclass
class QualityTrend:
    """Quality trend for a metric over time."""
    module: str
    metric: str = "score"
    values: list[tuple[str, float]] = field(default_factory=list)

    @property
    def direction(self) -> str:
        if len(self.values) < 2:
            return "stable"
        recent = [v for _, v in self.values[-3:]]
        if all(recent[i] >= recent[i + 1] for i in range(len(recent) - 1)):
            return "degrading"
        if all(recent[i] <= recent[i + 1] for i in range(len(recent) - 1)):
            return "improving"
        return "stable"


class LearningStore:
    """Persists learning data to .architecture/learning/."""

    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)

    # --- Corrections ---

    def add_correction(self, correction: Correction) -> None:
        corrections = self._load_json("corrections.json", [])
        corrections.append(asdict(correction))
        self._save_json("corrections.json", corrections)

    def get_corrections(self, module: str | None = None) -> list[Correction]:
        data = self._load_json("corrections.json", [])
        corrections = [Correction(**d) for d in data]
        if module:
            corrections = [c for c in corrections if c.module == module]
        return corrections

    def corrections_as_evidence(self) -> list[Evidence]:
        return [
            Evidence(
                source="user_correction",
                confidence=1.0,
                raw=f"{c.correction_type} {c.entity_id}: {c.reason}",
            )
            for c in self.get_corrections()
        ]

    # --- Calibration ---

    def set_calibration(self, module: str, parameter: str, value: float, reason: str = "") -> None:
        cal = self._load_json("calibration.json", {})
        if module not in cal:
            cal[module] = {}
        cal[module][parameter] = {"value": value, "reason": reason}
        self._save_json("calibration.json", cal)

    def get_calibration(self, module: str) -> dict[str, float]:
        cal = self._load_json("calibration.json", {})
        module_cal = cal.get(module, {})
        return {k: v["value"] for k, v in module_cal.items()}

    # --- Quality History ---

    def record_run(self, date: str, scores: dict[str, float]) -> None:
        history = self._load_json("history.json", [])
        history.append({"date": date, "scores": scores})
        self._save_json("history.json", history)

    def get_trend(self, module: str) -> QualityTrend:
        history = self._load_json("history.json", [])
        values = [
            (h["date"], h["scores"].get(module, 0.0))
            for h in history
            if module in h.get("scores", {})
        ]
        trend = QualityTrend(module=module, values=values)
        return trend

    # --- Resolutions ---

    def add_resolution(self, outcome: ResolutionOutcome) -> None:
        resolutions = self._load_json("resolutions.json", [])
        resolutions.append({
            "category": outcome.uncertainty.category,
            "description": outcome.uncertainty.description,
            "method": outcome.method,
            "attempts": outcome.attempts,
            "duration_ms": outcome.duration_ms,
            "resolution_source": outcome.resolution.source,
            "resolution_raw": outcome.resolution.raw,
        })
        self._save_json("resolutions.json", resolutions)

    def get_resolutions(self, category: str | None = None) -> list[ResolutionOutcome]:
        data = self._load_json("resolutions.json", [])
        results = []
        for d in data:
            outcome = ResolutionOutcome(
                uncertainty=Uncertainty(
                    category=d["category"],
                    description=d["description"],
                    suggested_fallback="",
                    priority="",
                ),
                resolution=Evidence(
                    source=d["resolution_source"],
                    confidence=1.0,
                    raw=d["resolution_raw"],
                ),
                method=d["method"],
                attempts=d["attempts"],
                duration_ms=d["duration_ms"],
            )
            if category is None or d["category"] == category:
                results.append(outcome)
        return results

    # --- Helpers ---

    def _load_json(self, filename: str, default: Any) -> Any:
        path = self.path / filename
        if not path.exists():
            return default
        return json.loads(path.read_text())

    def _save_json(self, filename: str, data: Any) -> None:
        path = self.path / filename
        path.write_text(json.dumps(data, indent=2, default=str))
