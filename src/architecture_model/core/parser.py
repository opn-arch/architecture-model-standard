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
    Constraint,
    ConstraintType,
    DataField,
    Entities,
    Interface,
    InterfaceType,
    Layer,
    ModelMeta,
    Priority,
    Relationship,
    RelationType,
    StateTransition,
    Status,
    Strength,
    Symbol,
    SymbolKind,
)

SCHEMA_PATH = Path(__file__).parent.parent / "spec" / "schema.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_model(path: str | Path) -> ArchitectureModel:
    """Load and parse an architecture model YAML file."""
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ValueError(f"Empty model file: {path}")

    return _parse_raw(raw)


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
    )


def _parse_entities(d: dict) -> Entities:
    return Entities(
        actors=[_parse_actor(a) for a in d.get("actors", [])],
        capabilities=[_parse_capability(c) for c in d.get("capabilities", [])],
        behaviors=[_parse_behavior(b) for b in d.get("behaviors", [])],
        interfaces=[_parse_interface(i) for i in d.get("interfaces", [])],
        constraints=[_parse_constraint(c) for c in d.get("constraints", [])],
        layers=[_parse_layer(l) for l in d.get("layers", [])],
        components=[_parse_component(c) for c in d.get("components", [])],
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
    }


def _parse_actor(d: dict) -> Actor:
    base = _parse_base(d)
    return Actor(
        **base,
        type=ActorType(d.get("type", "human")),
        goals=d.get("goals", []),
    )


def _parse_capability(d: dict) -> Capability:
    base = _parse_base(d)
    return Capability(
        **base,
        f_block=d.get("f_block", ""),
        priority=_parse_priority(d.get("priority")),
        requirements=d.get("requirements", []),
    )


def _parse_behavior(d: dict) -> Behavior:
    base = _parse_base(d)
    pattern_str = d.get("pattern", "sequential")
    try:
        pattern = BehaviorPattern(pattern_str)
    except ValueError:
        pattern = BehaviorPattern.SEQUENTIAL

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
    )


def _parse_interface(d: dict) -> Interface:
    base = _parse_base(d)
    return Interface(
        **base,
        type=InterfaceType(d.get("type", "internal")),
        protocol=d.get("protocol", ""),
        provider=d.get("provider", ""),
        consumer=d.get("consumer", ""),
        data_format=d.get("data_format", ""),
        endpoints=d.get("endpoints", []),
        schema=d.get("schema", ""),
    )


def _parse_constraint(d: dict) -> Constraint:
    base = _parse_base(d)
    return Constraint(
        **base,
        type=ConstraintType(d.get("type", "technology")),
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
    try:
        kind = ComponentKind(kind_str)
    except ValueError:
        kind = ComponentKind.SERVICE

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

    return Component(
        **base,
        layer=d.get("layer", ""),
        f_block=d.get("f_block", ""),
        technology=d.get("technology", ""),
        files=d.get("files", []),
        responsibilities=d.get("responsibilities", []),
        kind=kind,
        fields=fields,
        region=d.get("region", ""),
        replicas=d.get("replicas"),
        symbols=symbols,
        functions=d.get("functions", []),
    )


def _parse_relationship(d: dict) -> Relationship:
    return Relationship(
        type=RelationType(d.get("type", "depends-on")),
        from_id=d.get("from", ""),
        to_id=d.get("to", ""),
        description=d.get("description", ""),
        strength=Strength(d.get("strength", "moderate")),
        extensions=d.get("extensions", {}),
        imports=d.get("imports", []),
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
    return d


def _dump_base(entity: Any) -> dict:
    d: dict[str, Any] = {
        "id": entity.id,
        "name": entity.name,
        "status": entity.status.value,
    }
    if entity.description:
        d["description"] = entity.description
    if entity.tags:
        d["tags"] = entity.tags
    if entity.source_file:
        d["source_file"] = entity.source_file
    if entity.source_line is not None:
        d["source_line"] = entity.source_line
    if entity.extensions:
        d["extensions"] = entity.extensions
    return d


def _dump_actor(a: Actor) -> dict:
    d = _dump_base(a)
    d["type"] = a.type.value
    if a.goals:
        d["goals"] = a.goals
    return d


def _dump_capability(c: Capability) -> dict:
    d = _dump_base(c)
    if c.f_block:
        d["f_block"] = c.f_block
    if c.priority != Priority.MEDIUM:
        d["priority"] = c.priority.value
    if c.requirements:
        d["requirements"] = c.requirements
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
        d["priority"] = b.priority.value
    if b.pattern != BehaviorPattern.SEQUENTIAL:
        d["pattern"] = b.pattern.value
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
    return d


def _dump_interface(i: Interface) -> dict:
    d = _dump_base(i)
    d["type"] = i.type.value
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
    return d


def _dump_constraint(c: Constraint) -> dict:
    d = _dump_base(c)
    d["type"] = c.type.value
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
    if c.f_block:
        d["f_block"] = c.f_block
    if c.technology:
        d["technology"] = c.technology
    if c.files:
        d["files"] = c.files
    if c.responsibilities:
        d["responsibilities"] = c.responsibilities
    if c.kind != ComponentKind.SERVICE:
        d["kind"] = c.kind.value
    if c.fields:
        d["fields"] = [
            {"name": f.name, "type": f.type, "required": f.required}
            | ({"description": f.description} if f.description else {})
            for f in c.fields
        ]
    if c.region:
        d["region"] = c.region
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
    return d


def _dump_relationship(r: Relationship) -> dict:
    d: dict[str, Any] = {
        "type": r.type.value,
        "from": r.from_id,
        "to": r.to_id,
    }
    if r.description:
        d["description"] = r.description
    if r.strength != Strength.MODERATE:
        d["strength"] = r.strength.value
    if r.extensions:
        d["extensions"] = r.extensions
    if r.imports:
        d["imports"] = r.imports
    return d
