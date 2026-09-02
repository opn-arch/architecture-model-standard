"""Deterministic, dependency-free SVG rendering for :class:`DiagramSpec`."""

from __future__ import annotations

from collections import defaultdict
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

    max_width: int = 2400
    max_height: int = 1800
    node_width: int = 190
    node_height: int = 92
    rank_gap: int = 110
    node_gap: int = 46
    margin: int = 48
    theme: str = "light"


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
    theme: str = "light"

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
            "theme": self.theme,
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
_PALETTES = {
    "light": {"background": "#ffffff", "text": "#172033", "muted": "#475569", "surface": "#f8fafc", "edge": "#475569", "critical": "#a33a12"},
    "dark": {"background": "#0f172a", "text": "#f8fafc", "muted": "#cbd5e1", "surface": "#1e293b", "edge": "#cbd5e1", "critical": "#f59e0b"},
}


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


def _crossing_minimized_order(
    buckets: dict[int | str, list[DiagramNode]], edges: list[DiagramEdge], order: list[int | str],
) -> dict[int | str, list[DiagramNode]]:
    neighbors: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        neighbors[edge.source].add(edge.target)
        neighbors[edge.target].add(edge.source)
    result = {key: sorted(values, key=lambda node: node.id) for key, values in buckets.items()}
    sweeps = ((order[1:], -1), (list(reversed(order[:-1])), 1)) * 4
    for sweep, offset in sweeps:
        positions = {node.id: index for key in order for index, node in enumerate(result[key])}
        groups = {node.id: key for key in order for node in result[key]}
        for key in sweep:
            key_index = order.index(key)
            reference = key_index + offset
            adjacent = {order[reference]} if 0 <= reference < len(order) else set()
            positions = {node.id: index for group in order for index, node in enumerate(result[group])}
            result[key].sort(key=lambda node: (
                sum(
                    positions[item] for item in neighbors[node.id]
                    if item in groups and groups[item] in adjacent
                ) / len([
                    item for item in neighbors[node.id]
                    if item in groups and groups[item] in adjacent
                ]) if any(item in groups and groups[item] in adjacent for item in neighbors[node.id]) else positions[node.id],
                node.id,
            ))
    return result


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


