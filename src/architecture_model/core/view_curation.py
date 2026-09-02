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
EXTERNAL_KINDS = {"source-system", "ai-service", "telemetry", "legacy-adapter", "external-service"}
VIEW_KEYS = {
    "featured", "hide", "order", "labels", "externals", "scenarios", "groups",
    "flows", "tiers", "aggregate_components",
    "preferred_capability_root", "mission_root", "drilldowns",
}
USE_CASE_VIEW_KEYS = {"actors", "associations", "annotations"}
SELECTOR_KEYS = {"qualified_id", "local_id", "system", "name", "source_file", "tag"}
GROUP_KEYS = {"id", "label", "kind", "parent", "order", "description", "members"}
SCENARIO_KEYS = GROUP_KEYS | {"goal", "outcomes", "requirements", "moes", "evidence"}
EXTERNAL_KEYS = {"id", "name", "inferred", "evidence", "kind", "description"}
FLOW_KEYS = {"source", "target", "kind", "label", "description", "inferred", "evidence"}
EVIDENCE_KEYS = {"source", "claim"}
USE_CASE_ACTOR_KEYS = {"id", "name", "inferred", "evidence"}
ASSOCIATION_KEYS = {"actor", "use_cases", "inferred", "evidence"}
ANNOTATION_KEYS = {
    "use_case", "goal", "trigger", "preconditions", "postconditions",
    "success_outcome", "moes", "evidence",
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
    kind: str = ""


@dataclass
class CuratedGroup:
    id: str
    label: str
    kind: str = "group"
    parent: str = ""
    order: int = 0
    members: list[str] = field(default_factory=list)


@dataclass
class CuratedScenario(CuratedGroup):
    goal: str = ""
    outcomes: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    moes: list[str] = field(default_factory=list)
    evidence: list[EvidenceRecord] = field(default_factory=list)


@dataclass
class CuratedFlow:
    source: str
    target: str
    kind: str = "flow"
    label: str = ""
    inferred: bool = False
    evidence: list[EvidenceRecord] = field(default_factory=list)


@dataclass
class CuratedUseCaseActor:
    id: str
    name: str
    inferred: bool
    evidence: list[EvidenceRecord]


@dataclass
class CuratedUseCaseAssociation:
    actor: str
    use_cases: list[str]
    inferred: bool
    evidence: list[EvidenceRecord]


@dataclass
class CuratedUseCaseAnnotation:
    use_case: str
    goal: str = ""
    trigger: str = ""
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)
    success_outcome: str = ""
    moes: list[str] = field(default_factory=list)
    evidence: list[EvidenceRecord] = field(default_factory=list)


@dataclass
class ViewCuration:
    featured: list[Selector] = field(default_factory=list)
    hide: list[Selector] = field(default_factory=list)
    order: list[str] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)
    externals: list[CuratedExternal] = field(default_factory=list)
    scenarios: list[CuratedScenario] = field(default_factory=list)
    groups: list[CuratedGroup] = field(default_factory=list)
    flows: list[CuratedFlow] = field(default_factory=list)
    tiers: list[CuratedGroup] = field(default_factory=list)
    aggregate_components: list[Selector] = field(default_factory=list)
    preferred_capability_root: Selector | None = None
    mission_root: Selector | None = None
    drilldowns: dict[str, Selector] = field(default_factory=dict)
    actors: list[CuratedUseCaseActor] = field(default_factory=list)
    associations: list[CuratedUseCaseAssociation] = field(default_factory=list)
    annotations: list[CuratedUseCaseAnnotation] = field(default_factory=list)
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
    modes = [key for key in SELECTOR_KEYS - {"system"} if raw.get(key) not in (None, "")]
    if len(modes) != 1:
        if diagnostics is not None:
            _diag(diagnostics, "CURATION_SELECTOR_INVALID", "Selector requires exactly one mode plus optional system", view=view)
            raise _InvalidView("selector")
        return None
    if raw.get("system") and modes[0] == "qualified_id":
        if diagnostics is not None:
            _diag(diagnostics, "CURATION_SELECTOR_INVALID", "Qualified selector cannot include system scope", view=view)
            raise _InvalidView("selector")
        return None
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


