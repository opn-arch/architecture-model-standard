"""Slice anchor for viewer panels — deterministic (model, files, artifacts) scope per view.

See docs/plans/2026-09-10-track4-slice-anchor-design.md for full design.
"""
from __future__ import annotations

from dataclasses import dataclass

from architecture_model.core.types import ArchitectureModel


VIEW_TO_ARTIFACT: dict[str, str] = {
    "conops": "conops",
    "functional": "functional-architecture",
    "logical": "logical-architecture",
    "use_cases": "use-cases",
}

ARTIFACT_TO_DOC: dict[str, str] = {
    "conops": ".architecture-models/docs/se/conops.md",
    "functional-architecture": ".architecture-models/docs/se/functional-analysis.md",
    "logical-architecture": ".architecture-models/docs/se/logical-architecture.md",
    "use-cases": ".architecture-models/docs/se/use-cases.md",
}


@dataclass(frozen=True)
class SliceAnchor:
    view_name: str
    artifact_name: str
    model: ArchitectureModel
    files: tuple[str, ...]
    artifacts: tuple[str, ...]
