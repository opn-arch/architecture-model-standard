"""Tests for code review prompt templates."""
from architecture_model.quality.code_prompts import (
    review_prompt, improve_prompt, compare_prompt, safe_change_prompt,
)
from architecture_model.quality.code_review import analyze_source


class TestPromptGeneration:
    def test_review_prompt_includes_issues(self):
        src = "def foo(x): pass"
        analysis = analyze_source(src, filename="test.py")
        prompt = review_prompt(src, analysis)
        assert "MISSING" in prompt
        assert "test.py" in prompt

    def test_improve_prompt_includes_code(self):
        src = "def foo(): return 1"
        analysis = analyze_source(src, filename="test.py")
        prompt = improve_prompt(src, analysis, goal="Add docstring")
        assert "def foo" in prompt
        assert "Add docstring" in prompt

    def test_compare_prompt_includes_both(self):
        src_a = "def foo(): return 1"
        src_b = "def foo():\n    '''Return one.'''\n    return 1"
        prompt = compare_prompt(src_a, src_b, criteria="readability")
        assert "Implementation A" in prompt
        assert "Implementation B" in prompt

    def test_safe_change_prompt_for_docstring(self):
        src = "def foo(x: int) -> int: return x"
        prompt = safe_change_prompt(src, change_type="docstring", function_name="foo")
        assert "foo" in prompt
        assert "docstring" in prompt.lower()
