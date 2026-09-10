"""``pack_proposal`` helper — Phase 4-A Task 2.

Centralizes prompt-digest computation and ``ModelPatch`` construction for
write-back projectors so subclasses only supply the domain-specific
``operations`` list. The helper guarantees byte-stable proposal identity
across repeated calls with identical inputs (via the SHA-256 provenance
identity that :class:`~architecture_model.ai.proposals.Provenance` already
enforces).
"""

from __future__ import annotations

from architecture_model.ai.proposals import ModelPatch
from architecture_model.ai.pack import pack_proposal


def test_pack_proposal_returns_model_patch_with_stable_identity():
    ops = [
        {"op": "replace", "target": "COMP-1", "field": "intent", "value": "x"},
    ]
    a = pack_proposal(
        work_order_id="wo-42",
        model_version="rev-abc",
        prompt="Author the intent.",
        operations=ops,
    )
    b = pack_proposal(
        work_order_id="wo-42",
        model_version="rev-abc",
        prompt="Author the intent.",
        operations=ops,
    )
    assert isinstance(a, ModelPatch)
    assert a.provenance.proposal_id == b.provenance.proposal_id
    assert a.provenance.proposal_id.startswith("sha256-v1:")
    assert a.operations == ops


def test_pack_proposal_digest_differs_for_different_prompts():
    ops = [{"op": "replace", "target": "COMP-1", "field": "intent", "value": "x"}]
    a = pack_proposal(
        work_order_id="wo-1",
        model_version="rev-1",
        prompt="Prompt A",
        operations=ops,
    )
    b = pack_proposal(
        work_order_id="wo-1",
        model_version="rev-1",
        prompt="Prompt B",
        operations=ops,
    )
    assert a.provenance.prompt_digest != b.provenance.prompt_digest
    assert a.provenance.proposal_id != b.provenance.proposal_id


def test_pack_proposal_operations_are_copied_not_aliased():
    ops = [{"op": "replace", "target": "COMP-1", "field": "intent", "value": "x"}]
    a = pack_proposal(
        work_order_id="wo-1",
        model_version="rev-1",
        prompt="p",
        operations=ops,
    )
    ops.append({"op": "add", "target": "COMP-2", "field": "intent", "value": "y"})
    # Mutating caller's list must not affect the proposal.
    assert len(a.operations) == 1


def test_pack_proposal_rejects_empty_prompt():
    import pytest as _pytest

    with _pytest.raises(ValueError):
        pack_proposal(
            work_order_id="wo-1",
            model_version="rev-1",
            prompt="",
            operations=[],
        )
