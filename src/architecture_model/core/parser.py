"""
Parser: Load architecture model YAML, validate against schema, return typed ArchitectureModel.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

try:
    import jsonschema

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

from .types import (
    Actor,
    ActorType,
    ArchitectureModel,
    Behavior,
    BehaviorPattern,
    Capability,
    Compensation,
    Component,
    ComponentKind,
    Constant,
    Constraint,
    ConstraintType,
    Data,
    DataField,
    Decision,
    DecisionEntry,
    DecisionStatus,
    Entities,
    Environment,
    EnvironmentKind,
    Event,
    EventKind,
    ExternalSystem,
    FunctionSignature,
    Interface,
    InterfaceType,
    Layer,
    Lifecycle,
    LifecyclePhase,
    ModelMeta,
    Priority,
    QualityAttribute,
    Relationship,
    RelationType,
    Requirement,
    Resource,
    ResourceKind,
    StateTransition,
    Status,
    Step,
    Strength,
    Symbol,
    SymbolKind,
    System,
    TestContract,
    ObservabilityContract,
    ComponentInterface,
    _enum_value,
)

SCHEMA_PATH = Path(__file__).parent.parent / "spec" / "schema.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_block_model(
    project_root: str | Path,
    block_id: str,
    output_dir: str = ".architecture-models",
) -> ArchitectureModel | None:
    """Load a block sub-model from the .architecture-models/ directory.
    Returns None if the sub-model doesn't exist.
    """
    root = Path(project_root)
    sub_model_path = root / output_dir / block_id / ".architecture-model.yaml"
    if not sub_model_path.exists():
        return None
    return load_model(sub_model_path)


def load_model(path: str | Path) -> ArchitectureModel:
    """Load and parse an architecture model YAML file."""
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ValueError(f"Empty model file: {path}")

    model = _parse_raw(raw)
    from architecture_model.core.confidence import compute_model_confidence
    compute_model_confidence(model)
    return model


def validate_model_data(data: dict[str, Any]) -> list[str]:
    """Validate raw dict against JSON Schema. Returns list of error messages."""
    if not HAS_JSONSCHEMA:
        return ["jsonschema not installed — skipping schema validation"]

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    return [f"{e.json_path}: {e.message}" for e in validator.iter_errors(data)]


def dump_model(model: ArchitectureModel) -> dict[str, Any]:
    """Serialize ArchitectureModel back to a plain dict suitable for YAML output."""
    return {
        "meta": _dump_meta(model.meta),
        "entities": _dump_entities(model.entities),
        "relationships": [_dump_relationship(r) for r in model.relationships],
    }


def save_model(model: ArchitectureModel, path: str | Path) -> None:
    """Serialize and write model to YAML file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dump_model(model)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True, width=120)


# ---------------------------------------------------------------------------
# Internal: Parsing
# ---------------------------------------------------------------------------


def _parse_status(val: str) -> Status:
    return Status(val.upper()) if val else Status.ACTIVE


def _parse_priority(val: str | None) -> Priority:
    if not val:
        return Priority.MEDIUM
    return Priority(val.lower())


def _parse_raw(raw: dict) -> ArchitectureModel:
    meta = _parse_meta(raw.get("meta", {}))
    entities = _parse_entities(raw.get("entities", {}))
    relationships = [_parse_relationship(r) for r in raw.get("relationships", [])]
    return ArchitectureModel(meta=meta, entities=entities, relationships=relationships)


def _parse_meta(d: dict) -> ModelMeta:
    return ModelMeta(
        schema_version=d.get("schema_version", "1.1"),
        project=d.get("project", ""),
        system=d.get("system", ""),
        generated_at=d.get("generated_at", datetime.now(timezone.utc).isoformat()),
        source_artifacts=d.get("source_artifacts", []),
        manifest_hash=d.get("manifest_hash", ""),
        source_language=d.get("source_language", ""),
        domain_profile=d.get("domain_profile", "software"),
        manifest_path=d.get("manifest_path", ""),
        lifecycle_phase=d.get("lifecycle_phase", "production"),
        parent_model=d.get("parent_model"),
        refines_component=d.get("refines_component"),
    )


