"""Tests for Schema v1.1 extensions: kind, pattern, extensions, schema."""

import pytest
from architecture_model.core.types import (
    Actor, ActorType, Behavior, BehaviorPattern, Capability, Compensation,
    Component, ComponentKind, Constraint, ConstraintType, DataField,
    Entities, Interface, InterfaceType, Layer, ModelMeta, Priority,
    Relationship, RelationType, StateTransition, Status, Strength,
    ArchitectureModel,
)


class TestEnums:
    def test_component_kind_values(self):
        assert ComponentKind.SERVICE.value == "service"
        assert ComponentKind.LIBRARY.value == "library"
        assert ComponentKind.DATA_MODEL.value == "data-model"
        assert ComponentKind.DATA_STORE.value == "data-store"
        assert ComponentKind.INFRASTRUCTURE.value == "infrastructure"
        assert ComponentKind.FRAMEWORK.value == "framework"
        assert ComponentKind.UI.value == "ui"
        assert ComponentKind.PIPELINE.value == "pipeline"

    def test_behavior_pattern_values(self):
        assert BehaviorPattern.SEQUENTIAL.value == "sequential"
        assert BehaviorPattern.EVENT_DRIVEN.value == "event-driven"
        assert BehaviorPattern.STATE_MACHINE.value == "state-machine"
        assert BehaviorPattern.SAGA.value == "saga"
        assert BehaviorPattern.PIPELINE.value == "pipeline"
        assert BehaviorPattern.PARALLEL.value == "parallel"


class TestExtensions:
    def test_base_entity_has_extensions_field(self):
        comp = Component(
            id="svc-1", name="Service", status=Status.ACTIVE,
            extensions={"x-team": "platform", "x-sla": "gold"},
        )
        assert comp.extensions == {"x-team": "platform", "x-sla": "gold"}

    def test_base_entity_extensions_default_empty(self):
        comp = Component(id="svc-1", name="Service", status=Status.ACTIVE)
        assert comp.extensions == {}

    def test_relationship_has_extensions_field(self):
        rel = Relationship(
            type=RelationType.DEPENDS_ON,
            from_id="a", to_id="b",
            extensions={"x-latency-budget": "50ms"},
        )
        assert rel.extensions == {"x-latency-budget": "50ms"}

    def test_relationship_extensions_default_empty(self):
        rel = Relationship(type=RelationType.DEPENDS_ON, from_id="a", to_id="b")
        assert rel.extensions == {}


class TestComponentKind:
    def test_component_kind_field(self):
        comp = Component(
            id="user-schema", name="User Schema", status=Status.ACTIVE,
            kind=ComponentKind.DATA_MODEL,
        )
        assert comp.kind == ComponentKind.DATA_MODEL

    def test_component_kind_default_service(self):
        comp = Component(id="svc-1", name="Service", status=Status.ACTIVE)
        assert comp.kind == ComponentKind.SERVICE

    def test_component_data_model_with_fields(self):
        comp = Component(
            id="user-schema", name="User Schema", status=Status.ACTIVE,
            kind=ComponentKind.DATA_MODEL,
            fields=[
                DataField(name="id", type="integer", required=True),
                DataField(name="email", type="string", required=True),
                DataField(name="created_at", type="datetime", required=False),
            ],
        )
        assert len(comp.fields) == 3
        assert comp.fields[0].name == "id"
        assert comp.fields[0].required is True

    def test_component_infrastructure_fields(self):
        comp = Component(
            id="prod-k8s", name="Production Cluster", status=Status.ACTIVE,
            kind=ComponentKind.INFRASTRUCTURE,
            region="us-east-1",
            replicas=3,
        )
        assert comp.region == "us-east-1"
        assert comp.replicas == 3

    def test_component_fields_default_empty(self):
        comp = Component(id="svc-1", name="Service", status=Status.ACTIVE)
        assert comp.fields == []
        assert comp.region == ""
        assert comp.replicas is None


