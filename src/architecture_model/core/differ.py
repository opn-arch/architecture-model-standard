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

from .types import ArchitectureModel, Relationship, Status  # noqa: F401  (Relationship/Status re-exported for callers)


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

    Delegates to :func:`architecture_model.lifecycle.diff.semantic_diff` and
    translates the canonical ``SemanticDiff`` back into the legacy
    ``ModelDiff`` shape expected by existing consumers. Relationship
    endpoints are exposed via ``from_id``/``to_id`` (matching the model's
    ``from``/``to`` keys) — never ``source``/``target``.

    Args:
        old_model: The previous/baseline model.
        new_model: The current/updated model.

    Returns:
        ModelDiff with all detected changes.
    """
    from architecture_model.lifecycle.diff import semantic_diff

    canonical = semantic_diff(old_model, new_model)
    result = ModelDiff()

    # Map plural entity-kind keys (as used by Entities dataclass) to the
    # singular entity_type strings that legacy consumers/report expect.
    _kind_singular = {
        "actors": "actor",
        "capabilities": "capability",
        "behaviors": "behavior",
        "interfaces": "interface",
        "constraints": "constraint",
        "layers": "layer",
        "components": "component",
    }

    # Build id → name lookups so we can populate EntityChange.entity_name.
    def _index_by_id(items: list) -> dict[str, Any]:
        return {e.id: e for e in items}

    old_index: dict[str, dict[str, Any]] = {
        kind: _index_by_id(getattr(old_model.entities, kind)) for kind in _kind_singular
    }
    new_index: dict[str, dict[str, Any]] = {
        kind: _index_by_id(getattr(new_model.entities, kind)) for kind in _kind_singular
    }

    for kind, singular in _kind_singular.items():
        kind_diff = canonical.entities.get(kind)
        if kind_diff is None:
            continue

        for eid in kind_diff.added:
            entity = new_index[kind].get(eid)
            name = getattr(entity, "name", eid)
            result.entity_changes.append(
                EntityChange(
                    change_type=ChangeType.ADDED,
                    entity_type=singular,
                    entity_id=eid,
                    entity_name=name,
                )
            )
        for eid in kind_diff.removed:
            entity = old_index[kind].get(eid)
            name = getattr(entity, "name", eid)
            result.entity_changes.append(
                EntityChange(
                    change_type=ChangeType.REMOVED,
                    entity_type=singular,
                    entity_id=eid,
                    entity_name=name,
                )
            )

        # Group per-field `changed` entries by entity id and reduce to
        # a single MODIFIED entry per entity (matching legacy shape).
        per_entity: dict[str, list[str]] = {}
        for change in kind_diff.changed:
            per_entity.setdefault(change["id"], []).append(
                _format_field_change(change["field"], change["old"], change["new"])
            )
        for eid, details in per_entity.items():
            entity = new_index[kind].get(eid) or old_index[kind].get(eid)
            name = getattr(entity, "name", eid)
            result.entity_changes.append(
                EntityChange(
                    change_type=ChangeType.MODIFIED,
                    entity_type=singular,
                    entity_id=eid,
                    entity_name=name,
                    details="; ".join(details),
                )
            )

    # Relationships: canonical uses from/to; legacy shape uses from_id/to_id
    # on RelationshipChange (also from/to semantically — never source/target).
    for entry in canonical.relationships.added:
        result.relationship_changes.append(
            RelationshipChange(
                change_type=ChangeType.ADDED,
                rel_type=entry["type"],
                from_id=entry["from"],
                to_id=entry["to"],
            )
        )
    for entry in canonical.relationships.removed:
        result.relationship_changes.append(
            RelationshipChange(
                change_type=ChangeType.REMOVED,
                rel_type=entry["type"],
                from_id=entry["from"],
                to_id=entry["to"],
            )
        )
    # semantic_diff also reports per-attribute relationship deltas; surface
    # them as MODIFIED entries so callers see attribute-level drift.
    seen_modified: set[tuple[str, str, str]] = set()
    for entry in canonical.relationships.changed:
        key = (entry["from"], entry["to"], entry["type"])
        if key in seen_modified:
            continue
        seen_modified.add(key)
        result.relationship_changes.append(
            RelationshipChange(
                change_type=ChangeType.MODIFIED,
                rel_type=entry["type"],
                from_id=entry["from"],
                to_id=entry["to"],
            )
        )

    return result


def _format_field_change(field_name: str, old_value: Any, new_value: Any) -> str:
    """Render a single field change as a legacy-style detail string."""
    if field_name == "description":
        return "description changed"
    if field_name == "name":
        return f"name: '{old_value}' -> '{new_value}'"
    # Enum-valued fields (status, priority) come through as plain values
    # thanks to semantic_diff's _to_plain step.
    return f"{field_name}: {old_value} -> {new_value}"
