import json
import math
from dataclasses import FrozenInstanceError
from typing import get_type_hints

import pytest

from architecture_model.core.diagram_spec import (
    Diagnostic,
    DiagramEdge,
    DiagramGroup,
    DiagramNode,
    DiagramProvenance,
    DiagramDrilldown,
    LegendEntry,
    DiagramCallout,
    DiagramSpec,
    bounded,
)


def test_diagram_spec_serializes_deterministically_and_json_safely():
    spec = DiagramSpec(
        id="overview",
        title="Overview",
        nodes=[
            DiagramNode(id="root::B", label="B", kind="component", metrics={"count": 2}),
            DiagramNode(id="root::A", label="A", kind="component", badges=["core"]),
        ],
        edges=[DiagramEdge(source="root::A", target="root::B", kind="depends-on")],
        groups=[DiagramGroup(id="G-1", label="Core", kind="system")],
        provenance={"source": "canonical"},
    )

    payload = spec.to_dict()

    assert [node["id"] for node in payload["nodes"]] == ["root::A", "root::B"]
    assert json.loads(json.dumps(payload)) == payload
    assert DiagramSpec.from_dict(payload).to_dict() == payload


@pytest.mark.parametrize(
    "spec, message",
    [
        (DiagramSpec(id="x", title="X", nodes=[DiagramNode("a", "A", "component"), DiagramNode("a", "A2", "component")]), "Duplicate node ID"),
        (DiagramSpec(id="x", title="X", nodes=[DiagramNode("a", "A", "component")], edges=[DiagramEdge("a", "missing", "flow")]), "unknown target"),
    ],
)
def test_diagram_spec_rejects_duplicate_or_invalid_references(spec, message):
    with pytest.raises(ValueError, match=message):
        spec.validate()


def test_bounded_selection_is_stable_and_reports_omissions():
    selected, warning = bounded(["c", "a", "b"], 2, key=lambda value: value)
    assert selected == ["a", "b"]
    assert warning == "1 item omitted (limit 2)"


def test_diagram_spec_rejects_embedded_html():
    spec = DiagramSpec(id="x", title="Latency < 10ms", nodes=[DiagramNode("n", "<b>literal</b>", "note")])
    spec.validate()
    assert spec.nodes[0].safe_text is True


@pytest.mark.parametrize("label", ["<script>alert(1)</script>", '<img onerror="run()">', "javascript:run()", "bad\x00text", "x" * 501])
def test_diagram_spec_rejects_unsafe_or_oversized_text(label):
    with pytest.raises(ValueError, match="presentation text"):
        DiagramSpec(id="x", title=label).validate()


def test_typed_provenance_and_drilldowns_preserve_dict_shape():
    hints = get_type_hints(DiagramSpec)
    assert hints["provenance"] is DiagramProvenance
    assert hints["drilldowns"] == list[DiagramDrilldown]
    spec = DiagramSpec(
        id="x", title="X",
        nodes=[DiagramNode("n", "Node", "component", drilldown_ref="detail")],
        provenance=DiagramProvenance(source="canonical", entity_refs=["root::COMP-1"]),
        drilldowns=[DiagramDrilldown("detail", source="n", route="/entities/root::COMP-1")],
    )
    payload = spec.to_dict()
    assert payload["provenance"] == {"source": "canonical", "entity_refs": ["root::COMP-1"]}
    assert payload["drilldowns"] == [{
        "id": "detail", "source": "n", "target": "", "spec_ref": "", "route": "/entities/root::COMP-1"
    }]
    assert isinstance(DiagramSpec.from_dict(payload).provenance, DiagramProvenance)


@pytest.mark.parametrize(
    "spec, message",
    [
        (DiagramSpec("x", "X", legend=[LegendEntry("k", "A", "a"), LegendEntry("k", "B", "b")]), "Duplicate legend ID"),
        (DiagramSpec("x", "X", groups=[DiagramGroup("a", "A", "group", parent="missing")]), "unknown parent"),
        (DiagramSpec("x", "X", groups=[DiagramGroup("a", "A", "group", parent="b"), DiagramGroup("b", "B", "group", parent="a")]), "cycle"),
        (DiagramSpec("x", "X", nodes=[DiagramNode("n", "N", "component", group="missing")]), "unknown group"),
        (DiagramSpec("x", "X", nodes=[DiagramNode("n", "N", "component", lane="missing")]), "unknown lane"),
        (DiagramSpec("x", "X", callouts=[DiagramCallout("c", "C", target="missing")]), "unknown target"),
        (DiagramSpec("x", "X", nodes=[DiagramNode("n", "N", "component", drilldown_ref="missing")]), "unknown drilldown"),
        (DiagramSpec("x", "X", nodes=[DiagramNode("n", "N", "component")], drilldowns=[DiagramDrilldown("d", source="missing", route="arbitrary-route")]), "unknown source"),
        (DiagramSpec("x", "X", nodes=[DiagramNode("n", "N", "component")], drilldowns=[DiagramDrilldown("d", source="n")]), "exactly one"),
    ],
)
def test_diagram_spec_validates_all_internal_references(spec, message):
    with pytest.raises(ValueError, match=message):
        spec.validate()


