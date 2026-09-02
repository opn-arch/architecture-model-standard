from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import random
import re
import shutil
import subprocess
import struct
import zlib
from types import MappingProxyType
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
from architecture_model.core.se_view_projectors import (
    project_conops,
    project_functional_architecture,
    project_logical_architecture,
    project_use_cases,
)
from architecture_model.core.view_context import ArchitectureViewContext
from tests.test_conops_projector import _context as conops_context
from tests.test_functional_projector import _context as functional_context
from tests.test_logical_projector import _context as logical_context
from tests.test_use_case_projector import _context as use_case_context


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


def _box(element: ET.Element) -> tuple[float, float, float, float]:
    return tuple(float(element.attrib[key]) for key in ("data-x", "data-y", "data-width", "data-height"))


def _overlaps(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> bool:
    x1, y1, width1, height1 = first
    x2, y2, width2, height2 = second
    return x1 < x2 + width2 and x2 < x1 + width1 and y1 < y2 + height2 and y2 < y1 + height1


def _route_segments(path: str) -> list[tuple[float, float, float, float]]:
    tokens = re.findall(r"[A-Z]|-?\d+(?:\.\d+)?", path)
    index = 0
    x = y = 0.0
    segments = []
    while index < len(tokens):
        command = tokens[index]
        index += 1
        if command in {"M", "L"}:
            next_x, next_y = float(tokens[index]), float(tokens[index + 1])
            index += 2
        elif command == "H":
            next_x, next_y = float(tokens[index]), y
            index += 1
        elif command == "V":
            next_x, next_y = x, float(tokens[index])
            index += 1
        else:
            raise AssertionError(f"Unsupported route command {command}")
        if command != "M":
            segments.append((x, y, next_x, next_y))
        x, y = next_x, next_y
    return segments


def _segment_crosses_box(segment: tuple[float, float, float, float], box: tuple[float, float, float, float]) -> bool:
    x1, y1, x2, y2 = segment
    left, top, width, height = box
    right, bottom = left + width, top + height
    if x1 == x2:
        return left < x1 < right and max(min(y1, y2), top) < min(max(y1, y2), bottom)
    if y1 == y2:
        return top < y1 < bottom and max(min(x1, x2), left) < min(max(x1, x2), right)
    return True


def _proper_segment_crossing(first, second) -> bool:
    ax1, ay1, ax2, ay2 = first
    bx1, by1, bx2, by2 = second
    if ax1 == ax2 and by1 == by2:
        return min(ay1, ay2) < by1 < max(ay1, ay2) and min(bx1, bx2) < ax1 < max(bx1, bx2)
    if ay1 == ay2 and bx1 == bx2:
        return min(ax1, ax2) < bx1 < max(ax1, ax2) and min(by1, by2) < ay1 < max(by1, by2)
    return False


def _visual_crossings(root: ET.Element) -> tuple[int, int]:
    edges = root.findall(".//svg:path[@data-edge-id]", SVG)
    edge_crossings = 0
    for index, first in enumerate(edges):
        for second in edges[index + 1:]:
            if {first.attrib["data-source"], first.attrib["data-target"]} & {second.attrib["data-source"], second.attrib["data-target"]}:
                continue
            edge_crossings += any(
                _proper_segment_crossing(a, b)
                for a in _route_segments(first.attrib["d"])
                for b in _route_segments(second.attrib["d"])
            )
    label_crossings = 0
    for label in root.findall(".//svg:text[@data-edge-label]", SVG):
        label_box = _box(label)
        own = label.attrib["data-edge-label"]
        label_crossings += any(
            edge.attrib["id"] != own and any(_segment_crosses_box(segment, label_box) for segment in _route_segments(edge.attrib["d"]))
            for edge in edges
        )
    return edge_crossings, label_crossings


def _actual_specs(tmp_path: Path) -> dict[str, DiagramSpec]:
    paths = {name: tmp_path / name for name in ("conops", "functional", "logical", "use-cases")}
    for path in paths.values():
        path.mkdir()
    return {
        "conops": project_conops(conops_context(paths["conops"])),
        "functional": project_functional_architecture(functional_context(paths["functional"], ["MISSION-X", "CAP-A", "CAP-B"])),
        "logical": project_logical_architecture(logical_context(paths["logical"])),
        "use-cases": project_use_cases(use_case_context(paths["use-cases"], 4)),
    }


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
    assert 320 <= view_box[2]
    assert 240 <= view_box[3]
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

    assert all(x >= 0 and y >= 0 and x + box_width <= width and y + box_height <= height for x, y, box_width, box_height in _boxes(root))


def test_footer_items_expand_canvas_and_each_item_stays_inside_viewbox() -> None:
    spec = _spec()
    spec.legend = [LegendEntry(f"legend-{index}", f"Legend {index}", "component", "Description " * 8) for index in range(12)]
    spec.callouts = [DiagramCallout(f"callout-{index}", f"Callout {index} " * 12, "function", evidence=[f"evidence-{index}"]) for index in range(12)]
    spec.warnings = [Diagnostic("warning", f"WARN-{index}", f"Warning {index} " * 12) for index in range(12)]

    root = _root(render_diagram_svg(spec))
    _, _, width, height = (float(value) for value in root.attrib["viewBox"].split())
    items = root.findall(".//svg:g[@data-footer-item]", SVG)

    assert len(items) == 37
    for item in items:
        x, y, item_width, item_height = (float(item.attrib[key]) for key in ("data-x", "data-y", "data-width", "data-height"))
        assert 0 <= x and 0 <= y and x + item_width <= width and y + item_height <= height


def test_too_small_requested_bounds_are_ignored_without_clipping_and_diagnosed() -> None:
    panel = render_diagram_panel(_spec(), DiagramRenderOptions(max_width=20, max_height=10))
    root = _root(panel.svg)
    _, _, width, height = (float(value) for value in root.attrib["viewBox"].split())

    assert width >= 320 and height >= 240
    assert all(x + box_width <= width and y + box_height <= height for x, y, box_width, box_height in _boxes(root))
    assert any(item.code == "RENDER_BOUNDS_TOO_SMALL" for item in panel.warnings)


def test_default_bounds_do_not_inflate_natural_canvas() -> None:
    panel = render_diagram_panel(DiagramSpec("small", "Small", nodes=[DiagramNode("a", "A", "component")]))

    assert panel.width < 1000
    assert panel.height < 1000


def test_edge_styles_markers_evidence_and_parallel_paths_are_distinct() -> None:
    root = _root(render_diagram_svg(_spec()))
    edges = root.findall(".//svg:path[@data-edge-id]", SVG)
    parallel = [edge.attrib["d"] for edge in edges if edge.attrib["data-source"] == "actor" and edge.attrib["data-target"] == "scenario"]

    assert len(set(parallel)) == 2
    by_kind = {edge.attrib["data-kind"]: edge for edge in edges}
    assert "stroke-dasharray" in by_kind["decomposition"].attrib["style"]
    assert "stroke-dasharray" in by_kind["allocation"].attrib["style"]
    assert by_kind["operational"].attrib["marker-end"].endswith("-arrow)")
    assert any("is-critical" in edge.attrib["class"] for edge in edges)
    assert any("is-inferred" in edge.attrib["class"] for edge in edges)
    assert root.findall(".//svg:g[@data-evidence='true']", SVG)
    assert root.findall(".//svg:path/svg:title", SVG)


def test_long_edge_routes_around_intervening_node_and_parallel_lane_is_reserved() -> None:
    spec = DiagramSpec(
        "obstacles",
        "Obstacles",
        nodes=[DiagramNode("a", "A", "component"), DiagramNode("b", "B", "component"), DiagramNode("c", "C", "component")],
        edges=[
            DiagramEdge("a", "b", "next"),
            DiagramEdge("b", "c", "next"),
            DiagramEdge("a", "c", "dependency", "first"),
            DiagramEdge("a", "c", "dependency", "second"),
        ],
    )

    root = _root(render_diagram_svg(spec))
    middle = root.find(".//svg:g[@data-node-id='b']", SVG)
    paths = [edge.attrib["d"] for edge in root.findall(".//svg:path[@data-edge-id]", SVG) if edge.attrib["data-source"] == "a" and edge.attrib["data-target"] == "c"]

    assert middle is not None
    assert len(set(paths)) == 2
    assert all(float(re.findall(r"[-\d.]+", path)[2]) < float(middle.attrib["data-y"]) for path in paths)


def test_empty_groups_have_distinct_nonzero_positions() -> None:
    spec = DiagramSpec("groups", "Groups", groups=[DiagramGroup("a", "A", "group"), DiagramGroup("b", "B", "group")])

    root = _root(render_diagram_svg(spec))
    boxes = [tuple(float(item.attrib[key]) for key in ("data-x", "data-y", "data-width", "data-height")) for item in root.findall(".//svg:g[@data-container-id]", SVG)]

    assert len(boxes) == 2
    assert len(set(boxes)) == 2
    assert all(width > 0 and height > 0 for _, _, width, height in boxes)


@pytest.mark.parametrize("direction", ["TB", "LR"])
def test_lane_layout_is_ordered_contained_and_not_dependency_ranked(direction: str) -> None:
    spec = DiagramSpec(
        "lanes", "Lanes", direction=direction,
        lanes=[
            DiagramGroup("first", "First tier", "tier", order=1),
            DiagramGroup("second", "Second tier", "tier", order=2),
        ],
        nodes=[
            DiagramNode("a", "A", "system", lane="first"),
            DiagramNode("b", "B", "system", lane="first"),
            DiagramNode("c", "C", "system", lane="second"),
            DiagramNode("d", "D", "system", lane="second"),
        ],
        edges=[DiagramEdge("a", "b", "depends-on", style="cycle"), DiagramEdge("b", "a", "depends-on", style="cycle")],
    )

    root = _root(render_diagram_svg(spec))
    nodes = {item.attrib["data-node-id"]: _box(item) for item in root.findall(".//svg:g[@data-node-id]", SVG)}
    lanes = {item.attrib["data-container-id"]: _box(item) for item in root.findall(".//svg:g[@data-container-id]", SVG)}
    for lane_id, members in (("first", ("a", "b")), ("second", ("c", "d"))):
        left, top, width, height = lanes[lane_id]
        for member in members:
            x, y, node_width, node_height = nodes[member]
            assert left <= x and top + 24 <= y and x + node_width <= left + width and y + node_height <= top + height
    assert not _overlaps(lanes["first"], lanes["second"])
    if direction == "TB":
        assert nodes["a"][1] == nodes["b"][1]
        assert nodes["a"][0] < nodes["b"][0]
        assert lanes["first"][1] < lanes["second"][1]
    else:
        assert nodes["a"][0] == nodes["b"][0]
        assert nodes["a"][1] < nodes["b"][1]
        assert lanes["first"][0] < lanes["second"][0]


def test_many_lane_edges_reuse_bounded_local_tracks() -> None:
    nodes = [DiagramNode(f"a-{index}", f"A {index}", "system", lane="first") for index in range(4)]
    nodes += [DiagramNode(f"b-{index}", f"B {index}", "system", lane="second") for index in range(4)]
    edges = [DiagramEdge(f"a-{source}", f"b-{target}", "depends-on", f"edge {source}-{target}") for source in range(4) for target in range(4)]
    spec = DiagramSpec(
        "lane-routes", "Lane routes", direction="TB", nodes=nodes, edges=edges,
        lanes=[DiagramGroup("first", "First", "tier", order=0), DiagramGroup("second", "Second", "tier", order=1)],
    )

    root = _root(render_diagram_svg(spec))
    _, _, width, height = [float(value) for value in root.attrib["viewBox"].split()]
    paths = [edge.attrib["d"] for edge in root.findall(".//svg:path[@data-edge-id]", SVG)]
    nodes_by_id = {item.attrib["data-node-id"]: _box(item) for item in root.findall(".//svg:g[@data-node-id]", SVG)}

    assert width <= 1800 and height <= 1200
    assert len({tuple(_route_segments(path)) for path in paths}) > 4
    for edge, path in zip(root.findall(".//svg:path[@data-edge-id]", SVG), paths):
        unrelated = [box for identifier, box in nodes_by_id.items() if identifier not in {edge.attrib["data-source"], edge.attrib["data-target"]}]
        assert all(not _segment_crosses_box(segment, box) for segment in _route_segments(path) for box in unrelated)


@pytest.mark.parametrize("kind", ["initiates", "uses", "connects", "produces", "consumes", "exposes", "depends-on", "interface-port", "contains", "participates", "triggers", "next", "error", "compensates", "transition", "owns", "decomposition", "allocation"])
def test_projector_edge_kinds_have_semantic_style_classes(kind: str) -> None:
    spec = DiagramSpec("styles", "Styles", nodes=[DiagramNode("a", "A", "component"), DiagramNode("b", "B", "component")], edges=[DiagramEdge("a", "b", kind)])

    edge = _root(render_diagram_svg(spec)).find(".//svg:path[@data-edge-id]", SVG)

    assert edge is not None
    assert "edge-style-" in edge.attrib["class"]


def test_unsupported_custom_edge_style_is_rejected() -> None:
    spec = DiagramSpec("styles", "Styles", nodes=[DiagramNode("a", "A", "component"), DiagramNode("b", "B", "component")], edges=[DiagramEdge("a", "b", "uses", style="stroke:url(evil)")])

    with pytest.raises(ValueError, match="Unsupported edge style"):
        render_diagram_svg(spec)


def test_text_is_escaped_clamped_and_contains_no_active_content() -> None:
    spec = _spec()
    spec.nodes[0].label = "<img src=x> & " + "x" * 180
    svg = render_diagram_svg(spec)
    root = _root(svg)

    assert "<img" not in svg
    assert "onerror=" not in svg.lower()
    assert "<script" not in svg.lower()
    assert not re.search(r"\son[a-z]+\s*=", svg, re.IGNORECASE)
    assert "…" in "".join(root.itertext())


def test_hostile_event_like_text_is_rejected_by_spec_validation() -> None:
    spec = _spec()
    spec.nodes[0].label = "<img src=x onerror=alert(1)>"

    with pytest.raises(ValueError, match="Invalid presentation text"):
        render_diagram_svg(spec)


def test_clickable_nodes_emit_accessible_interaction_metadata_without_handlers() -> None:
    root = _root(render_diagram_svg(_spec()))
    clickable = root.findall(".//svg:g[@role='button']", SVG)

    assert clickable
    assert all(node.attrib["tabindex"] == "0" for node in clickable)
    assert all(node.attrib["data-keyboard-action"] == "activate" for node in clickable)
    assert all("data-entity-ref" in node.attrib or "data-drilldown-ref" in node.attrib for node in clickable)
    assert all(node.attrib["aria-label"] for node in clickable)
    assert all(node.attrib["data-view-id"] == "overview-lr" for node in clickable)
    assert all(node.attrib["data-entity-id"] for node in clickable)
    assert not any(key.lower().startswith("on") for element in root.iter() for key in element.attrib)


def test_node_text_blocks_are_spaced_and_contained_with_subtitle_and_badges() -> None:
    root = _root(render_diagram_svg(_spec()))
    node = root.find(".//svg:g[@data-node-id='function']", SVG)

    assert node is not None
    node_box = _box(node)
    blocks = [_box(item) for item in node.findall(".//svg:text[@data-text-role]", SVG)]
    assert len(blocks) >= 4
    for index, first in enumerate(blocks):
        assert node_box[0] <= first[0] and node_box[1] <= first[1]
        assert first[0] + first[2] <= node_box[0] + node_box[2]
        assert first[1] + first[3] <= node_box[1] + node_box[3]
        for second in blocks[index + 1 :]:
            assert not _overlaps(first, second)
    subtitle = _box(node.find(".//svg:text[@data-text-role='subtitle']", SVG))
    badge = _box(node.find(".//svg:text[@data-text-role='badge']", SVG))
    assert badge[1] - (subtitle[1] + subtitle[3]) >= 6


def test_hostile_unbroken_node_text_is_pixel_wrapped_ellipsized_and_clipped() -> None:
    token = "W" * 240
    spec = DiagramSpec(
        "hostile-text", "Hostile text",
        nodes=[DiagramNode("hostile", token, "actor", subtitle=token, badges=[token])],
    )

    root = _root(render_diagram_svg(spec))
    node = root.find(".//svg:g[@data-node-id='hostile']", SVG)
    clips = root.findall(".//svg:clipPath", SVG)

    assert node is not None
    assert len(clips) == 1
    text_group = node.find("svg:g[@data-node-text]", SVG)
    assert text_group is not None
    assert text_group.attrib["clip-path"] == f"url(#{clips[0].attrib['id']})"
    assert token in text_group.find("svg:title", SVG).text
    assert "…" in "".join(text_group.itertext())
    node_box = _box(node)
    for text in text_group.findall("svg:text", SVG):
        box = _box(text)
        assert node_box[0] <= box[0] and box[0] + box[2] <= node_box[0] + node_box[2]
        assert node_box[1] <= box[1] and box[1] + box[3] <= node_box[1] + node_box[3]
    glyph = _box(node.find("svg:g[@data-actor-glyph]", SVG))
    clip_rect = clips[0].find("svg:rect", SVG)
    assert clip_rect is not None
    assert float(clip_rect.attrib["y"]) >= glyph[1] + glyph[3]


@pytest.mark.parametrize("projector", ["conops", "logical", "use-cases"])
def test_actual_actor_glyph_region_does_not_overlap_text(projector: str, tmp_path) -> None:
    root = _root(render_diagram_svg(_actual_specs(tmp_path)[projector]))
    actors = [node for node in root.findall(".//svg:g[@data-node-id]", SVG) if node.attrib["data-kind"] == "actor"]

    assert actors
    for actor in actors:
        glyph = actor.find("svg:g[@data-actor-glyph]", SVG)
        assert glyph is not None
        glyph_box = _box(glyph)
        text_boxes = [_box(item) for item in actor.findall(".//svg:text[@data-text-role]", SVG)]
        assert text_boxes
        assert all(not _overlaps(glyph_box, text_box) for text_box in text_boxes)
        actor_box = _box(actor)
        assert glyph_box[1] >= actor_box[1]
        assert max(box[1] + box[3] for box in text_boxes) <= actor_box[1] + actor_box[3]


def test_actor_height_expands_for_wrapped_label_subtitle_and_badges() -> None:
    actor = DiagramNode(
        "actor",
        "A long actor name that wraps onto another line",
        "actor",
        subtitle="External operating role",
        badges=["active", "verified"],
    )
    root = _root(render_diagram_svg(DiagramSpec("actor-layout", "Actor layout", nodes=[actor])))
    rendered = root.find(".//svg:g[@data-node-id='actor']", SVG)

    assert rendered is not None
    glyph = _box(rendered.find("svg:g[@data-actor-glyph]", SVG))
    text_boxes = [_box(item) for item in rendered.findall(".//svg:text[@data-text-role]", SVG)]
    assert float(rendered.attrib["data-height"]) > DiagramRenderOptions().node_height
    assert min(box[1] for box in text_boxes) >= glyph[1] + glyph[3] + 6


def test_accessibility_ids_are_namespaced_for_multiple_inline_panels() -> None:
    first = _root(render_diagram_svg(DiagramSpec("first", "First")))
    second = _root(render_diagram_svg(DiagramSpec("second", "Second")))

    first_ids = {first.find("svg:title", SVG).attrib["id"], first.find("svg:desc", SVG).attrib["id"]}
    second_ids = {second.find("svg:title", SVG).attrib["id"], second.find("svg:desc", SVG).attrib["id"]}
    assert first_ids.isdisjoint(second_ids)
    assert set(first.attrib["aria-labelledby"].split()) == first_ids


def test_render_validates_spec_and_never_silently_drops_invalid_edges() -> None:
    spec = DiagramSpec("invalid", "Invalid", nodes=[DiagramNode("a", "A", "component")], edges=[DiagramEdge("a", "missing", "uses")])

    with pytest.raises(ValueError, match="unknown target"):
        render_diagram_svg(spec)


def test_panel_is_frozen_and_serializes_json_safe_toolbar_and_dimensions() -> None:
    panel = render_diagram_panel(_spec(), DiagramRenderOptions(max_width=1800, max_height=1400))
    payload = panel.to_dict()

    assert [action.action for action in panel.toolbar] == ["zoom-in", "zoom-out", "fit", "reset"]
    assert payload["view_box"] == [0, 0, panel.width, panel.height]
    assert payload["warnings"][0]["severity"] == "error"
    assert json.loads(json.dumps(payload))["svg"].startswith("<svg")
    with pytest.raises(FrozenInstanceError):
        panel.width = 1  # type: ignore[misc]


def test_panel_is_deeply_immutable_and_to_dict_thaws_nested_data() -> None:
    spec = _spec()
    spec.warnings[0].context["nested"] = {"values": ["value"]}
    panel = render_diagram_panel(spec)

    assert isinstance(panel.drilldowns, MappingProxyType)
    with pytest.raises(TypeError):
        panel.drilldowns["other"] = panel  # type: ignore[index]
    with pytest.raises(TypeError):
        panel.warnings[0].context["other"] = "value"  # type: ignore[index]
    with pytest.raises(TypeError):
        panel.warnings[0].context["nested"]["values"] = ()  # type: ignore[index]
    with pytest.raises(AttributeError):
        panel.warnings[0].context["nested"]["values"].append("other")  # type: ignore[union-attr]
    assert panel.to_dict()["warnings"][0]["context"] == {"nested": {"values": ["value"]}}
    assert panel.to_dict()["provenance"]["source"] == "curated model"


def test_legend_callouts_diagnostic_severity_and_provenance_are_visible() -> None:
    root = _root(render_diagram_svg(_spec()))

    assert root.find(".//svg:g[@data-section='legend']", SVG) is not None
    assert root.find(".//svg:g[@data-callout-id='note']", SVG) is not None
    diagnostic = root.find(".//svg:g[@data-diagnostic-code='MISSING-EVIDENCE']", SVG)
    assert diagnostic is not None and diagnostic.attrib["data-severity"] == "error"
    footer = root.find(".//svg:g[@data-section='provenance']", SVG)
    assert footer is not None and "curated model" in "".join(footer.itertext())


def test_callout_preserves_target_evidence_and_visible_connector() -> None:
    root = _root(render_diagram_svg(_spec()))
    callout = root.find(".//svg:g[@data-callout-id='note']", SVG)
    connector = root.find(".//svg:path[@data-callout-connector='note']", SVG)

    assert callout is not None
    assert callout.attrib["data-target-ref"] == "function"
    assert callout.attrib["data-evidence"] == ""
    assert callout.find("svg:title", SVG) is not None
    assert connector is not None and connector.attrib["data-target-ref"] == "function"


def test_callout_connector_is_orthogonal_and_avoids_unrelated_nodes() -> None:
    root = _root(render_diagram_svg(_spec()))
    connector = root.find(".//svg:path[@data-callout-connector='note']", SVG)
    nodes = {
        item.attrib["data-node-id"]: _box(item)
        for item in root.findall(".//svg:g[@data-node-id]", SVG)
    }

    assert connector is not None
    segments = _route_segments(connector.attrib["d"])
    assert segments and all(x1 == x2 or y1 == y2 for x1, y1, x2, y2 in segments)
    assert all(
        not _segment_crosses_box(segment, box)
        for segment in segments
        for identifier, box in nodes.items()
        if identifier != "function"
    )


def test_untargeted_callout_stays_in_footer_without_connector() -> None:
    spec = _spec()
    spec.callouts = [DiagramCallout("omitted", "12 additional use cases", kind="omitted-count")]

    root = _root(render_diagram_svg(spec))

    assert root.find(".//svg:g[@data-callout-id='omitted']", SVG) is not None
    assert root.find(".//svg:path[@data-callout-connector='omitted']", SVG) is None


def test_rendering_is_deterministic_when_inputs_are_shuffled() -> None:
    first = _spec()
    second = _spec()
    random.Random(7).shuffle(second.nodes)
    random.Random(8).shuffle(second.edges)
    random.Random(9).shuffle(second.groups)

    assert render_diagram_svg(first) == render_diagram_svg(second)


def test_total_edge_order_is_deterministic_across_all_fields_and_provenance() -> None:
    first = _spec()
    first.edges.extend([
        DiagramEdge("actor", "scenario", "data", "same", style="dashed", evidence=[DiagramProvenance("z-source")]),
        DiagramEdge("actor", "scenario", "data", "same", style="solid", evidence=[DiagramProvenance("a-source")]),
    ])
    second = DiagramSpec.from_dict(first.to_dict())
    random.Random(11).shuffle(second.edges)

    assert render_diagram_svg(first) == render_diagram_svg(second)


@pytest.mark.parametrize("projector", ["conops", "functional", "logical", "use-cases"])
def test_actual_projector_outputs_parse_and_layout_without_node_overlap(projector: str, tmp_path) -> None:
    spec = _actual_specs(tmp_path)[projector]

    root = _root(render_diagram_svg(spec))
    boxes = _boxes(root)

    assert root.attrib["data-diagram-id"] == spec.id
    assert len(root.findall(".//svg:g[@data-node-id]", SVG)) == len(spec.nodes)
    assert len(root.findall(".//svg:path[@data-edge-id]", SVG)) == len(spec.edges)
    assert len(root.findall(".//svg:g[@data-container-id]", SVG)) == len(spec.groups) + len(spec.lanes)
    for index, (x1, y1, w1, h1) in enumerate(boxes):
        for x2, y2, w2, h2 in boxes[index + 1 :]:
            assert x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1


@pytest.mark.parametrize("projector", ["conops", "functional", "logical", "use-cases"])
def test_actual_projector_geometry_has_no_visual_collisions(projector: str, tmp_path) -> None:
    root = _root(render_diagram_svg(_actual_specs(tmp_path)[projector]))
    nodes = {item.attrib["data-node-id"]: _box(item) for item in root.findall(".//svg:g[@data-node-id]", SVG)}

    for node in root.findall(".//svg:g[@data-node-id]", SVG):
        text_boxes = [_box(item) for item in node.findall(".//svg:text[@data-text-role]", SVG)]
        assert all(not _overlaps(first, second) for index, first in enumerate(text_boxes) for second in text_boxes[index + 1 :])

    group_labels = root.findall(".//svg:text[@data-group-label]", SVG)
    for label in group_labels:
        label_box = _box(label)
        assert all(not _overlaps(label_box, node_box) for node_box in nodes.values())
        assert all(not _overlaps(label_box, _box(other)) for other in group_labels if other is not label)

    for edge in root.findall(".//svg:path[@data-edge-id]", SVG):
        unrelated = [box for identifier, box in nodes.items() if identifier not in {edge.attrib["data-source"], edge.attrib["data-target"]}]
        assert all(not _segment_crosses_box(segment, box) for segment in _route_segments(edge.attrib["d"]) for box in unrelated)

    labels = [_box(item) for item in root.findall(".//svg:text[@data-edge-label]", SVG)]
    assert len(labels) == len(set(labels))
    assert all(not _overlaps(label, node) for label in labels for node in nodes.values())


def test_operational_routes_use_orthogonal_channels_without_unrelated_node_intrusion(tmp_path) -> None:
    spec = _actual_specs(tmp_path)["conops"]
    root = _root(render_diagram_svg(spec))
    nodes = {item.attrib["data-node-id"]: _box(item) for item in root.findall(".//svg:g[@data-node-id]", SVG)}

    for edge in root.findall(".//svg:path[@data-edge-id]", SVG):
        segments = _route_segments(edge.attrib["d"])
        unrelated = [box for identifier, box in nodes.items() if identifier not in {edge.attrib["data-source"], edge.attrib["data-target"]}]
        assert all(x1 == x2 or y1 == y2 for x1, y1, x2, y2 in segments)
        assert all(not _segment_crosses_box(segment, box) for segment in segments for box in unrelated)


@pytest.mark.parametrize("direction", ["LR", "TB"])
def test_edge_label_tracks_route_and_retains_hidden_text_in_title(direction: str) -> None:
    spec = DiagramSpec(
        "labels",
        "Labels",
        direction=direction,
        nodes=[DiagramNode("a", "A", "component"), DiagramNode("b", "B", "component")],
        edges=[DiagramEdge("a", "b", "uses", "same label") for _ in range(8)],
    )

    root = _root(render_diagram_svg(spec))
    labels = root.findall(".//svg:text[@data-edge-label]", SVG)
    edges = root.findall(".//svg:path[@data-edge-id]", SVG)

    assert len({_box(item) for item in labels}) == len(labels)
    assert all(not _overlaps(first, second) for index, first in enumerate(map(_box, labels)) for second in list(map(_box, labels))[index + 1 :])
    assert all(edge.find("svg:title", SVG) is not None and "same label" in edge.find("svg:title", SVG).text for edge in edges)
    assert all(edge.attrib.get("data-label-hidden") in {"true", "false"} for edge in edges)
    _, _, view_width, view_height = (float(value) for value in root.attrib["viewBox"].split())
    for edge, label in zip(edges, labels):
        x, y, width, height = _box(label)
        assert x + width <= view_width and y + height <= view_height
        segments = _route_segments(edge.attrib["d"])
        assert any(
            segment[0] == segment[2] and abs(x - segment[0]) <= 8
            or segment[1] == segment[3] and abs(y - segment[1]) <= 14
            for segment in segments
        )


def test_tb_mixed_width_edge_labels_reserve_non_overlapping_route_lanes() -> None:
    spec = DiagramSpec(
        "mixed-labels",
        "Mixed labels",
        direction="TB",
        nodes=[DiagramNode("a", "A", "component"), DiagramNode("b", "B", "component")],
        edges=[
            DiagramEdge("a", "b", "uses", "x"),
            DiagramEdge("a", "b", "uses", "a substantially longer edge label"),
            DiagramEdge("a", "b", "uses", "medium label"),
        ],
    )

    root = _root(render_diagram_svg(spec))
    labels = [_box(item) for item in root.findall(".//svg:text[@data-edge-label]", SVG)]

    assert all(not _overlaps(first, second) for index, first in enumerate(labels) for second in labels[index + 1 :])


def test_nested_group_headers_and_padding_do_not_overlap_children() -> None:
    root = _root(render_diagram_svg(_spec()))
    containers = {item.attrib["data-container-id"]: item for item in root.findall(".//svg:g[@data-container-id]", SVG)}
    parent, child = containers["system"], containers["functions"]
    parent_label = parent.find("svg:text[@data-group-label]", SVG)
    child_label = child.find("svg:text[@data-group-label]", SVG)

    assert parent_label is not None and child_label is not None
    assert not _overlaps(_box(parent_label), _box(child_label))
    assert float(child.attrib["data-y"]) >= float(parent.attrib["data-y"]) + float(parent.attrib["data-header-height"]) + 8
    parent_box, child_box = _box(parent), _box(child)
    assert parent_box[0] <= child_box[0] - 8
    assert parent_box[1] <= child_box[1] - float(parent.attrib["data-header-height"])
    assert parent_box[0] + parent_box[2] >= child_box[0] + child_box[2] + 8
    assert parent_box[1] + parent_box[3] >= child_box[1] + child_box[3] + 8


@pytest.mark.skipif(shutil.which("rsvg-convert") is None, reason="rsvg-convert is optional")
def test_actual_projector_svgs_render_with_rsvg(tmp_path) -> None:
    for name, spec in _actual_specs(tmp_path).items():
        svg_path = tmp_path / f"{name}.svg"
        png_path = tmp_path / f"{name}.png"
        svg_path.write_text(render_diagram_svg(spec), encoding="utf-8")
        subprocess.run(["rsvg-convert", str(svg_path), "-o", str(png_path)], check=True, capture_output=True)
        assert png_path.stat().st_size > 0


def test_real_logs_db_logical_svg_is_practically_bounded_and_collision_free(tmp_path) -> None:
    from architecture_model.core.view_curation import load_viewer_curation

    repo = Path("/Users/baigm2/Documents/Projects/logs_db")
    if not (repo / ".architecture/viewer-curation.yaml").is_file():
        pytest.skip("logs-db curation unavailable")
    context = ArchitectureViewContext.from_repo(repo)
    spec = project_logical_architecture(context, load_viewer_curation(repo, context).views.logical)
    root = _root(render_diagram_svg(spec, DiagramRenderOptions(max_width=1800, max_height=1200)))
    _, _, width, height = [float(value) for value in root.attrib["viewBox"].split()]
    nodes = {item.attrib["data-node-id"]: _box(item) for item in root.findall(".//svg:g[@data-node-id]", SVG)}

    assert width <= 1800 and height <= 1200
    for edge in root.findall(".//svg:path[@data-edge-id]", SVG):
        unrelated = [box for identifier, box in nodes.items() if identifier not in {edge.attrib["data-source"], edge.attrib["data-target"]}]
        assert all(not _segment_crosses_box(segment, box) for segment in _route_segments(edge.attrib["d"]) for box in unrelated)
    if shutil.which("rsvg-convert"):
        svg_path, png_path = tmp_path / "logical.svg", tmp_path / "logical.png"
        svg_path.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")
        subprocess.run(["rsvg-convert", str(svg_path), "-o", str(png_path)], check=True, capture_output=True)
        assert png_path.stat().st_size > 0


def test_view_aware_layouts_are_compact_and_edge_labels_do_not_collide(tmp_path) -> None:
    specs = _actual_specs(tmp_path)
    expected = {
        "conops": "operational-lanes",
        "functional": "functional-flow",
        "logical": "logical-tiers",
        "use-cases": "use-case-catalog",
    }
    for name, spec in specs.items():
        assert spec.layout == expected[name]
        root = _root(render_diagram_svg(spec))
        _, _, width, height = [float(value) for value in root.attrib["viewBox"].split()]
        if name == "functional":
            assert width <= 1400 and height <= 900
            nodes = _boxes(root)
            occupied = sum(box[2] * box[3] for box in nodes)
            assert occupied / (width * height) >= .08
        labels = [_box(item) for item in root.findall(".//svg:text[@data-edge-label]", SVG)]
        nodes = _boxes(root)
        assert all(not _overlaps(label, node) for label in labels for node in nodes)
        assert all(not _overlaps(first, second) for index, first in enumerate(labels) for second in labels[index + 1:])


def test_logical_tier_cycles_use_distinct_routes(tmp_path) -> None:
    spec = project_logical_architecture(logical_context(tmp_path))
    root = _root(render_diagram_svg(spec))
    routes = {
        (edge.attrib["data-source"], edge.attrib["data-target"]): edge.attrib["d"]
        for edge in root.findall(".//svg:path[@data-edge-id]", SVG)
        if edge.attrib["data-kind"] == "depends-on"
    }
    assert routes[("node:root::SYS-WEB", "node:root::SYS-DOMAIN")] != routes[("node:root::SYS-DOMAIN", "node:root::SYS-WEB")]


def test_real_logs_db_curated_views_meet_objective_geometry(tmp_path) -> None:
    from architecture_model.core.view_curation import load_viewer_curation

    repo = Path("/Users/baigm2/Documents/Projects/logs_db")
    if not (repo / ".architecture/viewer-curation.yaml").is_file():
        pytest.skip("logs-db curation unavailable")
    context = ArchitectureViewContext.from_repo(repo)
    curated = load_viewer_curation(repo, context).views
    specs = {
        "conops": project_conops(context, curated.conops),
        "functional": project_functional_architecture(context, curated.functional),
        "logical": project_logical_architecture(context, curated.logical),
        "use-cases": project_use_cases(context, curated.use_cases),
    }
    for name, spec in specs.items():
        root = _root(render_diagram_svg(spec))
        crossings = _visual_crossings(root)
        assert crossings[0] <= ({"conops": 0, "functional": 0, "logical": 1, "use-cases": 0}[name]), (name, crossings)
        assert crossings[1] == 0, (name, crossings)
        nodes = {item.attrib["data-node-id"]: _box(item) for item in root.findall(".//svg:g[@data-node-id]", SVG)}
        labels = [_box(item) for item in root.findall(".//svg:text[@data-edge-label]", SVG)]
        assert all(not _overlaps(label, node) for label in labels for node in nodes.values()), name
        assert all(not _overlaps(first, second) for index, first in enumerate(labels) for second in labels[index + 1:]), name
        _, _, view_width, view_height = [float(value) for value in root.attrib["viewBox"].split()]
        assert view_width <= 1800 and view_height <= 1200, name
        if shutil.which("rsvg-convert"):
            svg_path, png_path = tmp_path / f"{name}.svg", tmp_path / f"{name}.png"
            svg_path.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")
            subprocess.run(["rsvg-convert", str(svg_path), "-o", str(png_path)], check=True, capture_output=True)
            assert png_path.stat().st_size > 0

    conops_root = _root(render_diagram_svg(specs["conops"]))
    conops_lanes = {item.attrib["data-container-id"]: _box(item) for item in conops_root.findall(".//svg:g[@data-container-id]", SVG)}
    for node in conops_root.findall(".//svg:g[@data-node-id]", SVG):
        lane = next(item.lane for item in specs["conops"].nodes if item.id == node.attrib["data-node-id"])
        assert lane in conops_lanes
        node_x, node_y, node_width, node_height = _box(node)
        lane_x, lane_y, lane_width, lane_height = conops_lanes[lane]
        assert lane_x <= node_x and lane_y <= node_y
        assert node_x + node_width <= lane_x + lane_width
        assert node_y + node_height <= lane_y + lane_height
    boundary = next(node for node in specs["conops"].nodes if node.id == "conops:system-boundary")
    assert any(boundary.id in {edge.source, edge.target} for edge in specs["conops"].edges)

    functional_root = _root(render_diagram_svg(specs["functional"]))
    _, _, width, height = [float(value) for value in functional_root.attrib["viewBox"].split()]
    functional_boxes = _boxes(functional_root)
    assert width <= 1400 and height <= 900
    assert sum(box[2] * box[3] for box in functional_boxes) / (width * height) >= .08

    assert len(specs["logical"].lanes) == 5
    assert all(node.kind not in {"actor", "external", "summary"} for node in specs["logical"].nodes)
    logical_root = _root(render_diagram_svg(specs["logical"]))
    cycle_paths = [edge.attrib["d"] for edge in logical_root.findall(".//svg:path[@data-edge-id]", SVG) if "is-critical" in edge.attrib["class"]]
    assert len(cycle_paths) == len(set(cycle_paths))
    logical_dependencies = [edge for edge in logical_root.findall(".//svg:path[@data-edge-id]", SVG) if edge.attrib["data-kind"] == "depends-on"]
    dependency_ids = {edge.attrib["id"] for edge in logical_dependencies}
    visible_dependency_labels = [
        label.text for label in logical_root.findall(".//svg:text[@data-edge-label]", SVG)
        if label.attrib["data-edge-label"] in dependency_ids
    ]
    assert all("×" in label or "(" in label for label in visible_dependency_labels)
    assert all(float(edge.attrib["stroke-width"]) < 2 for edge in logical_dependencies if "is-critical" in edge.attrib["class"])

    assert len([node for node in specs["use-cases"].nodes if node.kind == "use-case"]) == 10
    assert all(node.status != "omitted" for node in specs["use-cases"].nodes)


def _real_logs_db_specs() -> dict[str, DiagramSpec]:
    from architecture_model.core.view_curation import load_viewer_curation

    repo = Path("/Users/baigm2/Documents/Projects/logs_db")
    if not (repo / ".architecture/viewer-curation.yaml").is_file():
        pytest.skip("logs-db curation unavailable")
    context = ArchitectureViewContext.from_repo(repo)
    curated = load_viewer_curation(repo, context).views
    return {
        "conops": project_conops(context, curated.conops),
        "logical": project_logical_architecture(context, curated.logical),
        "use-cases": project_use_cases(context, curated.use_cases),
    }


def test_real_conops_is_centered_compact_and_locally_routed() -> None:
    root = _root(render_diagram_svg(_real_logs_db_specs()["conops"]))
    nodes = {item.attrib["data-node-id"]: _box(item) for item in root.findall(".//svg:g[@data-node-id]", SVG)}
    scenarios = [box for identifier, box in nodes.items() if identifier.startswith("scenario-")]
    assert len(scenarios) == 5
    stack_top = min(box[1] for box in scenarios)
    stack_bottom = max(box[1] + box[3] for box in scenarios)
    middle_third = (stack_top + (stack_bottom - stack_top) / 3, stack_bottom - (stack_bottom - stack_top) / 3)
    for identifier in ("conops:system-boundary", "conops:outcomes"):
        center = nodes[identifier][1] + nodes[identifier][3] / 2
        assert middle_third[0] <= center <= middle_third[1]

    _, _, width, height = [float(value) for value in root.attrib["viewBox"].split()]
    for edge in root.findall(".//svg:path[@data-edge-id]", SVG):
        segments = _route_segments(edge.attrib["d"])
        xs = [coordinate for segment in segments for coordinate in (segment[0], segment[2])]
        ys = [coordinate for segment in segments for coordinate in (segment[1], segment[3])]
        assert (max(xs) - min(xs)) + (max(ys) - min(ys)) <= .7 * (width + height)
        unrelated = [box for identifier, box in nodes.items() if identifier not in {edge.attrib["data-source"], edge.attrib["data-target"]}]
        assert all(not _segment_crosses_box(segment, box) for segment in segments for box in unrelated)
        assert "data-full-label" in edge.attrib
    labels = root.findall(".//svg:text[@data-edge-label]", SVG)
    assert all(len(label.text or "") <= 18 and len((label.text or "").split()) <= 3 for label in labels)
    assert all(not _overlaps(_box(first), _box(second)) for index, first in enumerate(labels) for second in labels[index + 1:])


def test_real_use_cases_form_two_actor_owned_route_bands() -> None:
    spec = _real_logs_db_specs()["use-cases"]
    root = _root(render_diagram_svg(spec))
    bands = root.findall(".//svg:g[@data-actor-band]", SVG)
    assert len(bands) == 2
    assert sorted(int(item.attrib["data-case-count"]) for item in bands) == [4, 6]
    nodes = {item.attrib["data-node-id"]: _box(item) for item in root.findall(".//svg:g[@data-node-id]", SVG)}
    for band in bands:
        box = _box(band)
        member_ids = band.attrib["data-members"].split()
        assert len(member_ids) == int(band.attrib["data-case-count"]) + 1
        assert all(
            box[0] <= nodes[identifier][0] and nodes[identifier][0] + nodes[identifier][2] <= box[0] + box[2]
            and box[1] <= nodes[identifier][1] and nodes[identifier][1] + nodes[identifier][3] <= box[1] + box[3]
            for identifier in member_ids
        )
        for edge in root.findall(".//svg:path[@data-edge-id]", SVG):
            if edge.attrib["data-source"] != member_ids[0]:
                continue
            for x1, y1, x2, y2 in _route_segments(edge.attrib["d"]):
                assert box[0] <= min(x1, x2) and max(x1, x2) <= box[0] + box[2]
                assert box[1] <= min(y1, y2) and max(y1, y2) <= box[1] + box[3]
    assert _visual_crossings(root)[0] == 0
    _, _, width, height = [float(value) for value in root.attrib["viewBox"].split()]
    assert width <= 1800 and height <= 1200


def test_real_logical_dependencies_use_clear_tier_gutters_without_labels() -> None:
    spec = _real_logs_db_specs()["logical"]
    assert all("No cross-system dependency" not in node.badges for node in spec.nodes)
    assert any("No cross-system link" in node.badges for node in spec.nodes)
    root = _root(render_diagram_svg(spec))
    lanes = [_box(item) for item in root.findall(".//svg:g[@data-container-id]", SVG)]
    dependency_ids = {
        edge.attrib["id"] for edge in root.findall(".//svg:path[@data-edge-id]", SVG)
        if edge.attrib["data-kind"] in {"dependency", "depends-on"}
    }
    assert not [
        label for label in root.findall(".//svg:text[@data-edge-label]", SVG)
        if label.attrib["data-edge-label"] in dependency_ids
    ]
    for edge in root.findall(".//svg:path[@data-edge-id]", SVG):
        if edge.attrib["id"] not in dependency_ids:
            continue
        for segment in _route_segments(edge.attrib["d"]):
            for left, top, lane_width, lane_height in lanes:
                right, bottom = left + lane_width, top + lane_height
                assert not (segment[0] == segment[2] and segment[0] in {left, right} and max(min(segment[1], segment[3]), top) < min(max(segment[1], segment[3]), bottom))
                assert not (segment[1] == segment[3] and segment[1] in {top, top + 24, bottom} and max(min(segment[0], segment[2]), left) < min(max(segment[0], segment[2]), right))
        if "is-critical" in edge.attrib["class"]:
            assert float(edge.attrib["stroke-width"]) < 2
    assert _visual_crossings(root)[0] <= 1


def test_use_case_catalog_places_actors_in_dedicated_left_lane(tmp_path) -> None:
    spec = project_use_cases(use_case_context(tmp_path, 10))
    root = _root(render_diagram_svg(spec))
    actor_boxes = [
        _box(node) for node in root.findall(".//svg:g[@data-node-id]", SVG)
        if node.attrib["data-kind"] in {"actor", "external"}
    ]
    case_boxes = {
        node.attrib["data-node-id"]: _box(node)
        for node in root.findall(".//svg:g[@data-node-id]", SVG)
        if node.attrib["data-kind"] == "use-case"
    }

    assert actor_boxes and case_boxes
    assert max(box[0] + box[2] for box in actor_boxes) < min(box[0] for box in case_boxes.values())


def test_use_case_catalog_assigns_shared_case_once_without_crossing_actor_bands() -> None:
    spec = DiagramSpec(
        "shared-catalog", "Shared catalog", layout="use-case-catalog",
        nodes=[
            DiagramNode("actor-a", "Actor A", "actor"),
            DiagramNode("actor-b", "Actor B", "actor"),
            DiagramNode("case-a", "Case A", "use-case"),
            DiagramNode("case-b", "Case B", "use-case"),
            DiagramNode("case-shared", "Shared", "use-case"),
        ],
        edges=[
            DiagramEdge("actor-a", "case-a", "participates"),
            DiagramEdge("actor-b", "case-b", "participates"),
            DiagramEdge("actor-a", "case-shared", "participates"),
            DiagramEdge("actor-b", "case-shared", "participates"),
        ],
    )
    root = _root(render_diagram_svg(spec))
    boxes = {node.attrib["data-node-id"]: _box(node) for node in root.findall(".//svg:g[@data-node-id]", SVG)}
    bands = root.findall(".//svg:g[@data-actor-band]", SVG)
    assert len(bands) == 2
    owners = [band for band in bands if "case-shared" in band.attrib["data-members"].split()]
    assert len(owners) == 2
    assert boxes["case-shared"][1] < boxes["actor-b"][1]


def test_edge_labels_have_track_contrast_and_full_title_detail() -> None:
    spec = DiagramSpec(
        "contrast", "Contrast", layout="functional-flow",
        nodes=[DiagramNode("a", "A", "component"), DiagramNode("b", "B", "component")],
        edges=[DiagramEdge("a", "b", "data-flow", "compact", title="Detailed transfer label")],
    )
    root = _root(render_diagram_svg(spec))
    label = root.find(".//svg:text[@data-edge-label]", SVG)
    edge = root.find(".//svg:path[@data-edge-id]", SVG)

    assert label is not None and "edge-label-contrast" in label.attrib["class"]
    assert edge is not None and "Detailed transfer label" in edge.find("svg:title", SVG).text


def _contrast(first: str, second: str) -> float:
    def luminance(value: str) -> float:
        channels = [int(value[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        channels = [channel / 12.92 if channel <= .04045 else ((channel + .055) / 1.055) ** 2.4 for channel in channels]
        return .2126 * channels[0] + .7152 * channels[1] + .0722 * channels[2]
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + .05) / (dark + .05)


@pytest.mark.parametrize("theme,background,text,surface,edge", [
    ("light", "#ffffff", "#172033", "#f8fafc", "#475569"),
    ("dark", "#0f172a", "#f8fafc", "#1e293b", "#cbd5e1"),
])
def test_standalone_svg_embeds_explicit_accessible_theme(theme, background, text, surface, edge) -> None:
    options = DiagramRenderOptions(theme=theme)
    panel = render_diagram_panel(_spec(), options)
    root = _root(panel.svg)
    canvas = root.find("svg:rect[@data-canvas-background]", SVG)

    assert canvas is not None and canvas.attrib["fill"] == background
    assert root.attrib["data-theme"] == theme
    assert f"--diagram-text: {text}" in panel.svg
    assert f"--diagram-surface: {surface}" in panel.svg
    assert f"--diagram-edge: {edge}" in panel.svg
    assert "prefers-color-scheme" not in panel.svg
    assert panel.theme == theme and panel.to_dict()["theme"] == theme
    assert _contrast(background, text) >= 7
    assert _contrast(surface, text) >= 7
    assert _contrast(background, edge) >= 3
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] in {"rect", "path", "polygon", "circle", "ellipse", "text"}:
            assert "var(" not in " ".join(element.attrib.values())
    assert all("fill" in item.attrib for item in root.findall(".//svg:text", SVG))
    assert all("stroke" in item.attrib for item in root.findall(".//svg:path[@data-edge-id]", SVG))
    for shape in root.findall('.//*[@class="node-shape"]'):
        assert "fill" in shape.attrib and "stroke" in shape.attrib


def test_renderer_rejects_unknown_theme() -> None:
    with pytest.raises(ValueError, match="theme"):
        render_diagram_svg(_spec(), DiagramRenderOptions(theme="system"))


@pytest.mark.skipif(shutil.which("rsvg-convert") is None, reason="rsvg-convert is optional")
def test_rsvg_png_uses_explicit_light_background_pixel(tmp_path) -> None:
    svg_path, png_path = tmp_path / "light.svg", tmp_path / "light.png"
    svg_path.write_text(render_diagram_svg(_spec()), encoding="utf-8")
    subprocess.run(["rsvg-convert", str(svg_path), "-o", str(png_path)], check=True, capture_output=True)
    data = png_path.read_bytes()

    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", data[16:24])
    assert width > 0 and height > 0
    offset, compressed = 8, b""
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        if kind == b"IDAT":
            compressed += payload
        offset += length + 12
    scanline = zlib.decompress(compressed)
    assert scanline[1:4] == b"\xff\xff\xff"


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


@pytest.mark.parametrize("layout", ["detail-cards", "operational-detail", "functional-detail", "logical-detail", "use-case-sequence"])
def test_semantic_drilldown_layouts_are_compact_and_well_utilized(layout: str) -> None:
    lanes = [DiagramGroup("lane-a", "Primary", "tier", order=0), DiagramGroup("lane-b", "Secondary", "tier", order=1)] if layout == "logical-detail" else []
    nodes = [
        DiagramNode(
            f"n-{index}", f"Node {index}",
            "capability" if layout == "functional-detail" and index < 3 else "step" if layout == "use-case-sequence" else "component",
            lane="lane-a" if lanes and index < 6 else "lane-b" if lanes else "",
            metrics={"order": index} if layout == "use-case-sequence" else {},
        )
        for index in range(12)
    ]
    edges = [DiagramEdge(f"n-{index}", f"n-{index + 1}", "next") for index in range(11)]
    root = _root(render_diagram_svg(DiagramSpec("semantic", "Semantic", layout=layout, nodes=nodes, edges=edges, lanes=lanes)))
    _, _, width, height = [float(value) for value in root.attrib["viewBox"].split()]
    rendered = _boxes(root)

    assert width <= 1800 and height <= 1200
    assert sum(box[2] * box[3] for box in rendered) / (width * height) >= .25
    nodes_by_id = {item.attrib["data-node-id"]: _box(item) for item in root.findall(".//svg:g[@data-node-id]", SVG)}
    for edge in root.findall(".//svg:path[@data-edge-id]", SVG):
        unrelated = [box for identifier, box in nodes_by_id.items() if identifier not in {edge.attrib["data-source"], edge.attrib["data-target"]}]
        assert all(not _segment_crosses_box(segment, box) for segment in _route_segments(edge.attrib["d"]) for box in unrelated)
    assert _visual_crossings(root)[0] <= 1


def test_conops_overview_shows_only_source_and_scenario_chain_labels_with_full_titles() -> None:
    spec = DiagramSpec(
        "conops-labels", "ConOps", layout="operational-lanes",
        lanes=[
            DiagramGroup("actors", "Actors", "lane", order=0), DiagramGroup("scenarios", "Scenarios", "lane", order=1),
            DiagramGroup("boundary", "Boundary", "lane", order=2), DiagramGroup("outcomes", "Outcomes", "lane", order=3),
        ],
        nodes=[
            DiagramNode("external", "Source", "external", lane="actors"),
            DiagramNode("acquire", "Acquire", "scenario", lane="scenarios"),
            DiagramNode("enrich", "Enrich", "scenario", lane="scenarios"),
            DiagramNode("system", "System", "system", lane="boundary"),
            DiagramNode("outcome", "Outcome", "outcome", lane="outcomes"),
        ],
        edges=[
            DiagramEdge("external", "acquire", "exchange", "Source records", title="Full source provenance"),
            DiagramEdge("acquire", "enrich", "operational-flow", "Validated records", title="Full scenario exchange"),
            DiagramEdge("acquire", "system", "allocation", "Delivered by", title="Full allocation provenance"),
            DiagramEdge("enrich", "outcome", "operational-flow", "Published outcomes", title="Full outcome provenance"),
        ],
    )
    root = _root(render_diagram_svg(spec))
    labels = root.findall(".//svg:text[@data-edge-label]", SVG)

    assert {label.text for label in labels} == {"Source records", "Validated records"}
    assert all(edge.find("svg:title", SVG).text.startswith("Full ") for edge in root.findall(".//svg:path[@data-edge-id]", SVG))


@pytest.mark.skipif(shutil.which("rsvg-convert") is None, reason="rsvg-convert is optional")
def test_real_logs_db_largest_curated_panels_meet_drilldown_geometry(tmp_path) -> None:
    from architecture_model.core.view_curation import load_viewer_curation

    repo = Path("/Users/baigm2/Documents/Projects/logs_db")
    if not (repo / ".architecture/viewer-curation.yaml").is_file():
        pytest.skip("logs-db curation unavailable")
    context = ArchitectureViewContext.from_repo(repo)
    curated = load_viewer_curation(repo, context).views
    specs = {
        "conops": project_conops(context, curated.conops),
        "functional": project_functional_architecture(context, curated.functional),
        "logical": project_logical_architecture(context, curated.logical),
        "use-cases": project_use_cases(context, curated.use_cases),
    }
    for name, root_spec in specs.items():
        descendants = [root_spec]
        for spec in descendants:
            descendants.extend(item.spec for item in spec.drilldowns if item.spec)
        rendered = [(spec, _root(render_diagram_svg(spec))) for spec in descendants]
        spec, root = max(rendered, key=lambda item: len(item[1].findall(".//svg:g[@data-node-id]", SVG)))
        _, _, width, height = [float(value) for value in root.attrib["viewBox"].split()]
        nodes = {item.attrib["data-node-id"]: _box(item) for item in root.findall(".//svg:g[@data-node-id]", SVG)}
        containers = root.findall(".//svg:g[@data-container-id]", SVG)

        assert width <= 1800 and height <= 1200, (name, spec.id, width, height)
        if width > 800 or height > 800:
            utilization = sum(box[2] * box[3] for box in nodes.values()) / (width * height)
            assert utilization >= .25, (name, spec.id, utilization)
        assert all(any(node.lane == item.attrib["data-container-id"] or node.group == item.attrib["data-container-id"] for node in spec.nodes) for item in containers)
        for edge in root.findall(".//svg:path[@data-edge-id]", SVG):
            unrelated = [box for identifier, box in nodes.items() if identifier not in {edge.attrib["data-source"], edge.attrib["data-target"]}]
            assert all(not _segment_crosses_box(segment, box) for segment in _route_segments(edge.attrib["d"]) for box in unrelated), (name, spec.id)
        assert _visual_crossings(root)[0] <= 1, (name, spec.id, _visual_crossings(root))

        svg_path, png_path = tmp_path / f"{name}-{spec.id.replace(':', '-')}.svg", tmp_path / f"{name}.png"
        svg_path.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")
        subprocess.run(["rsvg-convert", str(svg_path), "-o", str(png_path)], check=True, capture_output=True)
        assert png_path.stat().st_size > 0

    conops = _root(render_diagram_svg(specs["conops"]))
    labels = [_box(item) for item in conops.findall(".//svg:text[@data-edge-label]", SVG)]
    assert all(not _overlaps(first, second) for index, first in enumerate(labels) for second in labels[index + 1:])
    assert _visual_crossings(conops) == (0, 0)
