import json

import pytest

from architecture_model.core.diagram_spec import (
    DiagramEdge,
    DiagramGroup,
    DiagramNode,
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
    spec = DiagramSpec(id="x", title="<b>Unsafe</b>")
    with pytest.raises(ValueError, match="HTML"):
        spec.validate()