def test_drilldown_route_is_external_and_not_treated_as_internal_id():
    DiagramSpec(
        "x", "X", nodes=[DiagramNode("n", "N", "component")],
        drilldowns=[DiagramDrilldown("d", source="n", route="viewer:any route/value")],
    ).validate()


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, object()])
def test_json_serialization_rejects_non_json_values(value):
    spec = DiagramSpec("x", "X", nodes=[DiagramNode("n", "N", "component", metrics={"bad": value})])
    with pytest.raises(ValueError, match="Invalid diagram type"):
        spec.to_dict()


def test_provenance_entity_refs_reject_sets_even_if_deterministic():
    spec = DiagramSpec("x", "X", provenance={"entity_refs": {"b", "a"}})
    with pytest.raises(ValueError, match="Invalid diagram type"):
        spec.to_dict()


def test_json_serialization_rejects_non_string_mapping_keys():
    spec = DiagramSpec("x", "X", nodes=[DiagramNode("n", "N", "component", metrics={1: "bad"})])
    with pytest.raises(ValueError, match="Invalid diagram type"):
        spec.to_dict()


def test_group_and_lane_ids_share_one_container_namespace():
    spec = DiagramSpec(
        "x", "X",
        groups=[DiagramGroup("shared", "Group", "group")],
        lanes=[DiagramGroup("shared", "Lane", "lane")],
    )
    with pytest.raises(ValueError, match="Duplicate document ID"):
        spec.validate()


def test_node_and_edge_normalize_and_serialize_typed_provenance():
    node = DiagramNode("a", "A", "component", evidence=["model.yaml"])
    edge = DiagramEdge("a", "b", "flow", evidence=[DiagramProvenance(source="manifest", entity_refs=["root::A"])])
    spec = DiagramSpec("x", "X", nodes=[node, DiagramNode("b", "B", "component")], edges=[edge])
    payload = spec.to_dict()
    assert isinstance(node.evidence[0], DiagramProvenance)
    assert payload["nodes"][0]["evidence"] == [{"source": "model.yaml", "entity_refs": []}]
    assert payload["edges"][0]["evidence"] == [{"source": "manifest", "entity_refs": ["root::A"]}]
    restored = DiagramSpec.from_dict(payload)
    assert restored.nodes[0].evidence == [DiagramProvenance(source="model.yaml")]
    assert restored.edges[0].evidence == [DiagramProvenance(source="manifest", entity_refs=["root::A"])]


def test_all_document_element_ids_share_one_namespace():
    spec = DiagramSpec(
        "x", "X", nodes=[DiagramNode("shared", "N", "component")],
        legend=[LegendEntry("shared", "Legend", "component")],
    )
    with pytest.raises(ValueError, match="Duplicate document ID"):
        spec.validate()


def test_structured_diagnostics_serialize_as_dicts():
    spec = DiagramSpec("x", "X", warnings=["legacy", Diagnostic("warning", "TEST", "message", view="x")])
    payload = spec.to_dict()
    assert all(isinstance(item, Diagnostic) for item in spec.warnings)
    assert payload["warnings"] == [
        {"severity": "warning", "code": "LEGACY", "view": "", "source": "", "message": "legacy", "context": {}},
        {"severity": "warning", "code": "TEST", "view": "x", "source": "", "message": "message", "context": {}},
    ]


def test_provenance_is_frozen_and_nested_types_are_validated():
    provenance = DiagramProvenance(source="model", entity_refs=["root::A"])
    with pytest.raises(FrozenInstanceError):
        provenance.source = "changed"


