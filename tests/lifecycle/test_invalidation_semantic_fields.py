"""Phase 2 Task 22 — surgical per-entity view invalidation for semantic-field diffs.

Semantic-field-only diffs on a single entity must invalidate only that
entity's F1/F7 (etc) view instances, not the whole family. This is the
contract of :func:`stale_entity_view_ids`.
"""
from __future__ import annotations

from architecture_model.lifecycle.invalidation import (
    SEMANTIC_FIELD_RULES,
    stale_entity_view_ids,
    stale_families,
    stale_view_ids,
)


def _diff(**kw):
    return {
        "entities": kw.get("entities", {"added": [], "removed": [], "changed": []}),
        "relationships": kw.get(
            "relationships", {"added": [], "removed": [], "changed": []}
        ),
    }


ALL_VIEW_IDS = [
    # F1 per-entity views
    "family1.entity_page.COMP-1",
    "family1.entity_page.COMP-3",
    "family1.entity_page.COMP-9",
    "family1.mission.COMP-1",
    "family1.mission.COMP-3",
    # F2
    "family2.entity_page.COMP-3",
    # F3
    "family3.entity_page.COMP-3",
    "family3.dependency_matrix.COMP-3",
    # F5
    "family5.entity_page.COMP-3",
    # F7
    "family7.entity_page.COMP-3",
    "family7.req_matrix.COMP-3",
    "family7.risk.COMP-3",
    # F8
    "family8.entity_page.COMP-3",
    "family8.health.COMP-3",
    # Family-scoped (non-entity) views should never be picked up.
    "family1.mission",
    "family7.req_matrix",
]


class TestSemanticFieldRules:
    def test_rules_are_data_only(self):
        # All values are lists of "family<N>.<view_name>" strings.
        for field, prefixes in SEMANTIC_FIELD_RULES.items():
            assert isinstance(field, str) and field
            assert isinstance(prefixes, list) and prefixes
            for p in prefixes:
                assert p.startswith("family") and "." in p

    def test_intent_prefixes(self):
        assert SEMANTIC_FIELD_RULES["intent"] == [
            "family1.entity_page",
            "family1.mission",
        ]


class TestStaleEntityViewIds:
    def test_intent_on_comp3_returns_entity_scoped_f1_views(self):
        diff = _diff(entities={
            "added": [], "removed": [],
            "changed": [{"kind": "component", "id": "COMP-3", "fields": ["intent"]}],
        })
        stale = stale_entity_view_ids(diff, ALL_VIEW_IDS)
        assert stale == [
            "family1.entity_page.COMP-3",
            "family1.mission.COMP-3",
        ]

    def test_result_is_sorted_and_deduped(self):
        diff = _diff(entities={
            "added": [], "removed": [],
            "changed": [
                # Both fields map to family1.entity_page — must dedup.
                {"kind": "component", "id": "COMP-3",
                 "fields": ["intent", "owner"]},
            ],
        })
        stale = stale_entity_view_ids(diff, ALL_VIEW_IDS)
        # dedup: family1.entity_page.COMP-3 appears once.
        assert stale.count("family1.entity_page.COMP-3") == 1
        assert stale == sorted(stale)

    def test_only_registered_views_are_returned(self):
        # COMP-99 has no registered views; result is empty.
        diff = _diff(entities={
            "added": [], "removed": [],
            "changed": [{"kind": "component", "id": "COMP-99", "fields": ["intent"]}],
        })
        assert stale_entity_view_ids(diff, ALL_VIEW_IDS) == []

    def test_family_scoped_views_never_included(self):
        # "family1.mission" (no entity suffix) must never be returned.
        diff = _diff(entities={
            "added": [], "removed": [],
            "changed": [{"kind": "component", "id": "COMP-3", "fields": ["intent"]}],
        })
        stale = stale_entity_view_ids(diff, ALL_VIEW_IDS)
        assert "family1.mission" not in stale

    def test_non_semantic_change_returns_empty(self):
        # A field not in _SEMANTIC_FIELDS => not semantic_only => no per-entity views.
        diff = _diff(entities={
            "added": [], "removed": [],
            "changed": [{"kind": "component", "id": "COMP-3", "fields": ["name"]}],
        })
        assert stale_entity_view_ids(diff, ALL_VIEW_IDS) == []

    def test_mixed_semantic_and_structural_returns_empty(self):
        # Any non-semantic field poisons semantic_only — nothing surgical.
        diff = _diff(entities={
            "added": [], "removed": [],
            "changed": [{"kind": "component", "id": "COMP-3",
                         "fields": ["intent", "name"]}],
        })
        assert stale_entity_view_ids(diff, ALL_VIEW_IDS) == []

    def test_failure_modes_maps_to_family7(self):
        diff = _diff(entities={
            "added": [], "removed": [],
            "changed": [{"kind": "component", "id": "COMP-3",
                         "fields": ["failure_modes"]}],
        })
        stale = stale_entity_view_ids(diff, ALL_VIEW_IDS)
        assert stale == [
            "family7.entity_page.COMP-3",
            "family7.risk.COMP-3",
        ]

    def test_slos_multiple_prefixes(self):
        diff = _diff(entities={
            "added": [], "removed": [],
            "changed": [{"kind": "component", "id": "COMP-3", "fields": ["slos"]}],
        })
        stale = stale_entity_view_ids(diff, ALL_VIEW_IDS)
        assert stale == [
            "family5.entity_page.COMP-3",
            "family7.entity_page.COMP-3",
            "family8.entity_page.COMP-3",
        ]

    def test_multiple_entities_are_scoped_independently(self):
        diff = _diff(entities={
            "added": [], "removed": [],
            "changed": [
                {"kind": "component", "id": "COMP-1", "fields": ["intent"]},
                {"kind": "component", "id": "COMP-3", "fields": ["intent"]},
            ],
        })
        stale = stale_entity_view_ids(diff, ALL_VIEW_IDS)
        assert "family1.entity_page.COMP-1" in stale
        assert "family1.entity_page.COMP-3" in stale
        assert "family1.mission.COMP-1" in stale
        assert "family1.mission.COMP-3" in stale
        # COMP-9 not touched.
        assert not any("COMP-9" in v for v in stale)

    def test_empty_changed_list_returns_empty(self):
        diff = _diff()
        assert stale_entity_view_ids(diff, ALL_VIEW_IDS) == []


class TestBackCompatWithCoarseInvalidation:
    """The coarse family-level path must be unaffected by Task 22."""

    def test_intent_change_still_populates_stale_families(self):
        diff = _diff(entities={
            "added": [], "removed": [],
            "changed": [{"kind": "component", "id": "COMP-3", "fields": ["intent"]}],
        })
        # Semantic-only change on a component: pre-existing invariant is
        # that we get family1 (from _SEMANTIC_FIELD_FAMILIES["intent"]) and
        # no structural fallback.
        fams = stale_families(diff)
        assert "family1" in fams
        assert "family3" not in fams  # no structural fallback for semantic-only
        assert "family8" not in fams

    def test_coarse_and_surgical_can_be_used_together(self):
        diff = _diff(entities={
            "added": [], "removed": [],
            "changed": [{"kind": "component", "id": "COMP-3", "fields": ["intent"]}],
        })
        coarse = stale_view_ids(diff, ALL_VIEW_IDS)
        surgical = stale_entity_view_ids(diff, ALL_VIEW_IDS)
        # Surgical is a strict subset of coarse (both include family1
        # entity_page.COMP-3 and mission.COMP-3).
        assert set(surgical).issubset(set(coarse))
