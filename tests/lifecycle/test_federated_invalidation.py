"""Task 19 — federated invalidation rules.

Verifies that federated child-package deltas map onto the correct set of
stale parent view ids per the Phase-4 plan:

* Child added   → M1 root views become stale (family1.mission,
                  family3.component_diagram).
* Child removed → all parent views that referenced the removed child's
                  namespaced entity ids become stale, plus M1 roots.
* Child revised → all parent views referencing the child's namespaced
                  entity ids become stale, plus M1 roots.
"""

from __future__ import annotations

from architecture_model.lifecycle.diff import ChildDiffEntry
from architecture_model.lifecycle.invalidation import (
    stale_from_federated_children,
)


_ALL_VIEW_IDS = [
    "family1.mission",
    "family1.entity_page:childA:COMP-1",
    "family1.entity_page:childB:COMP-1",
    "family1.entity_page:LOCAL-COMP",
    "family3.component_diagram",
    "family3.entity_page:childA:COMP-2",
    "family3.entity_page:LOCAL-COMP",
    "family6.icd",
    "family7.risk",
]


def test_child_added_invalidates_only_m1_roots() -> None:
    entries = [ChildDiffEntry(kind="added", child_arch_id="childC", to_rev="0000001")]
    result = stale_from_federated_children(entries, _ALL_VIEW_IDS)
    assert result == ["family1.mission", "family3.component_diagram"]


def test_child_removed_invalidates_namespaced_entity_views_and_roots() -> None:
    entries = [
        ChildDiffEntry(kind="removed", child_arch_id="childA", from_rev="0000002")
    ]
    result = stale_from_federated_children(entries, _ALL_VIEW_IDS)
    assert result == [
        "family1.entity_page:childA:COMP-1",
        "family1.mission",
        "family3.component_diagram",
        "family3.entity_page:childA:COMP-2",
    ]


def test_child_revised_invalidates_namespaced_entity_views_and_roots() -> None:
    entries = [
        ChildDiffEntry(
            kind="revised",
            child_arch_id="childB",
            from_rev="0000001",
            to_rev="0000002",
        )
    ]
    result = stale_from_federated_children(entries, _ALL_VIEW_IDS)
    assert result == [
        "family1.entity_page:childB:COMP-1",
        "family1.mission",
        "family3.component_diagram",
    ]


def test_multiple_entries_are_unioned_and_deduplicated() -> None:
    entries = [
        ChildDiffEntry(kind="added", child_arch_id="childC", to_rev="0000001"),
        ChildDiffEntry(
            kind="revised",
            child_arch_id="childA",
            from_rev="0000001",
            to_rev="0000002",
        ),
    ]
    result = stale_from_federated_children(entries, _ALL_VIEW_IDS)
    assert result == [
        "family1.entity_page:childA:COMP-1",
        "family1.mission",
        "family3.component_diagram",
        "family3.entity_page:childA:COMP-2",
    ]


def test_empty_entries_yield_empty() -> None:
    assert stale_from_federated_children([], _ALL_VIEW_IDS) == []


def test_unknown_child_arch_id_still_invalidates_roots_on_revise() -> None:
    entries = [
        ChildDiffEntry(
            kind="revised",
            child_arch_id="ghost",
            from_rev="0000001",
            to_rev="0000002",
        )
    ]
    result = stale_from_federated_children(entries, _ALL_VIEW_IDS)
    # No entity_page:ghost:* exists, so only roots become stale.
    assert result == ["family1.mission", "family3.component_diagram"]


def test_accepts_plain_dict_entries() -> None:
    entries = [{"kind": "added", "child_arch_id": "childC", "to_rev": "1"}]
    result = stale_from_federated_children(entries, _ALL_VIEW_IDS)
    assert result == ["family1.mission", "family3.component_diagram"]
