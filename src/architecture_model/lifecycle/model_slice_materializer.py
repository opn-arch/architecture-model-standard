"""ModelSlice materializer: resolve a :class:`ModelSlice` contract into a
concrete :class:`MaterializedSlice` fragment.

Purpose
-------
A :class:`ModelSlice` is a *contract* — selectors + closure policy. This
module realizes that contract against an :class:`ArchitecturePackage` by
loading the package's model (and, for ``scope == "descendants"``, its
descendants' models), applying selectors + curation, closing the
relationship set under the configured closure policy, and packaging the
result as a deterministic, content-addressable :class:`MaterializedSlice`.

Commit-1 scope
--------------
This commit implements ``scope`` ∈ {``local``, ``descendants``} and
``shared_refs == "none"``. ``scope == "federated"`` and
``shared_refs`` ∈ {``explicit``, ``transitive``} raise
:class:`NotImplementedError` — they land in T14 commit 2.

Invariants
----------
* The returned :class:`MaterializedSlice` is deterministic given a fixed
  model + slice + wall-clock: fragment entities and relationships are
  sorted by id / (from,to,type) so two calls yield equal fragments.
* The dangling-relationship bug in the legacy
  :mod:`architecture_model.core.slicer` (which keeps a relationship if
  *either* endpoint is in the fragment) does **not** occur here: under
  ``closure == "strict"`` a relationship is retained only when *both*
  endpoints are in the fragment; otherwise it is dropped and a
  ``SLICE.DANGLING_STRIPPED`` warning is recorded.
* ``curation.include`` re-adds entities that selectors dropped; it is
  applied *after* ``curation.exclude`` so a redundant include+exclude
  pair yields exclusion (exclude wins on precedence).
* ``curation.redactions`` clears descriptive fields (``description``,
  ``rationale``, ``intent``) but preserves identity (``id``, ``name``,
  ``kind``, ``status``).

Thread safety
-------------
Pure functions; no module-level mutable state. :class:`MaterializedSlice`
is a frozen dataclass. The materializer is safe to call concurrently
provided the underlying :class:`ArchitecturePackage` tree is not being
mutated.

Error taxonomy
--------------
* :class:`NotImplementedError` — federated scope / shared_refs modes not
  yet implemented.
* :class:`FileNotFoundError` — the package's ``model_ref`` cannot be
  resolved to a file (bubbled from :func:`load_model`).
* :class:`ValueError` — a malformed selector value (bubbled from
  underlying utilities).

Warnings are non-fatal and surfaced via :attr:`MaterializedSlice.warnings`.
"""
from __future__ import annotations

import copy
import fnmatch
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from architecture_model.core.parser import load_model
from architecture_model.core.types import (
    ArchitectureModel,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
)
from architecture_model.lifecycle.model_slice import ModelSlice
from architecture_model.lifecycle.package import (
    ArchitecturePackage,
    iter_descendants,
)
from architecture_model.lifecycle.serialization import digest as _digest

MATERIALIZER_VERSION = "1.0.0"

# Ordered so we always iterate entity kinds deterministically.
_ENTITY_FIELDS: tuple[str, ...] = (
    "actors",
    "capabilities",
    "behaviors",
    "interfaces",
    "constraints",
    "layers",
    "components",
    "systems",
    "data",
    "events",
    "resources",
    "environments",
    "quality_attributes",
    "decisions",
    "lifecycles",
    "requirements",
    "external_systems",
)

# Both singular and plural aliases resolve to a canonical plural field.
_KIND_ALIASES: dict[str, str] = {}
for _plural in _ENTITY_FIELDS:
    _KIND_ALIASES[_plural] = _plural
    # crude singularizer covering the 17 fields we care about
    if _plural.endswith("ies"):
        _KIND_ALIASES[_plural[:-3] + "y"] = _plural
    elif _plural.endswith("s") and not _plural.endswith("ss"):
        _KIND_ALIASES[_plural[:-1]] = _plural

_TRANSITIVE_MAX_DEPTH = 3


@dataclass(frozen=True)
class MaterializationWarning:
    code: str
    message: str
    entity_id: str = ""


