"""Regenability scorer — per-level regen readiness assessment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LevelScore:
    """Score for a single entity at a level."""

    id: str
    name: str
    score: float = 0.0
    grade: str = "F"
    blockers: list[str] = field(default_factory=list)


@dataclass
class RegenReport:
    """Full regenability assessment across all levels."""

    overall_score: float = 0.0
    overall_grade: str = "F"

    system_scores: list[LevelScore] = field(default_factory=list)
    component_scores: list[LevelScore] = field(default_factory=list)
    capability_scores: list[LevelScore] = field(default_factory=list)
    behavior_scores: list[LevelScore] = field(default_factory=list)

    # Grade distributions
    system_grades: dict[str, int] = field(default_factory=dict)
    component_grades: dict[str, int] = field(default_factory=dict)
    capability_grades: dict[str, int] = field(default_factory=dict)
    behavior_grades: dict[str, int] = field(default_factory=dict)

    # Averages per level
    system_avg: float = 0.0
    component_avg: float = 0.0
    capability_avg: float = 0.0
    behavior_avg: float = 0.0


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 50:
        return "C"
    elif score >= 30:
        return "D"
    return "F"


def _grade_distribution(scores: list[LevelScore]) -> dict[str, int]:
    dist = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for s in scores:
        dist[s.grade] = dist.get(s.grade, 0) + 1
    return dist


def score_regenability(model: Any) -> RegenReport:
    """Compute per-level regenability scores."""
    report = RegenReport()

    if not model:
        return report

    components = model.entities.components or []
    capabilities = model.entities.capabilities or []
    behaviors = model.entities.behaviors or []
    systems = model.entities.systems or []
    relationships = model.relationships or []

    # --- Component scores (use built-in regen readiness if available) ---
    try:
        from architecture_model.core.regen_readiness import compute_regen_readiness

        regen = compute_regen_readiness(model)
        for comp_r in regen.components:
            report.component_scores.append(
                LevelScore(
                    id=comp_r.component_id,
                    name=comp_r.component_id,  # We don't have name in regen result
                    score=comp_r.score,
                    grade=_grade(comp_r.score),
                    blockers=comp_r.blockers,
                )
            )
        report.overall_score = regen.overall
        report.overall_grade = regen.grade
    except Exception:
        # Fallback: simple scoring based on signatures/contracts
        for comp in components:
            sigs = len(getattr(comp, "signatures", []))
            tests = len(getattr(comp, "test_contracts", []))
            files = len(comp.files)

            score = 0.0
            blockers = []
            if sigs > 0:
                score += 40
            else:
                blockers.append("no signatures")
            if tests > 0:
                score += 30
            else:
                blockers.append("no test contracts")
            if files > 0:
                score += 20
            if getattr(comp, "contract", ""):
                score += 10
            else:
                blockers.append("no contract description")

            report.component_scores.append(
                LevelScore(
                    id=comp.id,
                    name=comp.name,
                    score=score,
                    grade=_grade(score),
                    blockers=blockers,
                )
            )

    # --- Capability scores ---
    # A capability is "regenable" if it has:
    # - A realizes relationship connecting to a component
    # - That component has signatures
    realizes_map: dict[str, str] = {}  # capability_id → component_id
    for rel in relationships:
        if getattr(rel, "type", "") == "realizes" or getattr(rel, "rel_type", "") == "realizes":
            realizes_map[getattr(rel, "to_id", "")] = getattr(rel, "from_id", "")

    comp_map = {c.id: c for c in components}

    for cap in capabilities:
        score = 0.0
        blockers = []

        # Has realizes relationship?
        realizing_comp_id = realizes_map.get(cap.id)
        if realizing_comp_id:
            score += 40
            # Realizing component has signatures?
            realizing_comp = comp_map.get(realizing_comp_id)
            if realizing_comp and getattr(realizing_comp, "signatures", []):
                score += 40
            else:
                blockers.append("realizing component lacks signatures")
            # Has description?
            if getattr(cap, "description", ""):
                score += 20
            else:
                blockers.append("no description")
        else:
            blockers.append("no realizes relationship")
            if getattr(cap, "description", ""):
                score += 30

        report.capability_scores.append(
            LevelScore(
                id=cap.id,
                name=cap.name,
                score=score,
                grade=_grade(score),
                blockers=blockers,
            )
        )

    # --- Behavior scores ---
    for beh in behaviors:
        score = 0.0
        blockers = []

        # Has trigger?
        if getattr(beh, "trigger", ""):
            score += 25
        else:
            blockers.append("no trigger")

        # Has actor?
        if getattr(beh, "actor", ""):
            score += 25
        else:
            blockers.append("no actor")

        # Has steps?
        steps = getattr(beh, "steps", [])
        if steps:
            score += 25
            if len(steps) >= 3:
                score += 10  # well-detailed
        else:
            blockers.append("no steps")

        # Has capability link?
        cap_id = getattr(beh, "capability_id", "")
        if cap_id:
            score += 15
        else:
            blockers.append("no capability link")

        report.behavior_scores.append(
            LevelScore(
                id=beh.id,
                name=beh.name,
                score=score,
                grade=_grade(score),
                blockers=blockers,
            )
        )

    # --- System scores (avg of contained components) ---
    for sys in systems:
        comp_ids = getattr(sys, "component_ids", [])
        sys_comp_scores = [cs.score for cs in report.component_scores if cs.id in comp_ids]
        avg = sum(sys_comp_scores) / len(sys_comp_scores) if sys_comp_scores else 0.0
        blockers = []
        if not comp_ids:
            blockers.append("no components assigned")

        report.system_scores.append(
            LevelScore(
                id=sys.id,
                name=sys.name,
                score=avg,
                grade=_grade(avg),
                blockers=blockers,
            )
        )

    # --- Distributions and averages ---
    report.system_grades = _grade_distribution(report.system_scores)
    report.component_grades = _grade_distribution(report.component_scores)
    report.capability_grades = _grade_distribution(report.capability_scores)
    report.behavior_grades = _grade_distribution(report.behavior_scores)

    report.system_avg = (
        sum(s.score for s in report.system_scores) / len(report.system_scores)
        if report.system_scores
        else 0.0
    )
    report.component_avg = (
        sum(s.score for s in report.component_scores) / len(report.component_scores)
        if report.component_scores
        else 0.0
    )
    report.capability_avg = (
        sum(s.score for s in report.capability_scores) / len(report.capability_scores)
        if report.capability_scores
        else 0.0
    )
    report.behavior_avg = (
        sum(s.score for s in report.behavior_scores) / len(report.behavior_scores)
        if report.behavior_scores
        else 0.0
    )

    return report
