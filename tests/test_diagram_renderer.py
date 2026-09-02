from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
import random
import re
import xml.etree.ElementTree as ET

import pytest

from architecture_model.core.diagram_renderer import (
    DiagramRenderOptions,
    render_diagram_drilldowns,
    render_diagram_panel,
    render_diagram_svg,
)
from architecture_model.core.diagram_spec import (
    Diagnostic,
    DiagramCallout,
    DiagramDrilldown,
    DiagramEdge,
    DiagramGroup,
    DiagramNode,
    DiagramProvenance,
    DiagramSpec,
    LegendEntry,
)


SVG = {"svg": "http://www.w3.org/2000/svg"}


def _spec(direction: str = "LR") -> DiagramSpec:
    detail = DiagramSpec(
        "detail-a",
        "Independent detail",
        nodes=[DiagramNode("detail-node", "Detail node", "component", entity_ref="COMP-D")],
    )
    return DiagramSpec(
        id=f"overview-{direction.lower()}",
        title="System <Overview> & operations",
        subtitle="Offline renderer",
        direction=direction,
        groups=[
            DiagramGroup("system", "System boundary", "system", order=2),
            DiagramGroup("functions", "Functions", "functional", parent="system", order=1),
        ],
        lanes=[DiagramGroup("external-lane", "External", "external", order=0)],
        nodes=[
            DiagramNode("actor", "Operator", "actor", lane="external-lane", entity_ref="ACT-1"),
            DiagramNode("external", "Weather feed", "external", lane="external-lane", inferred=True),
            DiagramNode("scenario", "Run mission scenario", "scenario", group="functions"),
            DiagramNode("interface", "Control API", "interface", group="system", entity_ref="IF-1"),
            DiagramNode("port", "Telemetry port", "port", group="system"),
            DiagramNode("system-node", "Mission system", "system", group="system"),
            DiagramNode(
                "function",
                "Plan and execute a very long mission safely without overflowing its box",
                "functional-block",
                subtitle="Bounded operational function subtitle",
                group="functions",
                status="active",
                drilldown_ref="open-detail",
                badges=["critical", "verified"],
            ),
            DiagramNode("component", "Planner", "component", group="system", entity_ref="COMP-1"),
            DiagramNode("requirement", "Latency < 10 ms", "requirement", group="system"),
            DiagramNode("outcome", "Mission complete", "outcome", group="system"),
        ],
        edges=[
            DiagramEdge("actor", "scenario", "operational", "starts", evidence=[DiagramProvenance("model")]),
            DiagramEdge("actor", "scenario", "data", "request", count=3),
            DiagramEdge("scenario", "function", "decomposition", "includes"),
            DiagramEdge("function", "component", "allocation", "allocated to"),
            DiagramEdge("component", "interface", "dependency", "uses", critical=True),
            DiagramEdge("interface", "outcome", "operational", "delivers", style="cycle"),
            DiagramEdge("external", "port", "data", "forecast", inferred=True),
        ],
        callouts=[DiagramCallout("note", "Review before release", "function", "warning")],
        legend=[LegendEntry("component-key", "Component", "component", "Deployable unit")],
        warnings=[Diagnostic("error", "MISSING-EVIDENCE", "Evidence unavailable", source="curation")],
        provenance=DiagramProvenance("curated model", ("COMP-1",), ("model.yaml",)),
        drilldowns=[DiagramDrilldown("open-detail", source="function", spec=detail)],
    )


def _root(svg: str) -> ET.Element:
    return ET.fromstring(svg)


def _boxes(root: ET.Element) -> list[tuple[float, float, float, float]]:
    result = []
    for node in root.findall(".//svg:g[@data-node-id]", SVG):
        result.append(tuple(float(node.attrib[key]) for key in ("data-x", "data-y", "data-width", "data-height")))
    return result


