"""
ModelRefiner: Iterative model refinement using validator feedback.

Takes an extracted ArchitectureModel, validates it, identifies issues,
and uses an LLM to fix problems (orphaned entities, missing relationships,
invalid references) through iterative refinement rounds.
"""

from __future__ import annotations

from typing import Any, Optional

import yaml

from architecture_model.core.parser import _parse_raw
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Relationship,
)
from architecture_model.core.validator import validate_model, ValidationResult
from architecture_model.training.surrogate import _strip_fences


_REFINE_SYSTEM_PROMPT = """\
You are an architecture model repair engine. Given a model with validation \
issues, you must fix the problems by adding missing entities or relationships.

Common issues:
- Orphaned entities: components/capabilities with no relationships → add relationships
- Missing layers: components reference layers that don't exist → add the layers
- Dangling references: relationships reference non-existent entities → add the entities

Output ONLY the corrections as valid YAML. Include new entities and/or relationships:

layers:
  - id: <id>
    name: <name>
    status: ACTIVE
components:
  - id: <id>
    name: <name>
    status: ACTIVE
    layer: <layer_id>
relationships:
  - type: <type>
    from: <source_id>
    to: <target_id>

Output raw YAML only — no markdown fences, no explanation. \
Only include entities/relationships that need to be ADDED to fix issues."""


