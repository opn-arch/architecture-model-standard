"""Safe loader for optional, presentation-only architecture viewer curation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, TypeVar

import yaml

from architecture_model.core.view_context import ArchitectureViewContext
from architecture_model.core.types import RelationType
from architecture_model.core.diagram_spec import Diagnostic, validate_presentation_text


T = TypeVar("T")
VIEW_NAMES = ("conops", "functional", "logical", "use_cases")
CANONICAL_LINK_KINDS = {item.value for item in RelationType}
INFERRED_FLOW_KINDS = {"exchange", "operational-flow", "data-flow"}
VIEW_KEYS = {
    "featured", "hide", "order", "labels", "externals", "scenarios", "groups",
    "flows", "tiers", "aggregate_components",
    "preferred_capability_root", "mission_root", "drilldowns",
}
SELECTOR_KEYS = {"qualified_id", "local_id", "system", "name", "source_file", "tag"}
GROUP_KEYS = {"id", "label", "kind", "parent", "order", "description"}
EXTERNAL_KEYS = {"id", "name", "inferred", "evidence", "kind", "description"}
FLOW_KEYS = {"source", "target", "kind", "label", "description", "inferred", "evidence"}
EVIDENCE_KEYS = {"source", "claim"}


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
    preferred_capability_root: Selector | None = None
    mission_root: Selector | None = None
    drilldowns: dict[str, Selector] = field(default_factory=dict)
    safe_text: bool = True


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
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def warnings(self) -> list[Diagnostic]:
        return self.diagnostics


def _diag(values: list[Diagnostic], code: str, message: str, *, view: str = "", source: str = "") -> None:
    diagnostic = Diagnostic("warning", code, message, view=view, source=source)
    if diagnostic not in values:
        values.append(diagnostic)


class _InvalidView(ValueError):
    pass


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


def _check_keys(raw: dict[str, Any], allowed: set[str], diagnostics: list[Diagnostic], view: str, record: str) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        for key in unknown:
            _diag(diagnostics, "CURATION_KEY_UNSUPPORTED", f"Unknown key in {record}: {key}", view=view)
        raise _InvalidView(record)


def _text(value: Any, diagnostics: list[Diagnostic], view: str, field_name: str) -> str:
    try:
        return validate_presentation_text(str(value))
    except ValueError as exc:
        _diag(diagnostics, "CURATION_TEXT_UNSAFE", f"Invalid {field_name}: {exc}", view=view)
        raise _InvalidView(field_name) from exc


def _selector(raw: Any, diagnostics: list[Diagnostic] | None = None, view: str = "") -> Selector | None:
    if isinstance(raw, str):
        return Selector(qualified_id=raw)
    if not isinstance(raw, dict):
        return None
    if diagnostics is not None:
        _check_keys(raw, SELECTOR_KEYS, diagnostics, view, "selector")
    return Selector(**{key: str(value) for key, value in raw.items() if key in SELECTOR_KEYS and value is not None})


def _collection(raw: dict[str, Any], key: str, diagnostics: list[Diagnostic], expected: type, view: str) -> Any:
    value = raw.get(key, expected())
    if not isinstance(value, expected):
        _diag(diagnostics, "CURATION_VALUE_INVALID", f"Invalid {key}; expected {expected.__name__}", view=view)
        raise _InvalidView(key)
    return value


def _evidence(raw: Any, root: Path, diagnostics: list[Diagnostic], owner: str, view: str) -> list[EvidenceRecord]:
    if not isinstance(raw, list) or not raw:
        _diag(diagnostics, "CURATION_EVIDENCE_INVALID", f"Invalid {owner} evidence; nonempty evidence records are required", view=view)
        raise _InvalidView(owner)
    result: list[EvidenceRecord] = []
    for value in raw:
        if not isinstance(value, dict) or not value.get("source") or not value.get("claim"):
            _diag(diagnostics, "CURATION_EVIDENCE_INVALID", f"Invalid {owner} evidence record; unsafe evidence format, source and claim are required", view=view)
            raise _InvalidView(owner)
        _check_keys(value, EVIDENCE_KEYS, diagnostics, view, "evidence")
        source, claim = str(value["source"]), _text(value["claim"], diagnostics, view, "evidence claim").strip()
        if not claim or _safe_file(root, source) is None:
            _diag(diagnostics, "CURATION_EVIDENCE_INVALID", f"Invalid {owner} evidence record: unsafe or missing source {source}", view=view)
            raise _InvalidView(owner)
        result.append(EvidenceRecord(source, claim))
    return result


def _groups(raw: Any, diagnostics: list[Diagnostic], label: str, identifiers: set[str], view: str) -> list[CuratedGroup]:
    result: list[CuratedGroup] = []
    for value in raw if isinstance(raw, list) else []:
        if not isinstance(value, dict) or not value.get("id") or not value.get("label"):
            _diag(diagnostics, "CURATION_VALUE_INVALID", f"Invalid {label} entry", view=view)
            raise _InvalidView(label)
        _check_keys(value, GROUP_KEYS, diagnostics, view, label)
        identifier = str(value["id"])
        if identifier in identifiers:
            _diag(diagnostics, "CURATION_ID_DUPLICATE", f"Duplicate presentation ID ignored: {identifier}", view=view)
            continue
        try:
            order = int(value.get("order", 0))
        except (TypeError, ValueError):
            _diag(diagnostics, "CURATION_VALUE_INVALID", f"Invalid {label} order: {identifier}", view=view)
            raise _InvalidView(label)
        identifiers.add(identifier)
        group_label = _text(value["label"], diagnostics, view, f"{label} label")
        if value.get("description") is not None:
            _text(value["description"], diagnostics, view, f"{label} description")
        result.append(CuratedGroup(identifier, group_label, str(value.get("kind", label)), str(value.get("parent", "")), order))
    return sorted(result, key=lambda item: (item.order, item.id))


def _parse_view(raw: Any, root: Path, context: ArchitectureViewContext, diagnostics: list[Diagnostic], view_name: str) -> ViewCuration:
    if not isinstance(raw, dict):
        _diag(diagnostics, "CURATION_VIEW_INVALID", "Invalid view curation; expected dict", view=view_name)
        return ViewCuration()
    unknown = sorted(set(raw) - VIEW_KEYS)
    if unknown:
        for key in unknown:
            _diag(diagnostics, "CURATION_KEY_UNSUPPORTED", f"Unknown {view_name} key: {key}", view=view_name)
        return ViewCuration()
    try:
        return _parse_valid_view(raw, root, context, diagnostics, view_name)
    except _InvalidView:
        return ViewCuration()


def _parse_valid_view(raw: dict[str, Any], root: Path, context: ArchitectureViewContext, diagnostics: list[Diagnostic], view_name: str) -> ViewCuration:
    result = ViewCuration()
    identifiers = {entity.key for entity in context.entities()}
    for field_name in ("featured", "hide", "aggregate_components"):
        seen: set[str] = set()
        for value in _collection(raw, field_name, diagnostics, list, view_name):
            selector = _selector(value, diagnostics, view_name)
            if not selector:
                _diag(diagnostics, "CURATION_SELECTOR_INVALID", f"Invalid selector in {field_name}", view=view_name)
                raise _InvalidView(field_name)
            matches = context.select(
                qualified_id=selector.qualified_id, local_id=selector.local_id, system=selector.system,
                name=selector.name, source_file=selector.source_file, tag=selector.tag,
            )
            if len(matches) != 1:
                description = selector.qualified_id or selector.local_id or selector.name or selector.source_file or selector.tag
                code = "CURATION_SELECTOR_AMBIGUOUS" if selector.name or selector.local_id else "CURATION_SELECTOR_UNRESOLVED"
                _diag(diagnostics, code, f"Ambiguous selector ignored: {description}" if code.endswith("AMBIGUOUS") else f"Unresolved selector ignored: {description}", view=view_name)
                continue
            selector.resolved_id = matches[0].key
            if selector.resolved_id in seen:
                _diag(diagnostics, "CURATION_SELECTOR_DUPLICATE", f"Duplicate selector ignored: {selector.resolved_id}", view=view_name)
                continue
            seen.add(selector.resolved_id)
            getattr(result, field_name).append(selector)
    result.order = [str(value) for value in _collection(raw, "order", diagnostics, list, view_name)]
    labels = _collection(raw, "labels", diagnostics, dict, view_name)
    try:
        result.labels = {str(key): validate_presentation_text(str(value)) for key, value in labels.items()}
    except ValueError as exc:
        _diag(diagnostics, "CURATION_TEXT_UNSAFE", str(exc), view=view_name)
        raise _InvalidView("labels") from exc
    result.groups = _groups(_collection(raw, "groups", diagnostics, list, view_name), diagnostics, "group", identifiers, view_name)
    result.scenarios = _groups(_collection(raw, "scenarios", diagnostics, list, view_name), diagnostics, "scenario", identifiers, view_name)
    result.tiers = _groups(_collection(raw, "tiers", diagnostics, list, view_name), diagnostics, "tier", identifiers, view_name)
    for value in _collection(raw, "externals", diagnostics, list, view_name):
        if not isinstance(value, dict):
            _diag(diagnostics, "CURATION_VALUE_INVALID", "Invalid external", view=view_name)
            raise _InvalidView("external")
        _check_keys(value, EXTERNAL_KEYS, diagnostics, view_name, "external")
        identifier, name = str(value.get("id", "")), str(value.get("name", ""))
        name = _text(name, diagnostics, view_name, "external name")
        if value.get("description") is not None:
            _text(value["description"], diagnostics, view_name, "external description")
        evidence = _evidence(value.get("evidence"), root, diagnostics, f"external {identifier or name}", view_name)
        if not identifier or not name or value.get("inferred") is not True or not evidence:
            _diag(diagnostics, "CURATION_EXTERNAL_INVALID", f"Invalid inferred external: {identifier or name or '<unknown>'}", view=view_name)
            raise _InvalidView("external")
        if identifier in identifiers:
            _diag(diagnostics, "CURATION_ID_DUPLICATE", f"Duplicate presentation ID ignored: {identifier}", view=view_name)
            continue
        identifiers.add(identifier)
        result.externals.append(CuratedExternal(identifier, name, True, evidence, str(value.get("kind", "external"))))
    presentation_ids = {item.id for item in result.groups + result.scenarios + result.tiers + result.externals}
    flow_keys: set[tuple[str, str, str, str]] = set()
    for value in _collection(raw, "flows", diagnostics, list, view_name):
        if not isinstance(value, dict) or not value.get("source") or not value.get("target"):
            _diag(diagnostics, "CURATION_FLOW_INVALID", "Invalid curated flow", view=view_name)
            raise _InvalidView("flow")
        _check_keys(value, FLOW_KEYS, diagnostics, view_name, "flow")
        source, target, kind = str(value["source"]), str(value["target"]), str(value.get("kind", "flow"))
        inferred = value.get("inferred") is True
        evidence = _evidence(value.get("evidence"), root, diagnostics, f"flow {source} -> {target}", view_name) if inferred else []
        if kind in CANONICAL_LINK_KINDS:
            _diag(diagnostics, "CURATION_FLOW_CANONICAL", f"Curated flow cannot create canonical relationship: {kind}", view=view_name)
            raise _InvalidView("flow")
        if inferred and kind not in INFERRED_FLOW_KINDS:
            _diag(diagnostics, "CURATION_FLOW_KIND_UNSUPPORTED", f"Unsupported inferred flow kind: {kind}", view=view_name)
            raise _InvalidView("flow")
        if inferred and not evidence:
            _diag(diagnostics, "CURATION_EVIDENCE_INVALID", f"Inferred curated flow requires evidence: {source} -> {target}", view=view_name)
            raise _InvalidView("flow")
        if not inferred and not ({source, target} <= presentation_ids):
            _diag(diagnostics, "CURATION_FLOW_ENDPOINT_INVALID", f"Curated flow must link presentation groups: {source} -> {target}", view=view_name)
            raise _InvalidView("flow")
        flow_label = _text(value.get("label", ""), diagnostics, view_name, "flow label")
        if value.get("description") is not None:
            _text(value["description"], diagnostics, view_name, "flow description")
        flow_key = (source, target, kind, flow_label)
        if flow_key in flow_keys:
            _diag(diagnostics, "CURATION_FLOW_DUPLICATE", f"Duplicate curated flow ignored: {source} -> {target}", view=view_name)
            continue
        flow_keys.add(flow_key)
        result.flows.append(CuratedFlow(source, target, kind, flow_label, inferred, evidence))
    result.externals.sort(key=lambda item: item.id)
    result.flows.sort(key=lambda item: (item.source, item.target, item.kind, item.label))
    for field_name in ("preferred_capability_root", "mission_root"):
        value = raw.get(field_name)
        if value is not None:
            selector = _selector(value, diagnostics, view_name)
            if selector is None or not selector.resolve(context):
                _diag(diagnostics, "CURATION_SELECTOR_UNRESOLVED", f"Unresolved selector in {field_name}", view=view_name)
            else:
                setattr(result, field_name, selector)
    drilldowns = _collection(raw, "drilldowns", diagnostics, dict, view_name)
    for key, value in sorted(drilldowns.items()):
        selector = _selector(value, diagnostics, view_name)
        if selector is None:
            _diag(diagnostics, "CURATION_SELECTOR_INVALID", f"Invalid drilldown selector: {key}", view=view_name)
            raise _InvalidView("drilldowns")
        if selector.resolve(context):
            result.drilldowns[str(key)] = selector
    return result


def validate_view_curation(view: ViewCuration, context: ArchitectureViewContext) -> list[Diagnostic]:
    identifiers = {entity.key for entity in context.entities()}
    identifiers.update(item.id for item in view.groups + view.scenarios + view.tiers + view.externals)
    diagnostics: list[Diagnostic] = []
    for flow in view.flows:
        if flow.source not in identifiers:
            _diag(diagnostics, "CURATION_FLOW_ENDPOINT_UNKNOWN", f"Curated flow has unknown source: {flow.source}")
        if flow.target not in identifiers:
            _diag(diagnostics, "CURATION_FLOW_ENDPOINT_UNKNOWN", f"Curated flow has unknown target: {flow.target}")
    return diagnostics


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
        return ViewerCuration(diagnostics=[Diagnostic("warning", "CURATION_PATH_INVALID", f"Curation path is outside repository: {candidate}")])
    if not resolved.exists():
        return ViewerCuration()
    diagnostics: list[Diagnostic] = []
    try:
        raw = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        return ViewerCuration(diagnostics=[Diagnostic("warning", "CURATION_ROOT_INVALID", f"Invalid curation file: {exc}")])
    if not isinstance(raw, dict) or raw.get("version") != 1 or not isinstance(raw.get("views", {}), dict):
        return ViewerCuration(diagnostics=[Diagnostic("warning", "CURATION_ROOT_INVALID", "Invalid viewer curation schema; expected version 1 and views mapping")])
    unknown_root = sorted(set(raw) - {"version", "views"})
    if unknown_root:
        return ViewerCuration(diagnostics=[Diagnostic("warning", "CURATION_ROOT_INVALID", f"Unknown top-level key: {key}") for key in unknown_root])
    unknown = sorted(set(raw["views"]) - set(VIEW_NAMES))
    if unknown:
        return ViewerCuration(diagnostics=[Diagnostic("warning", "CURATION_ROOT_INVALID", f"Unknown curation view: {name}") for name in unknown])
    parsed = {}
    for name in VIEW_NAMES:
        parsed[name] = _parse_view(raw["views"].get(name, {}), root, context, diagnostics, name)
    return ViewerCuration(1, CuratedViews(**parsed), diagnostics)
