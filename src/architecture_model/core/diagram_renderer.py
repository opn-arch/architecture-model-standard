"""Deterministic, dependency-free SVG rendering for :class:`DiagramSpec`."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from html import escape
import re
import textwrap
from types import MappingProxyType
from typing import Any

from architecture_model.core.diagram_spec import (
    Diagnostic,
    DiagramEdge,
    DiagramNode,
    DiagramProvenance,
    DiagramSpec,
)


@dataclass(frozen=True)
class DiagramRenderOptions:
    """Preferred canvas bounds and spacing used by the native renderer.

    Bounds smaller than the usable 320x240 canvas are ignored. The canvas
    expands beyond preferred bounds rather than clipping geometry or footers.
    """

    max_width: int = 4096
    max_height: int = 4096
    node_width: int = 190
    node_height: int = 92
    rank_gap: int = 110
    node_gap: int = 46
    margin: int = 48


@dataclass(frozen=True)
class DiagramToolbarAction:
    action: str
    label: str

    def to_dict(self) -> dict[str, str]:
        return {"action": self.action, "label": self.label}


@dataclass(frozen=True)
class DiagramPanelDiagnostic:
    severity: str
    code: str
    message: str
    view: str = ""
    source: str = ""
    context: MappingProxyType[str, Any] = MappingProxyType({})

    @classmethod
    def from_diagnostic(cls, value: Diagnostic) -> "DiagramPanelDiagnostic":
        return cls(value.severity, value.code, value.message, value.view, value.source, _freeze_mapping(value.context))

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity, "code": self.code, "message": self.message,
            "view": self.view, "source": self.source, "context": _thaw(self.context),
        }


@dataclass(frozen=True)
class DiagramPanel:
    """Renderer output suitable for contextual HTML assembly by a caller."""

    diagram_id: str
    svg: str
    toolbar: tuple[DiagramToolbarAction, ...]
    width: int
    height: int
    view_box: tuple[int, int, int, int]
    warnings: tuple[DiagramPanelDiagnostic, ...]
    provenance: DiagramProvenance
    drilldowns: MappingProxyType[str, "DiagramPanel"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "diagram_id": self.diagram_id,
            "svg": self.svg,
            "toolbar": [item.to_dict() for item in self.toolbar],
            "width": self.width,
            "height": self.height,
            "view_box": list(self.view_box),
            "warnings": [item.to_dict() for item in self.warnings],
            "provenance": self.provenance.to_dict(),
            "drilldowns": {key: value.to_dict() for key, value in sorted(self.drilldowns.items())},
        }


@dataclass(frozen=True)
class _Box:
    x: int
    y: int
    width: int
    height: int


_TOOLBAR = (
    DiagramToolbarAction("zoom-in", "Zoom in"),
    DiagramToolbarAction("zoom-out", "Zoom out"),
    DiagramToolbarAction("fit", "Fit diagram"),
    DiagramToolbarAction("reset", "Reset view"),
)

_ALLOWED_EDGE_STYLES = {"", "solid", "dashed", "dotted", "critical", "cycle"}
_DOTTED_EDGE_KINDS = {"decomposition", "contains", "error", "compensates"}
_DASHED_EDGE_KINDS = {"allocation", "owns", "interface-port"}
_DATA_EDGE_KINDS = {"data", "produces", "consumes", "exposes", "uses", "connects"}
_DEPENDENCY_EDGE_KINDS = {"dependency", "depends-on"}


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return _freeze_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted((_freeze(item) for item in value), key=repr))
    return value


def _freeze_mapping(value: dict[str, Any]) -> MappingProxyType[str, Any]:
    return MappingProxyType({key: _freeze(item) for key, item in sorted(value.items())})


def _thaw(value: Any) -> Any:
    if isinstance(value, MappingProxyType):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _text(value: object) -> str:
    value = str(value or "")
    value = "".join(char if ord(char) >= 32 or char in "\n\r\t" else " " for char in value)
    value = re.sub(r"\bon([a-z]+)\s*=", r"on \1: ", value, flags=re.IGNORECASE)
    value = re.sub(r"javascript\s*:", "javascript :", value, flags=re.IGNORECASE)
    return escape(value, quote=True)


def _lines(value: str, width: int, limit: int) -> list[str]:
    lines = textwrap.wrap(" ".join(value.split()), width=width, break_long_words=True) or [""]
    if len(lines) > limit:
        lines = lines[:limit]
        lines[-1] = lines[-1][:-1].rstrip() + "\u2026"
    return lines


def _ranks(spec: DiagramSpec) -> dict[str, int]:
    nodes = {node.id: node for node in spec.nodes}
    incoming = {identifier: 0 for identifier in nodes}
    outgoing: dict[str, list[str]] = {identifier: [] for identifier in nodes}
    for edge in sorted(spec.edges, key=_edge_key):
        if edge.source in nodes and edge.target in nodes and edge.source != edge.target:
            outgoing[edge.source].append(edge.target)
            incoming[edge.target] += 1
    ranks = {identifier: 0 for identifier in nodes}
    queue = sorted(identifier for identifier, count in incoming.items() if count == 0)
    visited: set[str] = set()
    while queue:
        identifier = queue.pop(0)
        visited.add(identifier)
        for target in sorted(outgoing[identifier]):
            ranks[target] = max(ranks[target], ranks[identifier] + 1)
            incoming[target] -= 1
            if incoming[target] == 0:
                queue.append(target)
                queue.sort()
    for identifier in sorted(nodes.keys() - visited):
        ranks[identifier] = max(ranks.values(), default=0) + 1

    # External actors and inferred systems start outside the system tiers.
    for node in nodes.values():
        if node.kind.lower() in {"actor", "external", "inferred-external"}:
            ranks[node.id] = 0
    return ranks


def _node_height(node: DiagramNode, options: DiagramRenderOptions) -> int:
    label_rows = len(_lines(node.label, 24, 2))
    content_height = 20 + label_rows * 16
    if node.subtitle:
        content_height += 18
    if node.badges:
        content_height += 16
    if node.kind.lower().replace("_", "-") == "actor":
        content_height += 76
    return max(options.node_height, content_height + 12)


def _layout(spec: DiagramSpec, options: DiagramRenderOptions) -> tuple[dict[str, _Box], dict[str, _Box], int, int]:
    ranks = _ranks(spec)
    buckets: dict[int, list[DiagramNode]] = {}
    for node in sorted(spec.nodes, key=lambda item: (ranks[item.id], item.group, item.lane, item.kind, item.id)):
        buckets.setdefault(ranks[node.id], []).append(node)
    boxes: dict[str, _Box] = {}
    direction = spec.direction.upper()
    label_lane = max((min(max(len(edge.label) * 6, 30), 168) + 6 for edge in spec.edges if edge.label), default=18)
    route_band = max(len(spec.edges), 1) * (label_lane if direction == "TB" else 18) + 18
    origin_x = options.margin + (route_band if direction == "TB" else 0)
    origin_y = options.margin + 72 + (route_band if direction != "TB" else 0)
    rank_count = max(len(buckets), 1)
    widest_rank = max((len(items) for items in buckets.values()), default=1)
    if direction == "TB":
        rank_step = min(
            options.node_height + options.rank_gap,
            max(options.node_height, (options.max_height - options.margin * 2 - 72 - options.node_height) // max(rank_count - 1, 1)),
        )
        item_step = min(
            options.node_width + options.node_gap,
            max(options.node_width, (options.max_width - options.margin * 2 - options.node_width) // max(widest_rank - 1, 1)),
        )
    else:
        rank_step = min(
            options.node_width + options.rank_gap,
            max(options.node_width, (options.max_width - options.margin * 2 - options.node_width) // max(rank_count - 1, 1)),
        )
        item_step = min(
            options.node_height + options.node_gap,
            max(options.node_height, (options.max_height - options.margin * 2 - 72 - options.node_height) // max(widest_rank - 1, 1)),
        )
    for rank_index, rank in enumerate(sorted(buckets)):
        cursor = 0
        for item_index, node in enumerate(buckets[rank]):
            height = _node_height(node, options)
            if direction == "TB":
                x = origin_x + item_index * item_step
                y = origin_y + rank_index * rank_step
            else:
                x = origin_x + rank_index * rank_step
                y = origin_y + cursor
                cursor += height + options.node_gap
            boxes[node.id] = _Box(x, y, options.node_width, height)

    containers = [*spec.groups, *spec.lanes]
    container_boxes: dict[str, _Box] = {}
    pending = {item.id: item for item in containers}
    for _ in range(len(pending) + 1):
        changed = False
        for identifier, container in sorted(list(pending.items())):
            members = [boxes[node.id] for node in spec.nodes if node.group == identifier or node.lane == identifier]
            members.extend(box for child, box in container_boxes.items() if next((item.parent for item in containers if item.id == child), "") == identifier)
            if not members and any(item.parent == identifier for item in containers if item.id in pending):
                continue
            if members:
                left = min(box.x for box in members) - 20
                top = min(box.y for box in members) - 36
                right = max(box.x + box.width for box in members) + 20
                bottom = max(box.y + box.height for box in members) + 20
                container_boxes[identifier] = _Box(left, top, right - left, bottom - top)
            else:
                empty_index = sum(1 for item in container_boxes.values() if item.width == options.node_width + 40 and item.height == options.node_height + 50)
                container_boxes[identifier] = _Box(
                    options.margin + empty_index * (options.node_width + options.node_gap),
                    options.margin + 42,
                    options.node_width + 40,
                    options.node_height + 50,
                )
            del pending[identifier]
            changed = True
        if not changed:
            break

    all_boxes = [*boxes.values(), *container_boxes.values()]
    content_right = max([box.x + box.width for box in all_boxes] + [320]) + options.margin
    content_bottom = max([box.y + box.height for box in all_boxes] + [170]) + options.margin
    footer_items = len(spec.legend) + len(spec.callouts) + len(spec.warnings) + bool(spec.provenance.source)
    width = max(content_right, 320)
    height = max(content_bottom + footer_items * 36 + (24 if footer_items else 0), 240)
    return boxes, container_boxes, width, height


def _shape(node: DiagramNode, box: _Box) -> str:
    x, y, width, height = box.x, box.y, box.width, box.height
    kind = node.kind.lower().replace("_", "-")
    common = 'class="node-shape" vector-effect="non-scaling-stroke"'
    if kind in {"scenario", "use-case", "behavior"}:
        return f'<ellipse {common} cx="{x + width / 2:g}" cy="{y + height / 2:g}" rx="{width / 2:g}" ry="{height / 2:g}"/>'
    if kind == "port":
        return f'<circle {common} cx="{x + width / 2:g}" cy="{y + height / 2:g}" r="{min(width, height) / 2:g}"/>'
    if kind in {"interface", "connector"}:
        inset = 18
        points = f"{x + inset},{y} {x + width - inset},{y} {x + width},{y + height / 2:g} {x + width - inset},{y + height} {x + inset},{y + height} {x},{y + height / 2:g}"
        return f'<polygon {common} points="{points}"/>'
    if kind == "actor":
        cx = x + width / 2
        return f'<g data-actor-glyph="true" data-x="{cx - 24:g}" data-y="{y + 5:g}" data-width="48" data-height="77"><circle {common} cx="{cx:g}" cy="{y + 17:g}" r="12"/><path {common} d="M {cx:g} {y + 29} V {y + 57} M {cx - 24:g} {y + 39} H {cx + 24:g} M {cx:g} {y + 57} L {cx - 20:g} {y + 82} M {cx:g} {y + 57} L {cx + 20:g} {y + 82}"/></g>'
    if kind == "system":
        return f'<rect {common} x="{x}" y="{y}" width="{width}" height="{height}" rx="8"/><rect {common} x="{x + 6}" y="{y + 6}" width="{width - 12}" height="{height - 12}" rx="5"/>'
    if kind in {"requirement", "callout", "note"}:
        fold = 18
        points = f"{x},{y} {x + width - fold},{y} {x + width},{y + fold} {x + width},{y + height} {x},{y + height}"
        return f'<polygon {common} points="{points}"/><path class="note-fold" d="M {x + width - fold} {y} V {y + fold} H {x + width}"/>'
    radius = 22 if kind in {"functional-block", "function", "outcome"} else 6
    return f'<rect {common} x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}"/>'


def _text_svg(role: str, value: str, x: float, y: float, width: float, height: float, css_class: str) -> str:
    return (
        f'<text class="{css_class}" data-text-role="{role}" data-x="{x:g}" data-y="{y:g}" '
        f'data-width="{width:g}" data-height="{height:g}" x="{x + width / 2:g}" y="{y + height * .72:g}">{_text(value)}</text>'
    )


def _node_svg(node: DiagramNode, box: _Box, view_id: str) -> str:
    classes = ["diagram-node", f"kind-{_text(node.kind.lower().replace('_', '-'))}"]
    if node.inferred:
        classes.append("is-inferred")
    if node.status:
        classes.append(f"status-{_text(node.status.lower())}")
    attributes = [
        f'id="node-{_text(node.id)}"', f'class="{" ".join(classes)}"', f'data-node-id="{_text(node.id)}"',
        f'data-kind="{_text(node.kind)}"', f'data-inferred="{str(node.inferred).lower()}"',
        f'data-status="{_text(node.status)}"', f'data-x="{box.x}"', f'data-y="{box.y}"',
        f'data-width="{box.width}"', f'data-height="{box.height}"',
        f'aria-label="{_text(node.label)}"', f'data-view-id="{_text(view_id)}"',
        f'data-entity-id="{_text(node.entity_ref or node.id)}"',
        f'data-display-entity-ref="{_text(node.entity_ref or node.id)}"',
    ]
    if node.entity_ref:
        attributes.append(f'data-entity-ref="{_text(node.entity_ref)}"')
    if node.drilldown_ref:
        attributes.append(f'data-drilldown-ref="{_text(node.drilldown_ref)}"')
    if node.entity_ref or node.drilldown_ref:
        attributes.extend(['tabindex="0"', 'role="button"', 'data-keyboard-action="activate"'])
    parts = [f'<g {" ".join(attributes)}><title>{_text(node.label)}</title>', _shape(node, box)]
    cursor = box.y + (88 if node.kind.lower().replace("_", "-") == "actor" else 12)
    text_x = box.x + 8
    text_width = box.width - 16
    for line in _lines(node.label, 24, 2):
        parts.append(_text_svg("title", line, text_x, cursor, text_width, 14, "node-label"))
        cursor += 16
    if node.subtitle:
        subtitle = _lines(node.subtitle, 28, 1)[0]
        cursor += 4
        parts.append(_text_svg("subtitle", subtitle, text_x, cursor, text_width, 10, "node-subtitle"))
        cursor += 10
    if node.badges:
        badge = _lines(" | ".join(sorted(node.badges)), 30, 1)[0]
        cursor += 6
        parts.append(_text_svg("badge", badge, text_x, cursor, text_width, 10, "node-badge"))
    if node.evidence:
        parts.append(f'<g class="evidence-indicator" data-evidence="true"><title>{_text(_provenance_text(node.evidence))}</title><circle cx="{box.x + box.width - 8}" cy="{box.y + 8}" r="4"/></g>')
    parts.append("</g>")
    return "".join(parts)


def _provenance_text(values: list[DiagramProvenance]) -> str:
    return "; ".join(filter(None, (value.source for value in values))) or "Evidence available"


def _edge_path(source: _Box, target: _Box, direction: str, lane: int, margin: int, lane_step: int = 18) -> str:
    if direction == "TB":
        sx, sy = source.x + source.width / 2, source.y
        tx, ty = target.x + target.width / 2, target.y
        lane_x = margin + lane * lane_step
        return f"M {sx:g} {sy:g} H {lane_x:g} V {ty:g} H {tx:g}"
    sx, sy = source.x + source.width, source.y + source.height / 2
    tx, ty = target.x, target.y + target.height / 2
    lane_y = margin + 72 + lane * 18
    return f"M {sx:g} {sy:g} V {lane_y:g} H {tx:g} V {ty:g}"


def _edge_style(edge: DiagramEdge) -> str:
    requested = edge.style.lower().strip()
    if requested not in _ALLOWED_EDGE_STYLES:
        raise ValueError(f"Unsupported edge style: {edge.style}")
    kind = edge.kind.lower().replace("_", "-")
    if requested in {"dashed", "dotted"}:
        return requested
    if kind in _DOTTED_EDGE_KINDS:
        return "dotted"
    if kind in _DASHED_EDGE_KINDS or edge.inferred:
        return "dashed"
    if kind in _DATA_EDGE_KINDS:
        return "data"
    if kind in _DEPENDENCY_EDGE_KINDS:
        return "dependency"
    return "operational"


def _edge_svg(edge: DiagramEdge, boxes: dict[str, _Box], direction: str, index: int, margin: int, lane_step: int) -> str:
    kind = edge.kind.lower().replace("_", "-")
    semantic_style = _edge_style(edge)
    classes = ["diagram-edge", f"kind-{_text(kind)}", f"edge-style-{semantic_style}"]
    dash = "stroke-dasharray:2 6;" if semantic_style == "dotted" else "stroke-dasharray:8 6;" if semantic_style == "dashed" else ""
    if edge.inferred:
        classes.append("is-inferred")
    if edge.critical or edge.style.lower() in {"critical", "cycle"}:
        classes.append("is-critical")
    label_text = _lines(edge.label + (f" ({edge.count})" if edge.count != 1 else ""), 28, 1)[0] if edge.label or edge.count != 1 else ""
    label_width = min(max(len(label_text) * 6, 30), 168) if label_text else 30
    path = _edge_path(boxes[edge.source], boxes[edge.target], direction, index, margin, lane_step)
    marker = ' marker-end="url(#arrow)"' if kind not in {"decomposition", "allocation"} else ""
    evidence_title = _provenance_text(edge.evidence) if edge.evidence else f"{edge.source} to {edge.target}"
    title = f"{edge.label}: {evidence_title}" if edge.label else evidence_title
    label = edge.label + (f" ({edge.count})" if edge.count != 1 else "")
    result = [
        f'<path id="edge-{index}" class="{" ".join(classes)}" data-edge-id="edge-{index}" data-source="{_text(edge.source)}" data-target="{_text(edge.target)}" data-kind="{_text(edge.kind)}" data-label-hidden="{str(not bool(label)).lower()}" d="{path}" style="{dash}"{marker}><title>{_text(title)}</title></path>'
    ]
    if label:
        source, target = boxes[edge.source], boxes[edge.target]
        if direction == "TB":
            x = margin + index * lane_step + 4
            y = (source.y + target.y) / 2 - 6
        else:
            x = (source.x + source.width + target.x) / 2 - label_width / 2
            y = margin + 72 + index * 18 - 13
        result.append(f'<text class="edge-label" data-edge-label="edge-{index}" data-x="{x:g}" data-y="{y:g}" data-width="{label_width:g}" data-height="12" x="{x + label_width / 2:g}" y="{y + 9:g}">{_text(label_text)}</text>')
    if edge.evidence:
        result.append(f'<g class="evidence-indicator" data-evidence="true"><title>{_text(title)}</title><circle cx="{boxes[edge.source].x + boxes[edge.source].width + 6}" cy="{boxes[edge.source].y + 6}" r="4"/></g>')
    return "".join(result)


def _stylesheet() -> str:
    return """<style>
