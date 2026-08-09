"""Context generator — produces LLM-readable summary from pipeline results.

Generates a concise markdown document summarizing the architecture for
use as LLM context (token-efficient representation).
"""
from __future__ import annotations

from pathlib import Path

from .allocate_types import AllocationResult
from .infer_types import InferenceResult
from .observe_types import Inventory
from .protocol import PipelineContext
from .relate_types import RelateResult
from .validate_types import ValidateResult


def generate_context(ctx: PipelineContext) -> str:
    """Generate context.md content from pipeline results."""
    lines: list[str] = []

    observe = ctx.get("observe")
    infer = ctx.get("infer")
    allocate = ctx.get("allocate")
    relate = ctx.get("relate")
    validate = ctx.get("validate")

    # Header
    lines.append(f"# Architecture Context: {ctx.repo_path.name}")
    lines.append("")

    # Validation summary
    if validate:
        v: ValidateResult = validate.output
        lines.append(f"**Score:** {v.score}/100 | **Valid:** {v.is_valid}")
        lines.append("")

    # Capabilities
    if infer:
        inf: InferenceResult = infer.output
        if inf.capabilities:
            lines.append("## Capabilities")
            for cap in inf.capabilities:
                lines.append(f"- **{cap.name}** ({cap.id}): {cap.description}")
            lines.append("")

        # Actors
        if inf.actors:
            lines.append("## Actors")
            for actor in inf.actors:
                lines.append(f"- **{actor.name}** ({actor.actor_type})")
            lines.append("")

    # Components
    if allocate:
        alloc: AllocationResult = allocate.output
        if alloc.components:
            lines.append("## Components")
            for comp in alloc.components:
                file_list = ", ".join(str(f) for f in comp.files[:5])
                suffix = f" (+{len(comp.files) - 5} more)" if len(comp.files) > 5 else ""
                lines.append(f"- **{comp.name}** ({comp.id}) [{comp.layer}]: {file_list}{suffix}")
            lines.append("")
            lines.append(f"File coverage: {alloc.file_coverage:.0f}% | Boundary coherence: {alloc.boundary_coherence:.0f}%")
            lines.append("")

    # Key relationships
    if relate:
        rel: RelateResult = relate.output
        if rel.relationships:
            lines.append("## Relationships")
            # Group by type
            by_type: dict[str, int] = {}
            for r in rel.relationships:
                by_type[r.rel_type] = by_type.get(r.rel_type, 0) + 1
            for rtype, count in sorted(by_type.items()):
                lines.append(f"- {rtype}: {count}")
            lines.append("")

    # Metrics
    if observe:
        inv: Inventory = observe.output
        lines.append("## Metrics")
        lines.append(f"- Modules: {len(inv.modules)}")
        lines.append(f"- Routes: {len(inv.routes)}")
        lines.append(f"- Test files: {len(inv.test_files)}")
        lines.append(f"- Docs: {len(inv.docs)}")
        lines.append("")

    return "\n".join(lines)


def write_context(ctx: PipelineContext) -> Path:
    """Write context.md to the output directory."""
    content = generate_context(ctx)
    path = ctx.output_dir / "context.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path
