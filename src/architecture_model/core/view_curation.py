"""Safe loader for optional, presentation-only architecture viewer curation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, TypeVar

import yaml

from architecture_model.core.view_context import ArchitectureViewContext
from architecture_model.core.types import RelationType


T = TypeVar("T")
VIEW_NAMES = ("conops", "functional", "logical", "use_cases")
CANONICAL_LINK_KINDS = {item.value for item in RelationType}
INFERRED_FLOW_KINDS = {"exchange", "operational-flow", "data-flow"}
VIEW_KEYS = {
    "featured", "hide", "order", "labels", "externals", "scenarios", "groups",
    "flows", "tiers", "aggregate_components",
}


@dataclass
class Selector:
    qualified_id: str = ""
    local_id: str = ""
    system: str = ""
    name: str = ""
    source_file: str = ""
    tag: str = ""
    resolved_id: str = ""

    def resolve(self, context: ArchitectureViewContext) -> str:
        matches = context.select(
            qualified_id=self.qualified_id, local_id=self.local_id, system=self.system,
            name=self.name, source_file=self.source_file, tag=self.tag,
        )
        self.resolved_id = matches[0].key if len(matches) == 1 else ""
        return self.resolved_id


@dataclass
class EvidenceRecord:
    source: str
    claim: str


@dataclass
class CuratedExternal:
    id: str
    name: str
    inferred: bool
    evidence: list[EvidenceRecord]
    kind: str = "external"


@dataclass
class CuratedGroup:
    id: str
    label: str
    kind: str = "group"
    parent: str = ""
    order: int = 0


@dataclass
class CuratedFlow:
    source: str
    target: str
    kind: str = "flow"
    label: str = ""
    inferred: bool = False
    evidence: list[EvidenceRecord] = field(default_factory=list)


@dataclass
class ViewCuration:
    featured: list[Selector] = field(default_factory=list)
    hide: list[Selector] = field(default_factory=list)
    order: list[str] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)
    externals: list[CuratedExternal] = field(default_factory=list)
    scenarios: list[CuratedGroup] = field(default_factory=list)
    groups: list[CuratedGroup] = field(default_factory=list)
    flows: list[CuratedFlow] = field(default_factory=list)
    tiers: list[CuratedGroup] = field(default_factory=list)
    aggregate_components: list[Selector] = field(default_factory=list)


@dataclass
class CuratedViews:
    conops: ViewCuration = field(default_factory=ViewCuration)
    functional: ViewCuration = field(default_factory=ViewCuration)
    logical: ViewCuration = field(default_factory=ViewCuration)
    use_cases: ViewCuration = field(default_factory=ViewCuration)


@dataclass
class ViewerCuration:
    version: int = 1
    views: CuratedViews = field(default_factory=CuratedViews)
    warnings: list[str] = field(default_factory=list)


def merge_ordered(base: Iterable[T], overlay: Iterable[T]) -> list[T]:
    result: list[T] = []
    for item in [*base, *overlay]:
        if item not in result:
            result.append(item)
    return result


def _safe_file(root: Path, value: str, *, must_exist: bool = True) -> Path | None:
    candidate = (root / str(value).replace("\\", "/")).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate if not must_exist or candidate.is_file() else None


def _selector(raw: Any) -> Selector | None:
    if isinstance(raw, str):
        return Selector(qualified_id=raw)
    if not isinstance(raw, dict):
        return None
    allowed = {"qualified_id", "local_id", "system", "name", "source_file", "tag"}
    return Selector(**{key: str(value) for key, value in raw.items() if key in allowed and value is not None})


def _collection(raw: dict[str, Any], key: str, warnings: list[str], expected: type) -> Any:
    value = raw.get(key, expected())
    if not isinstance(value, expected):
        warnings.append(f"Invalid {key}; expected {expected.__name__}")
        return expected()
    return value


def _evidence(raw: Any, root: Path, warnings: list[str], owner: str) -> list[EvidenceRecord]:
    if not isinstance(raw, list) or not raw:
        warnings.append(f"Invalid {owner} evidence; nonempty evidence records are required")
        return []
    result: list[EvidenceRecord] = []
    for value in raw:
        if not isinstance(value, dict) or not value.get("source") or not value.get("claim"):
            warnings.append(f"Invalid {owner} evidence record; unsafe evidence format, source and claim are required")
            return []
        source, claim = str(value["source"]), str(value["claim"]).strip()
        if not claim or _safe_file(root, source) is None:
            warnings.append(f"Invalid {owner} evidence record: unsafe or missing source {source}")
            return []
        result.append(EvidenceRecord(source, claim))
    return result


def _groups(raw: Any, warnings: list[str], label: str, identifiers: set[str]) -> list[CuratedGroup]:
    result: list[CuratedGroup] = []
    for value in raw if isinstance(raw, list) else []:
        if not isinstance(value, dict) or not value.get("id") or not value.get("label"):
            warnings.append(f"Invalid {label} entry ignored")
            continue
        identifier = str(value["id"])
        if identifier in identifiers:
            warnings.append(f"Duplicate presentation ID ignored: {identifier}")
            continue
        try:
            order = int(value.get("order", 0))
        except (TypeError, ValueError):
            warnings.append(f"Invalid {label} order ignored: {identifier}")
            continue
        identifiers.add(identifier)
        result.append(CuratedGroup(identifier, str(value["label"]), str(value.get("kind", label)), str(value.get("parent", "")), order))
    return sorted(result, key=lambda item: (item.order, item.id))


def _parse_view(raw: Any, root: Path, context: ArchitectureViewContext, warnings: list[str]) -> ViewCuration:
    if not isinstance(raw, dict):
        warnings.append("Invalid view curation; expected dict")
        return ViewCuration()
    result = ViewCuration()
    view_name = str(raw.pop("__view_name", "view"))
    warnings.extend(f"Unknown {view_name} key ignored: {key}" for key in sorted(set(raw) - VIEW_KEYS))
    identifiers = {entity.key for entity in context.entities()}
    for field_name in ("featured", "hide", "aggregate_components"):
        seen: set[str] = set()
        for value in _collection(raw, field_name, warnings, list):
            selector = _selector(value)
            if not selector:
                warnings.append(f"Invalid selector in {field_name}")
                continue
            matches = context.select(
                qualified_id=selector.qualified_id, local_id=selector.local_id, system=selector.system,
                name=selector.name, source_file=selector.source_file, tag=selector.tag,
            )
            if len(matches) != 1:
                description = selector.qualified_id or selector.local_id or selector.name or selector.source_file or selector.tag
                warnings.append(f"Ambiguous selector ignored: {description}" if matches == [] and (selector.name or selector.local_id) else f"Unresolved selector ignored: {description}")
                continue
            selector.resolved_id = matches[0].key
            if selector.resolved_id in seen:
                warnings.append(f"Duplicate selector ignored: {selector.resolved_id}")
                continue
            seen.add(selector.resolved_id)
            getattr(result, field_name).append(selector)
    result.order = [str(value) for value in _collection(raw, "order", warnings, list)]
    result.labels = {str(key): str(value) for key, value in _collection(raw, "labels", warnings, dict).items()}
    result.groups = _groups(_collection(raw, "groups", warnings, list), warnings, "group", identifiers)
    result.scenarios = _groups(_collection(raw, "scenarios", warnings, list), warnings, "scenario", identifiers)
    result.tiers = _groups(_collection(raw, "tiers", warnings, list), warnings, "tier", identifiers)
    for value in _collection(raw, "externals", warnings, list):
        if not isinstance(value, dict):
            warnings.append("Invalid external ignored")
            continue
        identifier, name = str(value.get("id", "")), str(value.get("name", ""))
        evidence = _evidence(value.get("evidence"), root, warnings, f"external {identifier or name}")
        if not identifier or not name or value.get("inferred") is not True or not evidence:
            warnings.append(f"Invalid inferred external ignored: {identifier or name or '<unknown>'}")
            continue
        if identifier in identifiers:
            warnings.append(f"Duplicate presentation ID ignored: {identifier}")
            continue
        identifiers.add(identifier)
        result.externals.append(CuratedExternal(identifier, name, True, evidence, str(value.get("kind", "external"))))
    presentation_ids = {item.id for item in result.groups + result.scenarios + result.tiers + result.externals}
    flow_keys: set[tuple[str, str, str, str]] = set()
    for value in _collection(raw, "flows", warnings, list):
        if not isinstance(value, dict) or not value.get("source") or not value.get("target"):
            warnings.append("Invalid curated flow ignored")
            continue
        source, target, kind = str(value["source"]), str(value["target"]), str(value.get("kind", "flow"))
        inferred = value.get("inferred") is True
        evidence = _evidence(value.get("evidence"), root, warnings, f"flow {source} -> {target}") if inferred else []
        if kind in CANONICAL_LINK_KINDS:
            warnings.append(f"Curated flow cannot create canonical relationship: {kind}")
            continue
        if inferred and kind not in INFERRED_FLOW_KINDS:
            warnings.append(f"Unsupported inferred flow kind ignored: {kind}")
            continue
        if inferred and not evidence:
            warnings.append(f"Inferred curated flow requires evidence: {source} -> {target}")
            continue
        if not inferred and not ({source, target} <= presentation_ids):
            warnings.append(f"Curated flow must link presentation groups: {source} -> {target}")
            continue
        flow_label = str(value.get("label", ""))
        flow_key = (source, target, kind, flow_label)
        if flow_key in flow_keys:
            warnings.append(f"Duplicate curated flow ignored: {source} -> {target}")
            continue
        flow_keys.add(flow_key)
        result.flows.append(CuratedFlow(source, target, kind, flow_label, inferred, evidence))
    result.externals.sort(key=lambda item: item.id)
    result.flows.sort(key=lambda item: (item.source, item.target, item.kind, item.label))
    return result


def validate_view_curation(view: ViewCuration, context: ArchitectureViewContext) -> list[str]:
    identifiers = {entity.key for entity in context.entities()}
    identifiers.update(item.id for item in view.groups + view.scenarios + view.tiers + view.externals)
    warnings: list[str] = []
    for flow in view.flows:
        if flow.source not in identifiers:
            warnings.append(f"Curated flow has unknown source: {flow.source}")
        if flow.target not in identifiers:
            warnings.append(f"Curated flow has unknown target: {flow.target}")
    return sorted(set(warnings))


def load_viewer_curation(
    repo_path: str | Path, context: ArchitectureViewContext, path: str | Path | None = None,
) -> ViewerCuration:
    root = Path(repo_path).resolve()
    candidate = Path(path) if path is not None else root / ".architecture/viewer-curation.yaml"
    candidate = candidate if candidate.is_absolute() else root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return ViewerCuration(warnings=[f"Curation path is outside repository: {candidate}"])
    if not resolved.exists():
        return ViewerCuration()
    warnings: list[str] = []
    try:
        raw = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        return ViewerCuration(warnings=[f"Invalid curation file: {exc}"])
    if not isinstance(raw, dict) or raw.get("version") != 1 or not isinstance(raw.get("views", {}), dict):
        return ViewerCuration(warnings=["Invalid viewer curation schema; expected version 1 and views mapping"])
    warnings.extend(f"Unknown top-level key ignored: {key}" for key in sorted(set(raw) - {"version", "views"}))
    unknown = sorted(set(raw["views"]) - set(VIEW_NAMES))
    warnings.extend(f"Unknown curation view ignored: {name}" for name in unknown)
    parsed = {}
    for name in VIEW_NAMES:
        value = raw["views"].get(name, {})
        if isinstance(value, dict):
            value = {**value, "__view_name": name}
        parsed[name] = _parse_view(value, root, context, warnings)
    return ViewerCuration(1, CuratedViews(**parsed), sorted(set(warnings)))
