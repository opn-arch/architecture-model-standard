"""Context assembler for artifact generation.

Given an artifact template + architecture model + optional manifest,
assembles the formatted context string included in the LLM prompt.

Extracts relevant model/manifest data for each template section and
formats it concisely for LLM consumption.
"""

from __future__ import annotations

from architecture_model.artifacts.templates import ArtifactTemplate
from architecture_model.core.types import ArchitectureModel


def assemble_artifact_context(
    template: ArtifactTemplate,
    model: ArchitectureModel,
    manifest: dict | None = None,
    max_tokens: int = 4000,
) -> str:
    """Assemble formatted context for artifact generation.

    Returns a structured prompt string containing:
    1. System prompt from template
    2. For each section: heading + extracted data + instructions

    Token budget is approximate (1 token ~ 4 chars). If total exceeds budget,
    truncate section data (not instructions).
    """
    max_chars = max_tokens * 4

    # Build header
    header = f"SYSTEM: {template.system_prompt}\n"

    # Build sections
    sections: list[str] = []
    for section in template.sections:
        data = _extract_section_data(section.source, model, manifest)
        section_text = (
            f"\n{section.heading}\n"
            f"DATA:\n{data}\n"
            f"INSTRUCTIONS: {section.instructions}\n"
        )
        sections.append(section_text)

    # Assemble full output
    full_output = header + "".join(sections)

    # Truncate if over budget
    if len(full_output) <= max_chars:
        return full_output

    # Truncate strategy: rebuild with trimmed section data
    # Keep header + instructions intact, trim data
    remaining = max_chars - len(header)
    truncated_sections: list[str] = []

    for section in template.sections:
        # Fixed overhead per section (heading + DATA: + INSTRUCTIONS:)
        frame = (
            f"\n{section.heading}\n"
            f"DATA:\n"
        )
        tail = f"\nINSTRUCTIONS: {section.instructions}\n"
        frame_cost = len(frame) + len(tail)

        if remaining <= frame_cost:
            # Not enough room for even the frame — skip section
            break

        data = _extract_section_data(section.source, model, manifest)
        available_for_data = remaining - frame_cost
        if len(data) > available_for_data:
            data = data[:available_for_data].rstrip() + "\n[truncated]"

        section_text = frame + data + tail
        truncated_sections.append(section_text)
        remaining -= len(section_text)

    return header + "".join(truncated_sections)


def _extract_section_data(
    source: str, model: ArchitectureModel, manifest: dict | None
) -> str:
    """Route to appropriate extractor based on source string."""
    extractors = {
        "meta": lambda: _format_meta(model),
        "components": lambda: _format_components(model),
        "interfaces": lambda: _format_interfaces(model),
        "capabilities": lambda: _format_capabilities(model),
        "behaviors": lambda: _format_behaviors(model),
        "constraints": lambda: _format_constraints(model),
        "layers": lambda: _format_layers(model),
        "relationships": lambda: _format_relationships(model),
        "manifest.tests": lambda: _format_manifest_tests(manifest),
        "manifest.metrics": lambda: _format_manifest_metrics(manifest),
    }

    extractor = extractors.get(source)
    if extractor is None:
        return "No data available for this section."
    return extractor()


def _format_meta(model: ArchitectureModel) -> str:
    """Format project metadata."""
    lines = [
        f"Project: {model.meta.project}",
        f"System: {model.meta.system}",
        f"Schema: {model.meta.schema_version}",
    ]
    if model.meta.generated_at:
        lines.append(f"Generated: {model.meta.generated_at}")
    return "\n".join(lines)


def _format_components(model: ArchitectureModel) -> str:
    """Format components list."""
    components = model.entities.components
    if not components:
        return "No data available for this section."

    lines = []
    for c in components:
        line = f"- {c.id}: {c.name} [{c.kind.value}] layer={c.layer} status={c.status.value}"
        if c.files:
            line += f"\n  files: {', '.join(c.files)}"
        if c.responsibilities:
            line += f"\n  responsibilities: {', '.join(c.responsibilities)}"
        lines.append(line)
    return "\n".join(lines)


def _format_interfaces(model: ArchitectureModel) -> str:
    """Format interfaces list."""
    interfaces = model.entities.interfaces
    if not interfaces:
        return "No data available for this section."

    lines = []
    for i in interfaces:
        line = f"- {i.id}: {i.name} [{i.type.value}] protocol={i.protocol}"
        line += f"\n  provider={i.provider} consumer={i.consumer}"
        line += f"\n  endpoints: {len(i.endpoints)}"
        lines.append(line)
    return "\n".join(lines)


def _format_capabilities(model: ArchitectureModel) -> str:
    """Format capabilities list."""
    capabilities = model.entities.capabilities
    if not capabilities:
        return "No data available for this section."

    lines = []
    for cap in capabilities:
        line = f"- {cap.id}: {cap.name} [priority={cap.priority.value}] f_block={cap.f_block}"
        lines.append(line)
    return "\n".join(lines)


def _format_behaviors(model: ArchitectureModel) -> str:
    """Format behaviors list."""
    behaviors = model.entities.behaviors
    if not behaviors:
        return "No data available for this section."

    lines = []
    for b in behaviors:
        line = f"- {b.id}: {b.name} trigger={b.trigger} pattern={b.pattern.value}"
        if b.steps:
            line += f"\n  steps: {', '.join(b.steps)}"
        lines.append(line)
    return "\n".join(lines)


def _format_constraints(model: ArchitectureModel) -> str:
    """Format constraints list."""
    constraints = model.entities.constraints
    if not constraints:
        return "No data available for this section."

    lines = []
    for c in constraints:
        line = f"- {c.id}: {c.name} [{c.type.value}] metric={c.metric} threshold={c.threshold}"
        lines.append(line)
    return "\n".join(lines)


def _format_layers(model: ArchitectureModel) -> str:
    """Format layers list."""
    layers = model.entities.layers
    if not layers:
        return "No data available for this section."

    lines = []
    for layer in layers:
        tech = ", ".join(layer.technology) if layer.technology else "none"
        line = f"- {layer.id}: {layer.name} [order={layer.order}] tech={tech}"
        lines.append(line)
    return "\n".join(lines)


def _format_relationships(model: ArchitectureModel) -> str:
    """Format relationship list."""
    relationships = model.relationships
    if not relationships:
        return "No data available for this section."

    lines = []
    for r in relationships:
        line = f"- {r.from_id} --{r.type.value}--> {r.to_id}"
        lines.append(line)
    return "\n".join(lines)


def _format_manifest_tests(manifest: dict | None) -> str:
    """Format test data from manifest."""
    if manifest is None or "test_files" not in manifest:
        return "No data available for this section."

    test_files = manifest["test_files"]
    lines = [f"Test files: {len(test_files)}"]
    for f in test_files:
        lines.append(f"- {f}")
    return "\n".join(lines)


def _format_manifest_metrics(manifest: dict | None) -> str:
    """Format metrics from manifest."""
    if manifest is None or "metrics" not in manifest:
        return "No data available for this section."

    metrics = manifest["metrics"]
    lines = []
    for key, value in metrics.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)
