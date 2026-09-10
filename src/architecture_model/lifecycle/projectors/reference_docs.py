"""Reference-doc projectors — Phase 4-A Tasks 13-15.

These projectors surface promoted Interface entities (produced by
:mod:`architecture_model.pipeline.endpoint_promotion`) as deterministic
Markdown references:

* ``family6.cli_reference`` — CLI commands grouped by framework.
* ``family6.api_reference`` — HTTP routes grouped by method.
* ``family6.plugin_guide`` — plugin hooks grouped by entry-point group.

All three follow the same conventions established by
``nonse.py``: single ``DiagramSpec`` per projector with
``id=f"prose:{name}"``, ``facets={"content_kind": "markdown", "body": ...}``.
Empty inputs render a stable "No X" placeholder so downstream consumers
can distinguish "not applicable" from missing data.
"""

from __future__ import annotations

from typing import Any, Iterable

from architecture_model.core.diagram_spec import DiagramSpec

__all__ = [
    "family6_cli_reference",
    "register_all",
]


def _cli_interfaces(fragment) -> list[Any]:
    return [i for i in fragment.entities.interfaces if getattr(i, "subkind", "") == "cli_command"]


def _framework_of(iface) -> str:
    meta = getattr(iface, "metadata", {}) or {}
    fw = meta.get("framework")
    return str(fw) if isinstance(fw, str) and fw else "unknown"


def _render_arg_row(arg: dict) -> str:
    name = str(arg.get("name", ""))
    typ = str(arg.get("type", "") or "—")
    required = "yes" if arg.get("required") else "no"
    default = arg.get("default")
    default_cell = "—" if default is None else f"`{default!r}`"
    return f"| `{name}` | {typ} | {required} | {default_cell} |"


def _render_cli_command(iface) -> str:
    lines: list[str] = [f"### {iface.name}"]
    intent = getattr(iface, "intent", "") or ""
    if intent:
        lines.append("")
        lines.append(intent)
    meta = getattr(iface, "metadata", {}) or {}
    args = meta.get("args") or []
    if args:
        lines.append("")
        lines.append("| Argument | Type | Required | Default |")
        lines.append("|---|---|---|---|")
        for arg in args:
            if isinstance(arg, dict):
                lines.append(_render_arg_row(arg))
    return "\n".join(lines)


def family6_cli_reference(fragment, config):
    """Render CLI commands as a grouped Markdown reference."""
    del config
    interfaces = _cli_interfaces(fragment)
    if not interfaces:
        body = "# CLI Reference\n\nNo CLI commands defined."
        return DiagramSpec(
            id="prose:family6.cli_reference",
            title="family6.cli_reference",
            facets={"content_kind": "markdown", "body": body},
        )
    groups: dict[str, list] = {}
    for iface in interfaces:
        groups.setdefault(_framework_of(iface), []).append(iface)
    sections: list[str] = ["# CLI Reference"]
    for framework in sorted(groups):
        sections.append("")
        sections.append(f"## {framework}")
        for iface in sorted(groups[framework], key=lambda i: (i.name, i.id)):
            sections.append("")
            sections.append(_render_cli_command(iface))
    body = "\n".join(sections)
    return DiagramSpec(
        id="prose:family6.cli_reference",
        title="family6.cli_reference",
        facets={"content_kind": "markdown", "body": body},
    )


def register_all(registry) -> None:
    if "family6.cli_reference" not in registry:
        registry.register("family6.cli_reference", family6_cli_reference, version="1.0.0")
