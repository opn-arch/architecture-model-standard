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
from architecture_model.core.slicer import slice_by_entity
from architecture_model.core.types import (
    ArchitectureModel,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
)
from architecture_model.lifecycle.model_slice import ModelSlice, parse_entity_scope
from architecture_model.lifecycle.package import (
    ArchitecturePackage,
    iter_descendants,
)
from architecture_model.lifecycle.serialization import digest as _digest
from architecture_model.manifest.types import (
    ClassInfo,
    FunctionInfo,
    InterfaceEdge,
    ModuleInfo,
)

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
class ManifestFunction:
    """A manifest function tagged with its source file (Phase 2 Task 9)."""

    file: str
    info: FunctionInfo


@dataclass(frozen=True)
class ManifestClass:
    """A manifest class tagged with its source file (Phase 2 Task 9)."""

    file: str
    info: ClassInfo


@dataclass(frozen=True)
class ManifestFragment:
    """Bounded projection of a reality manifest (Phase 2 Task 9).

    Populated by :func:`materialize` when the slice carries
    ``SupplementaryRef(kind="manifest")``. Contains only modules whose
    ``file`` is listed on a component present in the fragment's scope,
    plus imports whose endpoints are both in-scope. ``functions`` and
    ``classes`` are flat views over the retained modules for the benefit
    of family-6 projectors (CLI reference, API reference, plugin guide).
    """

    modules: tuple[ModuleInfo, ...] = ()
    functions: tuple[ManifestFunction, ...] = ()
    classes: tuple[ManifestClass, ...] = ()
    imports: tuple[InterfaceEdge, ...] = ()


@dataclass(frozen=True)
class ModelRevisionFragment:
    """A single revision snapshot within a temporal slice (Phase 2 Task 12).

    ``revision`` is a 7-digit generation id (e.g. ``"0000003"``);
    ``model_fragment`` is the projected model for that generation,
    subject to the same selectors + strict-closure rules as the primary
    fragment. Populated only when the slice carries a ``revision_range``.
    """

    revision: str
    model_fragment: ArchitectureModel


