"""Concrete WriteBackProjector subclasses for Phase 4-A Tasks 3–6.

Each subclass targets a specific doc family + set of semantic fields.
All variants share the same infrastructure (base view dispatch, prompt
build, provider.structured, ModelPatch packing) — they differ only in
which fields they author and which entity kinds they target.

Entity-id filtering: LLM output is intersected with entities actually
present in the model fragment. Unknown ids (hallucinations) are dropped
silently so downstream apply steps never encounter dangling patches.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, ClassVar, Iterable

from architecture_model.ai.pack import pack_proposal
from architecture_model.ai.proposals import ModelPatch
from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.lifecycle.projectors.write_back import WriteBackProjector


def _all_entity_ids(fragment) -> set[str]:
    """Collect ids from every entity list on ``fragment.entities``.

    Works with the current 7-kind schema (actors, capabilities, behaviors,
    interfaces, constraints, layers, components) plus any future kinds
    exposed as list-valued attributes of ``fragment.entities``.
    """
    ids: set[str] = set()
    entities = fragment.entities
    for attr_name in dir(entities):
        if attr_name.startswith("_"):
            continue
        try:
            value = getattr(entities, attr_name)
        except AttributeError:  # pragma: no cover
            continue
        if isinstance(value, (list, tuple)):
            for item in value:
                entity_id = getattr(item, "id", None)
                if isinstance(entity_id, str):
                    ids.add(entity_id)
    return ids


def _digest_context(model_version: str, projector_name: str) -> str:
    payload = f"{projector_name}|{model_version}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


class Family1MissionLLM(WriteBackProjector):
    """Authors ``intent`` + ``goals`` on top-level Capabilities and Actors.

    Base projector: ``family1.mission`` (deterministic mission summary).
    LLM contract: return ``{"authored": [{entity_id, intent, goals}, ...]}``.
    """

    base_projector_name: ClassVar[str] = "family1.mission"
    projector_name: ClassVar[str] = "family1.mission.llm"

    def build_prompt(
        self,
        base_view: DiagramSpec,
        fragment,
        config: dict[str, Any],
    ) -> str:
        body = base_view.facets.get("body", "")
        return (
            "Given this deterministic base view of the system mission "
            "(Markdown below), propose values for each entity's `intent` "
            "(one sentence, why it exists) and `goals` (measurable outcomes, "
            "list of strings).\n\n"
            "Return JSON of shape:\n"
            '  {"authored": [{"entity_id": "...", "intent": "...", '
            '"goals": ["...", ...]}, ...]}\n\n'
            f"Base view:\n{body}\n"
        )

    def expected_proposal_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "authored": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["entity_id", "intent"],
                        "properties": {
                            "entity_id": {"type": "string"},
                            "intent": {"type": "string"},
                            "goals": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                }
            },
        }

    def pack_proposal(self, raw, fragment, config) -> ModelPatch:
        known = _all_entity_ids(fragment)
        operations: list[dict[str, Any]] = []
        for item in raw.get("authored", []) or []:
            entity_id = item.get("entity_id")
            if entity_id not in known:
                continue
            intent = item.get("intent")
            if intent:
                operations.append(
                    {
                        "op": "replace",
                        "target_id": entity_id,
                        "field": "intent",
                        "value": intent,
                    }
                )
            goals = item.get("goals")
            if isinstance(goals, list):
                operations.append(
                    {
                        "op": "replace",
                        "target_id": entity_id,
                        "field": "goals",
                        "value": list(goals),
                    }
                )
        # Digest is over the prompt payload — but pack_proposal computes
        # it from a prompt string. We reconstruct a stable string proxy
        # here so proposal_id is deterministic per (raw, projector) pair.
        prompt_proxy = json.dumps(
            {"projector": self.projector_name, "raw": raw}, sort_keys=True
        )
        return pack_proposal(
            work_order_id=config.get("__work_order_id", "wo-inline"),
            model_version=config.get("__model_revision", "rev-inline"),
            prompt=prompt_proxy,
            operations=operations,
        )


class Family3ComponentSpecLLM(WriteBackProjector):
    """Authors ``dependencies_rationale`` + ``trade_offs`` on Components.

    Base projector: ``family3.component_spec``. LLM contract:
    ``{"authored": [{entity_id, dependencies_rationale, trade_offs}, ...]}``.
    ``trade_offs`` may be a list of strings (each a rationale bullet).
    """

    base_projector_name: ClassVar[str] = "family3.component_spec"
    projector_name: ClassVar[str] = "family3.component_spec.llm"

    def build_prompt(self, base_view, fragment, config):
        body = base_view.facets.get("body", "")
        return (
            "Given this deterministic component spec (Markdown below), "
            "propose for each Component: `dependencies_rationale` (why "
            "each declared dependency exists) and `trade_offs` (design "
            "trade-offs, list of bullet strings).\n\n"
            "Return JSON of shape:\n"
            '  {"authored": [{"entity_id": "COMP-...", '
            '"dependencies_rationale": "...", '
            '"trade_offs": ["...", ...]}, ...]}\n\n'
            f"Base view:\n{body}\n"
        )

    def expected_proposal_schema(self):
        return {
            "type": "object",
            "properties": {
                "authored": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["entity_id"],
                        "properties": {
                            "entity_id": {"type": "string"},
                            "dependencies_rationale": {"type": "string"},
                            "trade_offs": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                }
            },
        }

    def pack_proposal(self, raw, fragment, config):
        component_ids = {c.id for c in fragment.entities.components}
        operations: list[dict[str, Any]] = []
        for item in raw.get("authored", []) or []:
            entity_id = item.get("entity_id")
            if entity_id not in component_ids:
                continue
            rationale = item.get("dependencies_rationale")
            if rationale:
                operations.append(
                    {
                        "op": "replace",
                        "target_id": entity_id,
                        "field": "dependencies_rationale",
                        "value": rationale,
                    }
                )
            trade_offs = item.get("trade_offs")
            if isinstance(trade_offs, list):
                operations.append(
                    {
                        "op": "replace",
                        "target_id": entity_id,
                        "field": "trade_offs",
                        "value": list(trade_offs),
                    }
                )
        prompt_proxy = json.dumps(
            {"projector": self.projector_name, "raw": raw}, sort_keys=True
        )
        return pack_proposal(
            work_order_id=config.get("__work_order_id", "wo-inline"),
            model_version=config.get("__model_revision", "rev-inline"),
            prompt=prompt_proxy,
            operations=operations,
        )


class Family7RiskLLM(WriteBackProjector):
    """Authors ``failure_modes`` + ``assumptions`` on Components, Behaviors,
    and Interfaces.

    Base projector: ``family7.risk``. LLM contract:
    ``{"authored": [{entity_id, failure_modes, assumptions}, ...]}``.
    Only entity ids belonging to Components, Behaviors, or Interfaces are
    accepted — non-target kinds are dropped even if the id exists.
    """

    base_projector_name: ClassVar[str] = "family7.risk"
    projector_name: ClassVar[str] = "family7.risk.llm"

    def build_prompt(self, base_view, fragment, config):
        body = base_view.facets.get("body", "")
        return (
            "Given this deterministic risk-assessment base view (Markdown "
            "below), propose for each Component / Behavior / Interface: "
            "`failure_modes` (list of ways the entity can fail) and "
            "`assumptions` (list of preconditions the design relies on).\n\n"
            "Return JSON of shape:\n"
            '  {"authored": [{"entity_id": "...", '
            '"failure_modes": ["...", ...], '
            '"assumptions": ["...", ...]}, ...]}\n\n'
            f"Base view:\n{body}\n"
        )

    def expected_proposal_schema(self):
        return {
            "type": "object",
            "properties": {
                "authored": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["entity_id"],
                        "properties": {
                            "entity_id": {"type": "string"},
                            "failure_modes": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "assumptions": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                }
            },
        }

    def pack_proposal(self, raw, fragment, config):
        target_ids = (
            {c.id for c in fragment.entities.components}
            | {b.id for b in fragment.entities.behaviors}
            | {i.id for i in fragment.entities.interfaces}
        )
        operations: list[dict[str, Any]] = []
        for item in raw.get("authored", []) or []:
            entity_id = item.get("entity_id")
            if entity_id not in target_ids:
                continue
            failure_modes = item.get("failure_modes")
            if isinstance(failure_modes, list):
                operations.append(
                    {
                        "op": "replace",
                        "target_id": entity_id,
                        "field": "failure_modes",
                        "value": list(failure_modes),
                    }
                )
            assumptions = item.get("assumptions")
            if isinstance(assumptions, list):
                operations.append(
                    {
                        "op": "replace",
                        "target_id": entity_id,
                        "field": "assumptions",
                        "value": list(assumptions),
                    }
                )
        prompt_proxy = json.dumps(
            {"projector": self.projector_name, "raw": raw}, sort_keys=True
        )
        return pack_proposal(
            work_order_id=config.get("__work_order_id", "wo-inline"),
            model_version=config.get("__model_revision", "rev-inline"),
            prompt=prompt_proxy,
            operations=operations,
        )


__all__ = [
    "Family1MissionLLM",
    "Family3ComponentSpecLLM",
    "Family7RiskLLM",
]
