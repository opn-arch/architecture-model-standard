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
    "family6_api_reference",
    "family6_plugin_guide",
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
    if "family6.api_reference" not in registry:
        registry.register("family6.api_reference", family6_api_reference, version="1.0.0")
    if "family6.plugin_guide" not in registry:
        registry.register("family6.plugin_guide", family6_plugin_guide, version="1.0.0")


# ---------------------------------------------------------------------------
# family6.api_reference — HTTP routes
# ---------------------------------------------------------------------------


def _http_interfaces(fragment) -> list[Any]:
    return [i for i in fragment.entities.interfaces if getattr(i, "subkind", "") == "http_route"]


def _http_method_of(iface) -> str:
    meta = getattr(iface, "metadata", {}) or {}
    method = meta.get("http_method")
    return str(method).upper() if isinstance(method, str) and method else "GET"


def _http_path_of(iface) -> str:
    meta = getattr(iface, "metadata", {}) or {}
    path = meta.get("path")
    return str(path) if isinstance(path, str) and path else ""


def _render_route(iface) -> list[str]:
    path = _http_path_of(iface)
    intent = getattr(iface, "intent", "") or ""
    row = f"| `{path}` | `{iface.name}` | {intent or '—'} |"
    lines = [row]
    meta = getattr(iface, "metadata", {}) or {}
    args = meta.get("args") or []
    if args:
        lines.append("")
        lines.append("**Parameters**")
        lines.append("")
        lines.append("| Argument | Type | Required | Default |")
        lines.append("|---|---|---|---|")
        for arg in args:
            if isinstance(arg, dict):
                lines.append(_render_arg_row(arg))
    return lines


def family6_api_reference(fragment, config):
    """Render HTTP routes as a Markdown reference grouped by method."""
    del config
    interfaces = _http_interfaces(fragment)
    if not interfaces:
        body = "# API Reference\n\nNo HTTP routes defined."
        return DiagramSpec(
            id="prose:family6.api_reference",
            title="family6.api_reference",
            facets={"content_kind": "markdown", "body": body},
        )
    groups: dict[str, list] = {}
    for iface in interfaces:
        groups.setdefault(_http_method_of(iface), []).append(iface)
    sections: list[str] = ["# API Reference"]
    for method in sorted(groups):
        sections.append("")
        sections.append(f"## {method}")
        sections.append("")
        sections.append("| Path | Handler | Description |")
        sections.append("|---|---|---|")
        routes = sorted(groups[method], key=lambda i: (_http_path_of(i), i.id))
        # Emit each route row; append parameter blocks (which are not
        # table rows) after so tables stay well-formed per group.
        param_blocks: list[list[str]] = []
        for iface in routes:
            rendered = _render_route(iface)
            sections.append(rendered[0])
            if len(rendered) > 1:
                param_blocks.append([f"### `{_http_method_of(iface)} {_http_path_of(iface)}`", *rendered[1:]])
        for block in param_blocks:
            sections.append("")
            sections.extend(block)
    body = "\n".join(sections)
    return DiagramSpec(
        id="prose:family6.api_reference",
        title="family6.api_reference",
        facets={"content_kind": "markdown", "body": body},
    )


# ---------------------------------------------------------------------------
# family6.plugin_guide — entry-point plugin hooks
# ---------------------------------------------------------------------------


def _plugin_interfaces(fragment) -> list[Any]:
    return [i for i in fragment.entities.interfaces if getattr(i, "subkind", "") == "plugin_hook"]


def _entry_point_group_of(iface) -> str:
    meta = getattr(iface, "metadata", {}) or {}
    grp = meta.get("entry_point_group")
    return str(grp) if isinstance(grp, str) and grp else "unknown"


def _plugin_target_of(iface) -> str:
    meta = getattr(iface, "metadata", {}) or {}
    target = meta.get("target")
    return str(target) if isinstance(target, str) and target else ""


def _render_plugin_hook(iface) -> str:
    lines: list[str] = [f"### {iface.name}"]
    intent = getattr(iface, "intent", "") or ""
    if intent:
        lines.append("")
        lines.append(intent)
    target = _plugin_target_of(iface)
    if target:
        lines.append("")
        lines.append(f"**Target:** `{target}`")
    return "\n".join(lines)


def family6_plugin_guide(fragment, config):
    """Render plugin-hook interfaces grouped by entry-point group."""
    del config
    interfaces = _plugin_interfaces(fragment)
    if not interfaces:
        body = "# Plugin Guide\n\nNo plugin hooks defined."
        return DiagramSpec(
            id="prose:family6.plugin_guide",
            title="family6.plugin_guide",
            facets={"content_kind": "markdown", "body": body},
        )
    groups: dict[str, list] = {}
    for iface in interfaces:
        groups.setdefault(_entry_point_group_of(iface), []).append(iface)
    sections: list[str] = ["# Plugin Guide"]
    for group_name in sorted(groups):
        sections.append("")
        sections.append(f"## {group_name}")
        for iface in sorted(groups[group_name], key=lambda i: (i.name, i.id)):
            sections.append("")
            sections.append(_render_plugin_hook(iface))
    body = "\n".join(sections)
    return DiagramSpec(
        id="prose:family6.plugin_guide",
        title="family6.plugin_guide",
        facets={"content_kind": "markdown", "body": body},
    )