@dataclass(frozen=True)
class MaterializedSlice:
    slice_id: str
    architecture_id: str
    model_revision: str
    model_fragment: ArchitectureModel
    stub_entity_ids: tuple[str, ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[MaterializationWarning, ...] = ()
    manifest_fragment: ManifestFragment | None = None
    supplementary_fragments: dict[str, Any] = field(default_factory=dict)
    revision_series: tuple[ModelRevisionFragment, ...] = ()

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
    view_spec: Any = None,
) -> MaterializedSlice:
    """Materialize ``slice`` against ``pkg``.

    ``resolve_ref`` is accepted for API stability but ignored in this
    commit; it will be honoured when federated scope lands in commit 2.

    ``view_spec`` (Phase 3 Task 6) enables recursion controls on
    entity-scoped slices. When provided together with an ``entity(<id>)``
    scope, ``view_spec.depth`` prunes ``contains`` descendants of the
    scope root beyond N hops and ``view_spec.expand_kinds`` restricts
    which entity kinds are allowed to recurse. Ignored for non-entity
    scopes and when ``view_spec`` is ``None``.
    """
    if slice.scope == "federated" and resolve_ref is None:
        raise ValueError("federated scope requires resolve_ref callable")

    # Detect entity-scoped slice up front (Phase 3 Task 3). ``entity(<id>)``
    # is handled by reducing the base model via ``slice_by_entity`` before
    # the rest of the selection/closure/curation pipeline runs.
    entity_scope_id: str | None = parse_entity_scope(slice.scope)

    # -- 1. Load model(s) ---------------------------------------------------
    base_model = _load_pkg_model(pkg)
    merged = _clone_model(base_model)

    # Entity-scoped slice: reduce ``merged`` to the sub-model rooted at the
    # named entity BEFORE selectors/closure run. Raises KeyError if the id
    # is not present in the base model. Descendants merging and federated
    # resolution are intentionally skipped for entity scope: recursion is
    # expressed by the entity graph itself, not by cross-package walking.
    entity_scope_metadata: dict[str, Any] | None = None
    if entity_scope_id is not None:
        hops = int(slice.parameters.get("hops", 1))
        # Compute scope_chain / parent / peers against the ORIGINAL base
        # model (has ancestors) before reducing to the sub-model.
        entity_scope_metadata = _compute_entity_scope_metadata(
            base_model, entity_scope_id
        )
        merged = slice_by_entity(merged, entity_scope_id, include_hops=hops)

        # Phase 3 Task 6: enforce view_spec.depth + expand_kinds by
        # pruning ``contains`` descendants beyond N hops from the scope
        # root. The child's parent kind gates whether recursion may
        # continue past that node (empty expand_kinds = all kinds
        # recurse). Root is always kept.
        if view_spec is not None:
            merged = _prune_by_depth(
                merged,
                entity_scope_id,
                depth=int(getattr(view_spec, "depth", 1)),
                expand_kinds=tuple(getattr(view_spec, "expand_kinds", ()) or ()),
            )

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
    if entity_scope_id is not None:
        # Entity scope IS the selection: pick every entity from the
        # already-reduced sub-model and skip selector matching entirely.
        selected_ids = set(_all_ids(merged.entities))
        selector_warnings: list[MaterializationWarning] = []
    else:
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

    # -- 7b. Supplementary refs: manifest fragment -----------------------
    manifest_fragment, manifest_warnings = _build_manifest_fragment(
        slice, pkg, fragment
    )
    warnings.extend(manifest_warnings)

    # -- 7c. Supplementary refs: sil / gates / drift / test_results / learning
    supplementary_fragments, sup_warnings = _build_supplementary_fragments(
        slice, pkg
    )
    warnings.extend(sup_warnings)

    # -- 7d. Temporal: revision_series ------------------------------------
    revision_series, rev_warnings = _build_revision_series(slice, pkg)
    warnings.extend(rev_warnings)

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
    if entity_scope_metadata is not None:
        provenance["scope_metadata"] = entity_scope_metadata

    warnings_tuple = tuple(sorted(warnings, key=lambda w: (w.code, w.entity_id, w.message)))

    return MaterializedSlice(
        slice_id=slice.id,
        architecture_id=slice.architecture_id,
        model_revision=slice.model_revision,
        model_fragment=fragment,
        stub_entity_ids=stub_ids,
        provenance=provenance,
        warnings=warnings_tuple,
        manifest_fragment=manifest_fragment,
        supplementary_fragments=supplementary_fragments,
        revision_series=revision_series,
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


def _compute_entity_scope_metadata(
    model: ArchitectureModel, entity_id: str
) -> dict[str, Any]:
    """Compute scope_chain / parent / peers for entity-scoped views.

    Uses the full base ``model`` (which contains ancestors) to walk the
    ``contains`` graph upward from ``entity_id`` to the top of the tree.
    ``scope_chain`` is ``("ROOT", <topmost ancestor>, ..., <entity_id>)``.
    ``parent`` is the immediate parent by ``contains``, or ``None`` when
    ``entity_id`` is a top-level entity. ``peers`` are the other children
    of ``parent`` (excluding ``entity_id``), sorted ascending for
    determinism. ``roll_up`` is ``False`` for Phase 3 Task 4; aggregation
    projectors will flip it later.
    """
    parent_of: dict[str, str] = {}
    children_of: dict[str, list[str]] = {}
    for rel in model.relationships:
        if rel.type != RelationType.CONTAINS:
            continue
        parent_of[rel.to_id] = rel.from_id
        children_of.setdefault(rel.from_id, []).append(rel.to_id)

    parent = parent_of.get(entity_id)

    # Walk upward to build ancestor chain (top -> entity).
    chain: list[str] = [entity_id]
    seen = {entity_id}
    cur = parent
    while cur is not None and cur not in seen:
        chain.append(cur)
        seen.add(cur)
        cur = parent_of.get(cur)
    chain.reverse()

    peers: tuple[str, ...] = ()
    if parent is not None:
        peers = tuple(
            sorted(cid for cid in children_of.get(parent, []) if cid != entity_id)
        )

    # Locate the scoped entity's kind (singular canonical) for downstream
    # projector dispatch (Phase 3 Task 7). Absent when the id is not
    # present in the base model (caller should have failed earlier).
    scope_entity_kind = ""
    for f in _ENTITY_FIELDS:
        for ent in getattr(model.entities, f, []):
            if ent.id == entity_id:
                if f.endswith("ies"):
                    scope_entity_kind = f[:-3] + "y"
                elif f.endswith("s") and not f.endswith("ss"):
                    scope_entity_kind = f[:-1]
                else:
                    scope_entity_kind = f
                break
        if scope_entity_kind:
            break

    # Phase 3 Task 8: reverse-lookup inbound ``depends-on`` edges against
    # the base model. Family-1 entity_page surfaces these as implicit
    # stakeholders even when depth pruning has removed the source
    # entities from the fragment.
    inbound_depends_on: tuple[str, ...] = tuple(
        sorted(
            {
                rel.from_id
                for rel in model.relationships
                if rel.type == RelationType.DEPENDS_ON and rel.to_id == entity_id
            }
        )
    )

    return {
        "scope_chain": ("ROOT", *chain),
        "parent": parent,
        "peers": peers,
        "roll_up": False,
        "scope_entity_id": entity_id,
        "scope_entity_kind": scope_entity_kind,
        "inbound_depends_on": inbound_depends_on,
    }


def _prune_by_depth(
    model: ArchitectureModel,
    root_id: str,
    *,
    depth: int,
    expand_kinds: tuple[str, ...],
) -> ArchitectureModel:
    """Prune ``contains`` descendants of ``root_id`` beyond ``depth`` hops.

    ``depth=0`` keeps only the root. ``depth=N`` keeps the root plus N
    levels of ``contains`` children. ``expand_kinds`` gates recursion:
    when non-empty, a node at level ``d`` only expands its children if
    its own kind (singular canonical, e.g. ``"component"``) is in
    ``expand_kinds``. Empty tuple = all kinds recurse.

    Children at any kept level are included regardless of their own
    kind; ``expand_kinds`` only restricts *further* recursion past that
    child. Non-``contains`` relationships whose endpoints are both in
    the kept set are preserved.
    """
    # Build id -> plural field (e.g. "components") lookup, then map to
    # singular canonical kind ("component") for expand_kinds matching.
    id_to_field: dict[str, str] = {}
    for f in _ENTITY_FIELDS:
        for ent in getattr(model.entities, f, []):
            id_to_field[ent.id] = f

    def _singular(field: str) -> str:
        if field.endswith("ies"):
            return field[:-3] + "y"
        if field.endswith("s") and not field.endswith("ss"):
            return field[:-1]
        return field

    id_to_kind: dict[str, str] = {
        eid: _singular(f) for eid, f in id_to_field.items()
    }

    # contains children graph.
    children_of: dict[str, list[str]] = {}
    for rel in model.relationships:
        if rel.type != RelationType.CONTAINS:
            continue
        children_of.setdefault(rel.from_id, []).append(rel.to_id)

    allow_all = not expand_kinds
    allowed_kinds = set(expand_kinds)

    kept: set[str] = {root_id}
    # BFS: (id, level). Root is level 0.
    frontier: list[tuple[str, int]] = [(root_id, 0)]
    while frontier:
        next_frontier: list[tuple[str, int]] = []
        for node_id, level in frontier:
            if level >= depth:
                continue
            node_kind = id_to_kind.get(node_id, "")
            if not allow_all and node_kind not in allowed_kinds:
                continue
            for child_id in children_of.get(node_id, []):
                if child_id in kept:
                    continue
                kept.add(child_id)
                next_frontier.append((child_id, level + 1))
        frontier = next_frontier

    # Filter entity lists.
    pruned_entities = copy.deepcopy(model.entities)
    for f in _ENTITY_FIELDS:
        lst = getattr(pruned_entities, f)
        lst[:] = [e for e in lst if e.id in kept]

    # Filter relationships to those fully inside the kept set.
    pruned_rels = [
        copy.deepcopy(r)
        for r in model.relationships
        if r.from_id in kept and r.to_id in kept
    ]

    return ArchitectureModel(
        meta=copy.deepcopy(model.meta),
        entities=pruned_entities,
        relationships=pruned_rels,
    )


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


def _build_manifest_fragment(
    slice: ModelSlice,
    pkg: ArchitecturePackage,
    fragment: ArchitectureModel,
) -> tuple[ManifestFragment | None, list[MaterializationWarning]]:
    """Resolve ``SupplementaryRef(kind="manifest")`` to a bounded fragment.

    Returns ``(None, [])`` when no manifest ref is present. Emits
    ``SLICE.MANIFEST_UNAVAILABLE`` when a ref is present but the package
    exposes no filesystem root or manifest generation fails.
    """

    manifest_ref = next(
        (r for r in slice.supplementary_refs if r.kind == "manifest"),
        None,
    )
    if manifest_ref is None:
        return None, []

    warnings: list[MaterializationWarning] = []

    if pkg.root is None:
        warnings.append(
            MaterializationWarning(
                code="SLICE.MANIFEST_UNAVAILABLE",
                message="cannot resolve manifest: package has no filesystem root",
            )
        )
        return None, warnings

    # Determine project root: explicit override on the ref, else pkg.root.
    project_root: Path = pkg.root
    if manifest_ref.path:
        project_root = (pkg.root / manifest_ref.path).resolve()

    try:
        from architecture_model.manifest.generator import generate_manifest

        manifest = generate_manifest(project_root)
    except Exception as exc:  # noqa: BLE001
        warnings.append(
            MaterializationWarning(
                code="SLICE.MANIFEST_UNAVAILABLE",
                message=f"generate_manifest({project_root!s}) failed: {exc!s}",
            )
        )
        return None, warnings

    # Collect in-scope files from every component in the fragment.
    scope_files: set[str] = set()
    for comp in fragment.entities.components:
        for fp in getattr(comp, "files", None) or ():
            scope_files.add(fp)

    if not scope_files:
        # No component-file allocation to key off of; return empty fragment
        # so downstream projectors can still distinguish "resolved but empty"
        # from "not resolved".
        return ManifestFragment(), warnings

    kept_modules = tuple(
        sorted(
            (m for m in manifest.modules if m.file in scope_files),
            key=lambda m: m.file,
        )
    )
    functions = tuple(
        ManifestFunction(file=m.file, info=fn)
        for m in kept_modules
        for fn in m.functions
    )
    classes = tuple(
        ManifestClass(file=m.file, info=cls)
        for m in kept_modules
        for cls in m.classes
    )
    kept_files = {m.file for m in kept_modules}
    imports = tuple(
        sorted(
            (
                e for e in manifest.interfaces
                if e.source in kept_files and e.target in kept_files
            ),
            key=lambda e: (e.source, e.target, e.import_path),
        )
    )

    return (
        ManifestFragment(
            modules=kept_modules,
            functions=functions,
            classes=classes,
            imports=imports,
        ),
        warnings,
    )


_SUPPLEMENTARY_LOADERS: dict[str, Any] = {}


def _get_supplementary_loaders() -> dict[str, Any]:
    """Lazy loader-registry lookup (avoids circular import at module load)."""
    global _SUPPLEMENTARY_LOADERS
    if _SUPPLEMENTARY_LOADERS:
        return _SUPPLEMENTARY_LOADERS
    from architecture_model.lifecycle import supplementary_loaders as sl

    _SUPPLEMENTARY_LOADERS = {
        "sil": sl.load_sil,
        "gates": sl.load_gates,
        "drift": sl.load_drift,
        "test_results": sl.load_test_results,
        "learning": sl.load_learning,
    }
    return _SUPPLEMENTARY_LOADERS


def _build_supplementary_fragments(
    slice: ModelSlice,
    pkg: ArchitecturePackage,
) -> tuple[dict[str, Any], list[MaterializationWarning]]:
    """Resolve non-manifest supplementary refs to per-kind fragments.

    Returns ``({}, [])`` when the slice carries no such refs. A ref whose
    loader returns ``None`` (backing store missing or kind not yet wired)
    emits a ``SLICE.SUPPLEMENTARY_NOT_AVAILABLE`` warning and is omitted
    from the returned dict.
    """
    fragments: dict[str, Any] = {}
    warnings: list[MaterializationWarning] = []

    refs = [r for r in slice.supplementary_refs if r.kind != "manifest"]
    if not refs:
        return fragments, warnings

    if pkg.root is None:
        for ref in refs:
            warnings.append(
                MaterializationWarning(
                    code="SLICE.SUPPLEMENTARY_NOT_AVAILABLE",
                    message=(
                        f"cannot resolve supplementary {ref.kind!r}: "
                        "package has no filesystem root"
                    ),
                )
            )
        return fragments, warnings

    loaders = _get_supplementary_loaders()
    for ref in refs:
        loader = loaders.get(ref.kind)
        if loader is None:
            # SupplementaryKind literal already restricts this, but guard
            # anyway so future kinds don't silently no-op.
            warnings.append(
                MaterializationWarning(
                    code="SLICE.SUPPLEMENTARY_NOT_AVAILABLE",
                    message=f"unknown supplementary kind {ref.kind!r}",
                )
            )
            continue
        # Merge slice.time_window into the ref's filter for kinds that
        # support since/until semantics. Explicit ref.filter values win
        # over the slice-level window.
        effective_filter = _merge_time_window(ref, slice)
        try:
            fragment = loader(
                pkg.root,
                path=ref.path,
                filter=effective_filter,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                MaterializationWarning(
                    code="SLICE.SUPPLEMENTARY_NOT_AVAILABLE",
                    message=(
                        f"supplementary {ref.kind!r} loader raised: {exc!s}"
                    ),
                )
            )
            continue
        if fragment is None:
            warnings.append(
                MaterializationWarning(
                    code="SLICE.SUPPLEMENTARY_NOT_AVAILABLE",
                    message=(
                        f"supplementary {ref.kind!r} unavailable "
                        "(no backing store or empty)"
                    ),
                )
            )
            continue
        fragments[ref.kind] = fragment

    return fragments, warnings


# Kinds that understand ISO-8601 since/until in their filter dict.
_TIME_WINDOWED_KINDS = frozenset({"sil", "gates", "drift", "test_results", "learning"})


def _merge_time_window(ref, slice: ModelSlice) -> dict[str, Any] | None:
    """Overlay ``slice.time_window`` onto ``ref.filter`` for temporal kinds.

    Explicit ``since`` / ``until`` on the ref filter take precedence over
    the slice-level window. Returns the ref's filter unchanged when the
    slice has no ``time_window`` or the kind isn't temporal-aware.
    """
    if slice.time_window is None or ref.kind not in _TIME_WINDOWED_KINDS:
        return ref.filter
    merged: dict[str, Any] = dict(ref.filter or {})
    merged.setdefault("since", slice.time_window.from_)
    merged.setdefault("until", slice.time_window.to)
    return merged


def _build_revision_series(
    slice: ModelSlice,
    pkg: ArchitecturePackage,
) -> tuple[tuple[ModelRevisionFragment, ...], list[MaterializationWarning]]:
    """Load each generation in ``slice.revision_range`` and project it.

    For each generation N in the inclusive [from, to] range: load the
    generation's model file, apply the slice's selectors + curation, and
    close relationships strictly (both endpoints must remain in the
    fragment). Missing generations emit ``SLICE.REVISION_MISSING``;
    malformed models emit ``SLICE.REVISION_UNAVAILABLE``.
    """
    if slice.revision_range is None:
        return (), []

    warnings: list[MaterializationWarning] = []
    if pkg.root is None:
        warnings.append(
            MaterializationWarning(
                code="SLICE.REVISION_UNAVAILABLE",
                message=(
                    "cannot resolve revision_range: package has no filesystem root"
                ),
            )
        )
        return (), warnings

    from architecture_model.lifecycle.publication import generation_dir

    lo = int(slice.revision_range.from_)
    hi = int(slice.revision_range.to)

    fragments: list[ModelRevisionFragment] = []
    for n in range(lo, hi + 1):
        rev_id = f"{n:07d}"
        gen_dir = generation_dir(pkg, n)
        model_path = gen_dir / "model" / ".architecture-model.yaml"
        if not model_path.is_file():
            warnings.append(
                MaterializationWarning(
                    code="SLICE.REVISION_MISSING",
                    message=(
                        f"generation {rev_id!r} not found at {gen_dir!s}"
                    ),
                )
            )
            continue
        try:
            model = load_model(model_path)
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                MaterializationWarning(
                    code="SLICE.REVISION_UNAVAILABLE",
                    message=(
                        f"generation {rev_id!r} model load failed: {exc!s}"
                    ),
                )
            )
            continue
        rev_fragment = _project_revision(model, slice)
        fragments.append(
            ModelRevisionFragment(revision=rev_id, model_fragment=rev_fragment)
        )

    return tuple(fragments), warnings