def _normalize_entity_list(raw, id_key: str = "id") -> list[dict]:
    """Accept both list-of-dicts and dict-of-dicts (keyed by ID) formats.
    
    Agents often produce entities as:
        components:
          COMP-1:
            name: Foo
    Instead of:
        components:
          - id: COMP-1
            name: Foo
    
    This normalizes both to list-of-dicts.
    """
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        result = []
        for key, val in raw.items():
            if isinstance(val, dict):
                entry = dict(val)
                if id_key not in entry:
                    entry[id_key] = key
                result.append(entry)
            # Skip non-dict values (shouldn't happen but be defensive)
        return result
    return []


def _parse_entities(d: dict) -> Entities:
    return Entities(
        actors=[_parse_actor(a) for a in _normalize_entity_list(d.get("actors", []))],
        capabilities=[_parse_capability(c) for c in _normalize_entity_list(d.get("capabilities", []))],
        behaviors=[_parse_behavior(b) for b in _normalize_entity_list(d.get("behaviors", []))],
        interfaces=[_parse_interface(i) for i in _normalize_entity_list(d.get("interfaces", []))],
        constraints=[_parse_constraint(c) for c in _normalize_entity_list(d.get("constraints", []))],
        layers=[_parse_layer(l) for l in _normalize_entity_list(d.get("layers", []))],
        components=[_parse_component(c) for c in _normalize_entity_list(d.get("components", []))],
        systems=[_parse_system(s) for s in _normalize_entity_list(d.get("systems", []))],
        data=[_parse_data(x) for x in _normalize_entity_list(d.get("data", []))],
        events=[_parse_event(x) for x in _normalize_entity_list(d.get("events", []))],
        resources=[_parse_resource(x) for x in _normalize_entity_list(d.get("resources", []))],
        environments=[_parse_environment(x) for x in _normalize_entity_list(d.get("environments", []))],
        quality_attributes=[_parse_quality_attribute(x) for x in _normalize_entity_list(d.get("quality_attributes", []))],
        decisions=[_parse_decision(x) for x in _normalize_entity_list(d.get("decisions", []))],
        lifecycles=[_parse_lifecycle(x) for x in _normalize_entity_list(d.get("lifecycles", []))],
        requirements=[_parse_requirement(x) for x in _normalize_entity_list(d.get("requirements", []))],
        external_systems=[
            _parse_external_system(x)
            for x in _normalize_entity_list(d.get("external_systems", []))
        ],
    )


def _parse_base(d: dict) -> dict:
    return {
        "id": d.get("id", ""),
        "name": d.get("name", ""),
        "status": _parse_status(d.get("status", "ACTIVE")),
        "description": d.get("description", ""),
        "tags": d.get("tags", []),
        "source_file": d.get("source_file"),
        "source_line": d.get("source_line"),
        "extensions": d.get("extensions", {}),
        "confidence": float(d.get("confidence", 0.0)),
        "intent": d.get("intent", ""),
        "decisions": [
            DecisionEntry(
                choice=de["choice"],
                date=de.get("date", ""),
                rationale=de.get("rationale", ""),
                alternatives=de.get("alternatives", []),
                context=de.get("context", ""),
            )
            for de in d.get("decisions", [])
        ],
    }


def _parse_actor(d: dict) -> Actor:
    base = _parse_base(d)
    return Actor(
        **base,
        type=ActorType.parse(d.get("type", "human")),
        goals=d.get("goals", []),
    )


def _parse_capability(d: dict) -> Capability:
    base = _parse_base(d)
    return Capability(
        **base,
        source_block=d.get("source_block", "") or d.get("f_block", ""),
        priority=_parse_priority(d.get("priority")),
        requirements=d.get("requirements", []),
        moes=d.get("moes", []),
        goals=d.get("goals", []),
        trade_offs=d.get("trade_offs", []),
        failure_modes=d.get("failure_modes", []),
        monitored=d.get("monitored", []),
    )


