"""Typed, renderer-neutral presentation specifications for architecture diagrams."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from collections.abc import Mapping
from enum import Enum
import math
import re
from typing import Any, Callable, Iterable, TypeVar


JsonPrimitive = str | int | float | bool | None
T = TypeVar("T")
MAX_TEXT_LENGTH = 500


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str
    view: str = ""
    source: str = ""
    context: dict[str, JsonPrimitive] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _provenance_list(values: Iterable["DiagramProvenance | str | dict[str, Any]"] | Any) -> list["DiagramProvenance"] | Any:
    if not isinstance(values, list):
        return values
    result: list[DiagramProvenance] = []
    for value in values:
        if isinstance(value, DiagramProvenance):
            result.append(value)
        elif isinstance(value, dict):
            try:
                result.append(DiagramProvenance(**value))
            except TypeError:
                result.append(value)
        elif isinstance(value, str):
            result.append(DiagramProvenance(source=str(value)))
        else:
            result.append(value)
    return result


def _diagnostics(values: Iterable[Diagnostic | str]) -> list[Diagnostic]:
    return [value if isinstance(value, Diagnostic) else Diagnostic("warning", "LEGACY", str(value)) for value in values]


def _validate_text(value: str) -> None:
    unsafe = re.search(r"<\s*script\b|\bon\w+\s*=|javascript\s*:", value, re.IGNORECASE)
    controls = any(ord(char) < 32 and char not in "\n\r\t" for char in value)
    if unsafe or controls or len(value) > MAX_TEXT_LENGTH:
        raise ValueError("Invalid presentation text")


def validate_presentation_text(value: str) -> str:
    """Validate unescaped presentation data and retain its plain-text content."""
    _validate_text(value)
    return value


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


class _FrozenJsonMapping(tuple):
    """Marker tuple that preserves mapping semantics while remaining immutable."""


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("Provenance context keys must be strings")
        return _FrozenJsonMapping((key, _freeze_json(item)) for key, item in sorted(value.items()))
    if isinstance(value, set):
        frozen = [_freeze_json(item) for item in value]
        return tuple(sorted(frozen, key=lambda item: repr(_thaw_json(item))))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Provenance context must contain finite JSON values")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"Provenance context is not JSON-safe: {type(value).__name__}")


def _thaw_json(value: Any) -> Any:
    if isinstance(value, _FrozenJsonMapping):
        return {key: _thaw_json(item) for key, item in value}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


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
    evidence: list[DiagramProvenance] = field(default_factory=list)
    entity_ref: str = ""
    drilldown_ref: str = ""
    badges: list[str] = field(default_factory=list)
    metrics: dict[str, JsonPrimitive] = field(default_factory=dict)
    safe_text: bool = True

    def __post_init__(self) -> None:
        self.evidence = _provenance_list(self.evidence)


@dataclass
class DiagramEdge:
    source: str
    target: str
    kind: str
    label: str = ""
    evidence: list[DiagramProvenance] = field(default_factory=list)
    inferred: bool = False
    style: str = ""
    critical: bool = False
    count: int = 1
    title: str = ""

    def __post_init__(self) -> None:
        self.evidence = _provenance_list(self.evidence)


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


@dataclass(frozen=True)
class DiagramProvenance:
    source: str = ""
    entity_refs: tuple[str, ...] = field(default_factory=tuple)
    source_files: tuple[str, ...] = field(default_factory=tuple)
    context: tuple[tuple[str, Any], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if isinstance(self.entity_refs, (list, tuple)):
            object.__setattr__(self, "entity_refs", tuple(self.entity_refs))
        if isinstance(self.source_files, (list, tuple)):
            object.__setattr__(self, "source_files", tuple(self.source_files))
        context = self.context
        if isinstance(context, tuple) and not isinstance(context, _FrozenJsonMapping):
            if all(isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str) for item in context):
                context = dict(context)
        frozen = _freeze_json(context)
        if not isinstance(frozen, _FrozenJsonMapping):
            raise ValueError("Provenance context must be a mapping")
        object.__setattr__(self, "context", frozen)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "source": self.source,
            "entity_refs": list(self.entity_refs),
        }
        if self.source_files:
            result["source_files"] = list(self.source_files)
        if self.context:
            result["context"] = _thaw_json(self.context)
        return result


@dataclass
class DiagramDrilldown:
    id: str
    source: str
    target: str = ""
    spec_ref: str = ""
    route: str = ""
    spec: DiagramSpec | None = None


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
    warnings: list[Diagnostic] = field(default_factory=list)
    provenance: DiagramProvenance = field(default_factory=DiagramProvenance)
    drilldowns: list[DiagramDrilldown] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.warnings = _diagnostics(self.warnings)
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
        def require_list(name: str, value: Any, item_type: type) -> None:
            if not isinstance(value, list) or any(not isinstance(item, item_type) for item in value):
                raise ValueError(f"Invalid diagram type for {name}: expected list[{item_type.__name__}]")

        require_list("nodes", self.nodes, DiagramNode)
        require_list("edges", self.edges, DiagramEdge)
        require_list("groups", self.groups, DiagramGroup)
        require_list("lanes", self.lanes, DiagramGroup)
        require_list("callouts", self.callouts, DiagramCallout)
        require_list("legend", self.legend, LegendEntry)
        require_list("warnings", self.warnings, Diagnostic)
        require_list("drilldowns", self.drilldowns, DiagramDrilldown)
        if not isinstance(self.provenance, DiagramProvenance):
            raise ValueError("Invalid diagram type for provenance: expected DiagramProvenance")
        provenances = [self.provenance]
        for node in self.nodes:
            require_list(f"node {node.id} evidence", node.evidence, DiagramProvenance)
            require_list(f"node {node.id} badges", node.badges, str)
            if not isinstance(node.metrics, dict) or any(
                not isinstance(key, str) or not isinstance(value, (str, int, float, bool, type(None)))
                or isinstance(value, float) and not math.isfinite(value)
                for key, value in node.metrics.items()
            ):
                raise ValueError(f"Invalid diagram type for node {node.id} metrics: expected JSON primitives")
            provenances.extend(node.evidence)
        for edge in self.edges:
            require_list(f"edge {edge.source} evidence", edge.evidence, DiagramProvenance)
            provenances.extend(edge.evidence)
        for provenance in provenances:
            if not isinstance(provenance.source, str):
                raise ValueError("Invalid diagram type for provenance source: expected str")
            if not isinstance(provenance.entity_refs, tuple) or any(not isinstance(item, str) for item in provenance.entity_refs):
                raise ValueError("Invalid diagram type for provenance entity_refs: expected tuple[str]")
            if not isinstance(provenance.source_files, tuple) or any(not isinstance(item, str) for item in provenance.source_files):
                raise ValueError("Invalid diagram type for provenance source_files: expected tuple[str]")
            if not isinstance(provenance.context, tuple):
                raise ValueError("Invalid diagram type for provenance context: expected immutable JSON")

        def validate_text(value: Any) -> None:
            if isinstance(value, str):
                _validate_text(value)
            if isinstance(value, dict):
                for item in value.values():
                    validate_text(item)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    validate_text(item)

        validate_text(asdict(self))
        all_ids: list[str] = []
        for label, values in (("node", self.nodes), ("group", self.groups), ("lane", self.lanes), ("callout", self.callouts), ("legend", self.legend), ("drilldown", self.drilldowns)):
            ids = [value.id for value in values]
            duplicate = next((item for item in ids if ids.count(item) > 1), None)
            if duplicate:
                raise ValueError(f"Duplicate {label} ID: {duplicate}")
            all_ids.extend(ids)
        duplicate = next((identifier for identifier in all_ids if all_ids.count(identifier) > 1), None)
        if duplicate:
            raise ValueError(f"Duplicate document ID: {duplicate}")
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
            if sum(bool(value) for value in (drilldown.target, drilldown.spec_ref, drilldown.route, drilldown.spec)) != 1:
                raise ValueError(f"Drilldown {drilldown.id} must set exactly one target, spec_ref, route, or spec")
            if drilldown.spec:
                drilldown.spec.validate()
        for edge in self.edges:
            if edge.source not in node_ids:
                raise ValueError(f"Edge has unknown source: {edge.source}")
            if edge.target not in node_ids:
                raise ValueError(f"Edge has unknown target: {edge.target}")
        _json_safe(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        data = asdict(self)
        data["provenance"] = self.provenance.to_dict()
        data["nodes"] = sorted(data["nodes"], key=lambda item: item["id"])
        data["edges"] = sorted(data["edges"], key=lambda item: (item["source"], item["target"], item["kind"], item["label"]))
        for index, node in enumerate(sorted(self.nodes, key=lambda item: item.id)):
            data["nodes"][index]["evidence"] = [item.to_dict() for item in node.evidence]
        for index, edge in enumerate(sorted(self.edges, key=lambda item: (item.source, item.target, item.kind, item.label))):
            data["edges"][index]["evidence"] = [item.to_dict() for item in edge.evidence]
        data["drilldowns"] = []
        for drilldown in sorted(self.drilldowns, key=lambda item: item.id):
            item = {
                "id": drilldown.id,
                "source": drilldown.source,
                "target": drilldown.target,
                "spec_ref": drilldown.spec_ref,
                "route": drilldown.route,
            }
            if drilldown.spec:
                item["spec"] = drilldown.spec.to_dict()
            data["drilldowns"].append(item)
        for key in ("groups", "lanes", "callouts", "legend"):
            data[key] = sorted(data[key], key=lambda item: (item.get("order", 0), item["id"]))
        data["warnings"] = sorted(data["warnings"], key=lambda item: (item["severity"], item["code"], item["message"]))
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
            warnings=[Diagnostic(**item) if isinstance(item, dict) else item for item in data.get("warnings", [])], provenance=DiagramProvenance(**data.get("provenance", {})),
            drilldowns=[DiagramDrilldown(
                **{key: value for key, value in item.items() if key != "spec"},
                spec=cls.from_dict(item["spec"]) if item.get("spec") else None,
            ) for item in data.get("drilldowns", [])],
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