.diagram { font-family: system-ui, sans-serif; color: #172033; }
.diagram-node .node-shape { fill: #f8fafc; stroke: #334155; stroke-width: 1.5; }
.diagram-node.is-inferred .node-shape { stroke-dasharray: 7 5; }
.kind-system .node-shape { fill: #eef6ff; stroke: #1d4ed8; }
.kind-functional-block .node-shape,.kind-function .node-shape { fill: #ecfdf5; stroke: #047857; }
.kind-outcome .node-shape { fill: #fff7ed; stroke: #c2410c; }
.kind-requirement .node-shape { fill: #fffbeb; stroke: #a16207; }
.container { fill: #f8fafc; fill-opacity: .28; stroke: #94a3b8; stroke-width: 1; }
.container.system { stroke-width: 3; }
.diagram-edge { fill: none; stroke: #475569; stroke-width: 1.5; }
.diagram-edge.is-critical { stroke: #b91c1c; stroke-width: 3; }
.node-label,.node-subtitle,.edge-label,.footer-text,.container-label { fill: #172033; dominant-baseline: middle; }
.node-label { text-anchor: middle; font-size: 13px; font-weight: 600; }
.node-subtitle { text-anchor: middle; font-size: 10px; fill: #64748b; }
.node-badge { font-size: 8px; fill: #475569; }
.edge-label,.footer-text,.container-label { font-size: 10px; }
.diagram-title { font-size: 20px; font-weight: 700; }
.diagram-subtitle { font-size: 12px; fill: #64748b; }
.diagnostic-error { fill: #b91c1c; }.diagnostic-warning { fill: #a16207; }
.evidence-indicator { fill: #2563eb; }
</style>"""


def _footer(spec: DiagramSpec, start_y: int, boxes: dict[str, _Box], width: int) -> str:
    parts: list[str] = []
    y = start_y
    item_width = max(width - 96, 224)
    for item in sorted(spec.legend, key=lambda value: value.id):
        label = _lines(f"{item.label}: {item.description}", max(item_width // 7, 20), 2)
        parts.append(f'<g data-section="legend" data-footer-item="legend:{_text(item.id)}" data-x="48" data-y="{y - 14}" data-width="{item_width}" data-height="32"><text class="footer-text" x="48" y="{y}">{_text(" ".join(label))}</text></g>')
        y += 36
    for callout in sorted(spec.callouts, key=lambda item: item.id):
        evidence = "; ".join(callout.evidence)
        parts.append(f'<g data-callout-id="{_text(callout.id)}" data-footer-item="callout:{_text(callout.id)}" data-kind="{_text(callout.kind)}" data-target-ref="{_text(callout.target)}" data-evidence="{_text(evidence)}" data-x="48" data-y="{y - 14}" data-width="{item_width}" data-height="32"><title>{_text(evidence or callout.label)}</title><text class="footer-text" x="48" y="{y}">{_text(_lines(callout.label, max(item_width // 7, 20), 2)[0])}</text></g>')
        if callout.target in boxes:
            target = boxes[callout.target]
            parts.append(f'<path class="callout-connector" data-callout-connector="{_text(callout.id)}" data-target-ref="{_text(callout.target)}" d="M {target.x + target.width / 2:g} {target.y + target.height:g} L 48 {y - 14}"/>')
        y += 36
    for diagnostic in sorted(spec.warnings, key=lambda item: (item.severity, item.code, item.message)):
        parts.append(f'<g data-diagnostic-code="{_text(diagnostic.code)}" data-footer-item="diagnostic:{_text(diagnostic.code)}" data-severity="{_text(diagnostic.severity)}" data-x="48" data-y="{y - 14}" data-width="{item_width}" data-height="32"><text class="footer-text diagnostic-{_text(diagnostic.severity.lower())}" x="48" y="{y}">{_text(diagnostic.severity.upper())}: {_text(_lines(diagnostic.message, max(item_width // 7, 20), 2)[0])}</text></g>')
        y += 36
    if spec.provenance.source:
        parts.append(f'<g data-section="provenance" data-footer-item="provenance" data-x="48" data-y="{y - 14}" data-width="{item_width}" data-height="32"><title>{_text(str(spec.provenance.to_dict()))}</title><text class="footer-text" x="48" y="{y}">Source: {_text(spec.provenance.source)}</text></g>')
    return "".join(parts)


def _edge_key(edge: DiagramEdge) -> tuple[Any, ...]:
    evidence = tuple(repr(item.to_dict()) for item in edge.evidence)
    return edge.source, edge.target, edge.kind, edge.label, edge.count, edge.style, edge.critical, edge.inferred, evidence


def _overlaps(first: _Box, second: _Box) -> bool:
    return (
        first.x < second.x + second.width and second.x < first.x + first.width
        and first.y < second.y + second.height and second.y < first.y + first.height
    )


def _render(spec: DiagramSpec, options: DiagramRenderOptions) -> tuple[str, int, int]:
    spec.validate()
    for edge in spec.edges:
        _edge_style(edge)
    boxes, containers, width, height = _layout(spec, options)
    namespace = f"diagram-{re.sub(r'[^a-zA-Z0-9_-]+', '-', spec.id).strip('-') or 'view'}-{hashlib.sha256(spec.id.encode()).hexdigest()[:8]}"
    title_id, desc_id, arrow_id = f"{namespace}-title", f"{namespace}-desc", f"{namespace}-arrow"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" class="diagram" data-diagram-id="{_text(spec.id)}" data-pan-zoom="true" width="100%" height="auto" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet" role="img" aria-labelledby="{title_id} {desc_id}">',
        f'<title id="{title_id}">{_text(spec.title)}</title>',
        f'<desc id="{desc_id}">{_text(spec.subtitle or "Architecture diagram")}</desc>',
        _stylesheet(),
        f'<defs><marker id="{arrow_id}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z"/></marker></defs>',
        f'<text class="diagram-title" x="{options.margin}" y="30">{_text(spec.title)}</text>',
    ]
    if spec.subtitle:
        parts.append(f'<text class="diagram-subtitle" x="{options.margin}" y="51">{_text(_lines(spec.subtitle, 80, 1)[0])}</text>')
    container_lookup = {item.id: item for item in [*spec.groups, *spec.lanes]}
    group_label_boxes: list[_Box] = []
    for identifier, box in sorted(containers.items(), key=lambda item: (container_lookup[item[0]].order, item[0])):
        container = container_lookup[identifier]
        label_width = min(max(len(container.label) * 6, 30), max(box.width - 16, 30))
        label_box = _Box(box.x + 8, box.y + 5, label_width, 14)
        while any(_overlaps(label_box, occupied) for occupied in group_label_boxes) and label_box.x + label_box.width + 8 <= box.x + box.width:
            label_box = _Box(label_box.x + 8, label_box.y, label_box.width, label_box.height)
        group_label_boxes.append(label_box)
        parts.append(f'<g data-container-id="{_text(identifier)}" data-kind="{_text(container.kind)}" data-x="{box.x}" data-y="{box.y}" data-width="{box.width}" data-height="{box.height}" data-header-height="24"><rect class="container {_text(container.kind)}" x="{box.x}" y="{box.y}" width="{box.width}" height="{box.height}" rx="8"/><text class="container-label" data-group-label="{_text(identifier)}" data-x="{label_box.x}" data-y="{label_box.y}" data-width="{label_box.width}" data-height="{label_box.height}" x="{label_box.x}" y="{label_box.y + 11}">{_text(container.label)}</text></g>')

    ordered_edges = sorted(spec.edges, key=_edge_key)
    edge_lane_step = max(
        (min(max(len(_lines(edge.label, 28, 1)[0]) * 6, 30), 168) + 6 for edge in ordered_edges if edge.label),
        default=18,
    ) if spec.direction.upper() == "TB" else 18
    parallel_totals: dict[tuple[str, str], int] = {}
    for edge in ordered_edges:
        parallel_totals[(edge.source, edge.target)] = parallel_totals.get((edge.source, edge.target), 0) + 1
    parallel_seen: dict[tuple[str, str], int] = {}
    for index, edge in enumerate(ordered_edges):
        if edge.source not in boxes or edge.target not in boxes:
            continue
        key = (edge.source, edge.target)
        parallel_seen[key] = parallel_seen.get(key, 0) + 1
        edge_svg = _edge_svg(edge, boxes, spec.direction.upper(), index, options.margin, edge_lane_step)
        parts.append(edge_svg.replace('url(#arrow)', f'url(#{arrow_id})'))
    for node in sorted(spec.nodes, key=lambda item: item.id):
        parts.append(_node_svg(node, boxes[node.id], spec.id))
    footer_start = max([box.y + box.height for box in [*boxes.values(), *containers.values()]] + [160]) + 38
    parts.append(_footer(spec, footer_start, boxes, width))
    parts.append("</svg>")
    return "".join(parts), width, height


def render_diagram_svg(spec: DiagramSpec, options: DiagramRenderOptions | None = None) -> str:
    """Render a diagram directly to standalone, offline SVG."""

    return _render(spec, options or DiagramRenderOptions())[0]


def render_diagram_drilldowns(spec: DiagramSpec, options: DiagramRenderOptions | None = None) -> dict[str, DiagramPanel]:
    """Render embedded drilldowns keyed by their exact declared IDs."""

    result: dict[str, DiagramPanel] = {}
    for drilldown in sorted(spec.drilldowns, key=lambda item: item.id):
        if drilldown.spec is not None:
            result[drilldown.id] = render_diagram_panel(drilldown.spec, options)
    return result


def render_diagram_panel(spec: DiagramSpec, options: DiagramRenderOptions | None = None) -> DiagramPanel:
    """Return SVG plus host-controlled toolbar and interaction metadata."""

    selected = options or DiagramRenderOptions()
    svg, width, height = _render(spec, selected)
    warnings = list(spec.warnings)
    if selected.max_width < 320 or selected.max_height < 240:
        warnings.append(Diagnostic("warning", "RENDER_BOUNDS_TOO_SMALL", "Requested canvas bounds were below the usable 320x240 minimum", view=spec.id))
    return DiagramPanel(
        diagram_id=spec.id,
        svg=svg,
        toolbar=_TOOLBAR,
        width=width,
        height=height,
        view_box=(0, 0, width, height),
        warnings=tuple(DiagramPanelDiagnostic.from_diagnostic(item) for item in sorted(warnings, key=lambda item: (item.severity, item.code, item.message))),
        provenance=spec.provenance,
        drilldowns=MappingProxyType(render_diagram_drilldowns(spec, selected)),
    )