def _parse_behavior(d: dict) -> Behavior:
    base = _parse_base(d)
    pattern_str = d.get("pattern", "sequential")
    pattern = BehaviorPattern.parse(pattern_str)

    states = [
        StateTransition(
            name=s.get("name", ""),
            transitions=s.get("transitions", []),
        )
        for s in d.get("states", [])
    ]

    compensations = [
        Compensation(
            step=c.get("step", ""),
            compensate=c.get("compensate", ""),
        )
        for c in d.get("compensations", [])
    ]

    return Behavior(
        **base,
        trigger=d.get("trigger", ""),
        actor=d.get("actor", ""),
        preconditions=d.get("preconditions", []),
        postconditions=d.get("postconditions", []),
        steps=d.get("steps", []),
        frequency=d.get("frequency", ""),
        priority=_parse_priority(d.get("priority")),
        pattern=pattern,
        states=states,
        compensations=compensations,
        structured_steps=[
            Step(
                order=s.get("order", 0),
                action=s.get("action", ""),
                component_ref=s.get("component_ref", ""),
                actor=s.get("actor", ""),
                input=s.get("input", ""),
                output=s.get("output", ""),
                error_handling=s.get("error_handling", ""),
            )
            for s in d.get("structured_steps", [])
        ],
        goals=d.get("goals", []),
        moes=d.get("moes", []),
        failure_modes=d.get("failure_modes", []),
    )


def _parse_interface(d: dict) -> Interface:
    base = _parse_base(d)
    return Interface(
        **base,
        type=InterfaceType.parse(d.get("type", "internal")),
        protocol=d.get("protocol", ""),
        provider=d.get("provider", ""),
        consumer=d.get("consumer", ""),
        data_format=d.get("data_format", ""),
        endpoints=d.get("endpoints", []),
        schema=d.get("schema", ""),
        contract=d.get("contract", ""),
    )


def _parse_constraint(d: dict) -> Constraint:
    base = _parse_base(d)
    return Constraint(
        **base,
        type=ConstraintType.parse(d.get("type", "technology")),
        metric=d.get("metric", ""),
        threshold=d.get("threshold", ""),
        rationale=d.get("rationale", ""),
    )


def _parse_layer(d: dict) -> Layer:
    base = _parse_base(d)
    return Layer(
        **base,
        order=d.get("order", 0),
        technology=d.get("technology", []),
        directories=d.get("directories", []),
    )


def _parse_component(d: dict) -> Component:
    base = _parse_base(d)
    kind_str = d.get("kind", "service")
    kind = ComponentKind.parse(kind_str)

    fields = [
        DataField(
            name=f.get("name", ""),
            type=f.get("type", "string"),
            required=f.get("required", False),
            description=f.get("description", ""),
        )
        for f in d.get("fields", [])
    ]

    symbols = []
    for s in d.get("symbols", []):
        sk_str = s.get("kind", "class")
        try:
            sk = SymbolKind(sk_str)
        except ValueError:
            sk = SymbolKind.CLASS
        symbols.append(Symbol(
            name=s.get("name", ""),
            kind=sk,
            members=s.get("members", []),
            supers=s.get("supers", []),
        ))

    constants = [
        Constant(
            name=c.get("name", ""),
            value=c.get("value", ""),
            context=c.get("context", ""),
            type=c.get("type"),
        )
        for c in d.get("constants", [])
    ]

    signatures = [
        FunctionSignature(
            name=s.get("name", ""),
            params=s.get("params", []),
            returns=s.get("returns", ""),
            decorators=s.get("decorators", []),
            body_hint=s.get("body_hint", ""),
            complexity=s.get("complexity"),
        )
        for s in d.get("signatures", [])
    ]

    test_contracts = [
        TestContract(
            test_file=tc.get("test_file", ""),
            test_method=tc.get("test_method", ""),
            assertion=tc.get("assertion", ""),
            contract_type=tc.get("contract_type", ""),
            required_imports=tc.get("required_imports", []),
        )
        for tc in d.get("test_contracts", [])
    ]

    observability = [
        ObservabilityContract(
            function=o.get("function", ""),
            log_level=o.get("log_level", "INFO"),
            emits_metric=o.get("emits_metric"),
            on_error=o.get("on_error", "ERROR"),
            on_success=o.get("on_success"),
        )
        for o in d.get("observability", [])
    ]

    interfaces = [
        ComponentInterface(
            name=ci.get("name", ""),
            kind=ci.get("kind", "provides"),
            target_component=ci.get("target_component", ""),
            signature=ci.get("signature", ""),
            symbols=ci.get("symbols", []),
        )
        for ci in d.get("interfaces", [])
    ]

    return Component(
        **base,
        layer=d.get("layer", ""),
        source_block=d.get("source_block", "") or d.get("f_block", ""),
        technology=d.get("technology", ""),
        files=d.get("files", []),
        responsibilities=d.get("responsibilities", []),
        kind=kind,
        fields=fields,
        region=d.get("region", ""),
        pattern=d.get("pattern", ""),
        contract=d.get("contract", ""),
        replicas=d.get("replicas"),
        symbols=symbols,
        functions=d.get("functions", []),
        constants=constants,
        signatures=signatures,
        test_contracts=test_contracts,
        observability=observability,
        interfaces=interfaces,
        goals=d.get("goals", []),
        moes=d.get("moes", []),
        trade_offs=d.get("trade_offs", []),
        failure_modes=d.get("failure_modes", []),
        monitored=d.get("monitored", []),
    )