def _groups(raw: Any, diagnostics: list[Diagnostic], label: str, identifiers: set[str], view: str, context: ArchitectureViewContext) -> list[CuratedGroup]:
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
        members = value.get("members", [])
        if not isinstance(members, list):
            _diag(diagnostics, "CURATION_VALUE_INVALID", f"Invalid {label} members: {identifier}", view=view)
            raise _InvalidView(label)
        resolved_members: list[str] = []
        for member in members:
            selector = _selector(member, diagnostics, view)
            if selector is None or not selector.resolve(context):
                _diag(diagnostics, "CURATION_SELECTOR_UNRESOLVED", f"Unresolved {label} member: {member}", view=view)
                raise _InvalidView(label)
            resolved_members.append(selector.resolved_id)
        result.append(CuratedGroup(identifier, group_label, str(value.get("kind", label)), str(value.get("parent", "")), order, resolved_members))
    return sorted(result, key=lambda item: (item.order, item.id))


def _scenarios(
    raw: Any, root: Path, diagnostics: list[Diagnostic], identifiers: set[str],
    view: str, context: ArchitectureViewContext,
) -> list[CuratedScenario]:
    result: list[CuratedScenario] = []
    for value in raw if isinstance(raw, list) else []:
        if not isinstance(value, dict) or not value.get("id") or not value.get("label"):
            _diag(diagnostics, "CURATION_VALUE_INVALID", "Invalid scenario entry", view=view)
            raise _InvalidView("scenario")
        _check_keys(value, SCENARIO_KEYS, diagnostics, view, "scenario")
        identifier = str(value["id"])
        if identifier in identifiers:
            _diag(diagnostics, "CURATION_ID_DUPLICATE", f"Duplicate presentation ID ignored: {identifier}", view=view)
            continue
        try:
            order = int(value.get("order", 0))
        except (TypeError, ValueError) as exc:
            _diag(diagnostics, "CURATION_VALUE_INVALID", f"Invalid scenario order: {identifier}", view=view)
            raise _InvalidView("scenario") from exc
        members = value.get("members", [])
        if not isinstance(members, list):
            _diag(diagnostics, "CURATION_VALUE_INVALID", f"Invalid scenario members: {identifier}", view=view)
            raise _InvalidView("scenario")
        resolved_members: list[str] = []
        for member in members:
            selector = _selector(member, diagnostics, view)
            if selector is None or not selector.resolve(context):
                _diag(diagnostics, "CURATION_SELECTOR_UNRESOLVED", f"Unresolved scenario member: {member}", view=view)
                raise _InvalidView("scenario")
            resolved_members.append(selector.resolved_id)
        goal = _text(value.get("goal", ""), diagnostics, view, "scenario goal")
        outcomes = _safe_text_list(value.get("outcomes"), diagnostics, view, "scenario outcomes")
        requirements = _safe_text_list(value.get("requirements"), diagnostics, view, "scenario requirements")
        moes = _safe_text_list(value.get("moes"), diagnostics, view, "scenario moes")
        annotated = bool(goal or outcomes or requirements or moes)
        evidence = _evidence(value.get("evidence"), root, diagnostics, f"scenario {identifier}", view) if annotated or value.get("evidence") is not None else []
        identifiers.add(identifier)
        result.append(CuratedScenario(
            identifier, _text(value["label"], diagnostics, view, "scenario label"),
            str(value.get("kind", "scenario")), str(value.get("parent", "")), order,
            resolved_members, goal, outcomes, requirements, moes, evidence,
        ))
    return sorted(result, key=lambda item: (item.order, item.id))


