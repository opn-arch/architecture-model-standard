"""Tests for schema/dataclass field parity."""
from architecture_model.core.types import FunctionSignature, TestContract, Constant, ComponentKind


def test_function_signature_has_complexity():
    sig = FunctionSignature(name="foo", params="x: int", returns="int", complexity="TRIVIAL")
    assert sig.complexity == "TRIVIAL"


def test_function_signature_complexity_optional():
    sig = FunctionSignature(name="foo", params="x: int", returns="int")
    assert sig.complexity is None


def test_test_contract_has_required_imports():
    tc = TestContract(test_file="test_foo.py", test_method="test_foo", assertion="assert x == 1",
                      contract_type="unit", required_imports=["os", "sys"])
    assert tc.required_imports == ["os", "sys"]


def test_test_contract_required_imports_default():
    tc = TestContract(test_file="test_foo.py", test_method="test_foo", assertion="assert x == 1", contract_type="unit")
    assert tc.required_imports == []


def test_constant_has_type():
    c = Constant(name="FOO", value="42", type="int")
    assert c.type == "int"


def test_constant_type_optional():
    c = Constant(name="FOO", value="42")
    assert c.type is None


def test_component_kind_has_package_cli():
    assert ComponentKind.parse("package") == "package"
    assert ComponentKind.parse("cli") == "cli"
