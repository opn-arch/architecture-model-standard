"""Tests for the body_hints module — AST-based body hint extraction."""
import textwrap
from pathlib import Path

import pytest

from architecture_model.manifest.body_hints import (
    BodyComplexity,
    classify_function,
    extract_body_hint,
    extract_file_hints,
)
from architecture_model.core.types import FunctionSignature


# ---------------------------------------------------------------------------
# TestClassifyFunction
# ---------------------------------------------------------------------------

class TestClassifyFunction:
    """Tests for classify_function — categorizes by body statement count."""

    def test_trivial_single_statement(self):
        source = textwrap.dedent("""\
            def greet(name):
                return f"Hello, {name}"
        """)
        assert classify_function(source, "greet") == BodyComplexity.TRIVIAL

    def test_trivial_with_docstring(self):
        """Docstring should NOT be counted as a statement."""
        source = textwrap.dedent("""\
            def greet(name):
                \"\"\"Greet someone.\"\"\"
                return f"Hello, {name}"
        """)
        assert classify_function(source, "greet") == BodyComplexity.TRIVIAL

    def test_short_two_statements(self):
        source = textwrap.dedent("""\
            def add(a, b):
                result = a + b
                return result
        """)
        assert classify_function(source, "add") == BodyComplexity.SHORT

    def test_short_five_statements(self):
        source = textwrap.dedent("""\
            def process(data):
                x = data[0]
                y = data[1]
                z = x + y
                result = z * 2
                return result
        """)
        assert classify_function(source, "process") == BodyComplexity.SHORT

    def test_complex_six_statements(self):
        source = textwrap.dedent("""\
            def complex_func(items):
                result = []
                filtered = []
                for item in items:
                    if item > 0:
                        filtered.append(item)
                result = filtered
                total = sum(result)
                avg = total / len(result)
                return avg
        """)
        assert classify_function(source, "complex_func") == BodyComplexity.COMPLEX

    def test_complex_with_docstring_not_counted(self):
        """6 statements + docstring = COMPLEX (docstring excluded from count)."""
        source = textwrap.dedent("""\
            def big_func(x):
                \"\"\"Do something big.\"\"\"
                a = x + 1
                b = a * 2
                c = b - 3
                d = c / 4
                e = d + 5
                return e
        """)
        assert classify_function(source, "big_func") == BodyComplexity.COMPLEX

    def test_function_not_found_raises(self):
        source = textwrap.dedent("""\
            def foo():
                pass
        """)
        with pytest.raises(ValueError):
            classify_function(source, "nonexistent")


# ---------------------------------------------------------------------------
# TestExtractBodyHint
# ---------------------------------------------------------------------------

class TestExtractBodyHint:
    """Tests for extract_body_hint — produces tiered hint strings."""

    def test_trivial_returns_exact_body(self):
        source = textwrap.dedent("""\
            def get_value():
                return 42
        """)
        hint = extract_body_hint(source, "get_value")
        assert hint == "return 42"

    def test_trivial_with_docstring(self):
        source = textwrap.dedent("""\
            def get_value():
                \"\"\"Get the value.\"\"\"
                return 42
        """)
        hint = extract_body_hint(source, "get_value")
        assert hint == "return 42"

    def test_short_returns_semicolons(self):
        source = textwrap.dedent("""\
            def add(a, b):
                result = a + b
                return result
        """)
        hint = extract_body_hint(source, "add")
        assert ";" in hint
        assert "result = a + b" in hint
        assert "return result" in hint

    def test_complex_returns_structural_summary(self):
        source = textwrap.dedent("""\
            def process(items):
                result = []
                filtered = []
                for item in items:
                    if item > 0:
                        filtered.append(item)
                result = filtered
                total = sum(result)
                avg = total / len(result)
                return avg
        """)
        hint = extract_body_hint(source, "process")
        assert "for" in hint.lower() or "for item in items" in hint
        assert "return" in hint

    def test_init_method_with_class_name(self):
        source = textwrap.dedent("""\
            class MyClass:
                def __init__(self, x, y):
                    self.x = x
                    self.y = y
        """)
        hint = extract_body_hint(source, "__init__", class_name="MyClass")
        assert "self.x = x" in hint
        assert "self.y = y" in hint

    def test_class_method_extraction(self):
        source = textwrap.dedent("""\
            class Calculator:
                def add(self, a, b):
                    return a + b
        """)
        hint = extract_body_hint(source, "add", class_name="Calculator")
        assert hint == "return a + b"

    def test_complex_with_while_and_if(self):
        source = textwrap.dedent("""\
            def search(items, target):
                idx = 0
                found = False
                while idx < len(items):
                    if items[idx] == target:
                        found = True
                        break
                    idx += 1
                return found
        """)
        hint = extract_body_hint(source, "search")
        assert "while" in hint
        assert "return" in hint