def _lane_layout(spec: DiagramSpec, options: DiagramRenderOptions) -> dict[str, _Box]:
    """Place lane members by lane order, independent of graph cycles."""
    direction = spec.direction.upper()
    ordered_lanes = sorted(spec.lanes, key=lambda item: (item.order, item.id))
    lane_order = [lane.id for lane in ordered_lanes]
    lane_members = {
        lane.id: [node for node in spec.nodes if node.lane == lane.id]
        for lane in ordered_lanes
    }
    if spec.layout == "logical-tiers":
        lane_members = _crossing_minimized_order(lane_members, spec.edges, lane_order)
    elif spec.layout == "operational-lanes":
        scenario_order = {
            node.id: index for index, node in enumerate(node for node in spec.nodes if node.kind == "scenario")
        }
        targets: dict[str, int] = {}
        for edge in spec.edges:
            if edge.target in scenario_order:
                targets[edge.source] = min(targets.get(edge.source, len(scenario_order)), scenario_order[edge.target])
        lane_members = {
            key: sorted(values, key=lambda node: (
                scenario_order[node.id] if node.id in scenario_order else targets.get(node.id, len(scenario_order)), node.id,
            ))
            for key, values in lane_members.items()
        }
    else:
        lane_members = {key: sorted(values, key=lambda node: (node.kind, node.id)) for key, values in lane_members.items()}
    assigned = {node.id for members in lane_members.values() for node in members}
    unassigned = sorted((node for node in spec.nodes if node.id not in assigned), key=lambda node: (node.kind, node.id))
    boxes: dict[str, _Box] = {}
    header = 36
    lane_gap = 56
    origin_x = options.margin + 20
    origin_y = options.margin + 72 + header

    if direction == "TB":
        y = origin_y
        for lane in ordered_lanes:
            members = lane_members[lane.id]
            for index, node in enumerate(members):
                boxes[node.id] = _Box(
                    origin_x + index * (options.node_width + options.node_gap), y,
                    options.node_width, _node_height(node, options),
                )
            y += max((_node_height(node, options) for node in members), default=options.node_height) + lane_gap
        for index, node in enumerate(unassigned):
            boxes[node.id] = _Box(
                origin_x + index * (options.node_width + options.node_gap), y,
                options.node_width, _node_height(node, options),
            )
    else:
        x = origin_x
        for lane in ordered_lanes:
            members = lane_members[lane.id]
            tallest = max((_node_height(node, options) for node in members), default=options.node_height)
            footer_reserve = (len(spec.legend) + len(spec.callouts) + len(spec.warnings) + bool(spec.provenance.source)) * 36 + 24
            max_rows = max(1, (options.max_height - origin_y - options.margin - footer_reserve) // (tallest + options.node_gap))
            column_count = max(1, (len(members) + max_rows - 1) // max_rows)
            for index, node in enumerate(members):
                height = _node_height(node, options)
                column, row = divmod(index, max_rows)
                boxes[node.id] = _Box(
                    x + column * (options.node_width + options.node_gap),
                    origin_y + row * (tallest + options.node_gap),
                    options.node_width, height,
                )
            x += column_count * options.node_width + max(0, column_count - 1) * options.node_gap + options.rank_gap
        y = origin_y
        for node in unassigned:
            height = _node_height(node, options)
            boxes[node.id] = _Box(x, y, options.node_width, height)
            y += height + options.node_gap
    return boxes


def _functional_flow_layout(spec: DiagramSpec, options: DiagramRenderOptions) -> dict[str, _Box]:
    """Use compact topological columns without a global routing band."""
    ranks = _ranks(spec)
    buckets: dict[int, list[DiagramNode]] = defaultdict(list)
    for node in sorted(spec.nodes, key=lambda item: (ranks[item.id], item.id)):
        buckets[ranks[node.id]].append(node)
    columns = sorted(buckets)
    buckets = _crossing_minimized_order(buckets, spec.edges, columns)
    x_step = options.node_width + 74
    available_height = 720
    boxes: dict[str, _Box] = {}
    for column, rank in enumerate(columns):
        members = buckets[rank]
        heights = [_node_height(node, options) for node in members]
        gap = min(54, max(24, (available_height - sum(heights)) // max(len(members) - 1, 1)))
        y = options.margin + 72
        for node, height in zip(members, heights):
            boxes[node.id] = _Box(options.margin + 20 + column * x_step, y, options.node_width, height)
            y += height + gap
    return boxes


def _catalog_layout(spec: DiagramSpec, options: DiagramRenderOptions) -> dict[str, _Box]:
    """Place actors left of actor-contiguous use-case rows."""
    cases = [node for node in spec.nodes if node.kind in {"use-case", "scenario", "behavior"}]
    actors = sorted((node for node in spec.nodes if node.kind in {"actor", "external"}), key=lambda node: node.id)
    support = sorted((node for node in spec.nodes if node not in cases and node not in actors), key=lambda node: (node.kind, node.id))
    actor_order = {node.id: index for index, node in enumerate(actors)}
    memberships: dict[str, list[int]] = defaultdict(list)
    for edge in spec.edges:
        if edge.kind == "participates" and edge.source in actor_order:
            memberships[edge.target].append(actor_order[edge.source])
    cases.sort(key=lambda node: (tuple(memberships[node.id]) or (len(actors),), node.id))
    boxes: dict[str, _Box] = {}
    case_x = options.margin + options.node_width + 140
    y = options.margin + 72
    grouped = {
        membership: [node for node in cases if tuple(memberships[node.id]) == membership]
        for membership in sorted({tuple(memberships[node.id]) for node in cases})
    }
    exclusive_columns = {
        membership[0]: index for index, membership in enumerate(
            sorted(value for value in grouped if len(value) == 1)
        )
    }
    for membership, members in grouped.items():
        row_heights: list[int] = []
        for index in range(0, len(members), 2):
            row_heights.append(max(_node_height(node, options) for node in members[index:index + 2]))
        row_y = [y]
        for height in row_heights[:-1]:
            row_y.append(row_y[-1] + height + 8)
        for index, node in enumerate(members):
            if len(membership) > 1 and all(value in exclusive_columns for value in membership):
                column = sum(exclusive_columns[value] for value in membership) / len(membership)
            elif len(membership) == 1:
                column = exclusive_columns[membership[0]]
            else:
                column = 0
            boxes[node.id] = _Box(
                int(case_x + (column + index % 2) * (options.node_width + 54)), row_y[index // 2],
                options.node_width, _node_height(node, options),
            )
        y += sum(row_heights) + max(0, len(row_heights) - 1) * 8 + 42
    for actor in actors:
        targets = [edge.target for edge in spec.edges if edge.kind == "participates" and edge.source == actor.id and edge.target in boxes]
        height = _node_height(actor, options)
        top = min((boxes[target].y for target in targets), default=options.margin + 72)
        boxes[actor.id] = _Box(options.margin + 20, top, options.node_width, height)
    support_y = options.margin + 72
    support_x = case_x + 2 * (options.node_width + 54)
    for node in support:
        height = _node_height(node, options)
        boxes[node.id] = _Box(support_x, support_y, options.node_width, height)
        support_y += height + 24
    return boxes


def _semantic_detail_layout(spec: DiagramSpec, options: DiagramRenderOptions) -> dict[str, _Box]:
    """Place drilldown content densely while preserving its semantic order."""
    lane_order = {lane.id: index for index, lane in enumerate(sorted(spec.lanes, key=lambda item: (item.order, item.id)))}
    ranks = _ranks(spec)

    def key(node: DiagramNode) -> tuple[Any, ...]:
        if spec.layout == "use-case-sequence":
            return (0 if node.kind in {"actor", "external", "use-case"} else 1 if node.kind == "step" else 2,
                    node.metrics.get("order", 0), node.id)
        if spec.layout == "functional-detail":
            return (ranks[node.id], 0 if node.kind in {"functional-block", "function", "capability"} else 1, node.kind, node.id)
        if spec.layout == "logical-detail":
            return (lane_order.get(node.lane, len(lane_order)), ranks[node.id], node.kind, node.id)
        return (ranks[node.id], node.kind, node.id)

    ordered = sorted(spec.nodes, key=key)
    boxes: dict[str, _Box] = {}
    origin_x, origin_y = options.margin + 20, options.margin + 72
    x_step, y_step = options.node_width + 24, options.node_height + 24
    if spec.layout == "operational-detail":
        neighbors: dict[str, set[str]] = {node.id: set() for node in ordered}
        for edge in spec.edges:
            neighbors[edge.source].add(edge.target)
            neighbors[edge.target].add(edge.source)
        seen: set[str] = set()
        components: list[list[DiagramNode]] = []
        by_id = {node.id: node for node in ordered}
        for node in ordered:
            if node.id in seen:
                continue
            stack, component = [node.id], []
            while stack:
                identifier = stack.pop()
                if identifier in seen:
                    continue
                seen.add(identifier)
                component.append(by_id[identifier])
                stack.extend(sorted(neighbors[identifier] - seen, reverse=True))
            components.append(sorted(component, key=lambda item: (-len(neighbors[item.id]), key(item))))
        if len(components) > 1:
            rows = [component[index:index + 5] for component in components if len(component) > 1 for index in range(0, len(component), 5)]
            isolated = [component[0] for component in components if len(component) == 1]
            rows.extend(isolated[index:index + 5] for index in range(0, len(isolated), 5))
            for row, members in enumerate(rows):
                for column, node in enumerate(members):
                    boxes[node.id] = _Box(origin_x + column * x_step, origin_y + row * y_step,
                                          options.node_width, _node_height(node, options))
            return boxes
    if spec.layout == "logical-detail" and spec.lanes:
        y = origin_y
        for lane in sorted(spec.lanes, key=lambda item: (item.order, item.id)):
            members = [node for node in ordered if node.lane == lane.id]
            for index, node in enumerate(members):
                row, column = divmod(index, 5)
                if row % 2:
                    column = 4 - column
                boxes[node.id] = _Box(origin_x + column * x_step, y + row * y_step,
                                      options.node_width, _node_height(node, options))
            row_count = max(1, (len(members) + 4) // 5)
            y += row_count * y_step + 32
        unassigned = [node for node in ordered if not node.lane]
        for column, node in enumerate(unassigned):
            boxes[node.id] = _Box(origin_x + column * x_step, y, options.node_width, _node_height(node, options))
        return boxes

    columns = min(6 if spec.layout == "use-case-sequence" else 4, max(len(ordered), 1))
    for index, node in enumerate(ordered):
        row, column = divmod(index, columns)
        if row % 2:
            column = columns - column - 1
        boxes[node.id] = _Box(origin_x + column * x_step, origin_y + row * y_step,
                              options.node_width, _node_height(node, options))
    return boxes


def _use_case_edge_path(edge: DiagramEdge, boxes: dict[str, _Box], index: int) -> str:
    source, target = boxes[edge.source], boxes[edge.target]
    if edge.kind != "participates":
        return _lane_edge_path(source, target, "LR", index % 5, [
            box for identifier, box in boxes.items() if identifier not in {edge.source, edge.target}
        ])
    sx, sy = source.x + source.width, source.y + source.height / 2
    tx, ty = target.x, target.y + target.height / 2
    bus_x = sx + 24 + (sum(ord(char) for char in edge.source) % 5) * 8
    intervening = [
        box for identifier, box in boxes.items()
        if identifier not in {edge.source, edge.target}
        and box.x > bus_x and box.x < tx and box.y < ty < box.y + box.height
    ]
    if intervening:
        track_y = source.y - 12 - index % 3 * 4
        target_right = target.x + target.width + 18
        return _points_path([
            (sx, sy), (bus_x, sy), (bus_x, track_y),
            (target_right, track_y), (target_right, ty),
            (target.x + target.width, ty),
        ])
    return _points_path([(sx, sy), (bus_x, sy), (bus_x, ty), (tx, ty)])


def _operational_edge_path(edge: DiagramEdge, boxes: dict[str, _Box], nodes: dict[str, DiagramNode], index: int) -> str:
    """Route ConOps flows on separated source, delivery, and outcome buses."""

    source, target = boxes[edge.source], boxes[edge.target]
    source_node, target_node = nodes[edge.source], nodes[edge.target]
    obstacles = [box for identifier, box in boxes.items() if identifier not in {edge.source, edge.target}]
    sy, ty = source.y + source.height / 2, target.y + target.height / 2
    if source_node.kind in {"actor", "external"} and target_node.kind == "scenario":
        sx, tx = source.x + source.width, target.x
        bus_x = tx - 24 - index % 5 * 8
        return _points_path([(sx, sy), (bus_x, sy), (bus_x, ty), (tx, ty)])
    if source_node.kind == "scenario" and target_node.kind == "scenario":
        boundary_x = source.x + source.width
        return _points_path([(boundary_x, sy), (boundary_x, ty), (target.x + target.width, ty)])
    if source_node.kind == "scenario" and target_node.kind in {"system", "outcome"}:
        boundary_boxes = [box for identifier, box in boxes.items() if nodes[identifier].kind == "system"]
        boundary_left = min((box.x for box in boundary_boxes), default=target.x)
        trunk_x = source.x + source.width + max((boundary_left - source.x - source.width) / 2, 18)
        if target_node.kind == "system":
            return _points_path([(source.x + source.width, sy), (trunk_x, sy), (trunk_x, ty), (target.x, ty)])
        bottom = max(box.y + box.height for box in boxes.values()) + 20
        target_right = target.x + target.width
        outer_right = max(box.x + box.width for box in boxes.values()) + 20
        return _points_path([
            (source.x + source.width, sy), (trunk_x, sy), (trunk_x, bottom),
            (outer_right, bottom), (outer_right, ty), (target_right, ty),
        ])
    return _lane_edge_path(source, target, "LR", index % 5, obstacles)


def _layout(spec: DiagramSpec, options: DiagramRenderOptions) -> tuple[dict[str, _Box], dict[str, _Box], int, int]:
    direction = spec.direction.upper()
    if spec.layout in {"detail-cards", "operational-detail", "functional-detail", "logical-detail", "use-case-sequence"}:
        boxes = _semantic_detail_layout(spec, options)
    elif spec.layout == "functional-flow":
        boxes = _functional_flow_layout(spec, options)
    elif spec.layout == "use-case-catalog":
        boxes = _catalog_layout(spec, options)
    elif spec.lanes:
        boxes = _lane_layout(spec, options)
    else:
        ranks = _ranks(spec)
        buckets: dict[int, list[DiagramNode]] = {}
        for node in sorted(spec.nodes, key=lambda item: (ranks[item.id], item.group, item.kind, item.id)):
            buckets.setdefault(ranks[node.id], []).append(node)
        boxes = {}
        label_lane = max((min(max(len(edge.label) * 6, 30), 168) + 6 for edge in spec.edges if edge.label), default=18)
        route_band = max(len(spec.edges), 1) * (label_lane if direction == "TB" else 18) + 18
        origin_x = options.margin + (route_band if direction == "TB" else 0)
        origin_y = options.margin + 72 + (route_band if direction != "TB" else 0)
        rank_count = max(len(buckets), 1)
        widest_rank = max((len(items) for items in buckets.values()), default=1)
        footer_reserve = (len(spec.legend) + len(spec.callouts) + len(spec.warnings) + bool(spec.provenance.source)) * 36 + 24
        wrapped_linear = direction == "TB" and len(spec.nodes) > 12 and widest_rank <= 2
        rows_per_column = max(
            1, (options.max_height - origin_y - options.margin * 2 - footer_reserve) // (options.node_height + 24),
        ) if wrapped_linear else rank_count
        if direction == "TB":
            rank_step = options.node_height + 24 if wrapped_linear else min(options.node_height + options.rank_gap, max(options.node_height, (options.max_height - options.margin * 2 - 72 - options.node_height) // max(rank_count - 1, 1)))
            item_step = min(options.node_width + options.node_gap, max(options.node_width, (options.max_width - options.margin * 2 - options.node_width) // max(widest_rank - 1, 1)))
            max_columns = max(1, (options.max_width - origin_x - options.margin - 40) // max(item_step, 1))
            rank_offsets: dict[int, int] = {}
            rank_cursor = 0
            for rank in sorted(buckets):
                rank_offsets[rank] = rank_cursor
                rank_cursor += max(1, (len(buckets[rank]) + max_columns - 1) // max_columns) * rank_step
        else:
            rank_step = min(options.node_width + options.rank_gap, max(options.node_width, (options.max_width - options.margin * 2 - options.node_width) // max(rank_count - 1, 1)))
            item_step = min(options.node_height + options.node_gap, max(options.node_height, (options.max_height - options.margin * 2 - 72 - options.node_height) // max(widest_rank - 1, 1)))
            tallest = max((_node_height(node, options) for node in spec.nodes), default=options.node_height)
            max_rows = max(1, (options.max_height - origin_y - options.margin - 40 - footer_reserve) // (tallest + options.node_gap))
            rank_offsets = {}
            rank_cursor = 0
            for rank in sorted(buckets):
                rank_offsets[rank] = rank_cursor
                rank_cursor += max(1, (len(buckets[rank]) + max_rows - 1) // max_rows) * rank_step
        for rank_index, rank in enumerate(sorted(buckets)):
            cursor = 0
            for item_index, node in enumerate(buckets[rank]):
                height = _node_height(node, options)
                if direction == "TB":
                    if wrapped_linear:
                        column, row = divmod(rank_index, rows_per_column)
                        x = origin_x + column * (options.node_width + options.rank_gap)
                        y = origin_y + row * rank_step
                    else:
                        row, column = divmod(item_index, max_columns)
                        x = origin_x + column * item_step
                        y = origin_y + rank_offsets[rank] + row * rank_step
                else:
                    column, row = divmod(item_index, max_rows)
                    x = origin_x + rank_offsets[rank] + column * rank_step
                    y = origin_y + row * (tallest + options.node_gap)
                boxes[node.id] = _Box(x, y, options.node_width, height)

    footer_reserve = (len(spec.legend) + len(spec.callouts) + len(spec.warnings) + bool(spec.provenance.source)) * 36 + 24
    node_right = max((box.x + box.width for box in boxes.values()), default=0)
    node_bottom = max((box.y + box.height for box in boxes.values()), default=0)
    if node_right + options.margin + 20 > options.max_width or node_bottom + options.margin + footer_reserve + 20 > options.max_height:
        ordered = sorted(spec.nodes, key=lambda node: (boxes[node.id].y, boxes[node.id].x, node.id))
        step_x = options.node_width + options.node_gap
        columns = max(1, (options.max_width - options.margin * 2 - 40) // step_x)
        tallest = max((_node_height(node, options) for node in ordered), default=options.node_height)
        for index, node in enumerate(ordered):
            row, column = divmod(index, columns)
            boxes[node.id] = _Box(
                options.margin + 20 + column * step_x,
                options.margin + 108 + row * (tallest + options.node_gap),
                options.node_width, _node_height(node, options),
            )

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
                if container in spec.lanes and spec.layout in {"operational-lanes", "logical-tiers"}:
                    lane_index = sorted(spec.lanes, key=lambda item: (item.order, item.id)).index(container)
                    if direction == "TB":
                        container_boxes[identifier] = _Box(
                            options.margin, options.margin + 72 + lane_index * (options.node_height + 56),
                            options.node_width + 40, options.node_height + 50,
                        )
                    else:
                        container_boxes[identifier] = _Box(
                            options.margin + lane_index * (options.node_width + options.rank_gap), options.margin + 72,
                            options.node_width + 40, options.node_height + 50,
                        )
                else:
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


def _segment_intersects_box(first: tuple[float, float], second: tuple[float, float], box: _Box) -> bool:
    x1, y1 = first
    x2, y2 = second
    if x1 == x2:
        return box.x < x1 < box.x + box.width and max(min(y1, y2), box.y) < min(max(y1, y2), box.y + box.height)
    return box.y < y1 < box.y + box.height and max(min(x1, x2), box.x) < min(max(x1, x2), box.x + box.width)


def _points_path(points: list[tuple[float, float]]) -> str:
    parts = [f"M {points[0][0]:g} {points[0][1]:g}"]
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        parts.append(f"H {x2:g}" if y1 == y2 else f"V {y2:g}")
    return " ".join(parts)


def _path_segments(path: str) -> list[tuple[float, float, float, float]]:
    tokens = re.findall(r"[MLHV]|-?\d+(?:\.\d+)?", path)
    index = 0
    x = y = 0.0
    segments: list[tuple[float, float, float, float]] = []
    while index < len(tokens):
        command = tokens[index]
        index += 1
        if command in {"M", "L"}:
            next_x, next_y = float(tokens[index]), float(tokens[index + 1])
            index += 2
        elif command == "H":
            next_x, next_y = float(tokens[index]), y
            index += 1
        else:
            next_x, next_y = x, float(tokens[index])
            index += 1
        if command != "M":
            segments.append((x, y, next_x, next_y))
        x, y = next_x, next_y
    return segments


def _lane_edge_path(source: _Box, target: _Box, direction: str, track: int, obstacles: list[_Box]) -> str:
    offset = 10 + track * 8
    candidates: list[list[tuple[float, float]]] = []
    if direction == "TB":
        if source.y == target.y:
            sx, tx = source.x + source.width / 2, target.x + target.width / 2
            candidates.extend([
                [(sx, source.y), (sx, source.y - offset), (tx, source.y - offset), (tx, target.y)],
                [(sx, source.y + source.height), (sx, source.y + source.height + offset), (tx, source.y + source.height + offset), (tx, target.y + target.height)],
            ])
        else:
            downward = source.y < target.y
            sy = source.y + source.height if downward else source.y
            ty = target.y if downward else target.y + target.height
            sx, tx = source.x + source.width / 2, target.x + target.width / 2
            middle = (sy + ty) / 2 + (track - 2) * 5
            candidates.append([(sx, sy), (sx, middle), (tx, middle), (tx, ty)])
            for outer_x in (min(box.x for box in [source, target, *obstacles]) - offset,
                            max(box.x + box.width for box in [source, target, *obstacles]) + offset):
                source_gap = sy + (offset if downward else -offset)
                target_gap = ty - (offset if downward else -offset)
                candidates.append([(sx, sy), (sx, source_gap), (outer_x, source_gap), (outer_x, target_gap), (tx, target_gap), (tx, ty)])
    elif source.x == target.x:
        sy, ty = source.y + source.height / 2, target.y + target.height / 2
        candidates.extend([
            [(source.x, sy), (source.x - offset, sy), (source.x - offset, ty), (target.x, ty)],
            [(source.x + source.width, sy), (source.x + source.width + offset, sy), (source.x + source.width + offset, ty), (target.x + target.width, ty)],
        ])
    else:
        rightward = source.x < target.x
        sx = source.x + source.width if rightward else source.x
        tx = target.x if rightward else target.x + target.width
        sy, ty = source.y + source.height / 2, target.y + target.height / 2
        middle = (sx + tx) / 2 + (track - 2) * 5
        candidates.append([(sx, sy), (middle, sy), (middle, ty), (tx, ty)])
        for outer_y in (min(box.y for box in [source, target, *obstacles]) - offset,
                        max(box.y + box.height for box in [source, target, *obstacles]) + offset):
            source_gap = sx + (offset if rightward else -offset)
            target_gap = tx - (offset if rightward else -offset)
            candidates.append([(sx, sy), (source_gap, sy), (source_gap, outer_y), (target_gap, outer_y), (target_gap, ty), (tx, ty)])
    for points in candidates:
        if not any(_segment_intersects_box(first, second, box) for first, second in zip(points, points[1:]) for box in obstacles):
            return _points_path(points)
    return _points_path(candidates[-1])


def _semantic_edge_path(source: _Box, target: _Box, track: int) -> str:
    """Route through the compact grid gutters instead of across detail cards."""
    offset = 8 + track * 2
    source_center = source.x + source.width / 2
    target_center = target.x + target.width / 2
    if source.y == target.y:
        gutter_y = source.y - offset
        return _points_path([
            (source_center, source.y), (source_center, gutter_y),
            (target_center, gutter_y), (target_center, target.y),
        ])
    downward = source.y < target.y
    source_y = source.y + source.height if downward else source.y
    target_y = target.y if downward else target.y + target.height
    source_gutter = source_y + (offset if downward else -offset)
    target_gutter = target_y - (offset if downward else -offset)
    corridor_x = (
        min(source.x, target.x) - offset
        if downward
        else max(source.x + source.width, target.x + target.width) + offset
    )
    return _points_path([
        (source_center, source_y), (source_center, source_gutter),
        (corridor_x, source_gutter), (corridor_x, target_gutter),
        (target_center, target_gutter), (target_center, target_y),
    ])


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


def _edge_svg(
    edge: DiagramEdge, boxes: dict[str, _Box], direction: str, index: int,
    margin: int, lane_step: int, lane_aware: bool = False,
    occupied_labels: list[_Box] | None = None,
    layout: str = "flowchart",
    routed_paths: list[str] | None = None, nodes: dict[str, DiagramNode] | None = None,
) -> str:
    kind = edge.kind.lower().replace("_", "-")
    semantic_style = _edge_style(edge)
    classes = ["diagram-edge", f"kind-{_text(kind)}", f"edge-style-{semantic_style}"]
    dash = "stroke-dasharray:2 6;" if semantic_style == "dotted" else "stroke-dasharray:8 6;" if semantic_style == "dashed" else ""
    if edge.inferred:
        classes.append("is-inferred")
    if edge.critical or edge.style.lower() in {"critical", "cycle"}:
        classes.append("is-critical")
    visible_label = "" if (
        layout == "logical-tiers" and kind in _DEPENDENCY_EDGE_KINDS and edge.count == 1
        or layout == "operational-lanes" and nodes and not (
            nodes[edge.source].kind in {"actor", "external"} and nodes[edge.target].kind == "scenario"
            or nodes[edge.source].kind == "scenario" and nodes[edge.target].kind == "scenario"
        )
    ) else edge.label
    if layout == "operational-lanes" and visible_label:
        visible_label = _lines(visible_label, 18, 1)[0]
    label_text = _lines(visible_label + (f" ({edge.count})" if edge.count != 1 else ""), 28, 1)[0] if visible_label or edge.count != 1 else ""
    label_width = min(max(len(label_text) * 6, 30), 168) if label_text else 30
    track = index % 5
    obstacles = [box for identifier, box in boxes.items() if identifier not in {edge.source, edge.target}]
    path = _operational_edge_path(edge, boxes, nodes or {}, index) if layout == "operational-lanes" else _use_case_edge_path(edge, boxes, index) if layout == "use-case-catalog" else _semantic_edge_path(boxes[edge.source], boxes[edge.target], track) if layout in {"detail-cards", "operational-detail", "functional-detail", "logical-detail", "use-case-sequence"} else _lane_edge_path(boxes[edge.source], boxes[edge.target], direction, track, obstacles) if lane_aware else _edge_path(boxes[edge.source], boxes[edge.target], direction, index, margin, lane_step)
    marker = ' marker-end="url(#arrow)"' if kind not in {"decomposition", "allocation"} else ""
    evidence_title = _provenance_text(edge.evidence) if edge.evidence else f"{edge.source} to {edge.target}"
    detailed_label = edge.title or edge.label
    title = f"{detailed_label}: {evidence_title}" if detailed_label else evidence_title
    label = visible_label + (f" ({edge.count})" if edge.count != 1 else "")
    result = [
        f'<path id="edge-{index}" class="{" ".join(classes)}" data-edge-id="edge-{index}" data-source="{_text(edge.source)}" data-target="{_text(edge.target)}" data-kind="{_text(edge.kind)}" data-label-hidden="{str(not bool(label)).lower()}" d="{path}" style="{dash}"{marker}><title>{_text(title)}</title></path>'
    ]
    if label:
        source, target = boxes[edge.source], boxes[edge.target]
        if lane_aware and direction == "TB":
            x = (source.x + source.width / 2 + target.x + target.width / 2) / 2 - label_width / 2
            y = ((source.y + source.height if source.y < target.y else source.y) + (target.y if source.y < target.y else target.y + target.height)) / 2 - 13 + (track - 2) * 8
        elif lane_aware:
            x = ((source.x + source.width if source.x < target.x else source.x) + (target.x if source.x < target.x else target.x + target.width)) / 2 - label_width / 2 + (track - 2) * 8
            y = (source.y + source.height / 2 + target.y + target.height / 2) / 2 - 13
        elif direction == "TB":
            x = margin + index * lane_step + 4
            y = (source.y + target.y) / 2 - 6
        else:
            x = (source.x + source.width + target.x) / 2 - label_width / 2
            y = margin + 72 + index * 18 - 13
        if lane_aware or occupied_labels is not None:
            occupied = [*boxes.values(), *(occupied_labels or [])]
            candidates = [(x, y)]
            for distance in range(1, 14):
                candidates.extend([
                    (x + distance * 18, y), (x - distance * 18, y),
                    (x, y + distance * 14), (x, y - distance * 14),
                    (x + distance * 18, y + distance * 14),
                    (x + distance * 18, y - distance * 14),
                    (x - distance * 18, y + distance * 14),
                    (x - distance * 18, y - distance * 14),
                ])
            x, y = next((
                (candidate_x, candidate_y) for candidate_x, candidate_y in candidates
                if candidate_x >= margin and candidate_y >= 58
                and not any(_overlaps(_Box(int(candidate_x), int(candidate_y), label_width, 12), box) for box in occupied)
                and not any(
                    _segment_intersects_box((x1, y1), (x2, y2), _Box(int(candidate_x), int(candidate_y), label_width, 12))
                    for routed in (routed_paths or []) for x1, y1, x2, y2 in _path_segments(routed)
                )
            ), (x, y))
        if occupied_labels is not None:
            occupied_labels.append(_Box(int(x), int(y), label_width, 12))
        result.append(f'<text class="edge-label edge-label-contrast" data-edge-label="edge-{index}" data-x="{x:g}" data-y="{y:g}" data-width="{label_width:g}" data-height="12" x="{x + label_width / 2:g}" y="{y + 9:g}">{_text(label_text)}</text>')
    if edge.evidence:
        result.append(f'<g class="evidence-indicator" data-evidence="true"><title>{_text(title)}</title><circle cx="{boxes[edge.source].x + boxes[edge.source].width + 6}" cy="{boxes[edge.source].y + 6}" r="4"/></g>')
    return "".join(result)


def _stylesheet(theme: str) -> str:
    palette = _PALETTES[theme]
    text, muted, surface, edge = (palette[key] for key in ("text", "muted", "surface", "edge"))
    return """<style>
.diagram { --diagram-text: TEXT; --diagram-muted: MUTED; --diagram-surface: SURFACE; --diagram-edge: EDGE; font-family: system-ui, sans-serif; color: TEXT; }
.diagram-node .node-shape { fill: SURFACE; stroke: EDGE; stroke-width: 1.5; }
.diagram-node.is-inferred .node-shape { stroke-dasharray: 7 5; }
.container { fill: SURFACE; fill-opacity: .28; stroke: EDGE; stroke-width: 1; }
.container.system { stroke-width: 3; }
.diagram-edge { fill: none; stroke: EDGE; stroke-width: 1.5; }
.diagram-edge.is-critical { stroke: CRITICAL; stroke-width: 2; }
.node-label,.node-subtitle,.edge-label,.footer-text,.container-label,.diagram-title { fill: TEXT; dominant-baseline: middle; }
.node-label { text-anchor: middle; font-size: 13px; font-weight: 600; }
.node-subtitle { text-anchor: middle; font-size: 10px; fill: #64748b; }
.node-badge { font-size: 8px; fill: MUTED; }
.edge-label,.footer-text,.container-label { font-size: 10px; }
.edge-label-contrast { paint-order: stroke; stroke: SURFACE; stroke-width: 4px; stroke-linejoin: round; }
.diagram-title { font-size: 20px; font-weight: 700; }
.diagram-subtitle { font-size: 12px; fill: MUTED; }
.diagnostic-error { fill: #b91c1c; }.diagnostic-warning { fill: #a16207; }
.evidence-indicator { fill: #2563eb; }
</style>""".replace("TEXT", text).replace("MUTED", muted).replace("SURFACE", surface).replace("EDGE", edge).replace("CRITICAL", palette["critical"])


def _explicit_presentation(svg: str, theme: str) -> str:
    """Add literal SVG attributes for renderers with incomplete CSS support."""

    palette = _PALETTES[theme]

    def resolve(match: re.Match[str]) -> str:
        tag, attributes = match.group(1), match.group(2)
        classes = re.search(r'class="([^"]*)"', attributes)
        class_names = classes.group(1).split() if classes else []
        additions: list[str] = []
        if tag == "text" and "fill=" not in attributes:
            additions.append(f'fill="{palette["muted"] if "diagram-subtitle" in class_names or "node-subtitle" in class_names or "node-badge" in class_names else palette["text"]}"')
        elif tag == "path" and "data-edge-id=" in attributes:
            additions.extend((
                'fill="none"' if "fill=" not in attributes else "",
                f'stroke="{palette["critical"] if "is-critical" in class_names else palette["edge"]}"' if "stroke=" not in attributes else "",
                f'stroke-width="{2 if "is-critical" in class_names else 1.5}"' if "stroke-width=" not in attributes else "",
            ))
        elif "node-shape" in class_names:
            additions.extend((
                f'fill="{"none" if tag == "path" else palette["surface"]}"' if "fill=" not in attributes else "",
                f'stroke="{palette["edge"]}"' if "stroke=" not in attributes else "",
            ))
        elif tag == "path":
            additions.extend((
                'fill="none"' if "fill=" not in attributes else "",
                f'stroke="{palette["edge"]}"' if "stroke=" not in attributes else "",
            ))
        elif tag in {"rect", "polygon", "circle", "ellipse"} and "fill=" not in attributes:
            additions.append(f'fill="{palette["surface"]}"')
            if "stroke=" not in attributes and ("container" in class_names or "node-shape" in class_names):
                additions.append(f'stroke="{palette["edge"]}"')
        additions = [item for item in additions if item]
        return f'<{tag}{attributes}{(" " + " ".join(additions)) if additions else ""}>'

    return re.sub(r'<(rect|path|text|polygon|circle|ellipse)(\s[^>]*?)(/?)>', lambda match: resolve(match)[:-1] + match.group(3) + ">", svg)


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
            obstacles = [box for identifier, box in boxes.items() if identifier != callout.target]
            footer_y = y - 14
            outer_left = min(box.x for box in boxes.values()) - 16
            outer_right = max(box.x + box.width for box in boxes.values()) + 16
            candidates = [
                [(target.x, target.y + target.height / 2), (outer_left, target.y + target.height / 2), (outer_left, footer_y), (48, footer_y)],
                [(target.x + target.width, target.y + target.height / 2), (outer_right, target.y + target.height / 2), (outer_right, footer_y), (48, footer_y)],
            ]
            points = next((candidate for candidate in candidates if not any(
                _segment_intersects_box(first, second, obstacle)
                for first, second in zip(candidate, candidate[1:]) for obstacle in obstacles
            )), candidates[0])
            parts.append(f'<path class="callout-connector" data-callout-connector="{_text(callout.id)}" data-target-ref="{_text(callout.target)}" d="{_points_path(points)}"/>')
        y += 36
    for diagnostic in sorted(spec.warnings, key=lambda item: (item.severity, item.code, item.message)):
        parts.append(f'<g data-diagnostic-code="{_text(diagnostic.code)}" data-footer-item="diagnostic:{_text(diagnostic.code)}" data-severity="{_text(diagnostic.severity)}" data-x="48" data-y="{y - 14}" data-width="{item_width}" data-height="32"><text class="footer-text diagnostic-{_text(diagnostic.severity.lower())}" x="48" y="{y}">{_text(diagnostic.severity.upper())}: {_text(_lines(diagnostic.message, max(item_width // 7, 20), 2)[0])}</text></g>')
        y += 36
    if spec.provenance.source:
        parts.append(f'<g data-section="provenance" data-footer-item="provenance" data-x="48" data-y="{y - 14}" data-width="{item_width}" data-height="32"><title>{_text(str(spec.provenance.to_dict()))}</title><text class="footer-text" x="48" y="{y}">Source: {_text(spec.provenance.source)}</text></g>')
    return "".join(parts)


def _edge_key(edge: DiagramEdge) -> tuple[Any, ...]:
    evidence = tuple(repr(item.to_dict()) for item in edge.evidence)
    return edge.source, edge.target, edge.kind, edge.label, edge.count, edge.style, edge.critical, edge.inferred, edge.title, evidence


def _overlaps(first: _Box, second: _Box) -> bool:
    return (
        first.x < second.x + second.width and second.x < first.x + first.width
        and first.y < second.y + second.height and second.y < first.y + first.height
    )


def _render(spec: DiagramSpec, options: DiagramRenderOptions) -> tuple[str, int, int]:
    if options.theme not in {"light", "dark"}:
        raise ValueError(f"Unsupported diagram theme: {options.theme}")
    spec.validate()
    for edge in spec.edges:
        _edge_style(edge)
    boxes, containers, width, height = _layout(spec, options)
    namespace = f"diagram-{re.sub(r'[^a-zA-Z0-9_-]+', '-', spec.id).strip('-') or 'view'}-{hashlib.sha256(spec.id.encode()).hexdigest()[:8]}"
    title_id, desc_id, arrow_id = f"{namespace}-title", f"{namespace}-desc", f"{namespace}-arrow"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" class="diagram" data-diagram-id="{_text(spec.id)}" data-theme="{options.theme}" data-pan-zoom="true" width="100%" height="auto" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet" role="img" aria-labelledby="{title_id} {desc_id}">',
        f'<title id="{title_id}">{_text(spec.title)}</title>',
        f'<desc id="{desc_id}">{_text(spec.subtitle or "Architecture diagram")}</desc>',
        f'<rect data-canvas-background="true" width="{width}" height="{height}" fill="{"#ffffff" if options.theme == "light" else "#0f172a"}"/>',
        _stylesheet(options.theme),
        f'<defs><marker id="{arrow_id}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{_PALETTES[options.theme]["edge"]}" stroke="none"/></marker></defs>',
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
    occupied_labels: list[_Box] = []
    lane_aware = bool(spec.lanes) or spec.layout in {
        "functional-flow", "use-case-catalog", "detail-cards", "operational-detail",
        "functional-detail", "logical-detail", "use-case-sequence",
    }
    node_lookup = {node.id: node for node in spec.nodes}
    routed_paths = [
        _operational_edge_path(edge, boxes, node_lookup, index) if spec.layout == "operational-lanes" else _use_case_edge_path(edge, boxes, index) if spec.layout == "use-case-catalog" else _semantic_edge_path(
            boxes[edge.source], boxes[edge.target], index % 5,
        ) if spec.layout in {"detail-cards", "operational-detail", "functional-detail", "logical-detail", "use-case-sequence"} else _lane_edge_path(
            boxes[edge.source], boxes[edge.target], spec.direction.upper(), index % 5,
            [box for identifier, box in boxes.items() if identifier not in {edge.source, edge.target}],
        ) if lane_aware else _edge_path(
            boxes[edge.source], boxes[edge.target], spec.direction.upper(), index,
            options.margin, edge_lane_step,
        )
        for index, edge in enumerate(ordered_edges)
        if edge.source in boxes and edge.target in boxes
    ]
    for index, edge in enumerate(ordered_edges):
        if edge.source not in boxes or edge.target not in boxes:
            continue
        key = (edge.source, edge.target)
        parallel_seen[key] = parallel_seen.get(key, 0) + 1
        edge_svg = _edge_svg(
            edge, boxes, spec.direction.upper(), index, options.margin, edge_lane_step,
            lane_aware, occupied_labels, spec.layout,
            [path for path_index, path in enumerate(routed_paths) if path_index != index],
            node_lookup,
        )
        parts.append(edge_svg.replace('url(#arrow)', f'url(#{arrow_id})'))
    for node in sorted(spec.nodes, key=lambda item: item.id):
        parts.append(_node_svg(node, boxes[node.id], spec.id))
    footer_start = max([box.y + box.height for box in [*boxes.values(), *containers.values()]] + [160]) + 38
    parts.append(_footer(spec, footer_start, boxes, width))
    parts.append("</svg>")
    return _explicit_presentation("".join(parts), options.theme), width, height


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
        theme=selected.theme,
    )