class TestBehaviorPattern:
    def test_behavior_pattern_field(self):
        beh = Behavior(
            id="order-flow", name="Order Flow", status=Status.ACTIVE,
            pattern=BehaviorPattern.SAGA,
        )
        assert beh.pattern == BehaviorPattern.SAGA

    def test_behavior_pattern_default_sequential(self):
        beh = Behavior(id="b-1", name="Simple", status=Status.ACTIVE)
        assert beh.pattern == BehaviorPattern.SEQUENTIAL

    def test_behavior_state_machine(self):
        beh = Behavior(
            id="session-lifecycle", name="Session Lifecycle", status=Status.ACTIVE,
            pattern=BehaviorPattern.STATE_MACHINE,
            states=[
                StateTransition(name="created", transitions=[{"to": "active", "trigger": "login"}]),
                StateTransition(name="active", transitions=[{"to": "expired", "trigger": "timeout"}, {"to": "terminated", "trigger": "logout"}]),
                StateTransition(name="expired", transitions=[]),
                StateTransition(name="terminated", transitions=[]),
            ],
        )
        assert len(beh.states) == 4
        assert beh.states[0].name == "created"
        assert beh.states[1].transitions[0]["to"] == "expired"

    def test_behavior_saga_compensations(self):
        beh = Behavior(
            id="order-saga", name="Order Saga", status=Status.ACTIVE,
            pattern=BehaviorPattern.SAGA,
            compensations=[
                Compensation(step="Reserve inventory", compensate="Release inventory"),
                Compensation(step="Charge payment", compensate="Refund payment"),
            ],
        )
        assert len(beh.compensations) == 2
        assert beh.compensations[0].step == "Reserve inventory"

    def test_behavior_states_default_empty(self):
        beh = Behavior(id="b-1", name="Simple", status=Status.ACTIVE)
        assert beh.states == []
        assert beh.compensations == []


class TestInterfaceSchema:
    def test_interface_schema_field(self):
        iface = Interface(
            id="user-api", name="User API", status=Status.ACTIVE,
            type=InterfaceType.REST,
            schema="user-schema",
        )
        assert iface.schema == "user-schema"

    def test_interface_schema_default_empty(self):
        iface = Interface(id="i-1", name="Internal", status=Status.ACTIVE)
        assert iface.schema == ""


