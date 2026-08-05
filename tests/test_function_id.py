"""Tests for function addressability - id field (Task C2)."""
from architecture_model.core.types import FunctionSignature
from architecture_model.manifest.types import FunctionInfo


class TestFunctionId:
    def test_function_signature_has_id(self):
        fs = FunctionSignature(name="compute", params=["x"], id="COMP-1::compute")
        assert fs.id == "COMP-1::compute"

    def test_function_signature_id_default_empty(self):
        fs = FunctionSignature(name="compute", params=["x"])
        assert fs.id == ""

    def test_function_info_has_id(self):
        fi = FunctionInfo(name="compute", signature="def compute(x)", id="mod::compute")
        assert fi.id == "mod::compute"

    def test_function_info_id_default_empty(self):
        fi = FunctionInfo(name="compute", signature="def compute(x)")
        assert fi.id == ""
