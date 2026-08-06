"""
Differ: Compare two architecture model versions and produce a structured diff.

Use cases:
- Detect architectural drift between regenerations
- Show what changed when artifacts are updated
- Inform staleness detection (which entities changed → which artifacts are stale)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from architecture_model.monitoring import monitored

from .types import ArchitectureModel, Relationship, Status


class ChangeType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


@dataclass
class EntityChange:
    change_type: ChangeType
    entity_type: str  # "actor", "capability", etc.
    entity_id: str
    entity_name: str
    details: str = ""  # What specifically changed


@dataclass
class RelationshipChange:
    change_type: ChangeType
    rel_type: str
    from_id: str
    to_id: str


@dataclass
class ModelDiff:
    entity_changes: list[EntityChange] = field(default_factory=list)
    relationship_changes: list[RelationshipChange] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.entity_changes or self.relationship_changes)

    @property
    def added_count(self) -> int:
        return sum(1 for c in self.entity_changes if c.change_type == ChangeType.ADDED)

    @property
    def removed_count(self) -> int:
        return sum(1 for c in self.entity_changes if c.change_type == ChangeType.REMOVED)

    @property
    def modified_count(self) -> int:
        return sum(1 for c in self.entity_changes if c.change_type == ChangeType.MODIFIED)

    def summary(self) -> str:
        if not self.has_changes:
            return "No changes detected."
        return (
            f"Changes: +{self.added_count} -{self.removed_count} ~{self.modified_count} entities, "
            f"{len(self.relationship_changes)} relationship changes"
        )

    def format_report(self) -> str:
        """Format a human-readable diff report."""
        if not self.has_changes:
            return "No changes detected between model versions."

        lines: list[str] = [
            "# Architecture Model Diff",
            "",
            self.summary(),
            "",
        ]

        if self.entity_changes:
            lines.append("## Entity Changes")
            lines.append("")

            by_type: dict[str, list[EntityChange]] = {}
            for change in self.entity_changes:
                by_type.setdefault(change.entity_type, []).append(change)

            for etype, changes in sorted(by_type.items()):
                lines.append(f"### {etype.title()}s")
                for c in changes:
                    prefix = {"added": "+", "removed": "-", "modified": "~"}[c.change_type.value]
                    detail = f" ({c.details})" if c.details else ""
                    lines.append(f"  {prefix} {c.entity_id}: {c.entity_name}{detail}")
                lines.append("")

        if self.relationship_changes:
            lines.append("## Relationship Changes")
            lines.append("")
            for rc in self.relationship_changes:
                prefix = {"added": "+", "removed": "-", "modified": "~"}[rc.change_type.value]
                lines.append(f"  {prefix} {rc.from_id} --{rc.rel_type}--> {rc.to_id}")

        return "\n".join(lines)

    def affected_artifacts(self) -> set[str]:
        """
        Determine which artifacts might be stale based on changes.

        Returns set of artifact names that should be regenerated.
        """
        affected: set[str] = set()

        for change in self.entity_changes:
            etype = change.entity_type
            if etype in ("actor", "behavior"):
                affected.add("use-cases")
            if etype == "capability":
                affected.add("functional-architecture")
                affected.add("use-cases")
            if etype in ("layer", "component"):
                affected.add("logical-architecture")
            if etype == "interface":
                affected.add("icd")
            if etype == "constraint":
                affected.add("requirements-analysis")
            # All changes affect readme
            affected.add("readme")

        return affected


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@monitored(
    module="core.differ",
    outputs=lambda r: {"added": r.added_count, "removed": r.removed_count, "modified": r.modified_count},
)
def diff_models(
    old_model: ArchitectureModel,
    new_model: ArchitectureModel,
) -> ModelDiff:
    """
    Compare two model versions and produce a structured diff.

    Args:
        old_model: The previous/baseline model.
        new_model: The current/updated model.

    Returns:
        ModelDiff with all detected changes.
    """
    result = ModelDiff()

    # Compare entities
    _diff_entity_list(old_model.entities.actors, new_model.entities.actors, "actor", result)
    _diff_entity_list(
        old_model.entities.capabilities, new_model.entities.capabilities, "capability", result
    )
    _diff_entity_list(
        old_model.entities.behaviors, new_model.entities.behaviors, "behavior", result
    )
    _diff_entity_list(
        old_model.entities.interfaces, new_model.entities.interfaces, "interface", result
    )
    _diff_entity_list(
        old_model.entities.constraints, new_model.entities.constraints, "constraint", result
    )
    _diff_entity_list(old_model.entities.layers, new_model.entities.layers, "layer", result)
    _diff_entity_list(
        old_model.entities.components, new_model.entities.components, "component", result
    )

    # Compare relationships
    _diff_relationships(old_model.relationships, new_model.relationships, result)

    return result


# ---------------------------------------------------------------------------
# Internal comparison logic
# ---------------------------------------------------------------------------


def _diff_entity_list(
    old_entities: list,
    new_entities: list,
    entity_type: str,
    result: ModelDiff,
) -> None:
    """Compare two lists of entities by ID."""
    old_map = {e.id: e for e in old_entities}
    new_map = {e.id: e for e in new_entities}

    old_ids = set(old_map.keys())
    new_ids = set(new_map.keys())

    # Added
    for eid in new_ids - old_ids:
        entity = new_map[eid]
        result.entity_changes.append(
            EntityChange(
                change_type=ChangeType.ADDED,
                entity_type=entity_type,
                entity_id=eid,
                entity_name=entity.name,
            )
        )

    # Removed
    for eid in old_ids - new_ids:
        entity = old_map[eid]
        result.entity_changes.append(
            EntityChange(
                change_type=ChangeType.REMOVED,
                entity_type=entity_type,
                entity_id=eid,
                entity_name=entity.name,
            )
        )

    # Modified
    for eid in old_ids & new_ids:
        old_e = old_map[eid]
        new_e = new_map[eid]
        changes = _detect_entity_changes(old_e, new_e)
        if changes:
            result.entity_changes.append(
                EntityChange(
                    change_type=ChangeType.MODIFIED,
                    entity_type=entity_type,
                    entity_id=eid,
                    entity_name=new_e.name,
                    details="; ".join(changes),
                )
            )


def _detect_entity_changes(old_entity: Any, new_entity: Any) -> list[str]:
    """Detect specific field-level changes between two entities."""
    changes: list[str] = []

    # Check common fields
    if old_entity.name != new_entity.name:
        changes.append(f"name: '{old_entity.name}' -> '{new_entity.name}'")
    if old_entity.status != new_entity.status:
        changes.append(f"status: {old_entity.status.value} -> {new_entity.status.value}")
    if old_entity.description != new_entity.description:
        changes.append("description changed")

    # Check type-specific fields
    if hasattr(old_entity, "source_block") and old_entity.source_block != new_entity.source_block:
        changes.append(f"source_block: {old_entity.source_block} -> {new_entity.source_block}")
    if hasattr(old_entity, "layer") and old_entity.layer != new_entity.layer:
        changes.append(f"layer: {old_entity.layer} -> {new_entity.layer}")
    if hasattr(old_entity, "priority") and old_entity.priority != new_entity.priority:
        changes.append(f"priority: {old_entity.priority.value} -> {new_entity.priority.value}")

    return changes


def _diff_relationships(
    old_rels: list[Relationship],
    new_rels: list[Relationship],
    result: ModelDiff,
) -> None:
    """Compare relationship sets."""

    def rel_key(r: Relationship) -> tuple:
        return (r.type.value, r.from_id, r.to_id)

    old_set = {rel_key(r) for r in old_rels}
    new_set = {rel_key(r) for r in new_rels}

    for key in new_set - old_set:
        result.relationship_changes.append(
            RelationshipChange(
                change_type=ChangeType.ADDED,
                rel_type=key[0],
                from_id=key[1],
                to_id=key[2],
            )
        )

    for key in old_set - new_set:
        result.relationship_changes.append(
            RelationshipChange(
                change_type=ChangeType.REMOVED,
                rel_type=key[0],
                from_id=key[1],
                to_id=key[2],
            )
        )
