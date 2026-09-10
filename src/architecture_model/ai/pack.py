"""Proposal-packaging helper for write-back projectors — Phase 4-A Task 2.

``pack_proposal`` centralizes prompt-digest computation and ModelPatch
construction so :class:`~architecture_model.lifecycle.projectors.write_back.WriteBackProjector`
subclasses only supply the domain-specific operations list. Identical
inputs always produce identical ``proposal_id`` (SHA-256 identity on
``work_order_id | model_version | prompt_digest``) — this stability is
required for idempotent ``architect_propose`` invocations and for
deduping proposals in the lifecycle store.
"""

from __future__ import annotations

import hashlib
from typing import Any

from architecture_model.ai.proposals import ModelPatch, Provenance


def pack_proposal(
    *,
    work_order_id: str,
    model_version: str,
    prompt: str,
    operations: list[dict[str, Any]],
) -> ModelPatch:
    """Package an LLM-authored operations list into a :class:`ModelPatch`.

    Parameters
    ----------
    work_order_id
        Identifier of the originating :class:`WorkOrder`. Required.
    model_version
        Model revision (typically ``mslice.model_revision``) the LLM was
        prompted against. Required.
    prompt
        The exact prompt string sent to the provider — its SHA-256 digest
        becomes ``Provenance.prompt_digest`` and, transitively, part of
        ``Provenance.proposal_id``.
    operations
        Domain-specific patch operations (e.g. ``{"op": "replace",
        "target": "COMP-1", "field": "intent", "value": ...}``). Copied
        defensively; caller can safely mutate their own list afterwards.

    Raises
    ------
    ValueError
        If ``prompt`` is empty (would produce a meaningless digest).
    """
    if not prompt:
        raise ValueError("pack_proposal: prompt must be non-empty")
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    provenance = Provenance(
        work_order_id=work_order_id,
        model_version=model_version,
        prompt_digest=digest,
    )
    return ModelPatch(
        provenance=provenance,
        operations=[dict(op) for op in operations],
    )


__all__ = ["pack_proposal"]
