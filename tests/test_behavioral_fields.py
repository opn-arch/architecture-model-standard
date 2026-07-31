"""Tests for new behavioral fields on FunctionInfo."""
import pytest
from architecture_model.manifest.types import FunctionInfo


def test_function_info_has_behavioral_fields():
    fi = FunctionInfo(
        name="process", signature="(x: int) -> str",
        call_order=["validate", "transform", "save"],
        control_flow=["try_except", "for_loop"],
        data_in=["int"],
        data_out="str",
        guards=["assert x > 0"],
    )
    assert fi.call_order == ["validate", "transform", "save"]
    assert fi.control_flow == ["try_except", "for_loop"]
    assert fi.data_in == ["int"]
    assert fi.data_out == "str"
    assert fi.guards == ["assert x > 0"]


def test_function_info_defaults_empty():
    fi = FunctionInfo(name="simple", signature="() -> None")
    assert fi.call_order == []
    assert fi.control_flow == []
    assert fi.data_in == []
    assert fi.data_out == ""
    assert fi.guards == []