def _parse_view(raw: Any, root: Path, context: ArchitectureViewContext, diagnostics: list[Diagnostic], view_name: str) -> ViewCuration:
    if not isinstance(raw, dict):
        _diag(diagnostics, "CURATION_VIEW_INVALID", "Invalid view curation; expected dict", view=view_name)
        return ViewCuration()
    allowed = VIEW_KEYS | (USE_CASE_VIEW_KEYS if view_name == "use_cases" else set())
    unknown = sorted(set(raw) - allowed)
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
                getattr(result, field_name).append(selector)
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
    result.groups = _groups(_collection(raw, "groups", diagnostics, list, view_name), diagnostics, "group", identifiers, view_name, context)
    result.scenarios = _scenarios(
        _collection(raw, "scenarios", diagnostics, list, view_name), root,
        diagnostics, identifiers, view_name, context,
    )
    result.tiers = _groups(_collection(raw, "tiers", diagnostics, list, view_name), diagnostics, "tier", identifiers, view_name, context)
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
        kind = str(value.get("kind", ""))
        if kind and kind not in EXTERNAL_KINDS:
            _diag(diagnostics, "CURATION_EXTERNAL_KIND_UNSUPPORTED", f"Unsupported external kind: {kind}", view=view_name)
            raise _InvalidView("external")
        identifiers.add(identifier)
        result.externals.append(CuratedExternal(identifier, name, True, evidence, kind))
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
        if inferred and kind not in INFERRED_FLOW_KINDS:
            _diag(diagnostics, "CURATION_FLOW_KIND_UNSUPPORTED", f"Unsupported inferred flow kind: {kind}", view=view_name)
            raise _InvalidView("flow")
        if inferred and not evidence:
            _diag(diagnostics, "CURATION_EVIDENCE_INVALID", f"Inferred curated flow requires evidence: {source} -> {target}", view=view_name)
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
    if view_name == "use_cases":
        _parse_use_case_semantics(raw, root, context, diagnostics, result, identifiers)
    for field_name in ("preferred_capability_root", "mission_root"):
        value = raw.get(field_name)
        if value is not None:
            selector = _selector(value, diagnostics, view_name)
            if selector is None or not selector.resolve(context):
                _diag(diagnostics, "CURATION_SELECTOR_UNRESOLVED", f"Unresolved selector in {field_name}", view=view_name)
            if selector is not None:
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


def _safe_text_list(raw: Any, diagnostics: list[Diagnostic], view: str, field_name: str) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        _diag(diagnostics, "CURATION_VALUE_INVALID", f"Invalid {field_name}; expected list", view=view)
        raise _InvalidView(field_name)
    return [_text(value, diagnostics, view, field_name) for value in raw]


def _resolved_entity_selector(
    raw: Any, context: ArchitectureViewContext, diagnostics: list[Diagnostic], view: str,
    owner: str, entity_type: str,
) -> str:
    selector = _selector(raw, diagnostics, view)
    if selector is None or not selector.resolve(context):
        _diag(diagnostics, "CURATION_SELECTOR_UNRESOLVED", f"Unresolved {owner} selector", view=view)
        raise _InvalidView(owner)
    entity = context.entity(selector.resolved_id, diagnose=False)
    if not entity or entity.entity_type != entity_type:
        _diag(diagnostics, "CURATION_SELECTOR_INVALID", f"{owner} must select {entity_type}", view=view)
        raise _InvalidView(owner)
    return selector.resolved_id