class ModelRefiner:
    """Iterative model refiner using validator feedback.

    Validates the model, identifies issues, asks the LLM to fix them,
    and merges corrections back. Repeats until score is acceptable
    or max_rounds is reached.
    """

    def __init__(
        self,
        client: Any,
        max_rounds: int = 3,
        score_threshold: int = 95,
    ) -> None:
        self._client = client
        self._max_rounds = max_rounds
        self._score_threshold = score_threshold

    async def refine(
        self, model: ArchitectureModel, code_context: str
    ) -> ArchitectureModel:
        """Refine the model through iterative validation and correction.

        Args:
            model: The model to refine.
            code_context: Original code context for reference.

        Returns:
            The refined model (may be the same if already high-scoring).
        """
        for round_num in range(self._max_rounds):
            # Validate current model
            result = validate_model(model)

            # If score is good enough, stop
            if result.score >= self._score_threshold:
                return model

            # Build refinement prompt with issues
            prompt = self._build_refinement_prompt(model, result, code_context)

            # Ask LLM for corrections
            messages = [
                {"role": "system", "content": _REFINE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]

            try:
                response = await self._client._chat(messages)
                content = response.get("message", {}).get("content", "")
                content = _strip_fences(content)

                # Parse corrections
                corrections = yaml.safe_load(content)
                if isinstance(corrections, dict):
                    model = self._apply_corrections(model, corrections)
            except Exception:
                # If LLM call fails, return what we have
                break

        return model

    def _build_refinement_prompt(
        self,
        model: ArchitectureModel,
        validation: ValidationResult,
        code_context: str,
    ) -> str:
        """Build a prompt describing current issues and requesting fixes."""
        parts = []

        # Current model summary
        parts.append("# CURRENT MODEL")
        parts.append(f"Entities: {model.entity_count}")
        parts.append(f"Relationships: {model.relationship_count}")
        parts.append(f"Validation score: {validation.score}/100")

        # Issues
        parts.append("\n# VALIDATION ISSUES")
        for issue in validation.issues[:15]:  # Limit to top 15
            parts.append(f"- {issue}")

        # Entity listing (so LLM knows what exists)
        parts.append("\n# EXISTING ENTITIES")
        entity_summary = self._summarize_entities(model)
        parts.append(entity_summary)

        # Code context (truncated)
        parts.append("\n# CODE CONTEXT (for reference)")
        parts.append(code_context[:2000])

        parts.append("\n# INSTRUCTIONS")
        parts.append(
            "Fix the validation issues above by adding missing entities "
            "or relationships. Output ONLY the new entities/relationships to ADD."
        )

        return "\n".join(parts)

    def _summarize_entities(self, model: ArchitectureModel) -> str:
        """Produce a compact YAML summary of current entities."""
        summary: dict[str, list] = {}

        if model.entities.layers:
            summary["layers"] = [
                {"id": l.id, "name": l.name} for l in model.entities.layers
            ]
        if model.entities.components:
            summary["components"] = [
                {"id": c.id, "name": c.name, "layer": c.layer}
                for c in model.entities.components
            ]
        if model.entities.actors:
            summary["actors"] = [
                {"id": a.id, "name": a.name} for a in model.entities.actors
            ]
        if model.entities.capabilities:
            summary["capabilities"] = [
                {"id": c.id, "name": c.name} for c in model.entities.capabilities
            ]
        if model.entities.behaviors:
            summary["behaviors"] = [
                {"id": b.id, "name": b.name} for b in model.entities.behaviors
            ]
        if model.entities.interfaces:
            summary["interfaces"] = [
                {"id": i.id, "name": i.name} for i in model.entities.interfaces
            ]
        if model.entities.constraints:
            summary["constraints"] = [
                {"id": c.id, "name": c.name} for c in model.entities.constraints
            ]

        try:
            return yaml.dump(summary, default_flow_style=False, sort_keys=False)
        except Exception:
            return str(summary)

    def _apply_corrections(
        self, model: ArchitectureModel, corrections: dict[str, Any]
    ) -> ArchitectureModel:
        """Merge corrections into the existing model.

        Adds new entities and relationships without removing existing ones.
        """
        # Build a combined dict from existing model + corrections
        existing = self._model_to_dict(model)

        # Merge new entities
        entity_types = [
            "actors", "capabilities", "behaviors",
            "interfaces", "constraints", "layers", "components",
        ]
        for etype in entity_types:
            new_items = corrections.get(etype, [])
            if isinstance(new_items, list):
                existing_ids = {
                    e.get("id") for e in existing["entities"].get(etype, [])
                }
                for item in new_items:
                    if isinstance(item, dict) and item.get("id") not in existing_ids:
                        existing["entities"].setdefault(etype, []).append(item)

        # Merge new relationships
        new_rels = corrections.get("relationships", [])
        if isinstance(new_rels, list):
            for rel in new_rels:
                if isinstance(rel, dict):
                    existing.setdefault("relationships", []).append(rel)

        # Parse back into model
        try:
            return _parse_raw(existing)
        except Exception:
            return model

    def _model_to_dict(self, model: ArchitectureModel) -> dict[str, Any]:
        """Convert model back to a raw dict for merging."""
        result: dict[str, Any] = {
            "meta": {
                "schema_version": model.meta.schema_version,
                "project": model.meta.project,
            },
            "entities": {},
            "relationships": [],
        }

        # Entities
        if model.entities.actors:
            result["entities"]["actors"] = [
                {"id": a.id, "name": a.name, "status": a.status.value,
                 "type": getattr(a, "type", "human")}
                for a in model.entities.actors
            ]
        if model.entities.capabilities:
            result["entities"]["capabilities"] = [
                {"id": c.id, "name": c.name, "status": c.status.value}
                for c in model.entities.capabilities
            ]
        if model.entities.behaviors:
            result["entities"]["behaviors"] = [
                {"id": b.id, "name": b.name, "status": b.status.value}
                for b in model.entities.behaviors
            ]
        if model.entities.interfaces:
            result["entities"]["interfaces"] = [
                {"id": i.id, "name": i.name, "status": i.status.value,
                 "type": getattr(i, "type", "rest")}
                for i in model.entities.interfaces
            ]
        if model.entities.constraints:
            result["entities"]["constraints"] = [
                {"id": c.id, "name": c.name, "status": c.status.value}
                for c in model.entities.constraints
            ]
        if model.entities.layers:
            result["entities"]["layers"] = [
                {"id": l.id, "name": l.name, "status": l.status.value}
                for l in model.entities.layers
            ]
        if model.entities.components:
            result["entities"]["components"] = [
                {"id": c.id, "name": c.name, "status": c.status.value,
                 "layer": getattr(c, "layer", "")}
                for c in model.entities.components
            ]

        # Relationships
        for rel in model.relationships:
            result["relationships"].append({
                "type": rel.type.value,
                "from": rel.from_id,
                "to": rel.to_id,
            })

        return result