def test_provenance_is_deeply_immutable_and_serializes_collections():
    provenance = DiagramProvenance(
        source="model", entity_refs=["root::A"], source_files=["model.yaml"],
        context={"line": 3, "tags": ["a", "b"]},
    )
    assert provenance.entity_refs == ("root::A",)
    assert provenance.source_files == ("model.yaml",)
    with pytest.raises((AttributeError, TypeError)):
        provenance.entity_refs += ("root::B",)
    with pytest.raises(TypeError):
        provenance.context["line"] = 4
    payload = DiagramSpec("x", "X", provenance=provenance).to_dict()["provenance"]
    assert payload == {
        "source": "model", "entity_refs": ["root::A"], "source_files": ["model.yaml"],
        "context": {"line": 3, "tags": ["a", "b"]},
    }


def test_provenance_deep_freezes_every_context_input_shape():
    nested_list = [{"values": [2, 1]}]
    tuple_pairs = (("nested", nested_list), ("members", {"b", "a"}))
    provenance = DiagramProvenance(context=tuple_pairs)

    nested_list[0]["values"].append(3)
    nested_list.append({"changed": True})

    assert provenance.to_dict()["context"] == {
        "members": ["a", "b"],
        "nested": [{"values": [2, 1]}],
    }
    with pytest.raises(TypeError):
        provenance.context[0][1][0][0] = "changed"


def test_drilldown_can_own_a_valid_nested_spec_and_round_trip():
    detail = DiagramSpec("detail", "Detail", nodes=[DiagramNode("detail-node", "Detail", "behavior")])
    overview = DiagramSpec(
        "overview", "Overview",
        nodes=[DiagramNode("summary", "Summary", "scenario", drilldown_ref="open-detail")],
        drilldowns=[DiagramDrilldown("open-detail", "summary", spec=detail)],
    )

    payload = overview.to_dict()

    assert payload["drilldowns"][0]["spec"]["id"] == "detail"
    assert DiagramSpec.from_dict(payload).drilldowns[0].spec.to_dict() == detail.to_dict()


def test_drilldown_serialization_preserves_association_with_reverse_insertion_and_mismatched_ids():
    deepest = DiagramSpec("deep-z", "Deep", nodes=[DiagramNode("deep-node", "Deep", "behavior")])
    detail_for_a = DiagramSpec(
        "spec-z", "Detail A",
        nodes=[DiagramNode("detail-a", "Detail A", "behavior", drilldown_ref="nested-a")],
        drilldowns=[DiagramDrilldown("nested-a", "detail-a", spec=deepest)],
    )
    detail_for_z = DiagramSpec("spec-a", "Detail Z", nodes=[DiagramNode("detail-z", "Detail Z", "behavior")])
    overview = DiagramSpec(
        "overview", "Overview",
        nodes=[
            DiagramNode("source-a", "A", "scenario", drilldown_ref="drill-a"),
            DiagramNode("source-z", "Z", "scenario", drilldown_ref="drill-z"),
        ],
        drilldowns=[
            DiagramDrilldown("drill-z", "source-z", spec=detail_for_z),
            DiagramDrilldown("drill-a", "source-a", spec=detail_for_a),
        ],
    )

    payload = overview.to_dict()
    by_id = {item["id"]: item for item in payload["drilldowns"]}
    assert by_id["drill-a"]["source"] == "source-a"
    assert by_id["drill-a"]["spec"]["id"] == "spec-z"
    assert by_id["drill-a"]["spec"]["drilldowns"][0]["spec"]["id"] == "deep-z"
    assert by_id["drill-z"]["source"] == "source-z"
    assert by_id["drill-z"]["spec"]["id"] == "spec-a"

    restored = DiagramSpec.from_dict(payload).to_dict()
    assert restored == payload


@pytest.mark.parametrize("context", [{"bad": math.inf}, {"bad": object()}])
def test_provenance_context_rejects_non_json_values(context):
    with pytest.raises(ValueError, match="Provenance context"):
        DiagramProvenance(context=context)


@pytest.mark.parametrize(
    "spec",
    [
        DiagramSpec("x", "X", provenance=DiagramProvenance("model", "root::A")),
        DiagramSpec("x", "X", nodes=[DiagramNode("a", "A", "component", evidence="model")]),
        DiagramSpec("x", "X", nodes=[DiagramNode("a", "A", "component", evidence=[object()])]),
        DiagramSpec("x", "X", nodes=[DiagramNode("a", "A", "component", metrics={"bad": [1]})]),
        DiagramSpec("x", "X", nodes="not-a-list"),
    ],
)
def test_diagram_spec_rejects_invalid_nested_runtime_types(spec):
    with pytest.raises(ValueError, match="Invalid diagram type"):
        spec.validate()
