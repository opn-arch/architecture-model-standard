"""Task 18 — federated diff end-to-end.

Verifies that ``semantic_diff`` reports child-package deltas as a flat list of
``{kind, child_arch_id, from_rev?, to_rev?}`` records per the Phase-4 spec.
"""

from __future__ import annotations

from architecture_model.core.types import (
    ArchitectureModel,
    Entities,
    ModelMeta,
)
from architecture_model.lifecycle.diff import (
    ChildDiffEntry,
    SemanticDiff,
    semantic_diff,
)


def _empty_model() -> ArchitectureModel:
    return ArchitectureModel(
        meta=ModelMeta(project="p", schema_version="2.1"),
        entities=Entities(),
        relationships=[],
    )


def test_children_added_removed_and_revised_are_flat_records() -> None:
    a = _empty_model()
    b = _empty_model()
    diff = semantic_diff(
        a,
        b,
        child_revisions_a={"arch-1": "0000001", "arch-2": "0000003"},
        child_revisions_b={"arch-2": "0000004", "arch-3": "0000001"},
    )

    assert isinstance(diff, SemanticDiff)
    assert diff.children == [
        ChildDiffEntry(kind="added", child_arch_id="arch-3", to_rev="0000001"),
        ChildDiffEntry(kind="removed", child_arch_id="arch-1", from_rev="0000001"),
        ChildDiffEntry(
            kind="revised",
            child_arch_id="arch-2",
            from_rev="0000003",
            to_rev="0000004",
        ),
    ]


def test_children_absent_when_both_sides_missing() -> None:
    a = _empty_model()
    b = _empty_model()
    diff = semantic_diff(a, b)
    assert diff.children == []


def test_children_absent_when_no_changes() -> None:
    a = _empty_model()
    b = _empty_model()
    diff = semantic_diff(
        a,
        b,
        child_revisions_a={"arch-1": "0000001"},
        child_revisions_b={"arch-1": "0000001"},
    )
    assert diff.children == []


def test_children_sort_order_is_kind_then_arch_id() -> None:
    a = _empty_model()
    b = _empty_model()
    diff = semantic_diff(
        a,
        b,
        child_revisions_a={"z-old": "0000001", "a-old": "0000001"},
        child_revisions_b={"z-new": "0000002", "a-new": "0000002"},
    )
    kinds_and_ids = [(c.kind, c.child_arch_id) for c in diff.children]
    # added entries first (kind sorts before removed alphabetically),
    # each group sorted by child_arch_id.
    assert kinds_and_ids == [
        ("added", "a-new"),
        ("added", "z-new"),
        ("removed", "a-old"),
        ("removed", "z-old"),
    ]


def test_revised_entry_carries_both_revs() -> None:
    a = _empty_model()
    b = _empty_model()
    diff = semantic_diff(
        a,
        b,
        child_revisions_a={"arch-1": "0000001"},
        child_revisions_b={"arch-1": "0000005"},
    )
    assert len(diff.children) == 1
    entry = diff.children[0]
    assert entry.kind == "revised"
    assert entry.child_arch_id == "arch-1"
    assert entry.from_rev == "0000001"
    assert entry.to_rev == "0000005"