def test_renders_parseable_semantic_svg_with_expected_structure() -> None:
    root = _root(render_diagram_svg(_spec()))

    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert len(root.findall(".//svg:g[@data-node-id]", SVG)) == 10
    assert len(root.findall(".//svg:path[@data-edge-id]", SVG)) == 7
    assert len(root.findall(".//svg:g[@data-container-id]", SVG)) == 3
    assert root.find("svg:title", SVG).text == "System <Overview> & operations"
    assert root.find("svg:desc", SVG) is not None
    kinds = {node.attrib["data-kind"] for node in root.findall(".//svg:g[@data-node-id]", SVG)}
    assert {"actor", "external", "scenario", "interface", "port", "system", "functional-block", "component", "requirement", "outcome"} <= kinds
    assert root.findall(".//svg:ellipse", SVG)
    assert root.findall(".//svg:circle", SVG)
    assert root.findall(".//svg:polygon", SVG)


@pytest.mark.parametrize("direction", ["LR", "TB"])
def test_layout_has_no_node_overlaps_and_is_bounded(direction: str) -> None:
    root = _root(render_diagram_svg(_spec(direction)))
    boxes = _boxes(root)

    for index, (x1, y1, w1, h1) in enumerate(boxes):
        for x2, y2, w2, h2 in boxes[index + 1 :]:
            assert x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1
    view_box = [float(value) for value in root.attrib["viewBox"].split()]
    assert 320 <= view_box[2] <= 4096
    assert 240 <= view_box[3] <= 4096
    assert root.attrib["width"] == "100%"
    assert root.attrib["preserveAspectRatio"] == "xMidYMid meet"


def test_fifteen_rank_overview_remains_inside_global_viewbox() -> None:
    nodes = [DiagramNode(f"n-{index:02}", f"Node {index}", "component") for index in range(15)]
    spec = DiagramSpec(
        "bounded-overview",
        "Bounded overview",
        nodes=nodes,
        edges=[DiagramEdge(f"n-{index:02}", f"n-{index + 1:02}", "dependency") for index in range(14)],
    )

    root = _root(render_diagram_svg(spec))
    _, _, width, height = [float(value) for value in root.attrib["viewBox"].split()]

    assert width <= 4096 and height <= 4096
    assert all(x >= 0 and y >= 0 and x + box_width <= width and y + box_height <= height for x, y, box_width, box_height in _boxes(root))


def test_edge_styles_markers_evidence_and_parallel_paths_are_distinct() -> None:
    root = _root(render_diagram_svg(_spec()))
    edges = root.findall(".//svg:path[@data-edge-id]", SVG)
    parallel = [edge.attrib["d"] for edge in edges if edge.attrib["data-source"] == "actor" and edge.attrib["data-target"] == "scenario"]

    assert len(set(parallel)) == 2
    by_kind = {edge.attrib["data-kind"]: edge for edge in edges}
    assert "stroke-dasharray" in by_kind["decomposition"].attrib["style"]
    assert "stroke-dasharray" in by_kind["allocation"].attrib["style"]
    assert by_kind["operational"].attrib["marker-end"].endswith("#arrow)")
    assert any("is-critical" in edge.attrib["class"] for edge in edges)
    assert any("is-inferred" in edge.attrib["class"] for edge in edges)
    assert root.findall(".//svg:g[@data-evidence='true']", SVG)
    assert root.findall(".//svg:path/svg:title", SVG)


def test_text_is_escaped_clamped_and_contains_no_active_content() -> None:
    spec = _spec()
    spec.nodes[0].label = "<img src=x onerror=alert(1)> & " + "x" * 180
    svg = render_diagram_svg(spec)
    root = _root(svg)

    assert "<img" not in svg
    assert "onerror=" not in svg.lower()
    assert "<script" not in svg.lower()
    assert not re.search(r"\son[a-z]+\s*=", svg, re.IGNORECASE)
    assert "…" in "".join(root.itertext())


def test_clickable_nodes_emit_accessible_interaction_metadata_without_handlers() -> None:
    root = _root(render_diagram_svg(_spec()))
    clickable = root.findall(".//svg:g[@role='button']", SVG)

    assert clickable
    assert all(node.attrib["tabindex"] == "0" for node in clickable)
    assert all(node.attrib["data-keyboard-action"] == "activate" for node in clickable)
    assert all("data-entity-ref" in node.attrib or "data-drilldown-ref" in node.attrib for node in clickable)
    assert not any(key.lower().startswith("on") for element in root.iter() for key in element.attrib)


