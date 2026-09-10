"""Map a SemanticDiff onto the set of view families to invalidate.

The rule table is data; adding a rule is data-only, not code. Each rule
declares a trigger (entity kind + operation + optional field set) and
the set of families it invalidates.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Semantic-only fields; touching these invalidates F1/F7 only (surgical).
_SEMANTIC_FIELDS: frozenset[str] = frozenset({
    "intent", "goals", "stakeholders", "success_criteria",
    "failure_modes", "trade_offs", "assumptions", "open_questions",
    "requirements", "verification", "slos", "owner", "maturity",
    "dependencies_rationale",
})

_SEMANTIC_FIELD_FAMILIES: dict[str, set[str]] = {
    "intent": {"family1"},
    "goals": {"family1", "family7"},
    "stakeholders": {"family1"},
    "success_criteria": {"family1", "family7"},
    "failure_modes": {"family7"},
    "trade_offs": {"family1", "family3", "family7"},
    "assumptions": {"family7"},
    "open_questions": {"family7", "family8"},
    "requirements": {"family7"},
    "verification": {"family7"},
    "slos": {"family5", "family7", "family8"},
    "owner": {"family1", "family8"},
    "maturity": {"family1", "family8"},
    "dependencies_rationale": {"family3"},
}


@dataclass(frozen=True)
class Rule:
    trigger: dict[str, Any]
    invalidates: frozenset[str]


RULES: list[Rule] = [
    Rule({"kind": "component", "op": "added"},   frozenset({"family3", "family2", "family8"})),
    Rule({"kind": "component", "op": "removed"}, frozenset({"family3", "family2", "family8"})),
    Rule({"kind": "capability", "op": "added"},   frozenset({"family1", "family2", "family7"})),
    Rule({"kind": "capability", "op": "removed"}, frozenset({"family1", "family2", "family7"})),
    Rule({"kind": "capability", "op": "changed"}, frozenset({"family1", "family2", "family7"})),
    Rule({"kind": "constraint", "op": "added"},   frozenset({"family7", "family1"})),
    Rule({"kind": "constraint", "op": "removed"}, frozenset({"family7", "family1"})),
    Rule({"kind": "interface", "op": "added"},    frozenset({"family6", "family3"})),
    Rule({"kind": "interface", "op": "removed"},  frozenset({"family6", "family3"})),
    Rule({"kind": "interface", "op": "changed"},  frozenset({"family6", "family3"})),
    Rule({"kind": "behavior", "op": "added"},     frozenset({"family4", "family2", "family7"})),
    Rule({"kind": "behavior", "op": "removed"},   frozenset({"family4", "family2", "family7"})),
    Rule({"kind": "actor", "op": "added"},        frozenset({"family1", "family4"})),
    Rule({"kind": "actor", "op": "removed"},      frozenset({"family1", "family4"})),
    Rule({"kind": "layer", "op": "added"},        frozenset({"family3"})),
    Rule({"kind": "layer", "op": "removed"},      frozenset({"family3"})),
    Rule({"rel": True, "op": "added"},   frozenset({"family3", "family8"})),
    Rule({"rel": True, "op": "removed"}, frozenset({"family3", "family8"})),
]


def _semantic_only(fields: list[str]) -> bool:
    return bool(fields) and all(f in _SEMANTIC_FIELDS for f in fields)


def _families_for_semantic_fields(fields: list[str]) -> set[str]:
    result: set[str] = set()
    for f in fields:
        result |= _SEMANTIC_FIELD_FAMILIES.get(f, set())
    return result


def stale_families(diff: dict) -> set[str]:
    """Compute the set of view families made stale by a SemanticDiff.

    diff shape (subset used):
        {"entities": {"added": [{kind, id}], "removed": [...],
                      "changed": [{kind, id, fields}]},
         "relationships": {"added": [...], "removed": [...], "changed": [...]}}
    """
    stale: set[str] = set()

    ents = diff.get("entities", {})
    for op in ("added", "removed"):
        for entry in ents.get(op, []):
            kind = entry.get("kind")
            for rule in RULES:
                t = rule.trigger
                if t.get("kind") == kind and t.get("op") == op:
                    stale |= rule.invalidates

    # Changed: union surgical semantic-field families with any kind-level
    # `changed` rule. Only when the change is NOT semantic-only do we add
    # the structural {family3, family8} fallback.
    for entry in ents.get("changed", []):
        kind = entry.get("kind")
        fields = entry.get("fields", [])
        semantic_only = _semantic_only(fields)
        if semantic_only:
            stale |= _families_for_semantic_fields(fields)
        for rule in RULES:
            t = rule.trigger
            if t.get("kind") == kind and t.get("op") == "changed":
                stale |= rule.invalidates
        if not semantic_only:
            stale |= {"family3", "family8"}

    rels = diff.get("relationships", {})
    for op in ("added", "removed"):
        if rels.get(op):
            for rule in RULES:
                t = rule.trigger
                if t.get("rel") and t.get("op") == op:
                    stale |= rule.invalidates
    if rels.get("changed"):
        stale |= {"family3", "family8"}

    return stale


def stale_view_ids(diff: dict, all_view_ids: list[str]) -> list[str]:
    """Given all registered view IDs (family<N>.<name>[.llm]), return those in stale families."""
    families = stale_families(diff)
    result = []
    for vid in all_view_ids:
        head = vid.split(".", 1)[0]
        if head in families:
            result.append(vid)
    return sorted(result)


# Phase 2 Task 22: per-field → per-view (entity-scoped) invalidation.
# Each rule value is a list of ``family<N>.<view_name>`` prefixes;
# ``stale_entity_view_ids`` matches ``<prefix>.<entity_id>`` in the
# registered view-id list. This lets a semantic-field diff invalidate
# only the affected entity's F1/F7 view instances instead of the whole
# family (which is what ``stale_view_ids`` returns via ``stale_families``).
SEMANTIC_FIELD_RULES: dict[str, list[str]] = {
    "intent":                 ["family1.entity_page", "family1.mission"],
    "failure_modes":          ["family7.entity_page", "family7.risk"],
    "trade_offs":             ["family1.entity_page", "family3.entity_page"],
    "slos":                   ["family5.entity_page", "family7.entity_page", "family8.entity_page"],
    "owner":                  ["family1.entity_page"],
    "maturity":               ["family1.entity_page", "family8.health"],
    "requirements":           ["family7.req_matrix", "family7.entity_page"],
    "verification":           ["family7.req_matrix", "family7.entity_page"],
    "dependencies_rationale": ["family3.entity_page", "family3.dependency_matrix"],
    "assumptions":            ["family7.entity_page"],
    "open_questions":         ["family7.entity_page", "family8.health"],
    "goals":                  ["family1.entity_page", "family2.entity_page"],
    "stakeholders":           ["family1.entity_page"],
    "success_criteria":       ["family1.entity_page", "family7.entity_page"],
}


def stale_entity_view_ids(diff: dict, all_view_ids: list[str]) -> list[str]:
    """Return surgical, per-entity view IDs made stale by semantic-field diffs.

    Only ``entities.changed`` entries with a semantic-only field set
    contribute. For each such entry, every field maps via
    :data:`SEMANTIC_FIELD_RULES` to a list of view prefixes; each prefix
    is matched against ``all_view_ids`` in the form
    ``<prefix>.<entity_id>``. Non-semantic changes fall through to the
    coarser :func:`stale_view_ids` path and are not returned here.

    Result is sorted and de-duplicated.
    """
    result: set[str] = set()
    ents = diff.get("entities", {})
    view_id_set = set(all_view_ids)
    for entry in ents.get("changed", []):
        fields = entry.get("fields", []) or []
        entity_id = entry.get("id")
        if not entity_id or not _semantic_only(fields):
            continue
        for field in fields:
            for prefix in SEMANTIC_FIELD_RULES.get(field, []):
                candidate = f"{prefix}.{entity_id}"
                if candidate in view_id_set:
                    result.add(candidate)
    return sorted(result)


_M1_PROPAGATING_REL_TYPES: frozenset[str] = frozenset({"exposes", "consumes"})


# ---------------------------------------------------------------------------
# Phase 4 Task 19 — federated child-package invalidation
# ---------------------------------------------------------------------------

# M1 root parent views invalidated whenever the federated child set changes.
_FEDERATED_M1_ROOTS: tuple[str, ...] = (
    "family1.mission",
    "family3.component_diagram",
)


def _child_entry_get(entry: Any, key: str) -> Any:
    """Read ``key`` from a ChildDiffEntry or a plain dict."""
    if isinstance(entry, dict):
        return entry.get(key)
    return getattr(entry, key, None)


def stale_from_federated_children(
    children_diff: Any,
    all_view_ids: Any,
) -> list[str]:
    """Map federated child-package deltas onto the stale parent view id set.

    Parameters
    ----------
    children_diff
        Iterable of ``ChildDiffEntry`` (from
        :mod:`architecture_model.lifecycle.diff`) or equivalent plain
        ``{"kind", "child_arch_id", "from_rev", "to_rev"}`` dicts.
    all_view_ids
        Iterable of all registered view ids (e.g.
        ``"family3.entity_page:childA:COMP-2"``).

    Rules
    -----
    * ``kind == "added"``     → invalidate M1 root views only
      (``family1.mission``, ``family3.component_diagram``).
    * ``kind == "removed"``   → invalidate any view id whose entity-id
      segment is namespaced under the child (``":<child_arch_id>:"``
      appears in the view id), PLUS the M1 roots.
    * ``kind == "revised"``   → same as ``removed``.

    Returned ids are sorted, de-duplicated, and filtered against
    ``all_view_ids`` so only registered views appear. The M1 roots are
    only surfaced when they exist in ``all_view_ids``.
    """
    registered = set(all_view_ids)
    stale: set[str] = set()

    for entry in children_diff or ():
        kind = _child_entry_get(entry, "kind")
        arch_id = _child_entry_get(entry, "child_arch_id")
        if kind not in {"added", "removed", "revised"} or not arch_id:
            continue

        # M1 roots always invalidate on any federated child delta.
        for root in _FEDERATED_M1_ROOTS:
            if root in registered:
                stale.add(root)

        # For removed/revised, invalidate every registered view id whose
        # entity id is namespaced under this child (e.g.
        # ``family3.entity_page:childA:COMP-2``).
        if kind in {"removed", "revised"}:
            needle = f":{arch_id}:"
            for vid in registered:
                if needle in vid:
                    stale.add(vid)

    return sorted(stale)


# ---------------------------------------------------------------------------
# Phase 3 Task 18 — entity-scoped view invalidation
# ---------------------------------------------------------------------------


def _find_parent(entity_id: str, model: Any) -> str | None:
    """Return the entity id that ``contains`` ``entity_id``, or None."""
    if model is None:
        return None
    for rel in getattr(model, "relationships", ()) or ():
        rtype = getattr(rel, "type", None)
        rtype_val = getattr(rtype, "value", rtype)
        if rtype_val == "contains" and getattr(rel, "to_id", None) == entity_id:
            return getattr(rel, "from_id", None)
    return None


def _find_peers(entity_id: str, model: Any) -> tuple[str, ...]:
    """Return sibling entity ids sharing a ``contains`` parent with ``entity_id``.

    Sorted for determinism. Self is excluded. Returns empty when the
    entity has no parent.
    """
    parent = _find_parent(entity_id, model)
    if parent is None:
        return ()
    peers: set[str] = set()
    for rel in getattr(model, "relationships", ()) or ():
        rtype = getattr(rel, "type", None)
        rtype_val = getattr(rtype, "value", rtype)
        if rtype_val != "contains":
            continue
        if getattr(rel, "from_id", None) != parent:
            continue
        to_id = getattr(rel, "to_id", None)
        if to_id and to_id != entity_id:
            peers.add(to_id)
    return tuple(sorted(peers))


def entity_change_stale_set(
    entity_id: str, family: int, model: Any
) -> set[str]:
    """Return view IDs affected by a change to ``entity_id`` at ``family`` scope.

    Contract (from Phase 3 plan Task 18):

    * ``family{N}.entity_page:{entity_id}`` — the changed entity itself.
    * ``family{N}.entity_page:{parent}`` — its direct ``contains`` parent
      (roll-up may change).
    * ``family{N}.entity_page:{peer}`` — each sibling under the same
      parent (contains / depends-on shifts may cross-affect peers).
    * ``family{N}.root`` — the family's root view (aggregate listing).

    Returned IDs use the colon form to match the ``DiagramSpec`` id
    convention (``prose:family1.entity_page:COMP-1``); this differs from
    the dot form used by :func:`stale_entity_view_ids` for semantic-field
    diffs. Callers must not mix the two id spaces.
    """
    prefix = f"family{family}.entity_page:"
    stale: set[str] = {prefix + entity_id}
    parent = _find_parent(entity_id, model)
    if parent:
        stale.add(prefix + parent)
    for peer in _find_peers(entity_id, model):
        stale.add(prefix + peer)
    stale.add(f"family{family}.root")
    return stale


def propagates_to_m1(diff: dict) -> bool:
    """True iff this M2 diff must invalidate M1 as well.

    Propagation rules:
    - Any relationship added/removed of type "exposes" or "consumes" (public
      surface change) → propagate.
    - Any relationship added/removed with cross_subsystem=True → propagate.
    - Any changed entity with appears_in_m1=True → propagate.
    - Any component add/remove → propagate (conservative default; upstream
      may narrow via subsystem markers in future).
    - Otherwise → local to M2.
    """
    rels = diff.get("relationships", {})
    for op in ("added", "removed"):
        for r in rels.get(op, []):
            if r.get("type") in _M1_PROPAGATING_REL_TYPES:
                return True
            if r.get("cross_subsystem"):
                return True

    ents = diff.get("entities", {})
    for entry in ents.get("changed", []):
        if entry.get("appears_in_m1"):
            return True
    for op in ("added", "removed"):
        for entry in ents.get(op, []):
            if entry.get("kind") == "component":
                return True

    return False