class TestParserV11:
    def test_parse_component_with_kind(self):
        from architecture_model.core.parser import _parse_raw
        raw = {
            "meta": {"schema_version": "1.1", "project": "test", "generated_at": "2026-01-01T00:00:00Z"},
            "entities": {"components": [{"id": "user-schema", "name": "User Schema", "status": "ACTIVE", "kind": "data-model", "fields": [{"name": "id", "type": "integer", "required": True}, {"name": "email", "type": "string"}]}]},
            "relationships": [],
        }
        model = _parse_raw(raw)
        comp = model.entities.components[0]
        assert comp.kind == ComponentKind.DATA_MODEL
        assert len(comp.fields) == 2
        assert comp.fields[0].required is True
        assert comp.fields[1].required is False

    def test_parse_component_kind_defaults_to_service(self):
        from architecture_model.core.parser import _parse_raw
        raw = {"meta": {"schema_version": "1.0", "project": "test", "generated_at": "2026-01-01T00:00:00Z"}, "entities": {"components": [{"id": "svc", "name": "Svc", "status": "ACTIVE"}]}, "relationships": []}
        model = _parse_raw(raw)
        assert model.entities.components[0].kind == ComponentKind.SERVICE

    def test_parse_behavior_with_pattern_and_states(self):
        from architecture_model.core.parser import _parse_raw
        raw = {"meta": {"schema_version": "1.1", "project": "test", "generated_at": "2026-01-01T00:00:00Z"}, "entities": {"behaviors": [{"id": "session", "name": "Session", "status": "ACTIVE", "pattern": "state-machine", "states": [{"name": "created", "transitions": [{"to": "active", "trigger": "login"}]}, {"name": "active", "transitions": []}]}]}, "relationships": []}
        model = _parse_raw(raw)
        beh = model.entities.behaviors[0]
        assert beh.pattern == BehaviorPattern.STATE_MACHINE
        assert len(beh.states) == 2

    def test_parse_behavior_with_compensations(self):
        from architecture_model.core.parser import _parse_raw
        raw = {"meta": {"schema_version": "1.1", "project": "test", "generated_at": "2026-01-01T00:00:00Z"}, "entities": {"behaviors": [{"id": "saga", "name": "Saga", "status": "ACTIVE", "pattern": "saga", "compensations": [{"step": "Reserve", "compensate": "Release"}]}]}, "relationships": []}
        model = _parse_raw(raw)
        assert model.entities.behaviors[0].compensations[0].step == "Reserve"

    def test_parse_interface_with_schema(self):
        from architecture_model.core.parser import _parse_raw
        raw = {"meta": {"schema_version": "1.1", "project": "test", "generated_at": "2026-01-01T00:00:00Z"}, "entities": {"interfaces": [{"id": "api", "name": "API", "status": "ACTIVE", "type": "REST", "schema": "user-schema"}]}, "relationships": []}
        model = _parse_raw(raw)
        assert model.entities.interfaces[0].schema == "user-schema"

    def test_parse_extensions(self):
        from architecture_model.core.parser import _parse_raw
        raw = {"meta": {"schema_version": "1.1", "project": "test", "generated_at": "2026-01-01T00:00:00Z"}, "entities": {"components": [{"id": "svc", "name": "Svc", "status": "ACTIVE", "extensions": {"x-team": "platform"}}]}, "relationships": [{"type": "depends-on", "from": "a", "to": "b", "extensions": {"x-latency": "50ms"}}]}
        model = _parse_raw(raw)
        assert model.entities.components[0].extensions == {"x-team": "platform"}
        assert model.relationships[0].extensions == {"x-latency": "50ms"}

    def test_parse_v10_backward_compat(self):
        from architecture_model.core.parser import _parse_raw
        raw = {"meta": {"schema_version": "1.0", "project": "legacy"}, "entities": {"components": [{"id": "c", "name": "C", "status": "ACTIVE"}], "behaviors": [{"id": "b", "name": "B", "status": "ACTIVE"}], "interfaces": [{"id": "i", "name": "I", "status": "ACTIVE", "type": "REST"}]}, "relationships": [{"type": "depends-on", "from": "c", "to": "i"}]}
        model = _parse_raw(raw)
        assert model.entities.components[0].kind == ComponentKind.SERVICE
        assert model.entities.components[0].extensions == {}
        assert model.entities.behaviors[0].pattern == BehaviorPattern.SEQUENTIAL
        assert model.entities.interfaces[0].schema == ""
        assert model.relationships[0].extensions == {}


