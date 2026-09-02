"""Typed, renderer-neutral presentation specifications for architecture diagrams."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import math
import re
from typing import Any, Callable, Iterable, TypeVar


JsonPrimitive = str | int | float | bool | None
T = TypeVar("T")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("Value is not JSON-safe: mapping key must be a string")
        return {key: _json_safe(item) for key, item in sorted(value.items())}
    if isinstance(value, set):
        return sorted((_json_safe(item) for item in value), key=lambda item: repr(item))
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Value is not JSON-safe: non-finite float")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"Value is not JSON-safe: {type(value).__name__}")


@dataclass
class DiagramNode:
    id: str
    label: str
    kind: str
    subtitle: str = ""
    group: str = ""
    lane: str = ""
    status: str = ""
    inferred: bool = False
    evidence: list[str] = field(default_factory=list)
    entity_ref: str = ""
    drilldown_ref: str = ""
    badges: list[str] = field(default_factory=list)
    metrics: dict[str, JsonPrimitive] = field(default_factory=dict)


@dataclass
class DiagramEdge:
    source: str
    target: str
    kind: str
    label: str = ""
    evidence: list[str] = field(default_factory=list)
    inferred: bool = False
    style: str = ""
    critical: bool = False


@dataclass
class DiagramGroup:
    id: str
    label: str
    kind: str
    parent: str = ""
    order: int = 0
    evidence: list[str] = field(default_factory=list)


@dataclass
class DiagramCallout:
    id: str
    label: str
    target: str = ""
    kind: str = "note"
    evidence: list[str] = field(default_factory=list)


@dataclass
class LegendEntry:
    id: str
    label: str
    kind: str
    description: str = ""


@dataclass
class DiagramProvenance:
    source: str = ""
    entity_refs: list[str] = field(default_factory=list)


@dataclass
class DiagramDrilldown:
    id: str
    source: str
    target: str = ""
    spec_ref: str = ""
    route: str = ""


@dataclass
class DiagramSpec:
    id: str
    title: str
    subtitle: str = ""
    direction: str = "LR"
    layout: str = "flowchart"
    nodes: list[DiagramNode] = field(default_factory=list)
    edges: list[DiagramEdge] = field(default_factory=list)
    groups: list[DiagramGroup] = field(default_factory=list)
    lanes: list[DiagramGroup] = field(default_factory=list)
    callouts: list[DiagramCallout] = field(default_factory=list)
    legend: list[LegendEntry] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    provenance: DiagramProvenance = field(default_factory=DiagramProvenance)
    drilldowns: list[DiagramDrilldown] = field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.provenance, dict):
            self.provenance = DiagramProvenance(
                source=str(self.provenance.get("source", "")),
                entity_refs=self.provenance.get("entity_refs", []),
            )
        if isinstance(self.drilldowns, dict):
            self.drilldowns = [
                DiagramDrilldown(id=str(identifier), source="", route=str(route))
                for identifier, route in sorted(self.drilldowns.items())
            ]

    def validate(self) -> None:
        def reject_html(value: Any) -> None:
            if isinstance(value, str) and re.search(r"<\s*/?\s*[A-Za-z][^>]*>", value):
                raise ValueError("HTML is not allowed in diagram specifications")
            if isinstance(value, dict):
                for item in value.values():
                    reject_html(item)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    reject_html(item)

        reject_html(asdict(self))
        for label, values in (("node", self.nodes), ("group", self.groups), ("lane", self.lanes), ("callout", self.callouts), ("legend", self.legend), ("drilldown", self.drilldowns)):
            ids = [value.id for value in values]
            duplicate = next((item for item in ids if ids.count(item) > 1), None)
            if duplicate:
                raise ValueError(f"Duplicate {label} ID: {duplicate}")
        node_ids = {node.id for node in self.nodes}
        group_ids = {group.id for group in self.groups}
        lane_ids = {lane.id for lane in self.lanes}
        overlap = group_ids & lane_ids
        if overlap:
            raise ValueError(f"Duplicate container ID: {sorted(overlap)[0]}")
        container_ids = group_ids | lane_ids
        for group in [*self.groups, *self.lanes]:
            if group.parent and group.parent not in container_ids:
                raise ValueError(f"Group has unknown parent: {group.parent}")
            seen = {group.id}
            parent = group.parent
            parents = {item.id: item.parent for item in [*self.groups, *self.lanes]}
            while parent:
                if parent in seen:
                    raise ValueError(f"Group parent cycle at: {parent}")
                seen.add(parent)
                parent = parents.get(parent, "")
        for node in self.nodes:
            if node.group and node.group not in group_ids:
                raise ValueError(f"Node has unknown group: {node.group}")
            if node.lane and node.lane not in lane_ids:
                raise ValueError(f"Node has unknown lane: {node.lane}")
        for callout in self.callouts:
            if callout.target and callout.target not in node_ids | container_ids:
                raise ValueError(f"Callout has unknown target: {callout.target}")
        drilldown_ids = {drilldown.id for drilldown in self.drilldowns}
        for node in self.nodes:
            if node.drilldown_ref and node.drilldown_ref not in drilldown_ids:
                raise ValueError(f"Node has unknown drilldown: {node.drilldown_ref}")
        for drilldown in self.drilldowns:
            if drilldown.source and drilldown.source not in node_ids | container_ids:
                raise ValueError(f"Drilldown has unknown source: {drilldown.source}")
            if drilldown.target and drilldown.target not in node_ids | container_ids:
                raise ValueError(f"Drilldown has unknown target: {drilldown.target}")
            if sum(bool(value) for value in (drilldown.target, drilldown.spec_ref, drilldown.route)) != 1:
                raise ValueError(f"Drilldown {drilldown.id} must set exactly one target, spec_ref, or route")
        for edge in self.edges:
            if edge.source not in node_ids:
                raise ValueError(f"Edge has unknown source: {edge.source}")
            if edge.target not in node_ids:
                raise ValueError(f"Edge has unknown target: {edge.target}")
        _json_safe(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        data = asdict(self)
        data["nodes"] = sorted(data["nodes"], key=lambda item: item["id"])
        data["edges"] = sorted(data["edges"], key=lambda item: (item["source"], item["target"], item["kind"], item["label"]))
        for key in ("groups", "lanes", "callouts", "legend", "drilldowns"):
            data[key] = sorted(data[key], key=lambda item: (item.get("order", 0), item["id"]))
        data["warnings"] = sorted(set(data["warnings"]))
        return _json_safe(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DiagramSpec":
        spec = cls(
            id=data["id"], title=data["title"], subtitle=data.get("subtitle", ""),
            direction=data.get("direction", "LR"), layout=data.get("layout", "flowchart"),
            nodes=[DiagramNode(**item) for item in data.get("nodes", [])],
            edges=[DiagramEdge(**item) for item in data.get("edges", [])],
            groups=[DiagramGroup(**item) for item in data.get("groups", [])],
            lanes=[DiagramGroup(**item) for item in data.get("lanes", [])],
            callouts=[DiagramCallout(**item) for item in data.get("callouts", [])],
            legend=[LegendEntry(**item) for item in data.get("legend", [])],
            warnings=list(data.get("warnings", [])), provenance=DiagramProvenance(**data.get("provenance", {})),
            drilldowns=[DiagramDrilldown(**item) for item in data.get("drilldowns", [])],
        )
        spec.validate()
        return spec


def bounded(items: Iterable[T], limit: int, *, key: Callable[[T], Any]) -> tuple[list[T], str]:
    """Return a stable bounded selection and an omission warning."""
    ordered = sorted(items, key=key)
    selected = ordered[:max(limit, 0)]
    omitted = len(ordered) - len(selected)
    noun = "item" if omitted == 1 else "items"
    return selected, f"{omitted} {noun} omitted (limit {limit})" if omitted else ""
