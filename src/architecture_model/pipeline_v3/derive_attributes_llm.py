"""R7 — LLM-based Category B attribute inference stage for pipeline_v3.

Optional pipeline stage that proposes goals / requirements /
success_criteria / failure_modes / constraints as ``status=proposed``
promises using an LLM provider. Gated behind
``run_pipeline(infer_attributes=True)``.

Design: ``docs/plans/2026-09-20-r7-llm-attribute-inference-design.md``.

Idempotency policy:
    * Skip entities that already carry a ``verified`` promise for the
      target attribute.
    * Replace any existing ``proposed`` promises for the target attribute.
    * ``open``, ``typed-gap``, and ``intent`` promises are preserved.

Failure model:
    * A provider raise for a single (entity, attribute) pair leaves that
      pair unchanged; the rest of the pass continues.
    * A malformed provider response is treated as an empty proposal.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Iterable

from architecture_model.core.promise import Promise, PromiseStatus
from architecture_model.llm.provider import LLMProvider


__all__ = [
    "CATEGORY_B_ATTRIBUTES",
    "TARGET_KINDS",
    "AttributeInferenceRequest",
    "AttributeInferenceResult",
    "derive_attributes",
]


CATEGORY_B_ATTRIBUTES: tuple[str, ...] = (
    "goals",
    "requirements",
    "success_criteria",
    "failure_modes",
    "constraints",
)

TARGET_KINDS: tuple[str, ...] = (
    "behaviors",
    "components",
    "capabilities",
)

# Singular form for prompt substitution.
_KIND_SINGULAR = {
    "behaviors": "behavior",
    "components": "component",
    "capabilities": "capability",
}

_PROVENANCE = "pipeline_v3.derive_attributes_llm"


@dataclass(frozen=True)
class AttributeInferenceRequest:
    entity_id: str
    entity_kind: str
    entity_name: str
    entity_description: str
    target_attribute: str


@dataclass(frozen=True)
class AttributeInferenceResult:
    entity_id: str
    target_attribute: str
    items: tuple[str, ...]
    error: str | None = None


def derive_attributes(
    model: dict,
    *,
    provider: LLMProvider,
    target_kinds: tuple[str, ...] = TARGET_KINDS,
    target_attributes: tuple[str, ...] = CATEGORY_B_ATTRIBUTES,
) -> dict:
    """Return a new model dict with proposed attribute promises appended.

    Args:
        model: v3 model dict (as returned by ``load_v3_model``).
        provider: An :class:`LLMProvider` — its ``.structured()`` method is
            called once per (entity, target_attribute) pair.
        target_kinds: Which entity kinds to iterate. Default: the three
            promotion-strict kinds.
        target_attributes: Which attributes to infer per entity. Default:
            all five Category B attributes.

    Returns:
        A deep-copied model dict. Input model is not mutated.
    """
    out = copy.deepcopy(model)
    entities = out.get("entities", {})

    for kind in target_kinds:
        kind_singular = _KIND_SINGULAR.get(kind, kind.rstrip("s"))
        for entity in sorted(entities.get(kind, []), key=lambda e: e.get("id", "")):
            for attribute in target_attributes:
                _maybe_infer(entity, kind_singular, attribute, provider)

    return out


# --------------------------------------------------------------------------
# Internals
# --------------------------------------------------------------------------


def _maybe_infer(
    entity: dict, entity_kind: str, attribute: str, provider: LLMProvider
) -> None:
    """Infer one attribute for one entity, mutating ``entity["promises"]`` in place."""
    promises = entity.setdefault("promises", [])

    if _has_verified(promises, attribute):
        return

    request = AttributeInferenceRequest(
        entity_id=entity.get("id", ""),
        entity_kind=entity_kind,
        entity_name=entity.get("name", ""),
        entity_description=entity.get("description", ""),
        target_attribute=attribute,
    )

    result = _call_provider(request, provider)
    if result.error is not None:
        return

    # Remove any existing proposed promises for this attribute.
    entity["promises"] = [
        p for p in promises
        if not (p.get("attribute") == attribute and p.get("status") == PromiseStatus.PROPOSED.value)
    ]

    # Append new proposed promises.
    for item in result.items:
        content = item.strip()
        if not content:
            continue
        promise = Promise(
            attribute=attribute,
            content=content,
            owner_entity=entity["id"],
            status=PromiseStatus.PROPOSED,
            provenance=_PROVENANCE,
        )
        entity["promises"].append(promise.to_dict())


def _has_verified(promises: Iterable[dict], attribute: str) -> bool:
    for p in promises:
        if p.get("attribute") == attribute and p.get("status") == PromiseStatus.VERIFIED.value:
            return True
    return False


def _call_provider(
    request: AttributeInferenceRequest, provider: LLMProvider
) -> AttributeInferenceResult:
    prompt = _build_prompt(request)
    schema = _build_schema(request.target_attribute)
    try:
        raw = provider.structured(prompt, schema)
    except Exception as exc:
        return AttributeInferenceResult(
            entity_id=request.entity_id,
            target_attribute=request.target_attribute,
            items=(),
            error=f"{type(exc).__name__}: {exc}",
        )

    items = _parse_items(raw, request.target_attribute)
    return AttributeInferenceResult(
        entity_id=request.entity_id,
        target_attribute=request.target_attribute,
        items=items,
    )


def _build_prompt(request: AttributeInferenceRequest) -> str:
    """Small deterministic prompt. Kept minimal for Phase-1 R7 rollout.

    A follow-on (R7b) can swap in the ``fill_promise.md`` template + full
    context assembly. For now, callers can wrap this stage with richer
    context if needed.
    """
    return (
        f"Propose 1-5 concise items for the `{request.target_attribute}` "
        f"of this {request.entity_kind}.\n\n"
        f"Entity id: {request.entity_id}\n"
        f"Name: {request.entity_name}\n"
        f"Description: {request.entity_description}\n\n"
        f"Each item must be a single declarative sentence. "
        f"Return strict JSON matching the provided schema."
    )


def _build_schema(attribute: str) -> dict:
    return {
        "type": "object",
        "properties": {
            attribute: {
                "type": "array",
                "items": {"type": "string", "minLength": 1, "maxLength": 500},
                "maxItems": 5,
            },
        },
        "required": [attribute],
        "additionalProperties": False,
    }


def _parse_items(raw: object, attribute: str) -> tuple[str, ...]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return ()
    if not isinstance(raw, dict):
        return ()
    items = raw.get(attribute)
    if not isinstance(items, list):
        return ()
    return tuple(str(x) for x in items if isinstance(x, (str, int, float)) and str(x).strip())
