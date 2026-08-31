"""Component specification generator.

Generates per-component specification documents (COMP-*.md) with:
- Component purpose and responsibilities
- Source files, functions, and classes
- Relationships (dependencies, interfaces, capabilities)
- Test coverage information
- LLM-authored narrative when available
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel, Component


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)


def _component_context(
    comp: "Component",
    model: "ArchitectureModel",
) -> str:
    """Build a context string for LLM authoring of a component spec."""
    lines = []
    lines.append(f"Component: {comp.name} ({comp.id})")
    desc = getattr(comp, "description", "") or ""
    if desc:
        lines.append(f"Description: {desc}")

    # Relationships
    rels_out = []
    rels_in = []
    for rel in model.relationships:
        rt = _rel_type_str(rel.type)
        if rel.from_id == comp.id:
            rels_out.append(f"  {rt} → {rel.to_id}")
        elif rel.to_id == comp.id:
            rels_in.append(f"  {rel.from_id} → {rt}")
    if rels_out:
        lines.append("Outgoing relationships:")
        lines.extend(rels_out)
    if rels_in:
        lines.append("Incoming relationships:")
        lines.extend(rels_in)

    # Connected capabilities
    caps = []
    for rel in model.relationships:
        if rel.from_id == comp.id and _rel_type_str(rel.type) == "realizes":
            cap = next((c for c in model.entities.capabilities if c.id == rel.to_id), None)
            if cap:
                caps.append(f"  {cap.id}: {cap.name}")
    if caps:
        lines.append("Realizes capabilities:")
        lines.extend(caps)

    # Interfaces
    ifaces = []
    for rel in model.relationships:
        if rel.from_id == comp.id and _rel_type_str(rel.type) == "exposes":
            iface = next((i for i in model.entities.interfaces if i.id == rel.to_id), None)
            if iface:
                methods = getattr(iface, "methods", []) or []
                ifaces.append(f"  {iface.id}: {iface.name} ({', '.join(methods[:5])})")
    if ifaces:
        lines.append("Exposes interfaces:")
        lines.extend(ifaces)

    return "\n".join(lines)


def generate_component_spec(
    comp: "Component",
    model: "ArchitectureModel",
    manifest: object | None = None,
) -> str:
    """Generate a deterministic component specification document."""
    lines = []
    lines.append(f"# Component: {comp.name} ({comp.id})")
    lines.append("")

    status = getattr(comp, "status", "ACTIVE")
    status_str = status.value if hasattr(status, "value") else str(status)
    desc = getattr(comp, "description", "") or "—"
    lines.append(f"**Status:** {status_str}")
    lines.append(f"**Description:** {desc}")
    lines.append("")

    # Layer
    layer = getattr(comp, "layer", "") or ""
    if layer:
        lines.append(f"**Layer:** {layer}")
        lines.append("")

    # Responsibilities
    responsibilities = getattr(comp, "responsibilities", []) or []
    lines.append("## Responsibilities")
    lines.append("")
    if responsibilities:
        for r in responsibilities:
            lines.append(f"- {r}")
    else:
        lines.append("—")
    lines.append("")

    # Relationships
    lines.append("## Relationships")
    lines.append("")

    deps = []
    realizes = []
    exposes = []
    satisfies = []
    other_rels = []
    for rel in model.relationships:
        rt = _rel_type_str(rel.type)
        if rel.from_id == comp.id:
            if rt == "depends-on":
                deps.append(rel)
            elif rt == "realizes":
                realizes.append(rel)
            elif rt == "exposes":
                exposes.append(rel)
            elif rt == "satisfies":
                satisfies.append(rel)
            else:
                other_rels.append(("→", rel, rt))
        elif rel.to_id == comp.id:
            if rt == "depends-on":
                other_rels.append(("←", rel, rt))
            else:
                other_rels.append(("←", rel, rt))

    if deps:
        lines.append("### Dependencies")
        lines.append("")
        lines.append("| Target | Type |")
        lines.append("|--------|------|")
        for rel in deps:
            target_name = next(
                (c.name for c in model.entities.components if c.id == rel.to_id), rel.to_id
            )
            lines.append(f"| {target_name} (`{rel.to_id}`) | depends-on |")
        lines.append("")

    if realizes:
        lines.append("### Realizes")
        lines.append("")
        for rel in realizes:
            cap = next((c for c in model.entities.capabilities if c.id == rel.to_id), None)
            cap_name = cap.name if cap else rel.to_id
            lines.append(f"- {cap_name} (`{rel.to_id}`)")
        lines.append("")

    if exposes:
        lines.append("### Exposes Interfaces")
        lines.append("")
        for rel in exposes:
            iface = next((i for i in model.entities.interfaces if i.id == rel.to_id), None)
            if iface:
                methods = getattr(iface, "methods", []) or []
                lines.append(f"- **{iface.name}** (`{iface.id}`)")
                if methods:
                    for m in methods[:10]:
                        lines.append(f"  - `{m}`")
            else:
                lines.append(f"- `{rel.to_id}`")
        lines.append("")

    if satisfies:
        lines.append("### Satisfies Requirements")
        lines.append("")
        for rel in satisfies:
            req = next((r for r in model.entities.requirements if r.id == rel.to_id), None)
            req_name = req.name if req else rel.to_id
            lines.append(f"- {req_name} (`{rel.to_id}`)")
        lines.append("")

    # Children
    children = [
        c for c in model.entities.components
        if c.id.startswith(comp.id + ".") and c.id.count(".") == comp.id.count(".") + 1
    ]
    if children:
        lines.append("## Sub-Components")
        lines.append("")
        lines.append("| ID | Name | Description |")
        lines.append("|----|------|-------------|")
        for child in children:
            cdesc = getattr(child, "description", "") or "—"
            lines.append(f"| {child.id} | {child.name} | {cdesc} |")
        lines.append("")

    return "\n".join(lines)


def generate_all_component_specs(
    model: "ArchitectureModel",
    output_dir: Path,
    manifest: object | None = None,
    *,
    llm_callback: Any | None = None,
) -> dict[str, Any]:
    """Generate component spec files for all components.

    Args:
        model: Architecture model.
        output_dir: Directory to write COMP-*.md files.
        llm_callback: Optional LLM callback for authored specs.

    Returns:
        Dict with 'generated' and 'errors' lists.
    """
    import asyncio
    import json

    output_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {"generated": [], "errors": []}

    # Only generate for top-level components (no dot in ID)
    top_comps = [c for c in model.entities.components if "." not in c.id]

    for comp in top_comps:
        filename = f"{comp.id}.md"
        out_path = output_dir / filename

        content = None

        # Try LLM authoring
        if llm_callback:
            try:
                ctx = _component_context(comp, model)
                prompt = (
                    f"Write a detailed component specification for '{comp.name}' ({comp.id}).\n\n"
                    f"## Component Context\n{ctx}\n\n"
                    f"Write in markdown with sections: Purpose, Responsibilities, "
                    f"Architecture Patterns, API Surface, Dependencies, Test Coverage Strategy.\n"
                    f"Be specific — reference actual interfaces, capabilities, and relationships."
                )
                try:
                    loop = asyncio.get_running_loop()
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        future = pool.submit(asyncio.run, llm_callback("component_spec", prompt, {"component": comp.id}))
                        content = future.result(timeout=60)
                except RuntimeError:
                    content = asyncio.run(llm_callback("component_spec", prompt, {"component": comp.id}))
            except Exception:
                pass  # fall through to deterministic

        # Fallback to deterministic
        if not content:
            content = generate_component_spec(comp, model, manifest)

        out_path.write_text(content)
        result["generated"].append(str(out_path))

    return result