def _parse_use_case_semantics(
    raw: dict[str, Any], root: Path, context: ArchitectureViewContext,
    diagnostics: list[Diagnostic], result: ViewCuration, identifiers: set[str],
) -> None:
    actor_ids: set[str] = set()
    for value in _collection(raw, "actors", diagnostics, list, "use_cases"):
        if not isinstance(value, dict):
            raise _InvalidView("actors")
        _check_keys(value, USE_CASE_ACTOR_KEYS, diagnostics, "use_cases", "use-case actor")
        identifier = str(value.get("id", ""))
        name = _text(value.get("name", ""), diagnostics, "use_cases", "actor name")
        evidence = _evidence(value.get("evidence"), root, diagnostics, f"actor {identifier}", "use_cases")
        if not identifier or not name or value.get("inferred") is not True or identifier in identifiers or identifier in actor_ids:
            _diag(diagnostics, "CURATION_ACTOR_INVALID", f"Invalid inferred use-case actor: {identifier}", view="use_cases")
            raise _InvalidView("actors")
        actor_ids.add(identifier)
        result.actors.append(CuratedUseCaseActor(identifier, name, True, evidence))
    identifiers.update(actor_ids)

    association_keys: set[tuple[str, tuple[str, ...]]] = set()
    for value in _collection(raw, "associations", diagnostics, list, "use_cases"):
        if not isinstance(value, dict):
            raise _InvalidView("associations")
        _check_keys(value, ASSOCIATION_KEYS, diagnostics, "use_cases", "use-case association")
        actor_raw = value.get("actor")
        if isinstance(actor_raw, str) and actor_raw in actor_ids:
            actor = actor_raw
        else:
            actor = _resolved_entity_selector(actor_raw, context, diagnostics, "use_cases", "association actor", "actor")
        use_cases_raw = value.get("use_cases")
        if not isinstance(use_cases_raw, list) or not use_cases_raw:
            _diag(diagnostics, "CURATION_VALUE_INVALID", "Association requires nonempty use_cases", view="use_cases")
            raise _InvalidView("associations")
        use_cases = [
            _resolved_entity_selector(item, context, diagnostics, "use_cases", "association use case", "behavior")
            for item in use_cases_raw
        ]
        evidence = _evidence(value.get("evidence"), root, diagnostics, "use-case association", "use_cases")
        if value.get("inferred") is not True:
            _diag(diagnostics, "CURATION_ASSOCIATION_INVALID", "Use-case association must be inferred", view="use_cases")
            raise _InvalidView("associations")
        association_key = (actor, tuple(use_cases))
        if association_key in association_keys:
            _diag(diagnostics, "CURATION_ASSOCIATION_DUPLICATE", f"Duplicate use-case association: {actor}", view="use_cases")
            raise _InvalidView("associations")
        association_keys.add(association_key)
        result.associations.append(CuratedUseCaseAssociation(actor, use_cases, True, evidence))

    seen_annotations: set[str] = set()
    for value in _collection(raw, "annotations", diagnostics, list, "use_cases"):
        if not isinstance(value, dict):
            raise _InvalidView("annotations")
        _check_keys(value, ANNOTATION_KEYS, diagnostics, "use_cases", "use-case annotation")
        use_case = _resolved_entity_selector(value.get("use_case"), context, diagnostics, "use_cases", "annotation use case", "behavior")
        if use_case in seen_annotations:
            _diag(diagnostics, "CURATION_ANNOTATION_DUPLICATE", f"Duplicate annotation: {use_case}", view="use_cases")
            raise _InvalidView("annotations")
        seen_annotations.add(use_case)
        evidence = _evidence(value.get("evidence"), root, diagnostics, f"annotation {use_case}", "use_cases")
        semantic_keys = ANNOTATION_KEYS - {"use_case", "evidence"}
        if not any(value.get(key) for key in semantic_keys):
            _diag(diagnostics, "CURATION_ANNOTATION_INVALID", f"Annotation has no semantic fields: {use_case}", view="use_cases")
            raise _InvalidView("annotations")
        result.annotations.append(CuratedUseCaseAnnotation(
            use_case=use_case,
            goal=_text(value.get("goal", ""), diagnostics, "use_cases", "annotation goal"),
            trigger=_text(value.get("trigger", ""), diagnostics, "use_cases", "annotation trigger"),
            preconditions=_safe_text_list(value.get("preconditions"), diagnostics, "use_cases", "annotation preconditions"),
            postconditions=_safe_text_list(value.get("postconditions"), diagnostics, "use_cases", "annotation postconditions"),
            success_outcome=_text(value.get("success_outcome", ""), diagnostics, "use_cases", "annotation success outcome"),
            moes=_safe_text_list(value.get("moes"), diagnostics, "use_cases", "annotation moes"),
            evidence=evidence,
        ))