def _parse_system(d: dict) -> System:
    base = _parse_base(d)
    return System(
        **base,
        layer=d.get("layer", ""),
        source_block=d.get("source_block", "") or d.get("f_block", ""),
        complexity_score=float(d.get("complexity_score", 0.0)),
        sub_model_ref=d.get("sub_model_ref", ""),
        component_ids=d.get("component_ids", []),
        goals=d.get("goals", []),
        trade_offs=d.get("trade_offs", []),
        failure_modes=d.get("failure_modes", []),
        monitored=d.get("monitored", []),
    )


def _parse_data(d: dict) -> Data:
    base = _parse_base(d)
    fields = [DataField(name=f.get("name",""), type=f.get("type","string"), required=f.get("required",False), description=f.get("description","")) for f in d.get("fields",[])]
    return Data(**base, schema_def=d.get("schema_def",""), format=d.get("format",""), fields=fields, owner=d.get("owner",""), sensitivity=d.get("sensitivity",""))


def _parse_event(d: dict) -> Event:
    base = _parse_base(d)
    return Event(**base, kind=EventKind.parse(d.get("kind","message")), source=d.get("source",""), target=d.get("target",""), payload=d.get("payload",""), frequency=d.get("frequency",""), reliability=d.get("reliability",""))


def _parse_resource(d: dict) -> Resource:
    base = _parse_base(d)
    return Resource(**base, kind=ResourceKind.parse(d.get("kind","database")), provider=d.get("provider",""), location=d.get("location",""), sla=d.get("sla",""))


def _parse_environment(d: dict) -> Environment:
    base = _parse_base(d)
    return Environment(**base, kind=EnvironmentKind.parse(d.get("kind","production")), infrastructure=d.get("infrastructure",[]), constraints=d.get("constraints",[]), region=d.get("region",""))


def _parse_quality_attribute(d: dict) -> QualityAttribute:
    base = _parse_base(d)
    return QualityAttribute(**base, metric=d.get("metric",""), target=d.get("target",""), current=d.get("current",""), measurement_method=d.get("measurement_method",""), applies_to=d.get("applies_to",[]))


def _parse_decision(d: dict) -> Decision:
    base = _parse_base(d)
    return Decision(**base, decision_status=DecisionStatus.parse(d.get("decision_status","accepted")), context=d.get("context",""), options=d.get("options",[]), rationale=d.get("rationale",""), consequences=d.get("consequences",[]), supersedes=d.get("supersedes",""))


def _parse_lifecycle(d: dict) -> Lifecycle:
    base = _parse_base(d)
    return Lifecycle(**base, phase=LifecyclePhase.parse(d.get("phase","production")), version=d.get("version",""), start_date=d.get("start_date",""), end_date=d.get("end_date",""), migration_from=d.get("migration_from",""), migration_to=d.get("migration_to",""), milestones=d.get("milestones",[]))


def _parse_requirement(d: dict) -> Requirement:
    base = _parse_base(d)
    return Requirement(**base, text=d.get("text",""), source_doc=d.get("source_doc",""), source_anchor=d.get("source_anchor",""), content_hash=d.get("content_hash",""), rationale=d.get("rationale",""), priority=d.get("priority",""), moe=d.get("moe",""), value_function=d.get("value_function",""), moes=d.get("moes",[]), failure_modes=d.get("failure_modes",[]), monitored=d.get("monitored",[]))


