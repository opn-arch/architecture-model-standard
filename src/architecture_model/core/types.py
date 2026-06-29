"""
Typed dataclasses for all Architecture Model entity types and relationships.

These map 1:1 with the JSON Schema in spec/schema.json.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


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