# ---------------------------------------------------------------------------
# TestExtractFileHints
# ---------------------------------------------------------------------------

class TestExtractFileHints:
    """Tests for extract_file_hints — scans entire file for FunctionSignatures."""

    def _write_source(self, tmp_path: Path, content: str) -> Path:
        """Write source to a temp .py file."""
        p = tmp_path / "module.py"
        p.write_text(textwrap.dedent(content))
        return p

    def test_extracts_public_functions(self, tmp_path):
        filepath = self._write_source(tmp_path, """\
            def public_one():
                return 1

            def public_two():
                return 2
        """)
        results = extract_file_hints(filepath)
        names = [sig.name for sig in results]
        assert "public_one" in names
        assert "public_two" in names

    def test_excludes_private_functions(self, tmp_path):
        filepath = self._write_source(tmp_path, """\
            def public_func():
                return 1

            def _private_func():
                return 2
        """)
        results = extract_file_hints(filepath)
        names = [sig.name for sig in results]
        assert "public_func" in names
        assert "_private_func" not in names

    def test_includes_init(self, tmp_path):
        filepath = self._write_source(tmp_path, """\
            class Foo:
                def __init__(self, x):
                    self.x = x

                def _private(self):
                    pass
        """)
        results = extract_file_hints(filepath)
        names = [sig.name for sig in results]
        assert "Foo.__init__" in names
        assert "Foo._private" not in names
        assert "_private" not in names

    def test_include_private_flag(self, tmp_path):
        filepath = self._write_source(tmp_path, """\
            def public_func():
                return 1

            def _private_func():
                return 2
        """)
        results = extract_file_hints(filepath, include_private=True)
        names = [sig.name for sig in results]
        assert "public_func" in names
        assert "_private_func" in names

    def test_includes_class_methods(self, tmp_path):
        filepath = self._write_source(tmp_path, """\
            class MyClass:
                def method_one(self):
                    return 1

                def method_two(self, x):
                    return x * 2
        """)
        results = extract_file_hints(filepath)
        names = [sig.name for sig in results]
        assert "MyClass.method_one" in names
        assert "MyClass.method_two" in names

    def test_body_hint_populated(self, tmp_path):
        filepath = self._write_source(tmp_path, """\
            def get_value():
                return 42
        """)
        results = extract_file_hints(filepath)
        sig = next(s for s in results if s.name == "get_value")
        assert sig.body_hint == "return 42"

    def test_params_populated(self, tmp_path):
        filepath = self._write_source(tmp_path, """\
            def compute(x: int, y: str = "hi") -> float:
                return float(x)
        """)
        results = extract_file_hints(filepath)
        sig = next(s for s in results if s.name == "compute")
        assert "x: int" in sig.params
        assert any("y" in p for p in sig.params)
        assert sig.returns == "float"

    def test_returns_populated(self, tmp_path):
        filepath = self._write_source(tmp_path, """\
            def get_name() -> str:
                return "hello"
        """)
        results = extract_file_hints(filepath)
        sig = next(s for s in results if s.name == "get_name")
        assert sig.returns == "str"

    def test_decorators_populated(self, tmp_path):
        filepath = self._write_source(tmp_path, """\
            def my_decorator(f):
                return f

            @my_decorator
            def decorated():
                return True
        """)
        results = extract_file_hints(filepath)
        sig = next(s for s in results if s.name == "decorated")
        assert "my_decorator" in sig.decorators

    def test_self_and_cls_excluded_from_params(self, tmp_path):
        filepath = self._write_source(tmp_path, """\
            class Foo:
                def method(self, x, y):
                    return x + y

                @classmethod
                def create(cls, value):
                    return cls(value)
        """)
        results = extract_file_hints(filepath)
        method_sig = next(s for s in results if s.name == "Foo.method")
        assert "self" not in method_sig.params
        create_sig = next(s for s in results if s.name == "Foo.create")
        assert "cls" not in create_sig.params

    def test_args_and_kwargs(self, tmp_path):
        filepath = self._write_source(tmp_path, """\
            def variadic(*args, **kwargs):
                return args, kwargs
        """)
        results = extract_file_hints(filepath)
        sig = next(s for s in results if s.name == "variadic")
        assert "*args" in sig.params
        assert "**kwargs" in sig.params

    def test_returns_function_signature_instances(self, tmp_path):
        filepath = self._write_source(tmp_path, """\
            def foo():
                pass
        """)
        results = extract_file_hints(filepath)
        assert all(isinstance(sig, FunctionSignature) for sig in results)