def _parse_relationship(d: dict) -> Relationship:
    # Accept multiple key formats agents might use
    from_id = d.get("from") or d.get("from_id") or d.get("source") or ""
    to_id = d.get("to") or d.get("to_id") or d.get("target") or ""
    return Relationship(
        type=RelationType.parse(d.get("type", "depends-on")),
        from_id=from_id,
        to_id=to_id,
        description=d.get("description", ""),
        strength=Strength(d.get("strength", "moderate")),
        extensions=d.get("extensions", {}),
        imports=d.get("imports", []),
        import_count=d.get("import_count", 0),
        weight=d.get("weight", 0.0),
    )


def _parse_external_system(d: dict) -> ExternalSystem:
    return ExternalSystem(
        **_parse_base(d),
        url=d.get("url", ""),
        auth_method=d.get("auth_method", ""),
        api_type=d.get("api_type", ""),
        provider=d.get("provider", ""),
        sla=d.get("sla", ""),
    )


# ---------------------------------------------------------------------------
# Internal: Serialization
# ---------------------------------------------------------------------------


def _dump_meta(m: ModelMeta) -> dict:
    d: dict[str, Any] = {
        "schema_version": m.schema_version,
        "project": m.project,
    }
    if m.system:
        d["system"] = m.system
    d["generated_at"] = m.generated_at
    if m.source_artifacts:
        d["source_artifacts"] = m.source_artifacts
    if m.manifest_hash:
        d["manifest_hash"] = m.manifest_hash
    if m.source_language:
        d["source_language"] = m.source_language
    if m.domain_profile and m.domain_profile != "software":
        d["domain_profile"] = m.domain_profile
    if m.lifecycle_phase != "production":
        d["lifecycle_phase"] = m.lifecycle_phase
    if m.manifest_path:
        d["manifest_path"] = m.manifest_path
    if m.parent_model:
        d["parent_model"] = m.parent_model
    if m.refines_component:
        d["refines_component"] = m.refines_component
    return d


def _dump_entities(e: Entities) -> dict:
    d: dict[str, Any] = {}
    if e.actors:
        d["actors"] = [_dump_actor(a) for a in e.actors]
    if e.capabilities:
        d["capabilities"] = [_dump_capability(c) for c in e.capabilities]
    if e.behaviors:
        d["behaviors"] = [_dump_behavior(b) for b in e.behaviors]
    if e.interfaces:
        d["interfaces"] = [_dump_interface(i) for i in e.interfaces]
    if e.constraints:
        d["constraints"] = [_dump_constraint(c) for c in e.constraints]
    if e.layers:
        d["layers"] = [_dump_layer(l) for l in e.layers]
    if e.components:
        d["components"] = [_dump_component(c) for c in e.components]
    if e.systems:
        d["systems"] = [_dump_system(s) for s in e.systems]
    if e.data:
        d["data"] = [_dump_data(x) for x in e.data]
    if e.events:
        d["events"] = [_dump_event(x) for x in e.events]
    if e.resources:
        d["resources"] = [_dump_resource(x) for x in e.resources]
    if e.environments:
        d["environments"] = [_dump_environment(x) for x in e.environments]
    if e.quality_attributes:
        d["quality_attributes"] = [_dump_quality_attribute(x) for x in e.quality_attributes]
    if e.decisions:
        d["decisions"] = [_dump_decision(x) for x in e.decisions]
    if e.lifecycles:
        d["lifecycles"] = [_dump_lifecycle(x) for x in e.lifecycles]
    if e.requirements:
        d["requirements"] = [_dump_requirement(x) for x in e.requirements]
    if e.external_systems:
        d["external_systems"] = [_dump_external_system(x) for x in e.external_systems]
    return d


def _enum_val(v: Any) -> str:
    """Extract string value from enum or return as-is."""
    return v.value if hasattr(v, 'value') else str(v)


