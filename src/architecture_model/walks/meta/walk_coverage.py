"""architecture_model.walks.meta.walk_coverage — meta-walk over the walk substrate.

Scans ``.architecture/model/walks/*.v3.yaml`` (or any directory of WalkSpecs),
extracts each walk's ``audits`` list, and cross-references it against the
CAP-WK.* sub-cap inventory declared in the architecture model's capabilities
buckets. Emits Cards flagging:

* sub-caps with **zero** walks (uncovered)
* walks that audit **non-existent** sub-caps (dangling refs)
* sub-caps that appear multiple times (informational only)

This is a Python meta-walk, not a declarative WalkSpec, because its subject
is the WalkSpec YAMLs on disk rather than entities in the model graph.
Realizes ``CAP-WK.meta-coverage`` (see capabilities.v3.yaml).

Output shape mirrors the declarative walk runner: ``{walk_id, audits, cards}``.
Cards are deterministically ordered (verdict severity, then subject id).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from architecture_model.walks.spec.loader import (
    WalkSpec,
    load_walk_specs_from_dir,
)

__all__ = [
    "CoverageCard",
    "CoverageReport",
    "audit_walk_coverage",
    "collect_cap_wk_subcaps",
]

# Deterministic verdict severity (worst first for card ordering).
_VERDICT_ORDER = {
    "dangling-ref": 0,
    "uncovered": 1,
    "duplicate-walk": 2,
    "covered": 3,
}


@dataclass(frozen=True)
class CoverageCard:
    """One meta-coverage finding.

    ``subject`` is either a CAP-WK.* sub-cap id (uncovered / covered /
    duplicate-walk) or a WALK-* id (dangling-ref). ``walks`` lists the
    WalkSpec ids that audit ``subject`` (empty for uncovered).
    """

    subject: str
    verdict: str  # covered | uncovered | dangling-ref | duplicate-walk
    walks: tuple[str, ...]
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "verdict": self.verdict,
            "walks": list(self.walks),
            "detail": self.detail,
        }


@dataclass(frozen=True)
class CoverageReport:
    """Meta-walk output. Matches ``run_walk`` envelope shape."""

    walk_id: str = "META-walk-coverage"
    audits: tuple[str, ...] = ("CAP-WK.meta-coverage",)
    cards: tuple[CoverageCard, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "walk_id": self.walk_id,
            "audits": list(self.audits),
            "cards": [c.to_dict() for c in self.cards],
        }

    @property
    def uncovered(self) -> tuple[CoverageCard, ...]:
        return tuple(c for c in self.cards if c.verdict == "uncovered")

    @property
    def dangling(self) -> tuple[CoverageCard, ...]:
        return tuple(c for c in self.cards if c.verdict == "dangling-ref")


def collect_cap_wk_subcaps(model: dict[str, Any]) -> set[str]:
    """Extract CAP-WK.* sub-cap ids from a v3 model dict.

    Sub-caps live under ``entities.capabilities`` (canonical v3 shape) or
    under top-level ``capabilities`` (fragment shape). Matches on id prefix
    ``CAP-WK.`` — the umbrella ``CAP-WK`` itself is excluded (it's the
    parent, not a walk realization).
    """
    subcaps: set[str] = set()

    def _scan(caps: Any) -> None:
        if not isinstance(caps, list):
            return
        for cap in caps:
            if not isinstance(cap, dict):
                continue
            cid = cap.get("id")
            if isinstance(cid, str) and cid.startswith("CAP-WK.") and cid != "CAP-WK":
                subcaps.add(cid)

    entities = model.get("entities") or {}
    if isinstance(entities, dict):
        _scan(entities.get("capabilities"))
    _scan(model.get("capabilities"))
    # Also support "buckets" fragment shape used by some sub-models.
    for bucket in model.get("buckets") or []:
        if isinstance(bucket, dict):
            _scan(bucket.get("capabilities"))
    return subcaps


def audit_walk_coverage(
    walks_dir: Path,
    model: dict[str, Any],
) -> CoverageReport:
    """Run the meta-walk-coverage audit.

    Args:
        walks_dir: directory containing WalkSpec ``*.v3.yaml`` files.
        model: v3 architecture model dict (with ``buckets`` key).

    Returns:
        CoverageReport with cards sorted by (verdict severity, subject id).
    """
    specs: list[WalkSpec] = load_walk_specs_from_dir(walks_dir)
    subcaps = collect_cap_wk_subcaps(model)

    # walk-id → tuple(audits); subject (audited sub-cap) → list of walk ids.
    subject_to_walks: dict[str, list[str]] = {}
    for spec in specs:
        for audit in spec.audits:
            subject_to_walks.setdefault(audit, []).append(spec.id)

    cards: list[CoverageCard] = []

    # 1. Dangling refs: audited subjects that are not real CAP-WK sub-caps.
    #    (Non-CAP-WK audits like CAP-PB / CAP-SL / CAP-DF are legitimate cross-
    #    capability audits, not dangling — skip those.)
    for subject in sorted(subject_to_walks):
        if subject.startswith("CAP-WK.") and subject not in subcaps:
            cards.append(
                CoverageCard(
                    subject=subject,
                    verdict="dangling-ref",
                    walks=tuple(sorted(subject_to_walks[subject])),
                    detail=(
                        f"WalkSpec(s) audit {subject!r} but no matching sub-cap "
                        "declared in capabilities.v3.yaml"
                    ),
                )
            )

    # 2. Coverage: for every CAP-WK.* sub-cap, check for at least one walk.
    for subcap in sorted(subcaps):
        walks_for = sorted(subject_to_walks.get(subcap, []))
        if not walks_for:
            cards.append(
                CoverageCard(
                    subject=subcap,
                    verdict="uncovered",
                    walks=(),
                    detail=f"{subcap} has no WalkSpec realizing it",
                )
            )
        elif len(walks_for) > 1:
            cards.append(
                CoverageCard(
                    subject=subcap,
                    verdict="duplicate-walk",
                    walks=tuple(walks_for),
                    detail=(
                        f"{subcap} is audited by {len(walks_for)} walks "
                        "(informational — kind-dispatched realize is expected)"
                    ),
                )
            )
        else:
            cards.append(
                CoverageCard(
                    subject=subcap,
                    verdict="covered",
                    walks=tuple(walks_for),
                    detail=f"{subcap} realized by {walks_for[0]}",
                )
            )

    cards.sort(key=lambda c: (_VERDICT_ORDER.get(c.verdict, 99), c.subject))
    return CoverageReport(cards=tuple(cards))


# Convenience for CLI / dict-based consumers.
def audit_walk_coverage_dict(walks_dir: Path, model: dict[str, Any]) -> dict[str, Any]:
    return asdict(audit_walk_coverage(walks_dir, model))
