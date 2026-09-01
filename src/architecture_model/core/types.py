"""
Typed dataclasses for all Architecture Model entity types and relationships.

These map 1:1 with the JSON Schema in spec/schema.json.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import yaml


def _enum_value(v: Any) -> str:
    """Extract string value from an enum member or return the string as-is."""
    return v.value if isinstance(v, Enum) else v


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Status(str, Enum):
    ACTIVE = "ACTIVE"
    PLANNED = "PLANNED"
    DORMANT = "DORMANT"
    DEPRECATED = "DEPRECATED"


class RelationType(str, Enum):
    """Relationship types for architecture model edges.

    Valid values:
        realizes, contains, depends-on, exposes, consumes, uses,
        traces-to, allocated-to, constrained-by,
        mounted-on, connected-at, routed-through,
        produces, subscribes-to, transforms,
        supersedes, migrates-to, triggers,
        satisfies, derives-from, verifies,
        resolves, affects.
    """

    REALIZES = "realizes"
    CONTAINS = "contains"
    DEPENDS_ON = "depends-on"
    EXPOSES = "exposes"
    CONSUMES = "consumes"
    USES = "uses"
    TRACES_TO = "traces-to"
    ALLOCATED_TO = "allocated-to"
    CONSTRAINED_BY = "constrained-by"
    # Spatial
    MOUNTED_ON = "mounted-on"
    CONNECTED_AT = "connected-at"
    ROUTED_THROUGH = "routed-through"
    # Data/Event flow
    PRODUCES = "produces"
    SUBSCRIBES_TO = "subscribes-to"
    TRANSFORMS = "transforms"
    # Lifecycle
    SUPERSEDES = "supersedes"
    MIGRATES_TO = "migrates-to"
    # Behavioral flow
    TRIGGERS = "triggers"
    # Requirements traceability
    SATISFIES = "satisfies"
    # V&V traceability
    DERIVES_FROM = "derives-from"  # Child requirement refines parent
    VERIFIES = "verifies"  # Test evidence requirement is met
    # Decision wiring
    RESOLVES = "resolves"  # Decision → Constraint (decision resolves/addresses a constraint)
    AFFECTS = "affects"  # Decision → Component (decision affects component design)

    @classmethod
    def parse(cls, value: str) -> RelationType | str:
        """Parse a relation type, accepting unknown values as plain strings."""
        try:
            return cls(value)
        except ValueError:
            return value


class ActorType(str, Enum):
    HUMAN = "human"
    SYSTEM = "system"
    EXTERNAL_SERVICE = "external-service"

    @classmethod
    def parse(cls, value: str) -> ActorType | str:
        """Parse an actor type, accepting unknown values as plain strings."""
        try:
            return cls(value)
        except ValueError:
            return value


class InterfaceType(str, Enum):
    REST = "REST"
    WEBSOCKET = "WebSocket"
    DATABASE = "database"
    FILE = "file"
    MESSAGE_QUEUE = "message-queue"
    INTERNAL = "internal"
    EXTERNAL = "external"

    @classmethod
    def parse(cls, value: str) -> InterfaceType | str:
        """Parse an interface type, accepting unknown values as plain strings."""
        try:
            return cls(value)
        except ValueError:
            return value


class ConstraintType(str, Enum):
    PERFORMANCE = "performance"
    SECURITY = "security"
    RELIABILITY = "reliability"
    SCALABILITY = "scalability"
    REGULATORY = "regulatory"
    TECHNOLOGY = "technology"
    OPERATIONAL = "operational"
    FAILURE_MODE = "failure-mode"

    @classmethod
    def parse(cls, value: str) -> ConstraintType | str:
        """Parse a constraint type, accepting unknown values as plain strings."""
        try:
            return cls(value)
        except ValueError:
            return value


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Strength(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


class ComponentKind(str, Enum):
    SERVICE = "service"
    LIBRARY = "library"
    MODULE = "module"
    DATA_MODEL = "data-model"
    DATA_STORE = "data-store"
    INFRASTRUCTURE = "infrastructure"
    FRAMEWORK = "framework"
    UI = "ui"
    PIPELINE = "pipeline"
    PACKAGE = "package"
    CLI_TOOL = "cli"

    @classmethod
    def parse(cls, value: str) -> ComponentKind | str:
        """Parse a component kind, accepting unknown values as plain strings."""
        try:
            return cls(value)
        except ValueError:
            return value


class BehaviorPattern(str, Enum):
    SEQUENTIAL = "sequential"
    EVENT_DRIVEN = "event-driven"
    STATE_MACHINE = "state-machine"
    SAGA = "saga"
    PIPELINE = "pipeline"
    PARALLEL = "parallel"

    @classmethod
    def parse(cls, value: str) -> BehaviorPattern | str:
        """Parse a behavior pattern, accepting unknown values as plain strings."""
        try:
            return cls(value)
        except ValueError:
            return value


class SymbolKind(str, Enum):
    """Kind of code symbol (language-neutral type discrimination)."""

    CLASS = "class"
    DATACLASS = "dataclass"
    EXCEPTION = "exception"
    PROTOCOL = "protocol"
    STRUCT = "struct"
    INTERFACE = "interface"
    ENUM = "enum"
    TRAIT = "trait"
    TYPE_ALIAS = "type-alias"


class EventKind(str, Enum):
    MESSAGE = "message"
    SIGNAL = "signal"
    COMMAND = "command"
    NOTIFICATION = "notification"
    ALARM = "alarm"

    @classmethod
    def parse(cls, value: str) -> EventKind | str:
        try:
            return cls(value)
        except ValueError:
            return value


class ResourceKind(str, Enum):
    DATABASE = "database"
    API = "api"
    HARDWARE = "hardware"
    STORAGE = "storage"
    COMPUTE = "compute"
    SENSOR = "sensor"
    ACTUATOR = "actuator"

    @classmethod
    def parse(cls, value: str) -> ResourceKind | str:
        try:
            return cls(value)
        except ValueError:
            return value


class EnvironmentKind(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"
    FIELD = "field"
    LABORATORY = "laboratory"

    @classmethod
    def parse(cls, value: str) -> EnvironmentKind | str:
        try:
            return cls(value)
        except ValueError:
            return value


class DecisionStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"

    @classmethod
    def parse(cls, value: str) -> DecisionStatus | str:
        try:
            return cls(value)
        except ValueError:
            return value


class LifecyclePhase(str, Enum):
    CONCEPT = "concept"
    DESIGN = "design"
    PROTOTYPE = "prototype"
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"
    MAINTENANCE = "maintenance"
    END_OF_LIFE = "end-of-life"

    @classmethod
    def parse(cls, value: str) -> LifecyclePhase | str:
        try:
            return cls(value)
        except ValueError:
            return value


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


@dataclass
class DecisionEntry:
    """A lightweight decision record embedded in any entity."""

    choice: str
    date: str = ""
    rationale: str = ""
    alternatives: list[str] = field(default_factory=list)
    context: str = ""


@dataclass
class BaseEntity:
    id: str
    name: str
    status: Status
    description: str = ""
    tags: list[str] = field(default_factory=list)
    source_file: Optional[str] = None
    source_line: Optional[int] = None
    extensions: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    intent: str = ""
    decisions: list[DecisionEntry] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Entity Types
# ---------------------------------------------------------------------------


@dataclass
class Actor(BaseEntity):
    type: ActorType = ActorType.HUMAN
    goals: list[str] = field(default_factory=list)


@dataclass
class Capability(BaseEntity):
    source_block: str = ""
    priority: Priority = Priority.MEDIUM
    requirements: list[str] = field(default_factory=list)
    moes: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    trade_offs: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    monitored: list[str] = field(default_factory=list)


@dataclass
class StateTransition:
    """A state in a state-machine behavior."""

    name: str
    transitions: list[dict[str, str]] = field(default_factory=list)


@dataclass
class Compensation:
    """A compensation pair for saga behaviors."""

    step: str
    compensate: str


@dataclass
class Step:
    """A structured step within a behavior sequence."""

    order: int = 0
    action: str = ""  # Human-readable description
    component_ref: str = ""  # Component ID that performs this step
    actor: str = ""  # Who initiates (system, user, external)
    input: str = ""  # What goes in
    output: str = ""  # What comes out
    error_handling: str = ""  # What happens on failure


@dataclass
class Behavior(BaseEntity):
    trigger: str = ""
    actor: str = ""
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    frequency: str = ""
    priority: Priority = Priority.MEDIUM
    pattern: BehaviorPattern = BehaviorPattern.SEQUENTIAL
    states: list[StateTransition] = field(default_factory=list)
    compensations: list[Compensation] = field(default_factory=list)
    structured_steps: list[Step] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    moes: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)


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
    schema: str = ""
    contract: str = ""


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
class Symbol:
    """A code-level type definition within a component (language-neutral)."""

    name: str
    kind: SymbolKind = SymbolKind.CLASS
    members: list[str] = field(default_factory=list)
    supers: list[str] = field(default_factory=list)


@dataclass
class DataField:
    """Schema field for data-model components."""

    name: str
    type: str = "string"
    required: bool = False
    description: str = ""


@dataclass
class Constant:
    """A named constant value within a component (e.g., BLACK=30)."""

    name: str
    value: str
    context: str = ""
    type: Optional[str] = None


@dataclass
class FunctionSignature:
    """Full function signature with params, return type, and decorators."""

    name: str
    params: list[str] = field(default_factory=list)
    returns: str = ""
    decorators: list[str] = field(default_factory=list)
    body_hint: str = ""
    complexity: Optional[str] = None  # TRIVIAL, SHORT, COMPLEX
    id: str = ""


@dataclass
class TestContract:
    """A behavioral spec derived from test assertions."""

    test_file: str
    test_method: str
    assertion: str
    contract_type: str = ""
    required_imports: list[str] = field(default_factory=list)


@dataclass
class ObservabilityContract:
    """Declares expected logging/metrics behavior for a function."""

    function: str
    log_level: str  # DEBUG, INFO, WARNING, ERROR
    emits_metric: Optional[str] = None
    on_error: str = "ERROR"
    on_success: Optional[str] = None


@dataclass
class ComponentInterface:
    """An interface contract that a component exposes or consumes.

    Captures what a component provides to (or requires from) other components.
    Used to generate cross-dependency stubs during regeneration.
    """

    name: str  # e.g. "authenticate", "get_user"
    kind: str = "provides"  # provides | requires
    target_component: str = ""  # ID of the other component (for 'requires')
    signature: str = ""  # e.g. "(token: str) -> User"
    symbols: list[str] = field(default_factory=list)  # specific symbols involved


@dataclass
class Component(BaseEntity):
    layer: str = ""
    source_block: str = ""
    technology: str = ""
    files: list[str] = field(default_factory=list)
    responsibilities: list[str] = field(default_factory=list)
    kind: ComponentKind = ComponentKind.SERVICE
    fields: list[DataField] = field(default_factory=list)
    region: str = ""
    pattern: str = ""
    contract: str = ""
    replicas: Optional[int] = None
    symbols: list[Symbol] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    constants: list[Constant] = field(default_factory=list)
    signatures: list[FunctionSignature] = field(default_factory=list)
    test_contracts: list[TestContract] = field(default_factory=list)
    observability: list[ObservabilityContract] = field(default_factory=list)
    interfaces: list[ComponentInterface] = field(default_factory=list)
    technology_stack: list[str] = field(default_factory=list)
    operations: dict[str, Any] = field(default_factory=dict)
    external_dependencies: list[dict[str, Any]] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    moes: list[str] = field(default_factory=list)
    trade_offs: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    monitored: list[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    children: list[str] = field(default_factory=list)


@dataclass
class ExternalSystem(BaseEntity):
    """An external API or system that this architecture integrates with."""

    url: str = ""
    auth_method: str = ""
    api_type: str = ""  # REST, GraphQL, SOAP, gRPC, etc.
    provider: str = ""
    sla: str = ""


@dataclass
class System(BaseEntity):
    """A system-level entity that aggregates components into a logical subsystem."""

    layer: str = ""
    source_block: str = ""
    complexity_score: float = 0.0
    sub_model_ref: str = ""
    component_ids: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    trade_offs: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    monitored: list[str] = field(default_factory=list)


@dataclass
class Data(BaseEntity):
    """A data structure, schema, domain object, or BOM."""

    schema_def: str = ""
    format: str = ""
    fields: list[DataField] = field(default_factory=list)
    owner: str = ""
    sensitivity: str = ""


@dataclass
class Event(BaseEntity):
    """A discrete event, signal, or message that flows between components."""

    kind: EventKind = EventKind.MESSAGE
    source: str = ""
    target: str = ""
    payload: str = ""
    frequency: str = ""
    reliability: str = ""


@dataclass
class Resource(BaseEntity):
    """An external dependency the system uses but doesn't own."""

    kind: ResourceKind = ResourceKind.DATABASE
    provider: str = ""
    location: str = ""
    sla: str = ""


