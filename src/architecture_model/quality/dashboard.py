"""Unified quality dashboard — aggregates all quality dimensions into one report."""
from __future__ import annotations

from dataclasses import dataclass, field
from architecture_model.core.types import ArchitectureModel, Status
from architecture_model.core.validator import validate_model
from architecture_model.quality.monitoring import monitored


@dataclass
class QualityReport:
    """Aggregated quality report across all dimensions."""
    project: str
    validation_score: int  # 0-100
    validation_issues: int
    semantic_completeness: dict[str, str]  # field -> "populated/total"
    detail_level_distribution: dict[str, int]  # L0..L4 -> count
    regen_readiness_score: float  # 0-100
    confidence_score: float  # 0.0-1.0
    overall_score: int  # 0-100 weighted composite
    grade: str  # A-F

    def to_markdown(self) -> str:
        lines = [
            f"# Quality Report: {self.project}",
            "",
            f"**Overall Grade: {self.grade}** ({self.overall_score}/100)",
            "",
            "## Dimensions",
            "",
            f"| Dimension | Score |",
            f"|-----------|-------|",
            f"| Validation | {self.validation_score}/100 ({self.validation_issues} issues) |",
            f"| Regen Readiness | {self.regen_readiness_score:.0f}/100 |",
            f"| Confidence | {self.confidence_score:.1%} |",
            "",
            "## Semantic Completeness",
            "",
            "| Field | Coverage |",
            "|-------|----------|",
        ]
        for field_name, coverage in self.semantic_completeness.items():
            lines.append(f"| {field_name} | {coverage} |")

        lines.extend([
            "",
            "## Detail Level Distribution",
            "",
            "| Level | Count |",
            "|-------|-------|",
        ])
        for level, count in sorted(self.detail_level_distribution.items()):
            lines.append(f"| {level} | {count} |")

        return "\n".join(lines)


def _compute_semantic_completeness(model: ArchitectureModel) -> dict[str, str]:
    """Count how many entities have each v2.1 field populated."""
    comps = [c for c in model.entities.components
             if (c.status.value if hasattr(c.status, 'value') else str(c.status)) == "ACTIVE"]
    caps = [c for c in model.entities.capabilities
            if (c.status.value if hasattr(c.status, 'value') else str(c.status)) == "ACTIVE"]
    ifaces = model.entities.interfaces

    comp_with_intent = sum(1 for c in comps if c.intent)
    cap_with_intent = sum(1 for c in caps if c.intent)
    total_intent = len(comps) + len(caps)
    has_intent = comp_with_intent + cap_with_intent

    cap_with_moes = sum(1 for c in caps if c.moes)
    comp_with_goals = sum(1 for c in comps if c.goals)
    comp_with_tradeoffs = sum(1 for c in comps if c.trade_offs)
    comp_with_failure = sum(1 for c in comps if c.failure_modes)
    iface_with_contract = sum(1 for i in ifaces if i.contract)

    return {
        "intent_coverage": f"{has_intent}/{total_intent}",
        "moe_coverage": f"{cap_with_moes}/{len(caps)}",
        "goals_coverage": f"{comp_with_goals}/{len(comps)}",
        "trade_offs_coverage": f"{comp_with_tradeoffs}/{len(comps)}",
        "failure_modes_coverage": f"{comp_with_failure}/{len(comps)}",
        "contract_coverage": f"{iface_with_contract}/{len(ifaces)}",
    }


def _compute_detail_distribution(model: ArchitectureModel) -> dict[str, int]:
    """Count entities at each detail level."""
    from architecture_model.core.detail_level import compute_detail_level
    dist: dict[str, int] = {"L0": 0, "L1": 0, "L2": 0, "L3": 0, "L4": 0}
    for comp in model.entities.components:
        level = compute_detail_level(comp)
        dist[f"L{level}"] = dist.get(f"L{level}", 0) + 1
    for cap in model.entities.capabilities:
        level = compute_detail_level(cap)
        dist[f"L{level}"] = dist.get(f"L{level}", 0) + 1
    return dist


def _grade(score: int) -> str:
    if score >= 90: return "A"
    if score >= 80: return "B"
    if score >= 70: return "C"
    if score >= 60: return "D"
    return "F"


@monitored("quality.dashboard", quality=lambda r: {"overall": r.overall_score, "grade": r.grade})
def quality_report(model: ArchitectureModel, *, manifest=None) -> QualityReport:
    """Generate a unified quality report aggregating all dimensions."""
    # Validation
    val_result = validate_model(model)
    val_score = val_result.score

    # Semantic completeness
    semantic = _compute_semantic_completeness(model)

    # Detail level distribution
    detail_dist = _compute_detail_distribution(model)

    # Regen readiness (optional — may not have signatures)
    regen_score = 0.0
    try:
        from architecture_model.quality.regen_readiness import compute_regen_readiness
        rr = compute_regen_readiness(model)
        regen_score = rr.overall
    except Exception:
        pass

    # Confidence
    conf_score = 0.0
    try:
        from architecture_model.quality.confidence import model_confidence_summary
        summary = model_confidence_summary(model)
        conf_score = summary.get("overall", 0.0)
    except Exception:
        pass

    # Weighted composite: validation 30%, regen 25%, confidence 20%, semantic 25%
    sem_parts = semantic.get("intent_coverage", "0/1").split("/")
    sem_ratio = int(sem_parts[0]) / max(int(sem_parts[1]), 1) if len(sem_parts) == 2 else 0
    overall = int(val_score * 0.30 + regen_score * 0.25 + conf_score * 100 * 0.20 + sem_ratio * 100 * 0.25)
    overall = min(100, max(0, overall))

    return QualityReport(
        project=model.meta.project,
        validation_score=val_score,
        validation_issues=len(val_result.issues),
        semantic_completeness=semantic,
        detail_level_distribution=detail_dist,
        regen_readiness_score=regen_score,
        confidence_score=conf_score,
        overall_score=overall,
        grade=_grade(overall),
    )