def _dump_base(entity: Any) -> dict:
    d: dict[str, Any] = {
        "id": entity.id,
        "name": entity.name,
        "status": _enum_val(entity.status),
    }
    if entity.description:
        d["description"] = entity.description
    if entity.intent:
        d["intent"] = entity.intent
    if entity.tags:
        d["tags"] = entity.tags
    if entity.source_file:
        d["source_file"] = entity.source_file
    if entity.source_line is not None:
        d["source_line"] = entity.source_line
    if entity.extensions:
        d["extensions"] = entity.extensions
    if entity.decisions:
        d["decisions"] = [
            {k: v for k, v in {
                "date": de.date,
                "choice": de.choice,
                "rationale": de.rationale,
                "alternatives": de.alternatives,
                "context": de.context,
            }.items() if v}
            for de in entity.decisions
        ]
    return d


def _dump_actor(a: Actor) -> dict:
    d = _dump_base(a)
    d["type"] = _enum_val(a.type)
    if a.goals:
        d["goals"] = a.goals
    return d


def _dump_capability(c: Capability) -> dict:
    d = _dump_base(c)
    if c.source_block:
        d["source_block"] = c.source_block
    if c.priority != Priority.MEDIUM:
        d["priority"] = _enum_val(c.priority)
    if c.requirements:
        d["requirements"] = c.requirements
    if c.moes:
        d["moes"] = c.moes
    if c.goals:
        d["goals"] = c.goals
    if c.trade_offs:
        d["trade_offs"] = c.trade_offs
    if c.failure_modes:
        d["failure_modes"] = c.failure_modes
    if c.monitored:
        d["monitored"] = c.monitored
    return d


def _dump_behavior(b: Behavior) -> dict:
    d = _dump_base(b)
    if b.trigger:
        d["trigger"] = b.trigger
    if b.actor:
        d["actor"] = b.actor
    if b.preconditions:
        d["preconditions"] = b.preconditions
    if b.postconditions:
        d["postconditions"] = b.postconditions
    if b.steps:
        d["steps"] = b.steps
    if b.frequency:
        d["frequency"] = b.frequency
    if b.priority != Priority.MEDIUM:
        d["priority"] = _enum_val(b.priority)
    if b.pattern != BehaviorPattern.SEQUENTIAL:
        d["pattern"] = _enum_val(b.pattern)
    if b.states:
        d["states"] = [
            {"name": s.name, "transitions": s.transitions}
            for s in b.states
        ]
    if b.compensations:
        d["compensations"] = [
            {"step": c.step, "compensate": c.compensate}
            for c in b.compensations
        ]
    if b.structured_steps:
        d["structured_steps"] = [
            {k: v for k, v in {
                "order": s.order,
                "action": s.action,
                "component_ref": s.component_ref,
                "actor": s.actor,
                "input": s.input,
                "output": s.output,
                "error_handling": s.error_handling,
            }.items() if v}
            for s in b.structured_steps
        ]
    if b.goals:
        d["goals"] = b.goals
    if b.moes:
        d["moes"] = b.moes
    if b.failure_modes:
        d["failure_modes"] = b.failure_modes
    return d


def _dump_interface(i: Interface) -> dict:
    d = _dump_base(i)
    d["type"] = i.type.value if hasattr(i.type, 'value') else str(i.type)
    if i.protocol:
        d["protocol"] = i.protocol
    if i.provider:
        d["provider"] = i.provider
    if i.consumer:
        d["consumer"] = i.consumer
    if i.data_format:
        d["data_format"] = i.data_format
    if i.endpoints:
        d["endpoints"] = i.endpoints
    if i.schema:
        d["schema"] = i.schema
    if i.contract:
        d["contract"] = i.contract
    return d


def _dump_constraint(c: Constraint) -> dict:
    d = _dump_base(c)
    d["type"] = _enum_val(c.type)
    if c.metric:
        d["metric"] = c.metric
    if c.threshold:
        d["threshold"] = c.threshold
    if c.rationale:
        d["rationale"] = c.rationale
    return d


def _dump_layer(l: Layer) -> dict:
    d = _dump_base(l)
    d["order"] = l.order
    if l.technology:
        d["technology"] = l.technology
    if l.directories:
        d["directories"] = l.directories
    return d


