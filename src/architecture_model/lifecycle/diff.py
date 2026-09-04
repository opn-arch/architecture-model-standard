"""Semantic diff over architecture models, manifests, and child revisions.

Purpose
-------
Provide a complete, deterministic diff between two architecture-lifecycle
snapshots. Covers:

* All entity kinds present on :class:`architecture_model.core.types.Entities`
  (discovered reflectively via :func:`dataclasses.fields`).
* All relationship attributes (identity key = ``(from, to, type)``; any
  attribute delta becomes a ``changed`` entry).
* Manifest ground truth (files, symbols by fully-qualified name, symbol
  signatures).
* Child sub-architecture revisions (added / removed / revision changed).
* Git provenance propagation when both models carry
  ``meta.provenance.git_commit``.

Invariants
----------
* Deterministic ordering — all list outputs are lexicographically sorted.
* Missing inputs (``manifest_*=None`` or ``child_revisions_*=None``)
  produce empty structures, never ``None``.
* Field equality uses canonical JSON (NFC, sorted-keys) via
  :mod:`architecture_model.lifecycle.serialization` so nested dict/list
  equality is order-insensitive.
* Pydantic v2, ``extra=forbid``: unknown fields on any diff container
  raise ``ValidationError``.

Thread safety
-------------
Pure functions; no shared mutable state. Safe to call concurrently.

Error taxonomy
--------------
* Unsupported entity attribute types propagate ``TypeError`` from
  :func:`canonical_json`.
* Malformed inputs (non-``ArchitectureModel``) raise ``AttributeError``
  from the reflective walk — callers must supply parsed models.
"""

from __future__ import annotations

import dataclasses
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from architecture_model.core.types import ArchitectureModel, Entities, Relationship
from architecture_model.lifecycle.serialization import canonical_json

# Entity kinds that this diff reports on. Order is stable but display
# ordering is enforced separately by sorting keys at emit time.
_ENTITY_KINDS: tuple[str, ...] = tuple(f.name for f in dataclasses.fields(Entities))


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EntityKindDiff(_Strict):
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    changed: list[dict[str, Any]] = Field(default_factory=list)


class RelationshipDiff(_Strict):
    added: list[dict[str, str]] = Field(default_factory=list)
    removed: list[dict[str, str]] = Field(default_factory=list)
    changed: list[dict[str, Any]] = Field(default_factory=list)


class ManifestDiff(_Strict):
    files_added: list[str] = Field(default_factory=list)
    files_removed: list[str] = Field(default_factory=list)
    symbols_added: list[str] = Field(default_factory=list)
    symbols_removed: list[str] = Field(default_factory=list)
    symbols_signature_changed: list[str] = Field(default_factory=list)


class ChildrenDiff(_Strict):
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    revision_changed: list[dict[str, str]] = Field(default_factory=list)


class SemanticDiff(_Strict):
    entities: dict[str, EntityKindDiff]
    relationships: RelationshipDiff
    manifest: ManifestDiff
    children: ChildrenDiff
    git: dict[str, Optional[str]]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_plain(value: Any) -> Any:
    """Recursively convert dataclasses/enums to canonical-JSON-friendly values."""
    if isinstance(value, Enum):
        return value.value
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: _to_plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, dict):
        return {str(k): _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(v) for v in value]
    return value


def _canon_eq(a: Any, b: Any) -> bool:
    """Structural equality via canonical JSON."""
    try:
        return canonical_json(_to_plain(a)) == canonical_json(_to_plain(b))
    except TypeError:
        # Fall back to Python equality for unsupported types (e.g. float).
        return a == b


# Relationship attributes to consider for `changed` detection. `type`,
# `from_id`, `to_id` form the identity key and are excluded.
_REL_ATTRS: tuple[str, ...] = (
    "description",
    "strength",
    "import_count",
    "weight",
    "extensions",
    "imports",
)


def _entity_id_map(items: list[Any]) -> dict[str, Any]:
    return {e.id: e for e in items}


def _diff_entity_kind(old: list[Any], new: list[Any]) -> EntityKindDiff:
    old_map = _entity_id_map(old)
    new_map = _entity_id_map(new)
    old_ids = set(old_map)
    new_ids = set(new_map)

    added = sorted(new_ids - old_ids)
    removed = sorted(old_ids - new_ids)

    changed: list[dict[str, Any]] = []
    for eid in sorted(old_ids & new_ids):
        oe = old_map[eid]
        ne = new_map[eid]
        for f in dataclasses.fields(oe):
            fname = f.name
            if fname == "id":
                continue
            ov = getattr(oe, fname)
            nv = getattr(ne, fname)
            if not _canon_eq(ov, nv):
                changed.append(
                    {
                        "id": eid,
                        "field": fname,
                        "old": _to_plain(ov),
                        "new": _to_plain(nv),
                    }
                )
    changed.sort(key=lambda c: (c["id"], c["field"]))
    return EntityKindDiff(added=added, removed=removed, changed=changed)


def _rel_key(r: Relationship) -> tuple[str, str, str]:
    t = r.type.value if isinstance(r.type, Enum) else str(r.type)
    return (r.from_id, r.to_id, t)


def _rel_keydict(k: tuple[str, str, str]) -> dict[str, str]:
    return {"from": k[0], "to": k[1], "type": k[2]}


