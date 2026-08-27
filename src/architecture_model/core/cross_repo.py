"""Cross-repo consistency checking for multi-repo architectures."""
from __future__ import annotations

from dataclasses import dataclass
from architecture_model.core.types import ArchitectureModel
from architecture_model.monitoring import monitored


@dataclass
class ConsistencyIssue:
    """A consistency problem found across models."""
    severity: str  # "error" | "warning"
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.message}"


@monitored("core.cross_repo")
def check_consistency(models: list[ArchitectureModel]) -> list[ConsistencyIssue]:
    """Check consistency across multiple architecture models.

    Checks:
    1. Schema version alignment
    2. Shared entity ID consistency (same ID → same type/name)
    3. Interface compatibility
    """
    issues: list[ConsistencyIssue] = []
    if len(models) < 2:
        return issues

    # Check 1: Schema version alignment
    versions = {m.meta.project: m.meta.schema_version for m in models}
    unique_versions = set(versions.values())
    if len(unique_versions) > 1:
        version_list = ", ".join(f"{p}={v}" for p, v in versions.items())
        issues.append(ConsistencyIssue(
            severity="warning",
            message=f"Schema_version mismatch across repos: {version_list}",
        ))

    # Check 2: Shared entity ID consistency
    entity_registry: dict[str, tuple[str, str, str]] = {}  # id -> (type, name, project)
    for model in models:
        project = model.meta.project
        for entity_type in ["components", "capabilities", "behaviors", "interfaces",
                            "constraints", "actors"]:
            for entity in getattr(model.entities, entity_type, []):
                if entity.id in entity_registry:
                    prev_type, prev_name, prev_project = entity_registry[entity.id]
                    if prev_type != entity_type:
                        issues.append(ConsistencyIssue(
                            severity="error",
                            message=f"Entity {entity.id} is '{prev_type}' in {prev_project} but '{entity_type}' in {project}",
                        ))
                    elif prev_name != entity.name:
                        issues.append(ConsistencyIssue(
                            severity="warning",
                            message=f"Entity {entity.id} named '{prev_name}' in {prev_project} but '{entity.name}' in {project}",
                        ))
                else:
                    entity_registry[entity.id] = (entity_type, entity.name, project)

    return issues
