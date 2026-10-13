"""Regression tests for entity-differentiated Mermaid shapes (C15).

The component shape is Mermaid's asymmetric-flag ``>text]`` — a rectangle
with a pointy left edge — chosen to visually distinguish structural
components from other entity kinds in composite diagrams. This matches
SysML/Arcadia convention where components carry directional markings.
"""

from architecture_model.core.visualize import (
    _MERMAID_SHAPE, _SHAPES, _shape, shape,
)


def test_component_uses_pointy_flag_in_lowlevel_shape():
    assert _MERMAID_SHAPE["component"] == (">", "]")
    assert _shape("component", "COMP_1", "MyComp") == 'COMP_1>"MyComp"]'


def test_component_uses_pointy_flag_in_high_level_shape():
    assert _SHAPES["component"] == (">", "]")
    assert shape("component", "COMP-1", "MyComp") == "COMP_1>MyComp]"


def test_shape_kinds_remain_distinct():
    """Every mapped entity kind renders with a unique bracket pair."""
    seen: dict[tuple[str, str], str] = {}
    collisions: list[tuple[str, str]] = []
    for kind, brackets in _MERMAID_SHAPE.items():
        if kind == "layer":  # layer is subgraph-based; fallback rect is expected
            continue
        if brackets in seen:
            collisions.append((seen[brackets], kind))
        else:
            seen[brackets] = kind
    assert not collisions, f"Shape collisions: {collisions}"


def test_component_shape_distinct_from_all_others():
    comp_brackets = _MERMAID_SHAPE["component"]
    for kind, brackets in _MERMAID_SHAPE.items():
        if kind == "component":
            continue
        assert brackets != comp_brackets, (
            f"{kind} collides with component shape {comp_brackets}"
        )