@dataclass(frozen=True)
class MaterializedSlice:
    slice_id: str
    architecture_id: str
    model_revision: str
    model_fragment: ArchitectureModel
    stub_entity_ids: tuple[str, ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[MaterializationWarning, ...] = ()

    def to_dict(self) -> dict:
        """Serialize to the shape expected by ai.validators (fragment key).

        Enables straight-line materialize → validate flows: validators look up
        ``sl["fragment"]["entities"]``, so ``model_fragment`` is serialized
        under the ``fragment`` key rather than at the top level.
        """
        from dataclasses import asdict

        return {
            "slice_id": self.slice_id,
            "architecture_id": self.architecture_id,
            "model_revision": self.model_revision,
            "fragment": self.model_fragment.to_dict(),
            "stub_entity_ids": list(self.stub_entity_ids),
            "provenance": dict(self.provenance),
            "warnings": [asdict(w) for w in self.warnings],
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def materialize(
    slice: ModelSlice,
    pkg: ArchitecturePackage,
    *,
    resolve_ref: Callable[[str], ArchitectureModel] | None = None,
) -> MaterializedSlice:
    """Materialize ``slice`` against ``pkg``.

    ``resolve_ref`` is accepted for API stability but ignored in this
    commit; it will be honoured when federated scope lands in commit 2.
    """
    if slice.scope == "federated" and resolve_ref is None:
        raise ValueError("federated scope requires resolve_ref callable")

    # -- 1. Load model(s) ---------------------------------------------------
    base_model = _load_pkg_model(pkg)
    merged = _clone_model(base_model)
    local_ids: set[str] = set(_all_ids(merged.entities))
    source_pkg_by_id: dict[str, str] = {
        eid: pkg.architecture_id for eid in local_ids
    }

    warnings: list[MaterializationWarning] = []
    federated_sources: dict[str, str] = {}  # ref_id -> source_model_digest

    if slice.scope == "descendants":
        for child in iter_descendants(pkg, include_self=False):
            try:
                child_model = _load_pkg_model(child)
            except FileNotFoundError:
                continue
            _merge_into(merged, child_model, source_pkg_by_id, child.architecture_id)

    # -- 1b. shared_refs: descendants filter --------------------------------
    if slice.scope == "descendants" and slice.shared_refs in ("explicit", "transitive"):
        child_origin = {
            eid for eid, src in source_pkg_by_id.items()
            if src != pkg.architecture_id
        }
        if slice.shared_refs == "explicit":
            allow = set(slice.selectors.entity_ids or [])
        else:  # transitive: 1-hop reachable from local via any rel
            allow = set()
            for rel in merged.relationships:
                if rel.from_id in local_ids and rel.to_id in child_origin:
                    allow.add(rel.to_id)
                if rel.to_id in local_ids and rel.from_id in child_origin:
                    allow.add(rel.from_id)
        drop = child_origin - allow
        if drop:
            for f in _ENTITY_FIELDS:
                lst = getattr(merged.entities, f)
                lst[:] = [e for e in lst if e.id not in drop]
            merged.relationships = [
                r for r in merged.relationships
                if r.from_id not in drop and r.to_id not in drop
            ]
            for eid in drop:
                source_pkg_by_id.pop(eid, None)

    # -- 1c. shared_refs: federated resolution ------------------------------
    if slice.scope == "federated" and slice.shared_refs in ("explicit", "transitive"):
        to_resolve: list[str] = []
        seen: set[str] = set()
        # Explicit: pull ids from selectors.entity_ids not in local.
        if slice.selectors.entity_ids:
            for eid in slice.selectors.entity_ids:
                if eid not in local_ids and eid not in seen:
                    to_resolve.append(eid)
                    seen.add(eid)
        # Transitive: also follow 1 hop from local via local rels endpoints.
        if slice.shared_refs == "transitive":
            extra: set[str] = set()
            for rel in base_model.relationships:
                for endpoint in (rel.from_id, rel.to_id):
                    if endpoint not in local_ids and endpoint not in seen:
                        extra.add(endpoint)
            for eid in sorted(extra):
                to_resolve.append(eid)
                seen.add(eid)
        for eid in sorted(to_resolve):
            try:
                ext_model = resolve_ref(eid)  # type: ignore[misc]
            except KeyError as exc:
                warnings.append(
                    MaterializationWarning(
                        code="SLICE.UNRESOLVED_REF",
                        message=f"resolve_ref({eid!r}) raised KeyError: {exc!s}",
                        entity_id=eid,
                    )
                )
                continue
            if ext_model is None:
                warnings.append(
                    MaterializationWarning(
                        code="SLICE.UNRESOLVED_REF",
                        message=f"resolve_ref({eid!r}) returned None",
                        entity_id=eid,
                    )
                )
                continue
            found = _find_entity(ext_model, eid)
            if found is None:
                warnings.append(
                    MaterializationWarning(
                        code="SLICE.UNRESOLVED_REF",
                        message=(
                            f"resolve_ref({eid!r}) returned model without id {eid!r}"
                        ),
                        entity_id=eid,
                    )
                )
                continue
            field_name, ent = found
            dst_list = getattr(merged.entities, field_name)
            if not any(e.id == eid for e in dst_list):
                dst_list.append(copy.deepcopy(ent))
            source_pkg_by_id.setdefault(eid, f"ref:{eid}")
            federated_sources[eid] = _digest(_model_to_hashable(ext_model))

    source_digest = _digest(_model_to_hashable(merged))

    # -- 2. Select --------------------------------------------------------
    selected_ids, selector_warnings = _apply_selectors(merged, slice)
    warnings.extend(selector_warnings)

    # -- 3. Curation.exclude ----------------------------------------------
    if slice.curation.exclude:
        for eid in slice.curation.exclude:
            selected_ids.discard(eid)

    # -- 4. Curation.include (force-add from merged model) ----------------
    if slice.curation.include:
        for eid in slice.curation.include:
            if eid in _all_ids(merged.entities):
                selected_ids.add(eid)
            else:
                warnings.append(
                    MaterializationWarning(
                        code="SLICE.SELECTOR_UNMATCHED",
                        message=f"curation.include: id {eid!r} not present in source model",
                        entity_id=eid,
                    )
                )

    # -- 5. Closure -------------------------------------------------------
    closure = slice.closure
    stub_ids: tuple[str, ...] = ()
    if closure == "transitive":
        depth = int(slice.parameters.get("transitive_depth", 1))
        depth = max(0, min(depth, _TRANSITIVE_MAX_DEPTH))
        selected_ids = _bfs_expand(selected_ids, merged.relationships, depth)

    fragment = _project(merged, selected_ids)

    if closure == "strict":
        kept_rels: list[Relationship] = []
        for rel in merged.relationships:
            if rel.from_id in selected_ids and rel.to_id in selected_ids:
                kept_rels.append(copy.deepcopy(rel))
            elif rel.from_id in selected_ids or rel.to_id in selected_ids:
                warnings.append(
                    MaterializationWarning(
                        code="SLICE.DANGLING_STRIPPED",
                        message=(
                            f"dropped {rel.type.value} {rel.from_id!r}->{rel.to_id!r}: "
                            "endpoint outside fragment"
                        ),
                    )
                )
        fragment.relationships = kept_rels
    elif closure == "boundary-stubs":
        kept_rels = []
        new_stubs: list[str] = []
        for rel in merged.relationships:
            in_from = rel.from_id in selected_ids
            in_to = rel.to_id in selected_ids
            if in_from or in_to:
                kept_rels.append(copy.deepcopy(rel))
                for endpoint in (rel.from_id, rel.to_id):
                    if endpoint in selected_ids:
                        continue
                    if endpoint in new_stubs:
                        continue
                    added = _add_stub(
                        fragment,
                        merged,
                        endpoint,
                        origin_ref=source_pkg_by_id.get(endpoint, pkg.architecture_id),
                    )
                    if added:
                        new_stubs.append(endpoint)
        fragment.relationships = kept_rels
        stub_ids = tuple(sorted(new_stubs))
    elif closure == "transitive":
        # Only keep relationships fully inside expanded fragment.
        fragment.relationships = [
            copy.deepcopy(r)
            for r in merged.relationships
            if r.from_id in selected_ids and r.to_id in selected_ids
        ]

    # -- 6. Redactions ----------------------------------------------------
    if slice.curation.redactions:
        redaction_set = set(slice.curation.redactions)
        for field_name in _ENTITY_FIELDS:
            for ent in getattr(fragment.entities, field_name, []):
                if ent.id in redaction_set:
                    ent.description = ""
                    if hasattr(ent, "rationale"):
                        ent.rationale = ""
                    if hasattr(ent, "intent"):
                        ent.intent = ""

    # -- 7. Sort for determinism -----------------------------------------
    _sort_fragment(fragment)

    # -- 8. Provenance ----------------------------------------------------
    provenance: dict[str, Any] = {
        "selectors_applied": slice.selectors.model_dump(exclude_none=True),
        "closure": slice.closure,
        "shared_refs": slice.shared_refs,
        "scope": slice.scope,
        "source_model_digest": source_digest,
        "source_pkg_id": pkg.architecture_id,
        "produced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "materializer_version": MATERIALIZER_VERSION,
        "federated_sources": [
            {"ref_id": rid, "source_model_digest": federated_sources[rid]}
            for rid in sorted(federated_sources)
        ],
    }

    warnings_tuple = tuple(sorted(warnings, key=lambda w: (w.code, w.entity_id, w.message)))

    return MaterializedSlice(
        slice_id=slice.id,
        architecture_id=slice.architecture_id,
        model_revision=slice.model_revision,
        model_fragment=fragment,
        stub_entity_ids=stub_ids,
        provenance=provenance,
        warnings=warnings_tuple,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_pkg_model(pkg: ArchitecturePackage) -> ArchitectureModel:
    if pkg.root is None:
        raise ValueError(
            f"package {pkg.architecture_id!r} has no root; load via load_package()"
        )
    model_path = pkg.root / pkg.model_ref
    return load_model(model_path)


def _clone_model(model: ArchitectureModel) -> ArchitectureModel:
    return ArchitectureModel(
        meta=copy.deepcopy(model.meta),
        entities=copy.deepcopy(model.entities),
        relationships=[copy.deepcopy(r) for r in model.relationships],
    )


def _all_ids(entities: Entities) -> set[str]:
    ids: set[str] = set()
    for f in _ENTITY_FIELDS:
        for ent in getattr(entities, f, []):
            ids.add(ent.id)
    return ids


def _merge_into(
    dst: ArchitectureModel,
    src: ArchitectureModel,
    source_pkg_by_id: dict[str, str],
    src_pkg_id: str,
) -> None:
    """Merge ``src`` into ``dst`` (dedupe by id / (from,to,type))."""
    for f in _ENTITY_FIELDS:
        dst_list = getattr(dst.entities, f)
        existing = {e.id for e in dst_list}
        for ent in getattr(src.entities, f, []):
            if ent.id in existing:
                continue
            dst_list.append(copy.deepcopy(ent))
            existing.add(ent.id)
            source_pkg_by_id.setdefault(ent.id, src_pkg_id)
    seen_rels = {(r.from_id, r.to_id, r.type.value) for r in dst.relationships}
    for rel in src.relationships:
        key = (rel.from_id, rel.to_id, rel.type.value)
        if key in seen_rels:
            continue
        dst.relationships.append(copy.deepcopy(rel))
        seen_rels.add(key)


def _apply_selectors(
    model: ArchitectureModel, slice: ModelSlice
) -> tuple[set[str], list[MaterializationWarning]]:
    warnings: list[MaterializationWarning] = []
    sel = slice.selectors
    selected: set[str] = set()

    # Track (entity_id, entity_field) tuples so we can intersect predicates.
    all_pairs: list[tuple[str, str, Any]] = []
    for f in _ENTITY_FIELDS:
        for ent in getattr(model.entities, f, []):
            all_pairs.append((ent.id, f, ent))

    def keep(_id: str, _field: str, ent: Any) -> bool:
        if sel.entity_ids is not None and _id not in sel.entity_ids:
            return False
        if sel.entity_kinds is not None:
            canonical = {_KIND_ALIASES.get(k, k) for k in sel.entity_kinds}
            if _field not in canonical:
                return False
        if sel.layers is not None:
            layer_val = getattr(ent, "layer", None)
            if _field == "layers":
                if _id not in sel.layers:
                    return False
            elif layer_val not in sel.layers:
                return False
        if sel.fblocks is not None:
            fb = getattr(ent, "source_block", None)
            tags = list(getattr(ent, "tags", []) or [])
            if fb in sel.fblocks or any(t in sel.fblocks for t in tags):
                pass
            else:
                return False
        if sel.tags is not None:
            tags = list(getattr(ent, "tags", []) or [])
            if not any(t in sel.tags for t in tags):
                return False
        if sel.paths is not None:
            files: list[str] = list(getattr(ent, "files", []) or [])
            source_file = getattr(ent, "source_file", None)
            if source_file:
                files.append(source_file)
            if not any(
                fnmatch.fnmatchcase(fp, pat) for fp in files for pat in sel.paths
            ):
                return False
        return True

    for _id, _field, ent in all_pairs:
        if keep(_id, _field, ent):
            selected.add(_id)

    if sel.entity_ids is not None:
        missing = set(sel.entity_ids) - {p[0] for p in all_pairs}
        for m in sorted(missing):
            warnings.append(
                MaterializationWarning(
                    code="SLICE.SELECTOR_UNMATCHED",
                    message=f"entity_ids: id {m!r} not present in source model",
                    entity_id=m,
                )
            )

    return selected, warnings


def _project(model: ArchitectureModel, selected_ids: set[str]) -> ArchitectureModel:
    new_entities = Entities()
    for f in _ENTITY_FIELDS:
        keep = [
            copy.deepcopy(e) for e in getattr(model.entities, f, []) if e.id in selected_ids
        ]
        setattr(new_entities, f, keep)
    return ArchitectureModel(
        meta=copy.deepcopy(model.meta),
        entities=new_entities,
        relationships=[],  # closure phase decides
    )


def _bfs_expand(
    seeds: set[str], rels: list[Relationship], depth: int
) -> set[str]:
    frontier = set(seeds)
    reached = set(seeds)
    adjacency: dict[str, set[str]] = {}
    for r in rels:
        adjacency.setdefault(r.from_id, set()).add(r.to_id)
        adjacency.setdefault(r.to_id, set()).add(r.from_id)
    for _ in range(depth):
        next_frontier: set[str] = set()
        for node in frontier:
            for neigh in adjacency.get(node, ()):
                if neigh not in reached:
                    next_frontier.add(neigh)
        if not next_frontier:
            break
        reached |= next_frontier
        frontier = next_frontier
    return reached


def _find_entity(
    model: ArchitectureModel, entity_id: str
) -> tuple[str, Any] | None:
    for f in _ENTITY_FIELDS:
        for ent in getattr(model.entities, f, []):
            if ent.id == entity_id:
                return f, ent
    return None


def _add_stub(
    fragment: ArchitectureModel,
    source_model: ArchitectureModel,
    entity_id: str,
    *,
    origin_ref: str,
) -> bool:
    """Add a stub of ``entity_id`` to ``fragment``. Returns True if added."""
    found = _find_entity(source_model, entity_id)
    if found is None:
        # Unknown entity — cannot stub without kind. Skip.
        return False
    field_name, ent = found
    stub = copy.deepcopy(ent)
    # mark as stub via the shared extensions dict
    ext = dict(getattr(stub, "extensions", {}) or {})
    ext["stub"] = True
    ext["origin_ref"] = origin_ref
    stub.extensions = ext
    getattr(fragment.entities, field_name).append(stub)
    return True


def _sort_fragment(model: ArchitectureModel) -> None:
    for f in _ENTITY_FIELDS:
        lst = getattr(model.entities, f, None)
        if lst:
            lst.sort(key=lambda e: e.id)
    model.relationships.sort(key=lambda r: (r.from_id, r.to_id, r.type.value))


def _model_to_hashable(model: ArchitectureModel) -> dict:
    """Small deterministic projection of a model for digesting.

    We avoid full serialization: only ids + rel triples, sorted."""
    return {
        "entities": sorted(_all_ids(model.entities)),
        "relationships": sorted(
            [r.from_id, r.to_id, r.type.value] for r in model.relationships
        ),
        "meta_project": model.meta.project,
        "meta_schema_version": model.meta.schema_version,
    }


__all__ = [
    "MaterializationWarning",
    "MaterializedSlice",
    "materialize",
    "MATERIALIZER_VERSION",
]
