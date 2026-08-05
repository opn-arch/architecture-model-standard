"""Behavior spec document generator — Mermaid sequence diagrams and index."""

from __future__ import annotations

from architecture_model.core.types import Behavior
from architecture_model.manifest.call_graph import FlowTrace
from architecture_model.manifest.types import FunctionInfo, Manifest
from architecture_model.orchestration.behavior_flows import (
    BehaviorClassification,
    CrudSummary,
)


def _lookup_function(manifest: Manifest, file: str, func_name: str) -> FunctionInfo | None:
    for mod in manifest.modules:
        if mod.file == file:
            for f in mod.functions:
                if f.name == func_name:
                    return f
    return None


def generate_behavior_spec(
    behavior: Behavior,
    flow_trace: FlowTrace,
    scoped_manifest: Manifest,
    file_to_comp: dict[str, str],
) -> str:
    """Generate a markdown spec for a single cross-component behavior."""
    lines: list[str] = []

    # Header
    lines.append(f"# {behavior.name}")
    lines.append("")
    lines.append(f"**Trigger:** {behavior.trigger}")
    lines.append(f"**Actor:** {behavior.actor or 'System'}")
    lines.append(f"**Components:** {', '.join(flow_trace.components_crossed)}")
    lines.append("")

    # Sequence Diagram
    lines.append("## Sequence Diagram")
    lines.append("")
    lines.append("```mermaid")
    lines.append("sequenceDiagram")

    # Participants (unique, in order)
    seen_comps: list[str] = []
    for comp in flow_trace.components_crossed:
        if comp not in seen_comps:
            seen_comps.append(comp)
            lines.append(f"    participant {comp}")

    # Messages: arrows between different components
    prev_comp = None
    for module_file, func_name in flow_trace.steps:
        comp = file_to_comp.get(module_file, "UNKNOWN")
        if prev_comp is not None and comp != prev_comp:
            lines.append(f"    {prev_comp}->>+{comp}: {func_name}()")
        elif prev_comp is not None and comp == prev_comp:
            lines.append(f"    Note over {comp}: {func_name}()")
        prev_comp = comp

    lines.append("```")
    lines.append("")

    # Preconditions
    lines.append("## Preconditions")
    if behavior.preconditions:
        for pre in behavior.preconditions:
            lines.append(f"- {pre}")
    else:
        lines.append("- None")
    lines.append("")

    # Postconditions
    lines.append("## Postconditions")
    if behavior.postconditions:
        for post in behavior.postconditions:
            lines.append(f"- {post}")
    else:
        lines.append("- None")
    lines.append("")

    # Data Flow Table
    lines.append("## Data Flow")
    lines.append("")
    lines.append("| Step | Function | Input | Output |")
    lines.append("|------|----------|-------|--------|")
    for i, (module_file, func_name) in enumerate(flow_trace.steps, 1):
        func = _lookup_function(scoped_manifest, module_file, func_name)
        if func:
            data_in = ", ".join(func.data_in) if func.data_in else "-"
            data_out = func.data_out or "-"
        else:
            data_in = "-"
            data_out = "-"
        lines.append(f"| {i} | {func_name} | {data_in} | {data_out} |")
    lines.append("")

    # Error Paths
    lines.append("## Error Paths")
    has_errors = False
    for module_file, func_name in flow_trace.steps:
        func = _lookup_function(scoped_manifest, module_file, func_name)
        if func and func.raises:
            lines.append(f"- {func_name}: raises {', '.join(func.raises)}")
            has_errors = True
    if not has_errors:
        lines.append("- None")
    lines.append("")

    # Files Touched
    lines.append("## Files Touched")
    seen_files: set[str] = set()
    for module_file, _ in flow_trace.steps:
        if module_file not in seen_files:
            seen_files.add(module_file)
            comp = file_to_comp.get(module_file, "UNKNOWN")
            lines.append(f"- {module_file} ({comp})")
    lines.append("")

    return "\n".join(lines)


def generate_behavior_index(
    classification: BehaviorClassification,
    crud_summaries: dict[str, CrudSummary],
) -> str:
    """Generate a markdown index of all behaviors."""
    lines: list[str] = []

    lines.append("# Behavior Flows")
    lines.append("")

    # Cross-component flows
    count = len(classification.cross_component)
    lines.append(f"## Cross-Component Flows ({count})")
    lines.append("")
    lines.append("| Behavior | Trigger | Components | Steps |")
    lines.append("|----------|---------|------------|-------|")
    for beh, trace in classification.cross_component:
        comps = ", ".join(trace.components_crossed)
        steps = len(trace.steps)
        lines.append(f"| [{beh.name}](./behaviors/{beh.id}.md) | {beh.trigger} | {comps} | {steps} |")
    lines.append("")

    # CRUD groups
    if classification.crud_groups:
        lines.append("## Component CRUD Groups")
        lines.append("")
        for comp_id, behaviors in classification.crud_groups.items():
            summary = crud_summaries.get(comp_id)
            count_str = f"{len(behaviors)} endpoints"
            lines.append(f"### {comp_id} ({count_str})")
            if summary:
                lines.append(summary.summary)
            lines.append("")
            names = ", ".join(b.name for b in behaviors)
            lines.append(f"Endpoints: {names}")
            lines.append("")

    return "\n".join(lines)
