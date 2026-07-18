"""Tests for deepened manifest types and AST extraction."""
import textwrap
from pathlib import Path

from architecture_model.manifest.types import FunctionInfo
from architecture_model.manifest.scanner import scan_file


def test_function_info_new_fields_defaults():
    fi = FunctionInfo(name="foo", signature="foo()")
    assert fi.calls == []
    assert fi.docstring is None
    assert fi.raises == []


def test_function_info_new_fields_explicit():
    fi = FunctionInfo(name="foo", signature="foo()", docstring="doc", calls=["bar"], raises=["ValueError"])
    assert fi.docstring == "doc"
    assert fi.calls == ["bar"]
    assert fi.raises == ["ValueError"]


def test_scanner_extracts_function_docstring(tmp_path):
    src = tmp_path / "example.py"
    src.write_text(textwrap.dedent('''
        def greet(name: str) -> str:
            """Return a greeting for the given name."""
            return f"Hello, {name}"
    '''))
    info = scan_file(tmp_path, src)
    assert info.functions[0].docstring == "Return a greeting for the given name."


def test_scanner_extracts_function_calls(tmp_path):
    src = tmp_path / "example.py"
    src.write_text(textwrap.dedent('''
        def process(data):
            validated = validate(data)
            result = transform(validated)
            return format_output(result)
    '''))
    info = scan_file(tmp_path, src)
    func = info.functions[0]
    assert "validate" in func.calls
    assert "transform" in func.calls
    assert "format_output" in func.calls


def test_scanner_extracts_raises(tmp_path):
    src = tmp_path / "example.py"
    src.write_text(textwrap.dedent('''
        def divide(a, b):
            if b == 0:
                raise ValueError("Cannot divide by zero")
            if not isinstance(a, (int, float)):
                raise TypeError("a must be numeric")
            return a / b
    '''))
    info = scan_file(tmp_path, src)
    func = info.functions[0]
    assert "ValueError" in func.raises
    assert "TypeError" in func.raises


def test_scanner_docstring_none_when_absent(tmp_path):
    src = tmp_path / "example.py"
    src.write_text('def nodoc(): return 42\n')
    info = scan_file(tmp_path, src)
    assert info.functions[0].docstring is None


def test_to_dict_includes_new_fields_when_present(tmp_path):
    src = tmp_path / "example.py"
    src.write_text(textwrap.dedent('''
        def greet(name: str) -> str:
            """Say hello."""
            return format_name(name)
    '''))
    info = scan_file(tmp_path, src)
    d = info.to_dict()
    func_dict = d["functions"][0]
    assert func_dict["docstring"] == "Say hello."
    assert "format_name" in func_dict["calls"]


def test_to_dict_omits_empty_new_fields():
    fi = FunctionInfo(name="foo", signature="foo()")
    from architecture_model.manifest.types import ModuleInfo, ModuleStatus
    mod = ModuleInfo(
        file="test.py", name="Test", docstring=None,
        functions=[fi], imports=[], line_count=1,
        status=ModuleStatus.DORMANT, classes=[],
    )
    d = mod.to_dict()
    func_dict = d["functions"][0]
    assert "calls" not in func_dict
    assert "docstring" not in func_dict
    assert "raises" not in func_dict