def _dump_component(c: Component) -> dict:
    d = _dump_base(c)
    if c.layer:
        d["layer"] = c.layer
    if c.source_block:
        d["source_block"] = c.source_block
    if c.technology:
        d["technology"] = c.technology
    if c.files:
        d["files"] = c.files
    if c.responsibilities:
        d["responsibilities"] = c.responsibilities
    if c.kind != ComponentKind.SERVICE:
        d["kind"] = _enum_val(c.kind)
    if c.fields:
        d["fields"] = [
            {"name": f.name, "type": f.type, "required": f.required}
            | ({"description": f.description} if f.description else {})
            for f in c.fields
        ]
    if c.region:
        d["region"] = c.region
    if c.contract:
        d["contract"] = c.contract
    if c.pattern:
        d["pattern"] = c.pattern
    if c.replicas is not None:
        d["replicas"] = c.replicas
    if c.symbols:
        d["symbols"] = [
            {"name": s.name, "kind": s.kind.value}
            | ({"members": s.members} if s.members else {})
            | ({"supers": s.supers} if s.supers else {})
            for s in c.symbols
        ]
    if c.functions:
        d["functions"] = c.functions
    if c.constants:
        d["constants"] = [
            {"name": cn.name, "value": cn.value}
            | ({"context": cn.context} if cn.context else {})
            | ({"type": cn.type} if cn.type else {})
            for cn in c.constants
        ]
    if c.signatures:
        d["signatures"] = [
            {"name": sig.name}
            | ({"params": sig.params} if sig.params else {})
            | ({"returns": sig.returns} if sig.returns else {})
            | ({"decorators": sig.decorators} if sig.decorators else {})
            | ({"body_hint": sig.body_hint} if sig.body_hint else {})
            | ({"complexity": sig.complexity} if sig.complexity else {})
            for sig in c.signatures
        ]
    if c.test_contracts:
        d["test_contracts"] = [
            {"test_file": tc.test_file, "test_method": tc.test_method, "assertion": tc.assertion}
            | ({"contract_type": tc.contract_type} if tc.contract_type else {})
            | ({"required_imports": tc.required_imports} if tc.required_imports else {})
            for tc in c.test_contracts
        ]
    if c.observability:
        d["observability"] = [
            {"function": o.function, "log_level": o.log_level}
            | ({"emits_metric": o.emits_metric} if o.emits_metric else {})
            | ({"on_error": o.on_error} if o.on_error != "ERROR" else {})
            | ({"on_success": o.on_success} if o.on_success else {})
            for o in c.observability
        ]
    if c.interfaces:
        d["interfaces"] = [
            {"name": ci.name, "kind": ci.kind}
            | ({"target_component": ci.target_component} if ci.target_component else {})
            | ({"signature": ci.signature} if ci.signature else {})
            | ({"symbols": ci.symbols} if ci.symbols else {})
            for ci in c.interfaces
        ]
    if c.goals:
        d["goals"] = c.goals
    if c.moes:
        d["moes"] = c.moes
    if c.trade_offs:
        d["trade_offs"] = c.trade_offs
    if c.failure_modes:
        d["failure_modes"] = c.failure_modes
    if c.monitored:
        d["monitored"] = c.monitored
    return d


def _dump_system(s: System) -> dict:
    d = _dump_base(s)
    if s.layer:
        d["layer"] = s.layer
    if s.source_block:
        d["source_block"] = s.source_block
    if s.complexity_score:
        d["complexity_score"] = s.complexity_score
    if s.sub_model_ref:
        d["sub_model_ref"] = s.sub_model_ref
    if s.component_ids:
        d["component_ids"] = s.component_ids
    if s.goals:
        d["goals"] = s.goals
    if s.trade_offs:
        d["trade_offs"] = s.trade_offs
    if s.failure_modes:
        d["failure_modes"] = s.failure_modes
    if s.monitored:
        d["monitored"] = s.monitored
    return d


def _dump_data(dat: Data) -> dict:
    r = _dump_base(dat)
    if dat.schema_def: r["schema_def"] = dat.schema_def
    if dat.format: r["format"] = dat.format
    if dat.fields: r["fields"] = [{"name":f.name,"type":f.type,"required":f.required}|({"description":f.description} if f.description else {}) for f in dat.fields]
    if dat.owner: r["owner"] = dat.owner
    if dat.sensitivity: r["sensitivity"] = dat.sensitivity
    return r


