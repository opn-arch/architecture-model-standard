"""Slice anchor for viewer panels — deterministic (model, files, artifacts) scope per view.

See docs/plans/2026-09-10-track4-slice-anchor-design.md for full design.
"""
from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from architecture_model.core.types import ArchitectureModel, RelationType

_log = logging.getLogger(__name__)


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


_CLOSURE_TYPES = frozenset({
    RelationType.REALIZES,
    RelationType.CONTAINS,
    RelationType.DEPENDS_ON,
})


def _all_entities(model: ArchitectureModel):
    """Yield (kind, entity) for every entity in the model."""
    for kind in (
        "actors", "capabilities", "behaviors", "interfaces",
        "constraints", "layers", "components", "systems",
    ):
        for entity in getattr(model.entities, kind, []) or []:
            yield kind, entity


def apply_one_hop_closure(full: ArchitectureModel, sliced: ArchitectureModel) -> ArchitectureModel:
    """Expand sliced with one hop of realizes/contains/depends-on neighbors from full.

    One pass, no transitive expansion. Deterministic by sorted iteration.
    """
    slice_ids: set[str] = set()
    for _, entity in _all_entities(sliced):
        slice_ids.add(entity.id)

    id_to_kind_entity: dict[str, tuple[str, object]] = {}
    for kind, entity in _all_entities(full):
        id_to_kind_entity[entity.id] = (kind, entity)

    to_add: set[str] = set()
    rels_to_add: list = []
    sorted_rels = sorted(
        (r for r in full.relationships if r.type in _CLOSURE_TYPES),
        key=lambda r: (r.type.value, r.from_id, r.to_id),
    )
    for rel in sorted_rels:
        f, t = rel.from_id, rel.to_id
        if f in slice_ids and t not in slice_ids and t in id_to_kind_entity:
            to_add.add(t)
            rels_to_add.append(rel)
        elif t in slice_ids and f not in slice_ids and f in id_to_kind_entity:
            to_add.add(f)
            rels_to_add.append(rel)

    result = deepcopy(sliced)
    for eid in sorted(to_add):
        kind, entity = id_to_kind_entity[eid]
        bucket = getattr(result.entities, kind)
        bucket.append(deepcopy(entity))
    for rel in rels_to_add:
        result.relationships.append(deepcopy(rel))
    return result


def _derive_files(model: ArchitectureModel) -> tuple[str, ...]:
    seen: set[str] = set()
    for comp in model.entities.components or []:
        for sf in (getattr(comp, "files", None) or []):
            seen.add(sf)
    return tuple(sorted(seen))


def _derive_artifacts(artifact_name: str, repo_path: Path) -> tuple[str, ...]:
    if not artifact_name:
        return ()
    found: set[str] = set()
    primary = ARTIFACT_TO_DOC.get(artifact_name)
    if primary and (repo_path / primary).is_file():
        found.add(primary)
    se_dir = repo_path / ".architecture-models" / "docs" / "se"
    if se_dir.is_dir():
        try:
            import yaml  # type: ignore
        except ImportError:
            yaml = None  # type: ignore
        if yaml is not None:
            for md in sorted(se_dir.glob("*.md")):
                try:
                    text = md.read_text(encoding="utf-8")
                    if text.startswith("---\n"):
                        end = text.find("\n---", 4)
                        if end != -1:
                            fm = yaml.safe_load(text[4:end]) or {}
                            if isinstance(fm, dict) and fm.get("artifact") == artifact_name:
                                rel = md.relative_to(repo_path).as_posix()
                                found.add(rel)
                except Exception:
                    continue
    return tuple(sorted(found))


def build_slice_anchor(
    model: ArchitectureModel,
    view_name: str,
    repo_path: Path,
) -> SliceAnchor:
    """Compute the deterministic SliceAnchor for a viewer panel view name."""
    from architecture_model.core.slicer import slice_for_artifact

    artifact_name = VIEW_TO_ARTIFACT.get(view_name, "")
    if not artifact_name:
        _log.warning("viewer: no slicer mapping for view=%s; falling back to full model", view_name)
        return SliceAnchor(
            view_name=view_name,
            artifact_name="",
            model=deepcopy(model),
            files=(),
            artifacts=(),
        )
    sliced = slice_for_artifact(model, artifact_name)
    anchored = apply_one_hop_closure(model, sliced)
    files = _derive_files(anchored)
    artifacts = _derive_artifacts(artifact_name, Path(repo_path))
    _log.info(
        "viewer: anchor computed view=%s entities=%d files=%d artifacts=%d",
        view_name,
        sum(1 for _ in _all_entities(anchored)),
        len(files),
        len(artifacts),
    )
    return SliceAnchor(
        view_name=view_name,
        artifact_name=artifact_name,
        model=anchored,
        files=files,
        artifacts=artifacts,
    )
