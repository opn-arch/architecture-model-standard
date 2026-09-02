"""Build focused context for LLM doc authoring from pipeline stage results.

Each doc type gets a tailored context string containing the most relevant
model entities and code information for that specific document.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from architecture_model.core.types import ArchitectureModel


def _yaml_excerpt(data: list[dict], max_items: int = 30) -> str:
    """Render a list of dicts as a compact YAML-like text."""
    lines = []
    for item in data[:max_items]:
        parts = []
        for k, v in item.items():
            if v and v != "—":
                parts.append(f"{k}: {v}")
        if parts:
            lines.append("- " + ", ".join(parts))
    if len(data) > max_items:
        lines.append(f"  ... and {len(data) - max_items} more")
    return "\n".join(lines)


def _components_summary(model: ArchitectureModel) -> str:
    """Summarize components with their files and descriptions."""
    lines = []
    for c in model.entities.components:
        desc = getattr(c, "description", "") or ""
        files = getattr(c, "files", []) or []
        resp = getattr(c, "responsibilities", []) or []
        layer = getattr(c, "layer", "") or ""
        parts = [f"**{c.id}: {c.name}**"]
        if layer:
            parts.append(f"  Layer: {layer}")
        if desc:
            parts.append(f"  Description: {desc}")
        if resp:
            parts.append(f"  Responsibilities: {', '.join(resp)}")
        if files:
            parts.append(f"  Files: {', '.join(str(f) for f in files[:10])}")
            if len(files) > 10:
                parts[-1] += f" (+{len(files) - 10} more)"
        lines.append("\n".join(parts))
    return "\n\n".join(lines)


def _capabilities_summary(model: ArchitectureModel) -> str:
    """Summarize capabilities."""
    items = []
    for cap in model.entities.capabilities:
        desc = getattr(cap, "description", "") or ""
        items.append({"id": cap.id, "name": cap.name, "description": desc})
    return _yaml_excerpt(items)


def _behaviors_summary(model: ArchitectureModel, max_items: int = 30) -> str:
    """Summarize behaviors with steps."""
    lines = []
    for b in model.entities.behaviors[:max_items]:
        actor = getattr(b, "actor", "") or ""
        steps = getattr(b, "steps", []) or []
        cap = getattr(b, "capability_id", "") or ""
        line = f"- {b.id}: {b.name}"
        if actor:
            line += f" (actor: {actor})"
        if cap:
            line += f" (capability: {cap})"
        if steps:
            line += f"\n  Steps: {' → '.join(steps[:6])}"
        lines.append(line)
    if len(model.entities.behaviors) > max_items:
        lines.append(f"... and {len(model.entities.behaviors) - max_items} more behaviors")
    return "\n".join(lines)


def _interfaces_summary(model: ArchitectureModel) -> str:
    """Summarize interfaces."""
    lines = []
    for iface in model.entities.interfaces:
        protocol = getattr(iface, "protocol", "") or ""
        provider = getattr(iface, "provider", "") or ""
        consumer = getattr(iface, "consumer", "") or ""
        lines.append(
            f"- {iface.id}: {iface.name} (protocol={protocol}, provider={provider}, consumer={consumer})"
        )
    return "\n".join(lines) if lines else "No interfaces defined in model."


def _relationships_summary(model: ArchitectureModel, rel_type: str | None = None) -> str:
    """Summarize relationships, optionally filtered by type."""
    lines = []
    rels = getattr(model, "relationships", []) or []
    for r in rels:
        rtype = getattr(r, "type", "") or ""
        if rel_type and rtype != rel_type:
            continue
        src = getattr(r, "source", "") or ""
        tgt = getattr(r, "target", "") or ""
        lines.append(f"- {src} --{rtype}--> {tgt}")
    return "\n".join(lines[:50]) if lines else f"No {rel_type or ''} relationships defined."


def _actors_summary(model: ArchitectureModel) -> str:
    """Summarize actors."""
    lines = []
    for a in model.entities.actors:
        goals = getattr(a, "goals", []) or []
        atype = getattr(a, "type", "") or getattr(a, "actor_type", "") or ""
        line = f"- {a.id}: {a.name} (type={atype})"
        if goals:
            line += f"\n  Goals: {', '.join(goals)}"
        lines.append(line)
    return "\n".join(lines) if lines else "No actors defined."


def _requirements_summary(model: ArchitectureModel) -> str:
    """Summarize requirements."""
    reqs = getattr(model.entities, "requirements", []) or []
    if not reqs:
        return "No requirements defined in model."
    lines = []
    for r in reqs:
        priority = getattr(r, "priority", "") or ""
        desc = getattr(r, "description", "") or ""
        lines.append(f"- {r.id}: {r.name} (priority={priority}) {desc}")
    return "\n".join(lines)


def _constraints_summary(model: ArchitectureModel) -> str:
    """Summarize constraints."""
    constraints = getattr(model.entities, "constraints", []) or []
    if not constraints:
        return "No constraints defined."
    lines = []
    for c in constraints:
        ctype = getattr(c, "type", "") or getattr(c, "constraint_type", "") or ""
        lines.append(f"- {c.id}: {c.name} (type={ctype})")
    return "\n".join(lines)


def _code_context_from_observe(
    inventory: Any,
    component_files: dict[str, list[str]] | None = None,
    focus: str = "all",
    max_tokens_approx: int = 3000,
) -> str:
    """Build code context from observe stage inventory.

    Args:
        inventory: Inventory from observe stage result
        component_files: Optional mapping of component_id -> list of file paths
        focus: "all", "routes", "classes", "functions"
        max_tokens_approx: Rough token budget (chars / 4)
    """
    if inventory is None:
        return "No code inventory available."

    modules = getattr(inventory, "modules", []) or []
    routes = getattr(inventory, "routes", []) or []
    test_files = getattr(inventory, "test_files", []) or []

    lines: list[str] = []
    char_budget = max_tokens_approx * 4

    # Routes (API endpoints)
    if routes:
        lines.append("### API Routes")
        for r in routes[:30]:
            doc = f" — {r.docstring}" if r.docstring else ""
            lines.append(f"- {r.method} {r.path} → {r.function_name} ({r.file}){doc}")
        if len(routes) > 30:
            lines.append(f"  ... +{len(routes) - 30} more routes")
        lines.append("")

    # Module summaries (docstrings, key classes/functions)
    lines.append("### Module Summaries")
    for mod in modules:
        if len("\n".join(lines)) > char_budget:
            lines.append(f"... truncated ({len(modules)} total modules)")
            break

        mod_lines = []
        path_str = str(mod.path)

        # Skip test files in general context
        if "test" in path_str.lower() and focus != "tests":
            continue

        if mod.docstring:
            mod_lines.append(f"**{path_str}**: {mod.docstring[:200]}")
        else:
            mod_lines.append(f"**{path_str}** ({mod.line_count} lines)")

        # Classes
        for cls in mod.classes or []:
            bases = f"({', '.join(cls.bases)})" if cls.bases else ""
            methods_str = ", ".join(cls.methods[:8])
            if len(cls.methods) > 8:
                methods_str += f" +{len(cls.methods) - 8} more"
            mod_lines.append(f"  class {cls.name}{bases}: [{methods_str}]")
            # Include docstrings from method_details
            for md in (cls.method_details or [])[:3]:
                if md.docstring:
                    mod_lines.append(f"    {md.name}: {md.docstring[:100]}")

        # Top-level functions (with docstrings)
        for fn in (mod.functions or [])[:5]:
            sig = fn.signature[:80] if fn.signature else ""
            doc = f" — {fn.docstring[:80]}" if fn.docstring else ""
            mod_lines.append(f"  def {fn.name}({sig}){doc}")

        if mod_lines:
            lines.extend(mod_lines)
            lines.append("")

    # Test files
    if test_files and focus in ("all", "tests"):
        lines.append("### Test Files")
        for tf in test_files[:20]:
            targets = ", ".join(tf.targets) if tf.targets else "unknown"
            lines.append(f"- {tf.path} → tests: {targets}")
        lines.append("")

    return "\n".join(lines)


def build_context_for_doc(
    doc_name: str,
    model: ArchitectureModel,
    stage_results: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Build (model_context, code_context) for a specific doc type.

    Args:
        doc_name: The doc module name (e.g., "functional_analysis")
        model: The architecture model
        stage_results: Dict of stage_name -> StageResult (from ctx.cache)

    Returns:
        (model_context_str, code_context_str)
    """
    # Get observe inventory if available
    inventory = None
    if stage_results:
        observe_result = stage_results.get("observe")
        if observe_result:
            inventory = getattr(observe_result, "output", None)

    # Build component -> files mapping from allocate
    comp_files: dict[str, list[str]] = {}
    if stage_results:
        alloc_result = stage_results.get("allocate")
        if alloc_result:
            alloc_output = getattr(alloc_result, "output", None)
            if alloc_output:
                for comp in getattr(alloc_output, "components", []):
                    comp_files[comp.id] = [str(f) for f in comp.files]

    # Doc-type specific model context
    if doc_name == "functional_analysis":
        model_ctx = "\n\n".join(
            [
                "## Capabilities",
                _capabilities_summary(model),
                "## Behaviors",
                _behaviors_summary(model),
                "## Capability Realization (realizes relationships)",
                _relationships_summary(model, "realizes"),
                "## Components (brief)",
                _components_summary(model),
            ]
        )
        code_ctx = _code_context_from_observe(
            inventory, comp_files, focus="all", max_tokens_approx=2000
        )

    elif doc_name == "logical_architecture":
        model_ctx = "\n\n".join(
            [
                "## Components",
                _components_summary(model),
                "## Dependencies (uses/depends_on relationships)",
                _relationships_summary(model, "uses"),
                _relationships_summary(model, "depends_on"),
                "## Layers",
                "\n".join(
                    f"- {getattr(l, 'name', l)}"
                    for l in (getattr(model.entities, "layers", []) or [])
                )
                or "No explicit layers defined.",
            ]
        )
        code_ctx = _code_context_from_observe(
            inventory, comp_files, focus="all", max_tokens_approx=2500
        )

    elif doc_name == "use_cases":
        model_ctx = "\n\n".join(
            [
                "## Actors",
                _actors_summary(model),
                "## Behaviors (use cases / workflows)",
                _behaviors_summary(model, max_items=50),
                "## Capabilities",
                _capabilities_summary(model),
            ]
        )
        code_ctx = _code_context_from_observe(
            inventory, comp_files, focus="routes", max_tokens_approx=2000
        )

    elif doc_name == "behavior_flows":
        model_ctx = "\n\n".join(
            [
                "## Behaviors",
                _behaviors_summary(model, max_items=50),
                "## Components",
                _components_summary(model),
                "## Actors",
                _actors_summary(model),
                "## Trigger/Contains Relationships",
                _relationships_summary(model, "triggers"),
                _relationships_summary(model, "contains"),
            ]
        )
        code_ctx = _code_context_from_observe(
            inventory, comp_files, focus="routes", max_tokens_approx=2000
        )

    elif doc_name == "interface_spec":
        model_ctx = "\n\n".join(
            [
                "## Interfaces",
                _interfaces_summary(model),
                "## Exposes Relationships",
                _relationships_summary(model, "exposes"),
                "## Components",
                _components_summary(model),
            ]
        )
        code_ctx = _code_context_from_observe(
            inventory, comp_files, focus="all", max_tokens_approx=2500
        )

    elif doc_name == "requirements_analysis":
        model_ctx = "\n\n".join(
            [
                "## Requirements",
                _requirements_summary(model),
                "## Constraints",
                _constraints_summary(model),
                "## Capabilities",
                _capabilities_summary(model),
                "## Satisfies Relationships",
                _relationships_summary(model, "satisfies"),
            ]
        )
        code_ctx = _code_context_from_observe(
            inventory, comp_files, focus="all", max_tokens_approx=1500
        )

    elif doc_name == "conops":
        model_ctx = "\n\n".join(
            [
                "## System",
                f"Project: {getattr(model.meta, 'project', '') or getattr(model.meta, 'system', '')}",
                f"Description: {getattr(model.meta, 'description', '') or ''}",
                "## Actors",
                _actors_summary(model),
                "## Capabilities",
                _capabilities_summary(model),
                "## Constraints",
                _constraints_summary(model),
            ]
        )
        code_ctx = _code_context_from_observe(
            inventory, comp_files, focus="all", max_tokens_approx=1500
        )

    elif doc_name == "verification_validation":
        model_ctx = "\n\n".join(
            [
                "## Components",
                _components_summary(model),
                "## Requirements",
                _requirements_summary(model),
            ]
        )
        code_ctx = _code_context_from_observe(
            inventory, comp_files, focus="tests", max_tokens_approx=2000
        )

    elif doc_name == "operations_manual":
        model_ctx = "\n\n".join(
            [
                "## Components",
                _components_summary(model),
                "## Constraints (operational)",
                _constraints_summary(model),
            ]
        )
        code_ctx = _code_context_from_observe(
            inventory, comp_files, focus="all", max_tokens_approx=2000
        )

    elif doc_name == "maintenance_manual":
        model_ctx = "\n\n".join(
            [
                "## Components",
                _components_summary(model),
                "## Dependencies",
                _relationships_summary(model, "uses"),
            ]
        )
        code_ctx = _code_context_from_observe(
            inventory, comp_files, focus="all", max_tokens_approx=2500
        )

    elif doc_name == "risk_assessment":
        model_ctx = "\n\n".join(
            [
                "## Components",
                _components_summary(model),
                "## Constraints",
                _constraints_summary(model),
                "## Dependencies",
                _relationships_summary(model, "uses"),
                _relationships_summary(model, "depends_on"),
            ]
        )
        code_ctx = _code_context_from_observe(
            inventory, comp_files, focus="all", max_tokens_approx=1500
        )

    elif doc_name in ("api_reference", "cli_reference"):
        model_ctx = "\n\n".join(
            [
                "## Interfaces",
                _interfaces_summary(model),
                "## Components",
                _components_summary(model),
            ]
        )
        code_ctx = _code_context_from_observe(
            inventory, comp_files, focus="routes", max_tokens_approx=3000
        )

    elif doc_name == "data_model":
        model_ctx = "\n\n".join(
            [
                "## Components",
                _components_summary(model),
                "## Interfaces",
                _interfaces_summary(model),
            ]
        )
        code_ctx = _code_context_from_observe(
            inventory, comp_files, focus="classes", max_tokens_approx=3000
        )

    else:
        # Generic fallback for any doc type
        model_ctx = "\n\n".join(
            [
                "## Components",
                _components_summary(model),
                "## Capabilities",
                _capabilities_summary(model),
                "## Interfaces",
                _interfaces_summary(model),
            ]
        )
        code_ctx = _code_context_from_observe(
            inventory, comp_files, focus="all", max_tokens_approx=2000
        )

    return model_ctx, code_ctx