def _dump_event(e: Event) -> dict:
    r = _dump_base(e)
    r["kind"] = _enum_value(e.kind)
    if e.source: r["source"] = e.source
    if e.target: r["target"] = e.target
    if e.payload: r["payload"] = e.payload
    if e.frequency: r["frequency"] = e.frequency
    if e.reliability: r["reliability"] = e.reliability
    return r


def _dump_resource(res: Resource) -> dict:
    r = _dump_base(res)
    r["kind"] = _enum_value(res.kind)
    if res.provider: r["provider"] = res.provider
    if res.location: r["location"] = res.location
    if res.sla: r["sla"] = res.sla
    return r


def _dump_environment(env: Environment) -> dict:
    r = _dump_base(env)
    r["kind"] = _enum_value(env.kind)
    if env.infrastructure: r["infrastructure"] = env.infrastructure
    if env.constraints: r["constraints"] = env.constraints
    if env.region: r["region"] = env.region
    return r


def _dump_quality_attribute(qa: QualityAttribute) -> dict:
    r = _dump_base(qa)
    if qa.metric: r["metric"] = qa.metric
    if qa.target: r["target"] = qa.target
    if qa.current: r["current"] = qa.current
    if qa.measurement_method: r["measurement_method"] = qa.measurement_method
    if qa.applies_to: r["applies_to"] = qa.applies_to
    return r


def _dump_decision(dec: Decision) -> dict:
    r = _dump_base(dec)
    r["decision_status"] = _enum_value(dec.decision_status)
    if dec.context: r["context"] = dec.context
    if dec.options: r["options"] = dec.options
    if dec.rationale: r["rationale"] = dec.rationale
    if dec.consequences: r["consequences"] = dec.consequences
    if dec.supersedes: r["supersedes"] = dec.supersedes
    return r


def _dump_lifecycle(lc: Lifecycle) -> dict:
    r = _dump_base(lc)
    r["phase"] = _enum_value(lc.phase)
    if lc.version: r["version"] = lc.version
    if lc.start_date: r["start_date"] = lc.start_date
    if lc.end_date: r["end_date"] = lc.end_date
    if lc.migration_from: r["migration_from"] = lc.migration_from
    if lc.migration_to: r["migration_to"] = lc.migration_to
    if lc.milestones: r["milestones"] = lc.milestones
    return r


def _dump_requirement(req: Requirement) -> dict:
    r = _dump_base(req)
    if req.text: r["text"] = req.text
    if req.source_doc: r["source_doc"] = req.source_doc
    if req.source_anchor: r["source_anchor"] = req.source_anchor
    if req.content_hash: r["content_hash"] = req.content_hash
    if req.rationale: r["rationale"] = req.rationale
    if req.priority: r["priority"] = req.priority
    if req.moe: r["moe"] = req.moe
    if req.value_function: r["value_function"] = req.value_function
    if req.moes: r["moes"] = req.moes
    if req.failure_modes: r["failure_modes"] = req.failure_modes
    if req.monitored: r["monitored"] = req.monitored
    return r


def _dump_external_system(es: ExternalSystem) -> dict:
    r = _dump_base(es)
    if es.url: r["url"] = es.url
    if es.auth_method: r["auth_method"] = es.auth_method
    if es.api_type: r["api_type"] = es.api_type
    if es.provider: r["provider"] = es.provider
    if es.sla: r["sla"] = es.sla
    return r


def _dump_relationship(r: Relationship) -> dict:
    d: dict[str, Any] = {
        "type": r.type.value,
        "from": r.from_id,
        "to": r.to_id,
    }
    if r.description:
        d["description"] = r.description
    if r.strength != Strength.MODERATE:
        d["strength"] = _enum_val(r.strength)
    if r.extensions:
        d["extensions"] = r.extensions
    if r.imports:
        d["imports"] = r.imports
    if r.import_count:
        d["import_count"] = r.import_count
    if r.weight:
        d["weight"] = r.weight
    return d
