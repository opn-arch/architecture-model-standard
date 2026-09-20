"""architecture_model.walks.meta.walk_coverage — meta-walk over the walk substrate.

Scans ``.architecture/model/walks/*.v3.yaml`` (or any directory of WalkSpecs)
**and** Python meta-walks under ``src/architecture_model/walks/meta/*.py``,
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

**Python meta-walk discovery (L22).** Meta-walks written in Python (rather
than as declarative WalkSpecs) are discovered by parsing the module
docstring for a ``Realizes ``CAP-WK.<id>``` marker. Each discovered Python
meta-walk is treated as a walk whose id is ``META-<module_name>`` and whose
``audits`` list contains the single referenced sub-cap. This closes the L21
follow-on gap where Python meta-walks were invisible to the coverage audit.
"""

from __future__ import annotations

import re
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
    "discover_python_meta_walks",
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


_REALIZES_RE = re.compile(r"Realizes\s+``(CAP-WK\.[\w-]+)``")


def discover_python_meta_walks(python_meta_dir: Path) -> list[dict[str, Any]]:
    """Discover Python meta-walks in ``python_meta_dir`` (L22).

    Scans every ``*.py`` file (excluding ``__init__.py`` and dunder-only
    filenames) for a module docstring containing the marker
    ``Realizes ``CAP-WK.<id>``` (backtick-quoted, RST style). Each match
    yields a record ``{"walk_id": "META-<module_name>", "audits":
    ["CAP-WK.<id>"], "path": Path(...)}``.

    The walk_coverage.py module itself is intentionally included when
    scanning its own directory — it declares
    ``Realizes ``CAP-WK.meta-coverage``` at the top of the file — so
    the meta-coverage sub-cap is auto-covered by its own Python
    implementation.

    Discovery uses plain-text docstring parsing (regex), not import
    machinery, so a module with a syntax error still shows up if its
    docstring contains the marker. Deterministic ordering: sorted by
    module filename.
    """
    if not python_meta_dir.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for py_path in sorted(python_meta_dir.glob("*.py")):
        if py_path.name.startswith("_"):
            continue
        try:
            text = py_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        # Only look at the module-level docstring — extract the first
        # triple-quoted string. Simple heuristic: find `"""..."""` at
        # start-of-file (after an optional shebang/encoding line).
        docstring = _extract_module_docstring(text)
        if not docstring:
            continue
        matches = _REALIZES_RE.findall(docstring)
        if not matches:
            continue
        # Deduplicate while preserving order.
        seen: set[str] = set()
        audits: list[str] = []
        for cap in matches:
            if cap not in seen:
                seen.add(cap)
                audits.append(cap)
        walk_id = f"META-{py_path.stem}"
        records.append(
            {"walk_id": walk_id, "audits": audits, "path": py_path}
        )
    return records


def _extract_module_docstring(text: str) -> str | None:
    """Return the module-level docstring (first triple-quoted string) or None."""
    # Find the first """ or ''' after optional leading comments/blank lines.
    for quote in ('"""', "'''"):
        idx = text.find(quote)
        if idx == -1:
            continue
        end = text.find(quote, idx + 3)
        if end == -1:
            continue
        return text[idx + 3 : end]
    return None


def audit_walk_coverage(
    walks_dir: Path,
    model: dict[str, Any],
    python_meta_dir: Path | None = None,
) -> CoverageReport:
    """Run the meta-walk-coverage audit.

    Args:
        walks_dir: directory containing WalkSpec ``*.v3.yaml`` files.
        model: v3 architecture model dict (with ``buckets`` key).
        python_meta_dir: directory of Python meta-walks (``*.py``). Defaults
            to the packaged ``architecture_model.walks.meta`` directory when
            omitted. Each module whose docstring contains the marker
            ``Realizes ``CAP-WK.<id>``` is treated as a walk realizing that
            sub-cap (L22).

    Returns:
        CoverageReport with cards sorted by (verdict severity, subject id).
    """
    specs: list[WalkSpec] = load_walk_specs_from_dir(walks_dir)
    subcaps = collect_cap_wk_subcaps(model)

    if python_meta_dir is None:
        python_meta_dir = Path(__file__).parent
    py_meta_walks = discover_python_meta_walks(python_meta_dir)

    # walk-id → tuple(audits); subject (audited sub-cap) → list of walk ids.
    subject_to_walks: dict[str, list[str]] = {}
    for spec in specs:
        for audit in spec.audits:
            subject_to_walks.setdefault(audit, []).append(spec.id)
    for meta in py_meta_walks:
        for audit in meta["audits"]:
            subject_to_walks.setdefault(audit, []).append(meta["walk_id"])

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