def _diff_relationships(old: list[Relationship], new: list[Relationship]) -> RelationshipDiff:
    old_map: dict[tuple[str, str, str], Relationship] = {}
    for r in old:
        old_map[_rel_key(r)] = r
    new_map: dict[tuple[str, str, str], Relationship] = {}
    for r in new:
        new_map[_rel_key(r)] = r

    added_keys = sorted(set(new_map) - set(old_map))
    removed_keys = sorted(set(old_map) - set(new_map))

    added = [_rel_keydict(k) for k in added_keys]
    removed = [_rel_keydict(k) for k in removed_keys]

    changed: list[dict[str, Any]] = []
    for k in sorted(set(old_map) & set(new_map)):
        orel = old_map[k]
        nrel = new_map[k]
        for attr in _REL_ATTRS:
            ov = getattr(orel, attr, None)
            nv = getattr(nrel, attr, None)
            if not _canon_eq(ov, nv):
                entry = _rel_keydict(k)
                entry["field"] = attr
                entry["old"] = _to_plain(ov)
                entry["new"] = _to_plain(nv)
                changed.append(entry)
    changed.sort(key=lambda c: (c["from"], c["to"], c["type"], c["field"]))
    return RelationshipDiff(added=added, removed=removed, changed=changed)


def _extract_files_symbols(m: Any) -> tuple[list[str], dict[str, str]]:
    """Return (files, {symbol_name: signature}) from a manifest-like object.

    Accepts dict (``{"files": [...], "symbols": [{"name":..., "signature":...}]}``)
    or an object with matching attributes.
    """
    if m is None:
        return [], {}
    if isinstance(m, dict):
        files = list(m.get("files") or [])
        raw_syms = m.get("symbols") or []
    else:
        files = list(getattr(m, "files", []) or [])
        raw_syms = getattr(m, "symbols", []) or []
    syms: dict[str, str] = {}
    for s in raw_syms:
        if isinstance(s, dict):
            name = s.get("name")
            sig = s.get("signature", "")
        else:
            name = getattr(s, "name", None)
            sig = getattr(s, "signature", "")
        if name is not None:
            syms[str(name)] = str(sig) if sig is not None else ""
    return [str(f) for f in files], syms


def _diff_manifest(a: Any, b: Any) -> ManifestDiff:
    if a is None or b is None:
        return ManifestDiff()
    files_a, sym_a = _extract_files_symbols(a)
    files_b, sym_b = _extract_files_symbols(b)
    fa, fb = set(files_a), set(files_b)
    sa, sb = set(sym_a), set(sym_b)
    sig_changed = sorted(n for n in (sa & sb) if sym_a[n] != sym_b[n])
    return ManifestDiff(
        files_added=sorted(fb - fa),
        files_removed=sorted(fa - fb),
        symbols_added=sorted(sb - sa),
        symbols_removed=sorted(sa - sb),
        symbols_signature_changed=sig_changed,
    )


def _diff_children(
    a: Optional[dict[str, str]], b: Optional[dict[str, str]]
) -> ChildrenDiff:
    if a is None or b is None:
        return ChildrenDiff()
    ka, kb = set(a), set(b)
    revision_changed = [
        {"architecture_id": aid, "from": a[aid], "to": b[aid]}
        for aid in sorted(ka & kb)
        if a[aid] != b[aid]
    ]
    return ChildrenDiff(
        added=sorted(kb - ka),
        removed=sorted(ka - kb),
        revision_changed=revision_changed,
    )


def _git_commit(model: ArchitectureModel) -> Optional[str]:
    prov = getattr(model.meta, "provenance", None)
    if prov is None:
        return None
    if isinstance(prov, dict):
        v = prov.get("git_commit")
    else:
        v = getattr(prov, "git_commit", None)
    return str(v) if v else None


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------


def semantic_diff(
    a: ArchitectureModel,
    b: ArchitectureModel,
    *,
    manifest_a: Any = None,
    manifest_b: Any = None,
    child_revisions_a: Optional[dict[str, str]] = None,
    child_revisions_b: Optional[dict[str, str]] = None,
) -> SemanticDiff:
    """Compute the semantic diff between two architecture snapshots.

    See the module docstring for the full contract.
    """
    entity_diffs: dict[str, EntityKindDiff] = {}
    for kind in _ENTITY_KINDS:
        entity_diffs[kind] = _diff_entity_kind(
            getattr(a.entities, kind), getattr(b.entities, kind)
        )

    rel_diff = _diff_relationships(a.relationships, b.relationships)
    man_diff = _diff_manifest(manifest_a, manifest_b)
    child_diff = _diff_children(child_revisions_a, child_revisions_b)

    ga, gb = _git_commit(a), _git_commit(b)
    if ga is None or gb is None:
        git = {"commit_a": None, "commit_b": None}
    else:
        git = {"commit_a": ga, "commit_b": gb}

    return SemanticDiff(
        entities=entity_diffs,
        relationships=rel_diff,
        manifest=man_diff,
        children=child_diff,
        git=git,
    )


__all__ = [
    "ChildrenDiff",
    "EntityKindDiff",
    "ManifestDiff",
    "RelationshipDiff",
    "SemanticDiff",
    "semantic_diff",
]
