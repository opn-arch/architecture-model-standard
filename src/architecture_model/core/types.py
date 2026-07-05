"""
Typed dataclasses for all Architecture Model entity types and relationships.

These map 1:1 with the JSON Schema in spec/schema.json.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import yaml


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Status(str, Enum):
    ACTIVE = "ACTIVE"
    PLANNED = "PLANNED"
    DORMANT = "DORMANT"
    DEPRECATED = "DEPRECATED"


class RelationType(str, Enum):
    REALIZES = "realizes"
    CONTAINS = "contains"
    DEPENDS_ON = "depends-on"
    EXPOSES = "exposes"
    CONSUMES = "consumes"
    TRACES_TO = "traces-to"
    ALLOCATED_TO = "allocated-to"
    CONSTRAINED_BY = "constrained-by"


class ActorType(str, Enum):
    HUMAN = "human"
    SYSTEM = "system"
    EXTERNAL_SERVICE = "external-service"


class InterfaceType(str, Enum):
    REST = "REST"
    WEBSOCKET = "WebSocket"
    DATABASE = "database"
    FILE = "file"
    MESSAGE_QUEUE = "message-queue"
    INTERNAL = "internal"
    EXTERNAL = "external"


class ConstraintType(str, Enum):
    PERFORMANCE = "performance"
    SECURITY = "security"
    RELIABILITY = "reliability"
    SCALABILITY = "scalability"
    REGULATORY = "regulatory"
    TECHNOLOGY = "technology"
    OPERATIONAL = "operational"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Strength(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


@dataclass
class BaseEntity:
    id: str
    name: str
    status: Status
    description: str = ""
    tags: list[str] = field(default_factory=list)
    source_file: Optional[str] = None
    source_line: Optional[int] = None


# ---------------------------------------------------------------------------
# Entity Types
# ---------------------------------------------------------------------------


@dataclass
class Actor(BaseEntity):
    type: ActorType = ActorType.HUMAN
    goals: list[str] = field(default_factory=list)


@dataclass
class Capability(BaseEntity):
    f_block: str = ""
    priority: Priority = Priority.MEDIUM
    requirements: list[str] = field(default_factory=list)


@dataclass
class Behavior(BaseEntity):
    trigger: str = ""
    actor: str = ""
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    frequency: str = ""
    priority: Priority = Priority.MEDIUM


@dataclass
class Endpoint(BaseEntity):
    """Simplified — not a full entity, just a sub-structure of Interface."""

    method: str = ""
    path: str = ""


@dataclass
class Interface(BaseEntity):
    type: InterfaceType = InterfaceType.INTERNAL
    protocol: str = ""
    provider: str = ""
    consumer: str = ""
    data_format: str = ""
    endpoints: list[dict] = field(default_factory=list)


@dataclass
class Constraint(BaseEntity):
    type: ConstraintType = ConstraintType.TECHNOLOGY
    metric: str = ""
    threshold: str = ""
    rationale: str = ""


@dataclass
class Layer(BaseEntity):
    order: int = 0
    technology: list[str] = field(default_factory=list)
    directories: list[str] = field(default_factory=list)


@dataclass
class Component(BaseEntity):
    layer: str = ""
    f_block: str = ""
    technology: str = ""
    files: list[str] = field(default_factory=list)
    responsibilities: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------


@dataclass
class Relationship:
    type: RelationType
    from_id: str  # 'from' is reserved in Python
    to_id: str  # 'to' kept as to_id for symmetry
    description: str = ""
    strength: Strength = Strength.MODERATE


# ---------------------------------------------------------------------------
# Top-level Model
# ---------------------------------------------------------------------------


@dataclass
class ModelMeta:
    schema_version: str
    project: str
    system: str = ""
    generated_at: str = ""
    source_artifacts: list[str] = field(default_factory=list)
    manifest_hash: str = ""


@dataclass
class Entities:
    actors: list[Actor] = field(default_factory=list)
    capabilities: list[Capability] = field(default_factory=list)
    behaviors: list[Behavior] = field(default_factory=list)
    interfaces: list[Interface] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)
    layers: list[Layer] = field(default_factory=list)
    components: list[Component] = field(default_factory=list)


@dataclass
class ArchitectureModel:
    meta: ModelMeta
    entities: Entities
    relationships: list[Relationship] = field(default_factory=list)

    @property
    def all_entity_ids(self) -> set[str]:
        """Return set of all entity IDs across all types."""
        ids: set[str] = set()
        for actor in self.entities.actors:
            ids.add(actor.id)
        for cap in self.entities.capabilities:
            ids.add(cap.id)
        for beh in self.entities.behaviors:
            ids.add(beh.id)
        for iface in self.entities.interfaces:
            ids.add(iface.id)
        for con in self.entities.constraints:
            ids.add(con.id)
        for layer in self.entities.layers:
            ids.add(layer.id)
        for comp in self.entities.components:
            ids.add(comp.id)
        return ids

    @property
    def entity_count(self) -> int:
        return len(self.all_entity_ids)

    @property
    def relationship_count(self) -> int:
        return len(self.relationships)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the model to a plain dict suitable for YAML output.

        Produces output compatible with _parse_raw() for round-trip fidelity.
        Enum values are serialized as their string values. Empty optional fields
        are omitted for cleanliness.
        """
        return {
            "meta": self._dump_meta(),
            "entities": self._dump_entities(),
            "relationships": [self._dump_relationship(r) for r in self.relationships],
        }

    def to_yaml(self) -> str:
        """Serialize the model to a YAML string."""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    # -- Private serialization helpers --

    def _dump_meta(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "schema_version": self.meta.schema_version,
            "project": self.meta.project,
        }
        if self.meta.system:
            d["system"] = self.meta.system
        d["generated_at"] = self.meta.generated_at
        if self.meta.source_artifacts:
            d["source_artifacts"] = self.meta.source_artifacts
        if self.meta.manifest_hash:
            d["manifest_hash"] = self.meta.manifest_hash
        return d

    def _dump_entities(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.entities.actors:
            d["actors"] = [self._dump_actor(a) for a in self.entities.actors]
        if self.entities.capabilities:
            d["capabilities"] = [self._dump_capability(c) for c in self.entities.capabilities]
        if self.entities.behaviors:
            d["behaviors"] = [self._dump_behavior(b) for b in self.entities.behaviors]
        if self.entities.interfaces:
            d["interfaces"] = [self._dump_interface(i) for i in self.entities.interfaces]
        if self.entities.constraints:
            d["constraints"] = [self._dump_constraint(c) for c in self.entities.constraints]
        if self.entities.layers:
            d["layers"] = [self._dump_layer(l) for l in self.entities.layers]
        if self.entities.components:
            d["components"] = [self._dump_component(c) for c in self.entities.components]
        return d

    @staticmethod
    def _dump_base(entity: BaseEntity) -> dict[str, Any]:
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
        return d

    @classmethod
    def _dump_actor(cls, a: Actor) -> dict[str, Any]:
        d = cls._dump_base(a)
        d["type"] = a.type.value
        if a.goals:
            d["goals"] = a.goals
        return d

    @classmethod
    def _dump_capability(cls, c: Capability) -> dict[str, Any]:
        d = cls._dump_base(c)
        if c.f_block:
            d["f_block"] = c.f_block
        if c.priority != Priority.MEDIUM:
            d["priority"] = c.priority.value
        if c.requirements:
            d["requirements"] = c.requirements
        return d

    @classmethod
    def _dump_behavior(cls, b: Behavior) -> dict[str, Any]:
        d = cls._dump_base(b)
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
        return d

    @classmethod
    def _dump_interface(cls, i: Interface) -> dict[str, Any]:
        d = cls._dump_base(i)
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
        return d

    @classmethod
    def _dump_constraint(cls, c: Constraint) -> dict[str, Any]:
        d = cls._dump_base(c)
        d["type"] = c.type.value
        if c.metric:
            d["metric"] = c.metric
        if c.threshold:
            d["threshold"] = c.threshold
        if c.rationale:
            d["rationale"] = c.rationale
        return d

    @classmethod
    def _dump_layer(cls, l: Layer) -> dict[str, Any]:
        d = cls._dump_base(l)
        d["order"] = l.order
        if l.technology:
            d["technology"] = l.technology
        if l.directories:
            d["directories"] = l.directories
        return d

    @classmethod
    def _dump_component(cls, c: Component) -> dict[str, Any]:
        d = cls._dump_base(c)
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
        return d

    @staticmethod
    def _dump_relationship(r: Relationship) -> dict[str, Any]:
        d: dict[str, Any] = {
            "type": r.type.value,
            "from": r.from_id,
            "to": r.to_id,
        }
        if r.description:
            d["description"] = r.description
        if r.strength != Strength.MODERATE:
            d["strength"] = r.strength.value
        return d