class TestSerializationV11:
    def test_component_kind_round_trip(self):
        from architecture_model.core.parser import _parse_raw
        comp = Component(id="schema", name="Schema", status=Status.ACTIVE, kind=ComponentKind.DATA_MODEL, fields=[DataField(name="id", type="int", required=True)], extensions={"x-owner": "data"})
        model = ArchitectureModel(meta=ModelMeta(schema_version="1.1", project="test", generated_at="2026-01-01T00:00:00Z"), entities=Entities(components=[comp]))
        restored = _parse_raw(model.to_dict())
        rc = restored.entities.components[0]
        assert rc.kind == ComponentKind.DATA_MODEL
        assert rc.fields[0].name == "id"
        assert rc.extensions == {"x-owner": "data"}

    def test_behavior_pattern_round_trip(self):
        from architecture_model.core.parser import _parse_raw
        beh = Behavior(id="sm", name="SM", status=Status.ACTIVE, pattern=BehaviorPattern.STATE_MACHINE, states=[StateTransition(name="idle", transitions=[{"to": "active", "trigger": "go"}])])
        model = ArchitectureModel(meta=ModelMeta(schema_version="1.1", project="test", generated_at="2026-01-01T00:00:00Z"), entities=Entities(behaviors=[beh]))
        restored = _parse_raw(model.to_dict())
        assert restored.entities.behaviors[0].pattern == BehaviorPattern.STATE_MACHINE
        assert restored.entities.behaviors[0].states[0].name == "idle"

    def test_interface_schema_round_trip(self):
        from architecture_model.core.parser import _parse_raw
        iface = Interface(id="api", name="API", status=Status.ACTIVE, type=InterfaceType.REST, schema="user-schema")
        model = ArchitectureModel(meta=ModelMeta(schema_version="1.1", project="test", generated_at="2026-01-01T00:00:00Z"), entities=Entities(interfaces=[iface]))
        restored = _parse_raw(model.to_dict())
        assert restored.entities.interfaces[0].schema == "user-schema"

    def test_relationship_extensions_round_trip(self):
        from architecture_model.core.parser import _parse_raw
        rel = Relationship(type=RelationType.DEPENDS_ON, from_id="a", to_id="b", extensions={"x-note": "test"})
        model = ArchitectureModel(meta=ModelMeta(schema_version="1.1", project="test", generated_at="2026-01-01T00:00:00Z"), entities=Entities(), relationships=[rel])
        restored = _parse_raw(model.to_dict())
        assert restored.relationships[0].extensions == {"x-note": "test"}

    def test_defaults_not_serialized(self):
        comp = Component(id="svc", name="Svc", status=Status.ACTIVE)
        beh = Behavior(id="b", name="B", status=Status.ACTIVE)
        model = ArchitectureModel(meta=ModelMeta(schema_version="1.1", project="test", generated_at="2026-01-01T00:00:00Z"), entities=Entities(components=[comp], behaviors=[beh]))
        d = model.to_dict()
        assert "kind" not in d["entities"]["components"][0]
        assert "pattern" not in d["entities"]["behaviors"][0]
        assert "extensions" not in d["entities"]["components"][0]


class TestJsonSchemaV11:
    def test_component_with_kind_validates(self):
        from architecture_model.core.parser import validate_model_data
        data = {
            "meta": {"schema_version": "1.1.0", "project": "test", "generated_at": "2026-01-01T00:00:00Z"},
            "entities": {"components": [{"id": "user-schema", "name": "User Schema", "status": "ACTIVE", "kind": "data-model", "fields": [{"name": "id", "type": "integer", "required": True}], "extensions": {"x-team": "data"}}]},
            "relationships": [],
        }
        errors = validate_model_data(data)
        assert errors == [], f"Validation errors: {errors}"

    def test_invalid_kind_fails_validation(self):
        from architecture_model.core.parser import validate_model_data
        data = {
            "meta": {"schema_version": "1.1.0", "project": "test", "generated_at": "2026-01-01T00:00:00Z"},
            "entities": {"components": [{"id": "x", "name": "X", "status": "ACTIVE", "kind": "not-valid"}]},
            "relationships": [],
        }
        errors = validate_model_data(data)
        assert len(errors) > 0

    def test_behavior_with_pattern_validates(self):
        from architecture_model.core.parser import validate_model_data
        data = {
            "meta": {"schema_version": "1.1.0", "project": "test", "generated_at": "2026-01-01T00:00:00Z"},
            "entities": {"behaviors": [{"id": "flow", "name": "Flow", "status": "ACTIVE", "pattern": "state-machine", "states": [{"name": "idle", "transitions": [{"to": "active", "trigger": "start"}]}]}]},
            "relationships": [],
        }
        errors = validate_model_data(data)
        assert errors == [], f"Validation errors: {errors}"

    def test_relationship_with_extensions_validates(self):
        from architecture_model.core.parser import validate_model_data
        data = {
            "meta": {"schema_version": "1.1.0", "project": "test", "generated_at": "2026-01-01T00:00:00Z"},
            "entities": {},
            "relationships": [{"type": "depends-on", "from": "a", "to": "b", "extensions": {"x-latency": "50ms"}}],
        }
        errors = validate_model_data(data)
        assert errors == [], f"Validation errors: {errors}"

    def test_v10_yaml_still_validates(self):
        from architecture_model.core.parser import validate_model_data
        data = {
            "meta": {"schema_version": "1.0.0", "project": "legacy", "generated_at": "2026-01-01T00:00:00Z"},
            "entities": {"components": [{"id": "comp-1", "name": "Comp", "status": "ACTIVE"}]},
            "relationships": [{"type": "depends-on", "from": "comp-1", "to": "comp-1"}],
        }
        errors = validate_model_data(data)
        assert errors == [], f"Validation errors: {errors}"