def _project_revision(
    model: ArchitectureModel, slice: ModelSlice
) -> ArchitectureModel:
    """Apply selectors + curation + strict closure to a historical model.

    Deliberately minimal: no supplementary refs, no boundary stubs, no
    transitive expansion — historical fragments are meant for diffing
    against the primary fragment, so we want a directly comparable view.
    ``curation.include`` re-adds; ``curation.exclude`` drops; ``redactions``
    are applied. Warnings during projection are swallowed (revision
    quality is reported via SLICE.REVISION_* codes only).
    """
    working = _clone_model(model)
    selected, _ = _apply_selectors(working, slice)
    if slice.curation.exclude:
        for eid in slice.curation.exclude:
            selected.discard(eid)
    if slice.curation.include:
        present = _all_ids(working.entities)
        for eid in slice.curation.include:
            if eid in present:
                selected.add(eid)
    fragment = _project(working, selected)
    fragment.relationships = [
        copy.deepcopy(r)
        for r in working.relationships
        if r.from_id in selected and r.to_id in selected
    ]
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
    _sort_fragment(fragment)
    return fragment


__all__ = [
    "ManifestClass",
    "ManifestFragment",
    "ManifestFunction",
    "MaterializationWarning",
    "MaterializedSlice",
    "ModelRevisionFragment",
    "materialize",
    "MATERIALIZER_VERSION",
]