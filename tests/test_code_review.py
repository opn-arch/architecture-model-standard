"""Tests for static code analysis engine."""
import textwrap
from architecture_model.quality.code_review import (
    analyze_source, CodeAnalysis, CodeIssue, IssueSeverity,
)


class TestCyclomaticComplexity:
    def test_simple_function(self):
        src = "def foo(): return 1"
        analysis = analyze_source(src, filename="test.py")
        fn = analysis.functions[0]
        assert fn.complexity == 1  # no branches

    def test_branching_function(self):
        src = textwrap.dedent("""
            def foo(x):
                if x > 0:
                    if x > 10:
                        return "big"
                    return "small"
                elif x == 0:
                    return "zero"
                else:
                    for i in range(x):
                        if i % 2:
                            continue
                    return "negative"
        """)
        analysis = analyze_source(src, filename="test.py")
        fn = analysis.functions[0]
        assert fn.complexity >= 5  # if + if + elif + else + for + if


class TestDocstringDetection:
    def test_missing_module_docstring(self):
        src = "def foo(): pass"
        analysis = analyze_source(src, filename="test.py")
        assert any(i.code == "MISSING_MODULE_DOCSTRING" for i in analysis.issues)

    def test_missing_function_docstring(self):
        src = '"""Module doc."""\ndef foo(): pass'
        analysis = analyze_source(src, filename="test.py")
        assert any(i.code == "MISSING_FUNCTION_DOCSTRING" for i in analysis.issues)

    def test_has_docstring_no_issue(self):
        src = '"""Module doc."""\ndef foo():\n    """Function doc."""\n    pass'
        analysis = analyze_source(src, filename="test.py")
        assert not any(i.code == "MISSING_FUNCTION_DOCSTRING" for i in analysis.issues)


class TestTypeHintCoverage:
    def test_missing_return_type(self):
        src = '"""M."""\ndef foo(x: int): pass'
        analysis = analyze_source(src, filename="test.py")
        assert any(i.code == "MISSING_RETURN_TYPE" for i in analysis.issues)

    def test_missing_param_type(self):
        src = '"""M."""\ndef foo(x): pass'
        analysis = analyze_source(src, filename="test.py")
        assert any(i.code == "MISSING_PARAM_TYPE" for i in analysis.issues)


class TestCodeSmells:
    def test_long_function(self):
        body = "\n".join(f"    x = {i}" for i in range(60))
        src = f'"""M."""\ndef foo():\n    """D."""\n{body}'
        analysis = analyze_source(src, filename="test.py")
        assert any(i.code == "LONG_FUNCTION" for i in analysis.issues)

    def test_too_many_params(self):
        src = '"""M."""\ndef foo(a, b, c, d, e, f, g, h):\n    """D."""\n    pass'
        analysis = analyze_source(src, filename="test.py")
        assert any(i.code == "TOO_MANY_PARAMS" for i in analysis.issues)


class TestOverallScore:
    def test_clean_code_scores_high(self):
        src = '"""Module doc."""\ndef foo(x: int) -> int:\n    """Return x."""\n    return x'
        analysis = analyze_source(src, filename="test.py")
        assert analysis.score >= 80

    def test_messy_code_scores_low(self):
        body = "\n".join(f"    x = {i}" for i in range(60))
        src = f'def foo(a, b, c, d, e, f, g, h):\n{body}'
        analysis = analyze_source(src, filename="test.py")
        assert analysis.score < 70
