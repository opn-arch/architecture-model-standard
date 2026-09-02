from architecture_model.core.diagram_spec import (
    DiagramDrilldown,
    DiagramEdge,
    DiagramNode,
    DiagramSpec,
    bound_diagram_spec,
)
from architecture_model.core.diagram_renderer import render_diagram_panel


def _walk(spec: DiagramSpec):
    yield spec
    for drilldown in spec.drilldowns:
        if drilldown.spec:
            yield from _walk(drilldown.spec)


def test_dense_drilldown_is_recursively_bounded_without_losing_entity_refs() -> None:
    detail = DiagramSpec(
        "dense",
        "Dense detail",
        direction="TB",
        nodes=[DiagramNode(f"node-{index:03}", f"Node {index}", "component", entity_ref=f"COMP-{index:03}") for index in range(137)],
        edges=[DiagramEdge(f"node-{index:03}", f"node-{index + 1:03}", "next") for index in range(136)],
    )
    overview = DiagramSpec(
        "overview",
        "Overview",
        nodes=[DiagramNode("dense-link", "Dense", "summary", drilldown_ref="dense-detail")],
        drilldowns=[DiagramDrilldown("dense-detail", "dense-link", spec=detail)],
    )

    bounded = bound_diagram_spec(overview)
    specs = list(_walk(bounded))
    refs = {node.entity_ref for spec in specs for node in spec.nodes if node.entity_ref}

    assert all(len(spec.nodes) <= 25 and len(spec.edges) <= 40 for spec in specs)
    assert refs == {f"COMP-{index:03}" for index in range(137)}
    assert any(node.kind == "summary" and node.label.startswith("More ") for spec in specs for node in spec.nodes)
    assert all(render_diagram_panel(spec).width <= 2400 and render_diagram_panel(spec).height <= 1800 for spec in specs)


def test_bounding_is_deterministic_and_all_drilldown_references_resolve() -> None:
    spec = DiagramSpec(
        "sequence",
        "Sequence",
        direction="TB",
        nodes=[DiagramNode(f"step-{index:03}", f"Step {index}", "step", entity_ref=f"STEP-{index:03}") for index in range(80)],
        edges=[DiagramEdge(f"step-{index:03}", f"step-{index + 1:03}", "next") for index in range(79)],
    )

    first = bound_diagram_spec(spec)
    second = bound_diagram_spec(spec)

    assert first.to_dict() == second.to_dict()
    for page in _walk(first):
        ids = {item.id for item in page.drilldowns}
        assert all(not node.drilldown_ref or node.drilldown_ref in ids for node in page.nodes)