class TestValidatorV11:
    def test_data_model_without_fields_info(self):
        from architecture_model.core.validator import validate_model, Severity
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.1", project="test", generated_at="2026-01-01T00:00:00Z"),
            entities=Entities(components=[Component(id="schema-1", name="Schema", status=Status.ACTIVE, kind=ComponentKind.DATA_MODEL)]),
            relationships=[],
        )
        result = validate_model(model)
        info_msgs = [i for i in result.issues if i.severity == Severity.INFO and "data-model" in i.message.lower()]
        assert len(info_msgs) >= 1

    def test_state_machine_unreachable_state_warning(self):
        from architecture_model.core.validator import validate_model, Severity
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.1", project="test", generated_at="2026-01-01T00:00:00Z"),
            entities=Entities(behaviors=[
                Behavior(id="sm-1", name="SM", status=Status.ACTIVE, pattern=BehaviorPattern.STATE_MACHINE, states=[
                    StateTransition(name="start", transitions=[{"to": "end", "trigger": "go"}]),
                    StateTransition(name="end", transitions=[]),
                    StateTransition(name="orphan", transitions=[]),
                ]),
            ]),
            relationships=[],
        )
        result = validate_model(model)
        state_warnings = [i for i in result.issues if i.code == "STATE_UNREACHABLE"]
        assert len(state_warnings) >= 1
        assert "orphan" in state_warnings[0].message.lower()


