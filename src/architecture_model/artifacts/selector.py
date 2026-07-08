"""Model-driven artifact selector.

Determines which SE documentation artifacts are appropriate to generate
based on the richness of an ArchitectureModel. Pure function — no I/O, no LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from architecture_model.core.types import ArchitectureModel


@dataclass
class ArtifactSpec:
    """Specification for a generatable SE documentation artifact."""

    id: str  # e.g. "api-reference"
    name: str  # e.g. "API Reference"
    category: str  # "architecture" | "design" | "operations" | "requirements"
    requires: list[str]  # what model content is needed
    priority: int  # 1=always if data exists, 2=recommended, 3=optional


# ---------------------------------------------------------------------------
# Artifact Registry — the 12 supported artifacts
# ---------------------------------------------------------------------------

ARTIFACT_REGISTRY: list[ArtifactSpec] = [
    ArtifactSpec(
        id="system-overview",
        name="System Overview",
        category="architecture",
        requires=["components"],
        priority=1,
    ),
    ArtifactSpec(
        id="component-catalog",
        name="Component Catalog",
        category="architecture",
        requires=["components"],
        priority=1,
    ),
    ArtifactSpec(
        id="api-reference",
        name="API Reference",
        category="design",
        requires=["interfaces"],
        priority=1,
    ),
    ArtifactSpec(
        id="capability-map",
        name="Capability Map",
        category="requirements",
        requires=["capabilities"],
        priority=1,
    ),
    ArtifactSpec(
        id="behavior-flows",
        name="Behavior Flows",
        category="design",
        requires=["behaviors"],
        priority=2,
    ),
    ArtifactSpec(
        id="constraint-register",
        name="Constraint Register",
        category="requirements",
        requires=["constraints"],
        priority=2,
    ),
    ArtifactSpec(
        id="dependency-graph",
        name="Dependency Graph",
        category="architecture",
        requires=["components", "relationships"],
        priority=2,
    ),
    ArtifactSpec(
        id="layer-architecture",
        name="Layer Architecture",
        category="architecture",
        requires=["layers"],
        priority=2,
    ),
    ArtifactSpec(
        id="deployment-view",
        name="Deployment View",
        category="operations",
        requires=["components", "layers"],
        priority=2,
    ),
    ArtifactSpec(
        id="integration-guide",
        name="Integration Guide",
        category="design",
        requires=["interfaces", "components"],
        priority=3,
    ),
    ArtifactSpec(
        id="test-strategy",
        name="Test Strategy",
        category="operations",
        requires=["manifest.tests"],
        priority=3,
    ),
    ArtifactSpec(
        id="metrics-dashboard",
        name="Metrics Dashboard",
        category="operations",
        requires=["manifest.metrics"],
        priority=3,
    ),
]


def _requirement_met(req: str, model: ArchitectureModel, manifest: dict | None) -> bool:
    """Check whether a single requirement string is satisfied."""
    if req == "components":
        return len(model.entities.components) > 0
    elif req == "interfaces":
        return len(model.entities.interfaces) > 0
    elif req == "capabilities":
        return len(model.entities.capabilities) > 0
    elif req == "behaviors":
        return len(model.entities.behaviors) > 0
    elif req == "constraints":
        return len(model.entities.constraints) > 0
    elif req == "layers":
        return len(model.entities.layers) > 0
    elif req == "relationships":
        return len(model.relationships) > 0
    elif req == "manifest.tests":
        if manifest is None:
            return False
        tests = manifest.get("test_files") or manifest.get("tests")
        return bool(tests)
    elif req == "manifest.metrics":
        if manifest is None:
            return False
        return bool(manifest.get("metrics"))
    else:
        return False


def select_artifacts(
    model: ArchitectureModel, manifest: dict | None = None
) -> list[ArtifactSpec]:
    """Return artifacts appropriate for this model's richness.

    For each artifact in the registry, check if the model has the required entities.
    Return only those artifacts whose requirements are met.
    Results sorted by priority (1 first), then alphabetically by id.
    """
    selected: list[ArtifactSpec] = []

    for spec in ARTIFACT_REGISTRY:
        if all(_requirement_met(req, model, manifest) for req in spec.requires):
            selected.append(spec)

    selected.sort(key=lambda s: (s.priority, s.id))
    return selected


def get_artifact_spec(artifact_id: str) -> ArtifactSpec | None:
    """Look up a single artifact spec by ID."""
    for spec in ARTIFACT_REGISTRY:
        if spec.id == artifact_id:
            return spec
    return None


# ---------------------------------------------------------------------------
# Subsystem Decomposition Support
# ---------------------------------------------------------------------------


@dataclass
class SubsystemInfo:
    """Description of a subsystem within a larger system."""

    id: str  # e.g. "F1", "core", "cli"
    name: str  # e.g. "Core Engine", "CLI Commands"
    components: list[str]  # component IDs belonging to this subsystem
    file_count: int = 0  # number of source files
    test_count: int = 0  # number of test files


def should_decompose(model: ArchitectureModel, manifest: dict | None = None) -> bool:
    """Determine if system is complex enough to warrant per-subsystem docs.

    Heuristic: returns True if ANY of:
    - More than 5 functional blocks (distinct f_block values on components)
    - More than 50 source files in manifest
    - More than 20 components
    """
    # Check component count
    if len(model.entities.components) > 20:
        return True

    # Check distinct f_block values
    fblocks = {c.f_block for c in model.entities.components if c.f_block}
    if len(fblocks) > 5:
        return True

    # Check file count from manifest
    if manifest is not None:
        # Try metrics.total_files first
        total_files = manifest.get("metrics", {}).get("total_files", 0)
        if total_files > 50:
            return True
        # Fall back to counting modules list
        modules = manifest.get("modules")
        if modules and len(modules) > 50:
            return True

    return False


# Artifacts appropriate for subsystem-level generation
SUBSYSTEM_ARTIFACTS: list[str] = [
    "component-catalog",
    "api-reference",
    "behavior-flows",
    "test-strategy",
]


def _subsystem_requirement_met(
    req: str,
    subsystem: SubsystemInfo,
    model: ArchitectureModel,
    manifest: dict | None,
) -> bool:
    """Check whether a requirement is met scoped to a subsystem's components."""
    if req == "components":
        return len(subsystem.components) > 0
    elif req == "interfaces":
        comp_set = set(subsystem.components)
        return any(
            i.provider in comp_set or i.consumer in comp_set
            for i in model.entities.interfaces
        )
    elif req == "behaviors":
        comp_set = set(subsystem.components)
        return any(b.actor in comp_set for b in model.entities.behaviors)
    elif req == "manifest.tests":
        return subsystem.test_count > 0
    else:
        # Fall back to system-level logic for other requirements
        return _requirement_met(req, model, manifest)


def select_subsystem_artifacts(
    subsystem: SubsystemInfo,
    model: ArchitectureModel,
    manifest: dict | None = None,
) -> list[ArtifactSpec]:
    """Select artifacts appropriate for a subsystem (subset of system-level).

    Only returns artifacts from SUBSYSTEM_ARTIFACTS that:
    1. Are in the SUBSYSTEM_ARTIFACTS list
    2. Have their requirements met (scoped to subsystem's components)

    Returns empty list if subsystem has no components.
    """
    if not subsystem.components:
        return []

    selected: list[ArtifactSpec] = []

    for spec in ARTIFACT_REGISTRY:
        if spec.id not in SUBSYSTEM_ARTIFACTS:
            continue
        if all(
            _subsystem_requirement_met(req, subsystem, model, manifest)
            for req in spec.requires
        ):
            selected.append(spec)

    selected.sort(key=lambda s: (s.priority, s.id))
    return selected
