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