class TestFullRoundTripV11:
    """A complete model with ALL v1.1 features, serialized to YAML and back."""

    def test_full_v11_model_round_trip(self):
        """Construct a model using every v1.1 feature, to_yaml, parse back, assert equal."""
        from architecture_model.core.parser import _parse_raw
        import yaml

        model = ArchitectureModel(
            meta=ModelMeta(schema_version="1.1", project="e-commerce", generated_at="2026-07-05T00:00:00Z"),
            entities=Entities(
                actors=[Actor(id="customer", name="Customer", status=Status.ACTIVE, type=ActorType.HUMAN)],
                capabilities=[Capability(id="cap-checkout", name="Checkout", status=Status.ACTIVE, source_block="S3")],
                behaviors=[
                    Behavior(
                        id="order-saga", name="Order Processing", status=Status.ACTIVE,
                        pattern=BehaviorPattern.SAGA,
                        compensations=[Compensation(step="Reserve stock", compensate="Release stock")],
                        extensions={"x-timeout": "30s"},
                    ),
                    Behavior(
                        id="session-sm", name="Session Lifecycle", status=Status.ACTIVE,
                        pattern=BehaviorPattern.STATE_MACHINE,
                        states=[
                            StateTransition(name="anonymous", transitions=[{"to": "authenticated", "trigger": "login"}]),
                            StateTransition(name="authenticated", transitions=[{"to": "anonymous", "trigger": "logout"}]),
                        ],
                    ),
                ],
                interfaces=[
                    Interface(
                        id="order-api", name="Order API", status=Status.ACTIVE,
                        type=InterfaceType.REST,
                        schema="order-schema",
                        endpoints=[{"method": "POST", "path": "/orders", "request_schema": "order-schema"}],
                    ),
                ],
                constraints=[Constraint(id="con-latency", name="API Latency", status=Status.ACTIVE, type=ConstraintType.PERFORMANCE, threshold="<200ms")],
                layers=[Layer(id="layer-web", name="Web", status=Status.ACTIVE, order=0)],
                components=[
                    Component(
                        id="order-service", name="Order Service", status=Status.ACTIVE,
                        kind=ComponentKind.SERVICE, layer="layer-web",
                    ),
                    Component(
                        id="order-schema", name="Order Schema", status=Status.ACTIVE,
                        kind=ComponentKind.DATA_MODEL,
                        fields=[
                            DataField(name="order_id", type="uuid", required=True),
                            DataField(name="total", type="decimal", required=True),
                            DataField(name="items", type="array"),
                        ],
                    ),
                    Component(
                        id="prod-cluster", name="Production", status=Status.ACTIVE,
                        kind=ComponentKind.INFRASTRUCTURE,
                        technology="kubernetes",
                        region="us-east-1",
                        replicas=3,
                        extensions={"x-cost": "$500/mo"},
                    ),
                ],
            ),
            relationships=[
                Relationship(type=RelationType.ALLOCATED_TO, from_id="order-service", to_id="prod-cluster"),
                Relationship(type=RelationType.EXPOSES, from_id="order-service", to_id="order-api"),
                Relationship(type=RelationType.REALIZES, from_id="order-service", to_id="cap-checkout"),
                Relationship(
                    type=RelationType.DEPENDS_ON, from_id="order-service", to_id="order-schema",
                    extensions={"x-coupling": "tight"},
                ),
            ],
        )

        # Serialize to YAML
        yaml_str = model.to_yaml()
        assert "kind: data-model" in yaml_str
        assert "pattern: saga" in yaml_str
        assert "schema: order-schema" in yaml_str
        assert "x-cost:" in yaml_str

        # Parse back
        raw = yaml.safe_load(yaml_str)
        restored = _parse_raw(raw)

        # Assert structural equality
        assert restored.entity_count == model.entity_count
        assert restored.relationship_count == model.relationship_count

        # Check specific v1.1 features survived round-trip
        order_svc = next(c for c in restored.entities.components if c.id == "order-service")
        assert order_svc.kind == ComponentKind.SERVICE

        order_schema = next(c for c in restored.entities.components if c.id == "order-schema")
        assert order_schema.kind == ComponentKind.DATA_MODEL
        assert len(order_schema.fields) == 3
        assert order_schema.fields[0].name == "order_id"

        prod = next(c for c in restored.entities.components if c.id == "prod-cluster")
        assert prod.kind == ComponentKind.INFRASTRUCTURE
        assert prod.region == "us-east-1"
        assert prod.replicas == 3
        assert prod.extensions == {"x-cost": "$500/mo"}

        saga = next(b for b in restored.entities.behaviors if b.id == "order-saga")
        assert saga.pattern == BehaviorPattern.SAGA
        assert saga.compensations[0].step == "Reserve stock"
        assert saga.extensions == {"x-timeout": "30s"}

        sm = next(b for b in restored.entities.behaviors if b.id == "session-sm")
        assert sm.pattern == BehaviorPattern.STATE_MACHINE
        assert len(sm.states) == 2

        api = restored.entities.interfaces[0]
        assert api.schema == "order-schema"

        dep_rel = next(r for r in restored.relationships if r.type == RelationType.DEPENDS_ON)
        assert dep_rel.extensions == {"x-coupling": "tight"}
