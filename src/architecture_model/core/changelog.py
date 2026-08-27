"""Model changelog — human-readable diff between model versions."""
from architecture_model.core.types import ArchitectureModel
from architecture_model.monitoring import monitored


@monitored("core.changelog")
def generate_changelog(old: ArchitectureModel, new: ArchitectureModel) -> str:
    """Generate human-readable changelog between two model versions."""
    sections = []

    for entity_type in ["components", "capabilities", "behaviors", "interfaces",
                         "constraints", "requirements", "actors"]:
        old_entities = {e.id: e for e in getattr(old.entities, entity_type, [])}
        new_entities = {e.id: e for e in getattr(new.entities, entity_type, [])}

        added = set(new_entities) - set(old_entities)
        removed = set(old_entities) - set(new_entities)
        common = set(old_entities) & set(new_entities)

        if added:
            sections.append(f"### Added {entity_type}")
            for eid in sorted(added):
                sections.append(f"- {eid}: {new_entities[eid].name}")

        if removed:
            sections.append(f"### Removed {entity_type}")
            for eid in sorted(removed):
                sections.append(f"- {eid}: {old_entities[eid].name}")

        changed = []
        for eid in sorted(common):
            if old_entities[eid].description != new_entities[eid].description:
                changed.append(eid)
            elif old_entities[eid].intent != new_entities[eid].intent:
                changed.append(eid)
        if changed:
            sections.append(f"### Changed {entity_type}")
            for eid in changed:
                sections.append(f"- {eid}: {new_entities[eid].name}")

    if not sections:
        return "No changes detected."

    header = f"# Changelog\n\n**From:** {old.meta.generated_at} **To:** {new.meta.generated_at}\n\n"
    return header + "\n".join(sections)