@dataclass
class Environment(BaseEntity):
    """A deployment target or physical context where the system runs."""

    kind: EnvironmentKind = EnvironmentKind.PRODUCTION
    infrastructure: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    region: str = ""


@dataclass
class QualityAttribute(BaseEntity):
    """A measured quality property of the system."""

    metric: str = ""
    target: str = ""
    current: str = ""
    measurement_method: str = ""
    applies_to: list[str] = field(default_factory=list)


@dataclass
class Decision(BaseEntity):
    """An Architecture Decision Record (ADR)."""

    decision_status: DecisionStatus = DecisionStatus.ACCEPTED
    context: str = ""
    options: list[str] = field(default_factory=list)
    rationale: str = ""
    consequences: list[str] = field(default_factory=list)
    supersedes: str = ""


@dataclass
class Lifecycle(BaseEntity):
    """A version, phase, or migration path."""

    phase: LifecyclePhase = LifecyclePhase.PRODUCTION
    version: str = ""
    start_date: str = ""
    end_date: str = ""
    migration_from: str = ""
    migration_to: str = ""
    milestones: list[str] = field(default_factory=list)


@dataclass
class Requirement(BaseEntity):
    """A traceable requirement."""

    text: str = ""
    source_doc: str = ""
    source_anchor: str = ""
    content_hash: str = ""
    rationale: str = ""
    priority: str = ""
    moe: str = ""
    value_function: str = ""
    moes: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    monitored: list[str] = field(default_factory=list)


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
    import_count: int = 0  # Actual import edge count from AST (0 = unquantified)
    weight: float = 0.0  # Numeric coupling weight (0.0 = unquantified)
    extensions: dict[str, Any] = field(default_factory=dict)
    imports: list[str] = field(default_factory=list)


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
    source_language: str = ""
    domain_profile: str = "software"
    manifest_path: str = ""
    lifecycle_phase: str = "production"  # "concept" or "production"
    parent_model: str | None = None
    refines_component: str | None = None


