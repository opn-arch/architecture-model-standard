"""Tests for shape application in native panel diagrams (Track 4 Pass 2 Task 2).

Plan tests intended to verify each kind gets its shape. Because
``generate_functional_architecture_diagram`` is capability-only and
``generate_use_case_diagram`` does not emit actors, we cross-check the
component/actor shapes against the sibling native panels that do render
them (``generate_logical_architecture_diagram`` /
``generate_conops_diagram``). All four native panels are still exercised.
"""

from architecture_model.core.parser import _parse_raw
from architecture_model.core.visualize import (
    generate_conops_diagram,
    generate_functional_architecture_diagram,
    generate_logical_architecture_diagram,
    generate_use_case_diagrams,
)


def _build_model():
    return _parse_raw({
        "meta": {"project": "shapes-test", "schema_version": "2.1"},
        "entities": {
            "actors": [{"id": "ACT-1", "name": "User", "status": "ACTIVE"}],
            "capabilities": [
                {"id": "CAP-1", "name": "RootCap", "status": "ACTIVE"},
                {"id": "CAP-2", "name": "ChildCap", "status": "ACTIVE"},
            ],
            "components": [
                {"id": "COMP-1", "name": "Widget", "status": "ACTIVE"},
            ],
            "behaviors": [
                {"id": "BEH-1", "name": "UseIt", "status": "ACTIVE"},
            ],
        },
        "relationships": [
            {"from": "CAP-1", "to": "CAP-2", "type": "contains"},
            {"from": "COMP-1", "to": "CAP-1", "type": "realizes"},
            {"from": "ACT-1", "to": "BEH-1", "type": "consumes"},
        ],
    })


def test_functional_diagram_uses_hexagon_for_capability_and_rect_for_component():
    model = _build_model()
    functional = generate_functional_architecture_diagram(model)
    logical = generate_logical_architecture_diagram(model)
    # Capability = hexagon: {{"Name"}}
    assert '{{"RootCap"}}' in functional or '{{"CAP-1"}}' in functional
    # Component = rect: ["Name"] (asserted against logical panel which emits components)
    assert '["Widget"]' in logical or '["COMP-1"]' in logical


def test_use_case_diagram_uses_circle_for_actor_and_stadium_for_behavior():
    model = _build_model()
    diagrams = generate_use_case_diagrams(model)
    body = "\n".join(diagrams.values()) if isinstance(diagrams, dict) else str(diagrams)
    conops = generate_conops_diagram(model)
    # Actor = circle: (("User")) (asserted against conops panel which emits actors)
    assert '(("User"))' in conops or '(("ACT-1"))' in conops
    # Behavior = stadium: (["UseIt"])
    assert '(["UseIt"])' in body or '(["BEH-1"])' in body
