"""Tests for behavioral data integration in scan_file."""
import ast
from pathlib import Path
from architecture_model.manifest.scanner import scan_file


def test_scan_file_produces_call_order(tmp_path):
    code = '''
def process(x: int) -> str:
    validated = validate(x)
    result = transform(validated)
    save(result)
    return result
'''
    f = tmp_path / "mod.py"
    f.write_text(code)
    info = scan_file(tmp_path, f)
    func = info.functions[0]
    assert func.call_order == ["validate", "transform", "save"]


def test_scan_file_produces_control_flow(tmp_path):
    code = '''
def retry(func):
    for attempt in range(3):
        try:
            return func()
        except Exception:
            pass
'''
    f = tmp_path / "mod.py"
    f.write_text(code)
    info = scan_file(tmp_path, f)
    func = info.functions[0]
    assert "try_except" in func.control_flow
    assert "for_loop" in func.control_flow


def test_scan_file_produces_guards(tmp_path):
    code = '''
def process(x):
    assert x is not None
    if x < 0:
        raise ValueError("negative")
    return x * 2
'''
    f = tmp_path / "mod.py"
    f.write_text(code)
    info = scan_file(tmp_path, f)
    func = info.functions[0]
    assert len(func.guards) == 2
    assert any("assert" in g for g in func.guards)
    assert any("raise" in g for g in func.guards)


def test_scan_file_produces_data_in_out(tmp_path):
    code = '''
def transform(x: int, y: str) -> list[str]:
    return [y] * x
'''
    f = tmp_path / "mod.py"
    f.write_text(code)
    info = scan_file(tmp_path, f)
    func = info.functions[0]
    assert func.data_in == ["int", "str"]
    assert func.data_out == "list[str]"


def test_class_methods_have_behavioral_data(tmp_path):
    code = '''
class Service:
    def run(self) -> None:
        self.setup()
        self.execute()
        self.teardown()
'''
    f = tmp_path / "mod.py"
    f.write_text(code)
    info = scan_file(tmp_path, f)
    cls = info.classes[0]
    method = cls.method_details[0]
    assert method.call_order == ["self.setup", "self.execute", "self.teardown"]