@dataclass
class Entities:
    actors: list[Actor] = field(default_factory=list)
    capabilities: list[Capability] = field(default_factory=list)
    behaviors: list[Behavior] = field(default_factory=list)
    interfaces: list[Interface] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)
    layers: list[Layer] = field(default_factory=list)
    components: list[Component] = field(default_factory=list)
    systems: list[System] = field(default_factory=list)
    data: list[Data] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    resources: list[Resource] = field(default_factory=list)
    environments: list[Environment] = field(default_factory=list)
    quality_attributes: list[QualityAttribute] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    lifecycles: list[Lifecycle] = field(default_factory=list)
    requirements: list[Requirement] = field(default_factory=list)
    external_systems: list[ExternalSystem] = field(default_factory=list)


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
        for sys in self.entities.systems:
            ids.add(sys.id)
        for d in self.entities.data:
            ids.add(d.id)
        for e in self.entities.events:
            ids.add(e.id)
        for r in self.entities.resources:
            ids.add(r.id)
        for e in self.entities.environments:
            ids.add(e.id)
        for qa in self.entities.quality_attributes:
            ids.add(qa.id)
        for d in self.entities.decisions:
            ids.add(d.id)
        for lc in self.entities.lifecycles:
            ids.add(lc.id)
        for req in self.entities.requirements:
            ids.add(req.id)
        for es in self.entities.external_systems:
            ids.add(es.id)
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
        if self.meta.source_language:
            d["source_language"] = self.meta.source_language
        if self.meta.domain_profile and self.meta.domain_profile != "software":
            d["domain_profile"] = self.meta.domain_profile
        if self.meta.lifecycle_phase != "production":
            d["lifecycle_phase"] = self.meta.lifecycle_phase
        if self.meta.manifest_path:
            d["manifest_path"] = self.meta.manifest_path
        if self.meta.parent_model:
            d["parent_model"] = self.meta.parent_model
        if self.meta.refines_component:
            d["refines_component"] = self.meta.refines_component
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
        if self.entities.systems:
            d["systems"] = [self._dump_system(s) for s in self.entities.systems]
        if self.entities.data:
            d["data"] = [self._dump_data(x) for x in self.entities.data]
        if self.entities.events:
            d["events"] = [self._dump_event(x) for x in self.entities.events]
        if self.entities.resources:
            d["resources"] = [self._dump_resource(x) for x in self.entities.resources]
        if self.entities.environments:
            d["environments"] = [self._dump_environment(x) for x in self.entities.environments]
        if self.entities.quality_attributes:
            d["quality_attributes"] = [
                self._dump_quality_attribute(x) for x in self.entities.quality_attributes
            ]
        if self.entities.decisions:
            d["decisions"] = [self._dump_decision(x) for x in self.entities.decisions]
        if self.entities.lifecycles:
            d["lifecycles"] = [self._dump_lifecycle(x) for x in self.entities.lifecycles]
        if self.entities.requirements:
            d["requirements"] = [self._dump_requirement(x) for x in self.entities.requirements]
        if self.entities.external_systems:
            d["external_systems"] = [
                self._dump_external_system(x) for x in self.entities.external_systems
            ]
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
        if entity.extensions:
            d["extensions"] = entity.extensions
        if entity.intent:
            d["intent"] = entity.intent
        if entity.decisions:
            d["decisions"] = [
                {
                    key: value
                    for key, value in {
                        "choice": decision.choice,
                        "date": decision.date,
                        "rationale": decision.rationale,
                        "alternatives": decision.alternatives,
                        "context": decision.context,
                    }.items()
                    if value
                }
                for decision in entity.decisions
            ]
        return d

    @classmethod
    def _dump_actor(cls, a: Actor) -> dict[str, Any]:
        d = cls._dump_base(a)
        d["type"] = _enum_value(a.type)
        if a.goals:
            d["goals"] = a.goals
        return d

    @classmethod
    def _dump_capability(cls, c: Capability) -> dict[str, Any]:
        d = cls._dump_base(c)
        if c.source_block:
            d["source_block"] = c.source_block
        if c.priority != Priority.MEDIUM:
            d["priority"] = c.priority.value
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
        if b.pattern != BehaviorPattern.SEQUENTIAL:
            d["pattern"] = _enum_value(b.pattern)
        if b.states:
            d["states"] = [{"name": s.name, "transitions": s.transitions} for s in b.states]
        if b.compensations:
            d["compensations"] = [
                {"step": c.step, "compensate": c.compensate} for c in b.compensations
            ]
        if b.structured_steps:
            d["structured_steps"] = [
                {
                    key: value
                    for key, value in {
                        "order": step.order,
                        "action": step.action,
                        "component_ref": step.component_ref,
                        "actor": step.actor,
                        "input": step.input,
                        "output": step.output,
                        "error_handling": step.error_handling,
                    }.items()
                    if value
                }
                for step in b.structured_steps
            ]
        if b.goals:
            d["goals"] = b.goals
        if b.moes:
            d["moes"] = b.moes
        if b.failure_modes:
            d["failure_modes"] = b.failure_modes
        return d

    @classmethod
    def _dump_interface(cls, i: Interface) -> dict[str, Any]:
        d = cls._dump_base(i)
        d["type"] = _enum_value(i.type)
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

    @classmethod
    def _dump_constraint(cls, c: Constraint) -> dict[str, Any]:
        d = cls._dump_base(c)
        d["type"] = _enum_value(c.type)
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
        if c.source_block:
            d["source_block"] = c.source_block
        if c.technology:
            d["technology"] = c.technology
        if c.files:
            d["files"] = c.files
        if c.responsibilities:
            d["responsibilities"] = c.responsibilities
        if c.kind != ComponentKind.SERVICE:
            d["kind"] = _enum_value(c.kind)
        if c.fields:
            d["fields"] = [
                {"name": f.name, "type": f.type, "required": f.required}
                | ({"description": f.description} if f.description else {})
                for f in c.fields
            ]
        if c.region:
            d["region"] = c.region
        if c.pattern:
            d["pattern"] = c.pattern
        if c.contract:
            d["contract"] = c.contract
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
                for cn in c.constants
            ]
        if c.signatures:
            d["signatures"] = [
                {"name": sig.name}
                | ({"params": sig.params} if sig.params else {})
                | ({"returns": sig.returns} if sig.returns else {})
                | ({"decorators": sig.decorators} if sig.decorators else {})
                | ({"body_hint": sig.body_hint} if sig.body_hint else {})
                for sig in c.signatures
            ]
        if c.test_contracts:
            d["test_contracts"] = [
                {
                    "test_file": tc.test_file,
                    "test_method": tc.test_method,
                    "assertion": tc.assertion,
                }
                | ({"contract_type": tc.contract_type} if tc.contract_type else {})
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
        if c.technology_stack:
            d["technology_stack"] = c.technology_stack
        if c.operations:
            d["operations"] = c.operations
        if c.external_dependencies:
            d["external_dependencies"] = c.external_dependencies
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

    @classmethod
    def _dump_system(cls, s: "System") -> dict[str, Any]:
        d = cls._dump_base(s)
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

    @classmethod
    def _dump_data(cls, d_ent: "Data") -> dict[str, Any]:
        d = cls._dump_base(d_ent)
        if d_ent.schema_def:
            d["schema_def"] = d_ent.schema_def
        if d_ent.format:
            d["format"] = d_ent.format
        if d_ent.fields:
            d["fields"] = [
                {"name": f.name, "type": f.type, "required": f.required}
                | ({"description": f.description} if f.description else {})
                for f in d_ent.fields
            ]
        if d_ent.owner:
            d["owner"] = d_ent.owner
        if d_ent.sensitivity:
            d["sensitivity"] = d_ent.sensitivity
        return d

    @classmethod
    def _dump_event(cls, e: "Event") -> dict[str, Any]:
        d = cls._dump_base(e)
        d["kind"] = _enum_value(e.kind)
        if e.source:
            d["source"] = e.source
        if e.target:
            d["target"] = e.target
        if e.payload:
            d["payload"] = e.payload
        if e.frequency:
            d["frequency"] = e.frequency
        if e.reliability:
            d["reliability"] = e.reliability
        return d

    @classmethod
    def _dump_resource(cls, res: "Resource") -> dict[str, Any]:
        d = cls._dump_base(res)
        d["kind"] = _enum_value(res.kind)
        if res.provider:
            d["provider"] = res.provider
        if res.location:
            d["location"] = res.location
        if res.sla:
            d["sla"] = res.sla
        return d

    @classmethod
    def _dump_environment(cls, env: "Environment") -> dict[str, Any]:
        d = cls._dump_base(env)
        d["kind"] = _enum_value(env.kind)
        if env.infrastructure:
            d["infrastructure"] = env.infrastructure
        if env.constraints:
            d["constraints"] = env.constraints
        if env.region:
            d["region"] = env.region
        return d

    @classmethod
    def _dump_quality_attribute(cls, qa: "QualityAttribute") -> dict[str, Any]:
        d = cls._dump_base(qa)
        if qa.metric:
            d["metric"] = qa.metric
        if qa.target:
            d["target"] = qa.target
        if qa.current:
            d["current"] = qa.current
        if qa.measurement_method:
            d["measurement_method"] = qa.measurement_method
        if qa.applies_to:
            d["applies_to"] = qa.applies_to
        return d

    @classmethod
    def _dump_decision(cls, dec: "Decision") -> dict[str, Any]:
        d = cls._dump_base(dec)
        d["decision_status"] = _enum_value(dec.decision_status)
        if dec.context:
            d["context"] = dec.context
        if dec.options:
            d["options"] = dec.options
        if dec.rationale:
            d["rationale"] = dec.rationale
        if dec.consequences:
            d["consequences"] = dec.consequences
        if dec.supersedes:
            d["supersedes"] = dec.supersedes
        return d

    @classmethod
    def _dump_lifecycle(cls, lc: "Lifecycle") -> dict[str, Any]:
        d = cls._dump_base(lc)
        d["phase"] = _enum_value(lc.phase)
        if lc.version:
            d["version"] = lc.version
        if lc.start_date:
            d["start_date"] = lc.start_date
        if lc.end_date:
            d["end_date"] = lc.end_date
        if lc.migration_from:
            d["migration_from"] = lc.migration_from
        if lc.migration_to:
            d["migration_to"] = lc.migration_to
        if lc.milestones:
            d["milestones"] = lc.milestones
        return d

    @classmethod
    def _dump_requirement(cls, req: "Requirement") -> dict[str, Any]:
        d = cls._dump_base(req)
        if req.text:
            d["text"] = req.text
        if req.source_doc:
            d["source_doc"] = req.source_doc
        if req.source_anchor:
            d["source_anchor"] = req.source_anchor
        if req.content_hash:
            d["content_hash"] = req.content_hash
        if req.rationale:
            d["rationale"] = req.rationale
        if req.priority:
            d["priority"] = req.priority
        if req.moe:
            d["moe"] = req.moe
        if req.value_function:
            d["value_function"] = req.value_function
        if req.moes:
            d["moes"] = req.moes
        if req.failure_modes:
            d["failure_modes"] = req.failure_modes
        if req.monitored:
            d["monitored"] = req.monitored
        return d

    @classmethod
    def _dump_external_system(cls, es: "ExternalSystem") -> dict[str, Any]:
        d = cls._dump_base(es)
        if es.url:
            d["url"] = es.url
        if es.auth_method:
            d["auth_method"] = es.auth_method
        if es.api_type:
            d["api_type"] = es.api_type
        if es.provider:
            d["provider"] = es.provider
        if es.sla:
            d["sla"] = es.sla
        return d

    @staticmethod
    def _dump_relationship(r: Relationship) -> dict[str, Any]:
        d: dict[str, Any] = {
            "type": _enum_value(r.type),
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
        if r.import_count:
            d["import_count"] = r.import_count
        if r.weight:
            d["weight"] = r.weight
        return d
