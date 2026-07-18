"""Tests for schema v2.0 — new entity types, relationships, and systems-of-systems."""
import yaml
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Relationship, RelationType, Status, Strength,
    Data, Event, EventKind, Resource, ResourceKind, Environment, EnvironmentKind,
    QualityAttribute, Decision, DecisionStatus, Lifecycle, LifecyclePhase,
    ConstraintType, DataField,
)
from architecture_model.core.parser import _parse_raw, dump_model


def _make_meta(**kw):
    defaults = {"schema_version": "2.0", "project": "test"}
    defaults.update(kw)
    return ModelMeta(**defaults)


# --- Entity creation tests ---

def test_data_entity():
    d = Data(id="DAT-1", name="UserSchema", status=Status.ACTIVE, format="json", sensitivity="internal")
    assert d.format == "json"
    assert d.sensitivity == "internal"


def test_event_entity():
    e = Event(id="EVT-1", name="TempAlarm", status=Status.ACTIVE, kind=EventKind.ALARM, frequency="on-trigger")
    assert e.kind == EventKind.ALARM


def test_resource_entity():
    r = Resource(id="RES-1", name="PostgreSQL", status=Status.ACTIVE, kind=ResourceKind.DATABASE, sla="99.9%")
    assert r.kind == ResourceKind.DATABASE


def test_environment_entity():
    e = Environment(id="ENV-1", name="Production", status=Status.ACTIVE, kind=EnvironmentKind.PRODUCTION, region="us-east-1")
    assert e.region == "us-east-1"


def test_quality_attribute_entity():
    qa = QualityAttribute(id="QA-1", name="Latency", status=Status.ACTIVE, metric="p99", target="<100ms", applies_to=["COMP-1"])
    assert qa.applies_to == ["COMP-1"]


def test_decision_entity():
    d = Decision(id="DEC-1", name="Use YAML", status=Status.ACTIVE, decision_status=DecisionStatus.ACCEPTED, rationale="Human-readable")
    assert d.decision_status == DecisionStatus.ACCEPTED


def test_lifecycle_entity():
    lc = Lifecycle(id="LC-1", name="v2.0 Release", status=Status.ACTIVE, phase=LifecyclePhase.DEVELOPMENT, version="2.0.0")
    assert lc.phase == LifecyclePhase.DEVELOPMENT


# --- New relationship types ---

def test_spatial_relationship_types():
    for rt in ["mounted-on", "connected-at", "routed-through"]:
        r = Relationship(type=RelationType.parse(rt), from_id="A", to_id="B")
        assert r.type.value == rt


def test_event_relationship_types():
    for rt in ["produces", "subscribes-to", "transforms"]:
        r = Relationship(type=RelationType.parse(rt), from_id="A", to_id="B")
        assert r.type.value == rt


def test_lifecycle_relationship_types():
    for rt in ["supersedes", "migrates-to"]:
        r = Relationship(type=RelationType.parse(rt), from_id="A", to_id="B")
        assert r.type.value == rt


def test_failure_mode_constraint():
    assert ConstraintType.FAILURE_MODE.value == "failure-mode"


# --- Round-trip tests ---

def test_round_trip_new_entities():
    model = ArchitectureModel(
        meta=_make_meta(),
        entities=Entities(
            data=[Data(id="DAT-1", name="Schema", status=Status.ACTIVE, format="json")],
            events=[Event(id="EVT-1", name="Alarm", status=Status.ACTIVE, kind=EventKind.ALARM)],
            resources=[Resource(id="RES-1", name="DB", status=Status.ACTIVE, kind=ResourceKind.DATABASE)],
            environments=[Environment(id="ENV-1", name="Prod", status=Status.ACTIVE)],
            quality_attributes=[QualityAttribute(id="QA-1", name="Latency", status=Status.ACTIVE)],
            decisions=[Decision(id="DEC-1", name="ADR-1", status=Status.ACTIVE)],
            lifecycles=[Lifecycle(id="LC-1", name="v2", status=Status.ACTIVE)],
        ),
        relationships=[
            Relationship(type=RelationType.PRODUCES, from_id="COMP-1", to_id="EVT-1"),
            Relationship(type=RelationType.MOUNTED_ON, from_id="COMP-1", to_id="COMP-2"),
        ],
    )
    # Serialize
    raw = dump_model(model)
    # Parse back
    model2 = _parse_raw(raw)
    assert len(model2.entities.data) == 1
    assert model2.entities.data[0].format == "json"
    assert len(model2.entities.events) == 1
    assert model2.entities.events[0].kind == EventKind.ALARM
    assert len(model2.entities.resources) == 1
    assert len(model2.entities.environments) == 1
    assert len(model2.entities.quality_attributes) == 1
    assert len(model2.entities.decisions) == 1
    assert len(model2.entities.lifecycles) == 1
    assert len(model2.relationships) == 2


def test_all_entity_ids_includes_new_types():
    model = ArchitectureModel(
        meta=_make_meta(),
        entities=Entities(
            data=[Data(id="DAT-1", name="X", status=Status.ACTIVE)],
            events=[Event(id="EVT-1", name="X", status=Status.ACTIVE)],
        ),
    )
    ids = model.all_entity_ids
    assert "DAT-1" in ids
    assert "EVT-1" in ids


# --- ModelMeta linkage ---

def test_model_meta_parent_linkage():
    meta = ModelMeta(project="test", schema_version="2.0", parent_model="../../.architecture-model.yaml", refines_component="COMP-CORE")
    assert meta.parent_model == "../../.architecture-model.yaml"
    assert meta.refines_component == "COMP-CORE"


def test_model_meta_parent_defaults_none():
    meta = ModelMeta(project="test", schema_version="2.0")
    assert meta.parent_model is None
    assert meta.refines_component is None


def test_parent_linkage_round_trip():
    model = ArchitectureModel(
        meta=ModelMeta(project="sub", schema_version="2.0", parent_model="../.architecture-model.yaml", refines_component="COMP-CORE"),
        entities=Entities(),
    )
    raw = dump_model(model)
    model2 = _parse_raw(raw)
    assert model2.meta.parent_model == "../.architecture-model.yaml"
    assert model2.meta.refines_component == "COMP-CORE"
