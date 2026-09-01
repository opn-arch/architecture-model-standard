"""Universal semantic fields must work for every architecture entity type."""

from dataclasses import replace

import pytest
import yaml

from architecture_model.core.parser import _parse_raw, dump_model, validate_model_data
from architecture_model.core.types import (
    Actor,
    ArchitectureModel,
    Behavior,
    Capability,
    Component,
    ComponentInterface,
    Constraint,
    Data,
    Decision,
    DecisionEntry,
    Entities,
    Environment,
    Event,
    ExternalSystem,
    Interface,
    Layer,
    Lifecycle,
    ModelMeta,
    QualityAttribute,
    Requirement,
    Resource,
    Status,
    System,
)
from architecture_model.core.visualize import build_entity_properties, generate_html_viewer


ENTITY_CASES = [
    ("actors", Actor, "ACT-1"),
    ("capabilities", Capability, "CAP-1"),
    ("behaviors", Behavior, "BEH-1"),
    ("interfaces", Interface, "IF-1"),
    ("constraints", Constraint, "CON-1"),
    ("layers", Layer, "LAY-1"),
    ("components", Component, "COMP-1"),
    ("systems", System, "SYS-1"),
    ("data", Data, "DAT-1"),
    ("events", Event, "EVT-1"),
    ("resources", Resource, "RES-1"),
    ("environments", Environment, "ENV-1"),
    ("quality_attributes", QualityAttribute, "QA-1"),
    ("decisions", Decision, "DEC-1"),
    ("lifecycles", Lifecycle, "LC-1"),
    ("requirements", Requirement, "REQ-1"),
    ("external_systems", ExternalSystem, "EXT-1"),
]

UNIVERSAL_VALUES = {
    "intent": "Explain why this entity exists",
    "goals": ["Improve outcome"],
    "requirements": ["REQ-42", "The entity shall remain observable"],
    "rationale": "Selected from measured evidence",
    "moes": ["Success rate >= 99%"],
    "value_function": "maximize(success_rate - 0.1 * cost)",
    "failure_modes": ["Signal unavailable"],
    "trade_offs": ["Latency versus consistency"],
    "interface_refs": ["IF-42", "audit-contract"],
    "decisions": [
        DecisionEntry(
            choice="Use measured feedback",
            date="2026-09-01",
            rationale="It closes the improvement loop",
            alternatives=["Manual review"],
            context="Entity-level design",
        )
    ],
    "monitored": ["success_rate", "error_budget"],
}


def _entity(entity_class, entity_id):
    kwargs = dict(UNIVERSAL_VALUES)
    if entity_class is Component:
        kwargs["interfaces"] = [
            ComponentInterface(
                name="evaluate",
                kind="provides",
                target_component="COMP-2",
                signature="(sample: Sample) -> Score",
                symbols=["Score"],
            )
        ]
    return entity_class(id=entity_id, name=entity_class.__name__, status=Status.ACTIVE, **kwargs)


def _model(collection, entity):
    return ArchitectureModel(
        meta=ModelMeta(schema_version="2.1.0", project="universal-semantics"),
        entities=replace(Entities(), **{collection: [entity]}),
    )


@pytest.mark.parametrize("collection,entity_class,entity_id", ENTITY_CASES)
def test_every_entity_supports_and_round_trips_universal_semantics(
    collection, entity_class, entity_id
):
    entity = _entity(entity_class, entity_id)
    model = _model(collection, entity)

    parser_dump = dump_model(model)
    model_dump = model.to_dict()
    yaml_dump = yaml.safe_load(model.to_yaml())

    for raw in (parser_dump, model_dump, yaml_dump):
        assert validate_model_data(raw) == []
        restored = getattr(_parse_raw(raw).entities, collection)[0]
        for field, expected in UNIVERSAL_VALUES.items():
            assert getattr(restored, field) == expected

    if entity_class is Component:
        restored_component = _parse_raw(parser_dump).entities.components[0]
        assert restored_component.interfaces == entity.interfaces
        assert isinstance(restored_component.interfaces[0], ComponentInterface)


@pytest.mark.parametrize("collection,entity_class,entity_id", ENTITY_CASES)
def test_every_entity_has_viewer_properties_and_comment_page(
    collection, entity_class, entity_id, tmp_path
):
    entity = _entity(entity_class, entity_id)
    model = _model(collection, entity)

    properties = build_entity_properties(model)[entity_id]["properties"]
    assert properties["Intent"] == UNIVERSAL_VALUES["intent"]
    assert properties["Goals"] == UNIVERSAL_VALUES["goals"]
    assert properties["Requirements"] == UNIVERSAL_VALUES["requirements"]
    assert properties["Rationale"] == UNIVERSAL_VALUES["rationale"]
    assert properties["Measures of Effectiveness"] == UNIVERSAL_VALUES["moes"]
    assert properties["value_function"] == UNIVERSAL_VALUES["value_function"]
    assert properties["Failure Modes"] == UNIVERSAL_VALUES["failure_modes"]
    assert properties["Trade-offs"] == UNIVERSAL_VALUES["trade_offs"]
    assert properties["Interfaces"] == UNIVERSAL_VALUES["interface_refs"]
    assert properties["Decisions"][0]["choice"] == "Use measured feedback"
    assert properties["Monitored"] == UNIVERSAL_VALUES["monitored"]

    if entity_class is Component:
        assert properties["Component Interfaces"][0]["signature"] == "(sample: Sample) -> Score"

    output = generate_html_viewer(model, tmp_path / "viewer.html")
    html = output.read_text(encoding="utf-8")
    assert entity_id in html
    assert "comment-textarea" in html
    assert "Add notes about this entity" in html
