"""Typed, renderer-neutral presentation specifications for architecture diagrams."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from copy import deepcopy
from collections.abc import Mapping
from enum import Enum
import math
import re
from typing import Any, Callable, Iterable, TypeVar


JsonPrimitive = str | int | float | bool | None
T = TypeVar("T")
MAX_TEXT_LENGTH = 500
MAX_PRIMARY_NODES = 25
MAX_PRIMARY_EDGES = 40
MAX_DRILLDOWN_DEPTH = 12


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
    facets: dict[str, Any] = field(default_factory=dict)

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
        if not isinstance(self.facets, dict):
            raise ValueError("Invalid diagram type for facets: expected dict")
        _json_safe(self.facets)
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
            facets=data.get("facets", {}),
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


def bound_diagram_spec(
    spec: DiagramSpec, *, max_nodes: int = MAX_PRIMARY_NODES,
    max_edges: int = MAX_PRIMARY_EDGES, max_depth: int = MAX_DRILLDOWN_DEPTH,
) -> DiagramSpec:
    """Return a deterministic, recursively navigable bounded diagram tree."""

    if max_nodes < 2 or max_edges < 1 or max_depth < 1:
        raise ValueError("Diagram bounds require at least 2 nodes, 1 edge, and depth 1")

    def page_tree(template: DiagramSpec, nodes: list[DiagramNode], edges: list[DiagramEdge], depth: int) -> DiagramSpec:
        chunks = [nodes[index:index + max_nodes] for index in range(0, len(nodes), max_nodes)]
        pages: list[DiagramSpec] = []
        for index, chunk in enumerate(chunks, 1):
            ids = {node.id for node in chunk}
            drilldown_ids = {node.drilldown_ref for node in chunk if node.drilldown_ref}
            pages.append(DiagramSpec(
                f"{template.id}:page:{depth}:{index}", f"{template.title} - Page {index}", template.subtitle,
                template.direction, template.layout, chunk,
                [edge for edge in edges if edge.source in ids and edge.target in ids][:max_edges],
                deepcopy(template.groups), deepcopy(template.lanes), provenance=deepcopy(template.provenance),
                drilldowns=[item for item in template.drilldowns if item.id in drilldown_ids],
                facets={**deepcopy(template.facets), "page": index, "page_count": len(chunks)},
            ))
        while len(pages) > max_nodes:
            grouped: list[DiagramSpec] = []
            for group_index in range(0, len(pages), max_nodes):
                children = pages[group_index:group_index + max_nodes]
                directory_id = f"{template.id}:pages:{depth}:{group_index // max_nodes + 1}"
                directory_nodes = [
                    DiagramNode(
                        f"{directory_id}:item:{index}", child.title, "summary", status="page",
                        drilldown_ref=f"drilldown:{directory_id}:item:{index}",
                    )
                    for index, child in enumerate(children, 1)
                ]
                grouped.append(DiagramSpec(
                    directory_id, f"More {template.title}", nodes=directory_nodes,
                    drilldowns=[DiagramDrilldown(node.drilldown_ref, node.id, spec=child) for node, child in zip(directory_nodes, children)],
                    provenance=deepcopy(template.provenance), facets={"page_directory": True},
                ))
            pages = grouped
            depth += 1
            if depth >= max_depth:
                raise ValueError(f"Diagram drilldown depth exceeds safe limit {max_depth}: {template.id}")
        if len(pages) == 1:
            return pages[0]
        directory_id = f"{template.id}:pages:{depth}"
        directory_nodes = [
            DiagramNode(
                f"{directory_id}:item:{index}", page.title, "summary", status="page",
                drilldown_ref=f"drilldown:{directory_id}:item:{index}",
            )
            for index, page in enumerate(pages, 1)
        ]
        return DiagramSpec(
            directory_id, f"More {template.title}", nodes=directory_nodes,
            drilldowns=[DiagramDrilldown(node.drilldown_ref, node.id, spec=page) for node, page in zip(directory_nodes, pages)],
            provenance=deepcopy(template.provenance), facets={"page_directory": True},
        )

    def visit(current: DiagramSpec, depth: int) -> DiagramSpec:
        def prune_empty_containers(value: DiagramSpec) -> DiagramSpec:
            if value.layout != "logical-detail":
                return value
            containers = [*value.groups, *value.lanes]
            occupied = {node.group for node in value.nodes if node.group} | {node.lane for node in value.nodes if node.lane}
            parents = {item.parent for item in containers if item.id in occupied and item.parent}
            while not parents <= occupied:
                occupied.update(parents)
                parents = {item.parent for item in containers if item.id in occupied and item.parent}
            value.groups = [item for item in value.groups if item.id in occupied]
            value.lanes = [item for item in value.lanes if item.id in occupied]
            return value

        result = deepcopy(current)
        result.drilldowns = [
            DiagramDrilldown(item.id, item.source, item.target, item.spec_ref, item.route, visit(item.spec, depth + 1) if item.spec else None)
            for item in result.drilldowns
        ]
        if len(result.nodes) <= max_nodes and len(result.edges) <= max_edges:
            return prune_empty_containers(result)

        ordered = list(result.nodes)
        keep_count = max_nodes - 1
        selected = ordered[:keep_count]
        omitted = ordered[keep_count:]
        if not omitted:
            selected_ids = {node.id for node in selected}
            result.edges = result.edges[:max_edges]
            result.nodes = selected
            result.drilldowns = [item for item in result.drilldowns if item.source in selected_ids]
            return prune_empty_containers(result)
        if depth >= max_depth:
            raise ValueError(f"Diagram drilldown depth exceeds safe limit {max_depth}: {current.id}")

        summary_id = f"{result.id}:more:{depth}"
        drilldown_id = f"drilldown:{summary_id}"
        selected_ids = {node.id for node in selected}
        omitted_ids = {node.id for node in omitted}
        original_edges = result.edges
        retained_edges = [edge for edge in original_edges if edge.source in selected_ids and edge.target in selected_ids][:max_edges]
        child_edges = [edge for edge in result.edges if edge.source in omitted_ids and edge.target in omitted_ids]
        child_drilldown_ids = {node.drilldown_ref for node in omitted if node.drilldown_ref}
        child_template = DiagramSpec(
            f"{result.id}:continuation", f"More {result.title}", result.subtitle,
            result.direction, result.layout, groups=deepcopy(result.groups), lanes=deepcopy(result.lanes),
            provenance=deepcopy(result.provenance),
            drilldowns=[item for item in result.drilldowns if item.id in child_drilldown_ids],
            facets={**deepcopy(result.facets), "continuation_of": result.id},
        )
        child = page_tree(child_template, omitted, child_edges, depth + 1)
        selected.append(DiagramNode(
            summary_id, f"More {result.title} ({len(omitted)})", "summary",
            status="omitted", drilldown_ref=drilldown_id, badges=[f"items:{len(omitted)}"],
        ))
        result.nodes = selected
        result.edges = retained_edges
        used = {node.drilldown_ref for node in selected if node.drilldown_ref}
        result.drilldowns = [item for item in result.drilldowns if item.id in used]
        result.drilldowns.append(DiagramDrilldown(drilldown_id, summary_id, spec=child))
        result.facets = {
            **result.facets,
            "bounded": True,
            "omitted_edge_records": [asdict(edge) for edge in original_edges if edge not in retained_edges and edge not in child_edges],
        }
        return prune_empty_containers(result)

    bounded_spec = visit(spec, 0)
    bounded_spec.validate()
    return bounded_spec