def test_panel_is_frozen_and_serializes_json_safe_toolbar_and_dimensions() -> None:
    panel = render_diagram_panel(_spec(), DiagramRenderOptions(max_width=1800, max_height=1400))
    payload = panel.to_dict()

    assert [action.action for action in panel.toolbar] == ["zoom-in", "zoom-out", "fit", "reset"]
    assert payload["view_box"] == [0, 0, panel.width, panel.height]
    assert payload["warnings"][0]["severity"] == "error"
    assert json.loads(json.dumps(payload))["svg"].startswith("<svg")
    with pytest.raises(FrozenInstanceError):
        panel.width = 1  # type: ignore[misc]


def test_legend_callouts_diagnostic_severity_and_provenance_are_visible() -> None:
    root = _root(render_diagram_svg(_spec()))

    assert root.find(".//svg:g[@data-section='legend']", SVG) is not None
    assert root.find(".//svg:g[@data-callout-id='note']", SVG) is not None
    diagnostic = root.find(".//svg:g[@data-diagnostic-code='MISSING-EVIDENCE']", SVG)
    assert diagnostic is not None and diagnostic.attrib["data-severity"] == "error"
    footer = root.find(".//svg:g[@data-section='provenance']", SVG)
    assert footer is not None and "curated model" in "".join(footer.itertext())


def test_rendering_is_deterministic_when_inputs_are_shuffled() -> None:
    first = _spec()
    second = _spec()
    random.Random(7).shuffle(second.nodes)
    random.Random(8).shuffle(second.edges)
    random.Random(9).shuffle(second.groups)

    assert render_diagram_svg(first) == render_diagram_svg(second)


@pytest.mark.parametrize(
    ("view_id", "direction"),
    [("conops", "LR"), ("functional", "TB"), ("logical", "LR"), ("use-cases", "TB")],
)
def test_representative_curated_views_have_stable_golden_structure(view_id: str, direction: str) -> None:
    spec = _spec(direction)
    spec.id = view_id

    root = _root(render_diagram_svg(spec))

    assert root.attrib["data-diagram-id"] == view_id
    assert len(root.findall(".//svg:g[@data-node-id]", SVG)) == 10
    assert len(root.findall(".//svg:path[@data-edge-id]", SVG)) == 7
    assert len(root.findall(".//svg:g[@data-container-id]", SVG)) == 3
    assert len(_boxes(root)) == len({box for box in _boxes(root)})


def test_drilldown_panels_are_keyed_exactly_and_nested_specs_render_independently() -> None:
    deepest = DiagramSpec("deep", "Deep", nodes=[DiagramNode("deep-node", "Deep node", "outcome")])
    detail_z = DiagramSpec(
        "detail-z",
        "Detail Z",
        nodes=[DiagramNode("z", "Z", "component", drilldown_ref="deep-link")],
        drilldowns=[DiagramDrilldown("deep-link", source="z", spec=deepest)],
    )
    detail_a = DiagramSpec("detail-a", "Detail A", nodes=[DiagramNode("a", "A", "actor")])
    overview = DiagramSpec(
        "overview",
        "Overview",
        nodes=[
            DiagramNode("source-z", "Z", "component", drilldown_ref="z-link"),
            DiagramNode("source-a", "A", "component", drilldown_ref="a-link"),
        ],
        drilldowns=[
            DiagramDrilldown("z-link", source="source-z", spec=detail_z),
            DiagramDrilldown("a-link", source="source-a", spec=detail_a),
        ],
    )

    panels = render_diagram_drilldowns(overview)

    assert list(panels) == ["a-link", "z-link"]
    assert panels["a-link"].diagram_id == "detail-a"
    assert panels["z-link"].diagram_id == "detail-z"
    assert panels["z-link"].drilldowns["deep-link"].diagram_id == "deep"