def validate_view_curation(view: ViewCuration, context: ArchitectureViewContext) -> list[Diagnostic]:
    identifiers = {entity.key for entity in context.entities()}
    identifiers.update(item.id for item in view.groups + view.scenarios + view.tiers + view.externals)
    identifiers.update(item.id for item in view.actors)
    identifiers.update(item.resolved_id for item in view.aggregate_components if item.resolved_id)
    diagnostics: list[Diagnostic] = []
    for target in view.labels:
        if target not in identifiers:
            _diag(diagnostics, "CURATION_SEMANTIC_LABEL_TARGET", f"Unknown label target: {target}")
    group_ids = {item.id for item in view.groups + view.scenarios + view.tiers}
    for group in view.groups + view.scenarios + view.tiers:
        if group.parent and group.parent not in group_ids:
            _diag(diagnostics, "CURATION_SEMANTIC_GROUP_PARENT", f"Unknown group parent: {group.parent}")
    for field_name in ("preferred_capability_root", "mission_root"):
        selector = getattr(view, field_name)
        if selector is not None and selector.resolved_id not in identifiers:
            _diag(diagnostics, "CURATION_SEMANTIC_ROOT", f"Unknown {field_name}: {selector.resolved_id}")
    for selector in [*view.featured, *view.aggregate_components, *view.hide, *view.drilldowns.values()]:
        if not selector.resolved_id or selector.resolved_id not in identifiers:
            _diag(diagnostics, "CURATION_SEMANTIC_SELECTOR", f"Unknown resolved selector: {selector.resolved_id}")
    for flow in view.flows:
        if flow.source not in identifiers:
            _diag(diagnostics, "CURATION_SEMANTIC_FLOW_ENDPOINT", f"Curated flow has unknown source: {flow.source}")
        if flow.target not in identifiers:
            _diag(diagnostics, "CURATION_SEMANTIC_FLOW_ENDPOINT", f"Curated flow has unknown target: {flow.target}")
        canonical = any(
            relationship.target == flow.target and relationship.kind == flow.kind
            for relationship in context.outgoing(flow.source, flow.kind)
        ) if flow.source in identifiers and flow.target in identifiers else False
        if not canonical and (not flow.inferred or not flow.evidence):
            _diag(
                diagnostics, "CURATION_SEMANTIC_FLOW_EVIDENCE",
                f"Noncanonical curated flow must be inferred with evidence: {flow.source} -> {flow.target}",
            )
    for association in view.associations:
        actor = context.entity(association.actor, diagnose=False)
        presentation_actor = any(item.id == association.actor for item in view.actors)
        if not presentation_actor and (not actor or actor.entity_type != "actor"):
            _diag(diagnostics, "CURATION_SEMANTIC_ASSOCIATION_ACTOR", f"Unknown association actor: {association.actor}")
        for use_case in association.use_cases:
            entity = context.entity(use_case, diagnose=False)
            if not entity or entity.entity_type != "behavior":
                _diag(diagnostics, "CURATION_SEMANTIC_ASSOCIATION_USE_CASE", f"Unknown association use case: {use_case}")
    for annotation in view.annotations:
        entity = context.entity(annotation.use_case, diagnose=False)
        if not entity or entity.entity_type != "behavior":
            _diag(diagnostics, "CURATION_SEMANTIC_ANNOTATION_USE_CASE", f"Unknown annotation use case: {annotation.use_case}")
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
        view = _parse_view(raw["views"].get(name, {}), root, context, diagnostics, name)
        semantic = validate_view_curation(view, context)
        if semantic:
            diagnostics.extend(Diagnostic(item.severity, item.code, item.message, view=name, source=item.source, context=item.context) for item in semantic)
            view = ViewCuration()
        parsed[name] = view
    return ViewerCuration(1, CuratedViews(**parsed), diagnostics)
