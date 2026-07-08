"""Artifact template definitions.

Each template describes HOW to generate a specific SE documentation artifact:
- What sections it has
- What model/manifest data feeds each section
- What instructions the LLM follows for each section
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TemplateSection:
    """A single section within an artifact template."""

    heading: str  # e.g. "## Overview", "## Endpoints"
    source: str  # which model/manifest data feeds this section
    instructions: str  # LLM instructions for generating this section content


@dataclass
class ArtifactTemplate:
    """Full template for generating one artifact."""

    artifact_id: str  # matches ArtifactSpec.id from selector.py
    filename: str  # output filename, e.g. "api-reference.md"
    sections: list[TemplateSection]
    system_prompt: str  # role/context prompt for the LLM


# ---------------------------------------------------------------------------
# Template Definitions — one per artifact in ARTIFACT_REGISTRY
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, ArtifactTemplate] = {
    "system-overview": ArtifactTemplate(
        artifact_id="system-overview",
        filename="system-overview.md",
        system_prompt=(
            "You are a technical writer documenting a software system's architecture. "
            "Write clear, precise documentation based on the provided architecture model data."
        ),
        sections=[
            TemplateSection(
                heading="## System Purpose",
                source="meta",
                instructions=(
                    "Describe what this system does based on the project metadata. "
                    "State the project name and its primary purpose."
                ),
            ),
            TemplateSection(
                heading="## Architecture Overview",
                source="layers",
                instructions=(
                    "Describe the high-level architecture using the layer structure. "
                    "If no layers, describe based on component organization."
                ),
            ),
            TemplateSection(
                heading="## Key Components",
                source="components",
                instructions=(
                    "List and briefly describe each major component, its role, "
                    "and technology."
                ),
            ),
            TemplateSection(
                heading="## Key Relationships",
                source="relationships",
                instructions=(
                    "Describe how components interact, using the relationship data."
                ),
            ),
        ],
    ),
    "component-catalog": ArtifactTemplate(
        artifact_id="component-catalog",
        filename="component-catalog.md",
        system_prompt=(
            "You are a technical writer creating a component reference catalog. "
            "Be precise and include all components with their details."
        ),
        sections=[
            TemplateSection(
                heading="## Components",
                source="components",
                instructions=(
                    "For each component, document: name, kind, layer, status, files, "
                    "and responsibilities. Use a consistent format."
                ),
            ),
            TemplateSection(
                heading="## Component Dependencies",
                source="relationships",
                instructions=(
                    "Document depends-on relationships between components "
                    "as a dependency list."
                ),
            ),
        ],
    ),
    "api-reference": ArtifactTemplate(
        artifact_id="api-reference",
        filename="api-reference.md",
        system_prompt=(
            "You are a technical writer creating API documentation. "
            "Focus on precision — exact endpoint paths, methods, data formats."
        ),
        sections=[
            TemplateSection(
                heading="## Interfaces",
                source="interfaces",
                instructions=(
                    "For each interface, document: name, type, protocol, provider, "
                    "consumer, endpoints, and data format."
                ),
            ),
            TemplateSection(
                heading="## Data Contracts",
                source="interfaces",
                instructions=(
                    "Document the data schemas and contracts for each interface."
                ),
            ),
        ],
    ),
    "capability-map": ArtifactTemplate(
        artifact_id="capability-map",
        filename="capability-map.md",
        system_prompt=(
            "You are a technical writer documenting system capabilities. "
            "Focus on WHAT the system can do, not HOW."
        ),
        sections=[
            TemplateSection(
                heading="## Capabilities",
                source="capabilities",
                instructions=(
                    "List each capability with its priority, requirements, "
                    "and which components realize it."
                ),
            ),
            TemplateSection(
                heading="## Capability-Component Mapping",
                source="relationships",
                instructions=(
                    "Show which components realize which capabilities "
                    "using relationship data."
                ),
            ),
        ],
    ),
    "behavior-flows": ArtifactTemplate(
        artifact_id="behavior-flows",
        filename="behavior-flows.md",
        system_prompt=(
            "You are a technical writer documenting system workflows and behaviors. "
            "Describe step-by-step flows clearly."
        ),
        sections=[
            TemplateSection(
                heading="## Behaviors",
                source="behaviors",
                instructions=(
                    "For each behavior, document: trigger, actor, preconditions, "
                    "steps, postconditions, pattern type."
                ),
            ),
            TemplateSection(
                heading="## Interaction Sequences",
                source="behaviors",
                instructions=(
                    "Describe the sequence of interactions for key behaviors."
                ),
            ),
        ],
    ),
    "constraint-register": ArtifactTemplate(
        artifact_id="constraint-register",
        filename="constraint-register.md",
        system_prompt=(
            "You are a technical writer documenting non-functional requirements "
            "and design constraints."
        ),
        sections=[
            TemplateSection(
                heading="## Constraints",
                source="constraints",
                instructions=(
                    "For each constraint, document: type, metric, threshold, rationale."
                ),
            ),
            TemplateSection(
                heading="## Constraint Allocation",
                source="relationships",
                instructions=(
                    "Show which components are constrained by which constraints."
                ),
            ),
        ],
    ),
    "dependency-graph": ArtifactTemplate(
        artifact_id="dependency-graph",
        filename="dependency-graph.md",
        system_prompt=(
            "You are a technical writer documenting system dependencies and coupling."
        ),
        sections=[
            TemplateSection(
                heading="## Direct Dependencies",
                source="relationships",
                instructions=(
                    "List all depends-on relationships. Group by source component."
                ),
            ),
            TemplateSection(
                heading="## Dependency Analysis",
                source="relationships",
                instructions=(
                    "Identify highly-coupled components, potential circular "
                    "dependencies, and suggest improvements."
                ),
            ),
        ],
    ),
    "layer-architecture": ArtifactTemplate(
        artifact_id="layer-architecture",
        filename="layer-architecture.md",
        system_prompt=(
            "You are a technical writer documenting the layered architecture "
            "of the system."
        ),
        sections=[
            TemplateSection(
                heading="## Layers",
                source="layers",
                instructions=(
                    "For each layer, document: name, order, technology stack, "
                    "directories, and contained components."
                ),
            ),
            TemplateSection(
                heading="## Layer Interactions",
                source="relationships",
                instructions=(
                    "Describe how layers communicate. Note any violations "
                    "of layer ordering."
                ),
            ),
        ],
    ),
    "deployment-view": ArtifactTemplate(
        artifact_id="deployment-view",
        filename="deployment-view.md",
        system_prompt=(
            "You are a technical writer documenting deployment topology "
            "and operational concerns."
        ),
        sections=[
            TemplateSection(
                heading="## Deployment Units",
                source="components",
                instructions=(
                    "Group components by their deployment unit (layer + kind). "
                    "Describe what gets deployed together."
                ),
            ),
            TemplateSection(
                heading="## Operational Requirements",
                source="constraints",
                instructions=(
                    "List performance, reliability, and operational constraints "
                    "relevant to deployment."
                ),
            ),
        ],
    ),
    "integration-guide": ArtifactTemplate(
        artifact_id="integration-guide",
        filename="integration-guide.md",
        system_prompt=(
            "You are a technical writer creating integration documentation "
            "for developers connecting to this system."
        ),
        sections=[
            TemplateSection(
                heading="## Available Interfaces",
                source="interfaces",
                instructions=(
                    "List all interfaces available for integration with protocol "
                    "and data format details."
                ),
            ),
            TemplateSection(
                heading="## Integration Patterns",
                source="components",
                instructions=(
                    "Describe recommended patterns for integrating with "
                    "each component."
                ),
            ),
            TemplateSection(
                heading="## Authentication & Constraints",
                source="constraints",
                instructions=(
                    "Document security constraints and authentication requirements."
                ),
            ),
        ],
    ),
    "test-strategy": ArtifactTemplate(
        artifact_id="test-strategy",
        filename="test-strategy.md",
        system_prompt=(
            "You are a technical writer documenting the testing approach "
            "for this system."
        ),
        sections=[
            TemplateSection(
                heading="## Test Inventory",
                source="manifest.tests",
                instructions=(
                    "Summarize the test files, count, and coverage distribution "
                    "across components."
                ),
            ),
            TemplateSection(
                heading="## Testing Approach",
                source="components",
                instructions=(
                    "For each component, describe the testing strategy based on "
                    "its kind and responsibilities."
                ),
            ),
        ],
    ),
    "metrics-dashboard": ArtifactTemplate(
        artifact_id="metrics-dashboard",
        filename="metrics-dashboard.md",
        system_prompt=(
            "You are a technical writer summarizing code quality metrics."
        ),
        sections=[
            TemplateSection(
                heading="## Code Metrics",
                source="manifest.metrics",
                instructions=(
                    "Present the metrics data: lines of code, complexity, "
                    "file counts, module counts."
                ),
            ),
            TemplateSection(
                heading="## Quality Assessment",
                source="manifest.metrics",
                instructions=(
                    "Assess overall code health based on the metrics. "
                    "Note any concerning areas."
                ),
            ),
        ],
    ),
}


def get_template(artifact_id: str) -> ArtifactTemplate | None:
    """Look up template by artifact ID. Returns None if not found."""
    return TEMPLATES.get(artifact_id)
