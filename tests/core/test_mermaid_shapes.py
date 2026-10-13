"""Tests for Mermaid shape mapping and _shape helper (Track 4 Pass 2 Task 1)."""

import pytest

from architecture_model.core.visualize import _MERMAID_SHAPE, _shape


def test_shape_mapping_covers_seven_kinds():
    """_MERMAID_SHAPE must map all seven entity kinds to bracket pairs."""
    expected = {"component", "capability", "actor", "behavior",
                "interface", "constraint", "layer"}
    assert expected.issubset(set(_MERMAID_SHAPE.keys()))


def test_shape_emits_correct_mermaid_syntax_per_kind():
    """_shape returns Mermaid node syntax with the correct bracket pair per kind."""
    assert _shape("component", "COMP_1", "MyComp") == 'COMP_1>"MyComp"]'
    assert _shape("capability", "CAP_1", "MyCap") == 'CAP_1{{"MyCap"}}'
    assert _shape("actor", "ACT_1", "MyActor") == 'ACT_1(("MyActor"))'
    assert _shape("behavior", "BEH_1", "MyBeh") == 'BEH_1(["MyBeh"])'
    assert _shape("interface", "IF_1", "MyIF") == 'IF_1[/"MyIF"/]'
    assert _shape("constraint", "CON_1", "MyCon") == 'CON_1{"MyCon"}'


def test_shape_falls_back_to_rectangle_for_unknown_kind(caplog):
    """Unknown kinds return rectangle syntax and emit a DEBUG log."""
    import logging
    caplog.set_level(logging.DEBUG, logger="architecture_model.core.visualize")
    out = _shape("system", "SYS_1", "MyS")
    assert out == 'SYS_1["MyS"]'
