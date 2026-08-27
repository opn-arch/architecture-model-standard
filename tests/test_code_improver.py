"""Tests for LLM-driven code improvement loop."""
import json
from architecture_model.quality.code_improver import (
    parse_review_response, parse_improve_response,
    parse_compare_response, ImprovementPlan,
    plan_improvements, ReviewSuggestion,
)
from architecture_model.quality.code_review import analyze_source


class TestResponseParsing:
    def test_parse_review_response(self):
        llm_output = json.dumps({
            "assessment": "Good structure",
            "additional_issues": ["No error handling in parse()"],
            "suggestions": [
                {"description": "Add docstring to foo", "safety": "safe", "code": "..."},
                {"description": "Rewrite parse logic", "safety": "risky", "code": "..."},
            ]
        })
        result = parse_review_response(llm_output)
        assert result.assessment == "Good structure"
        assert len(result.suggestions) == 2
        assert result.suggestions[0].safety == "safe"

    def test_parse_improve_response(self):
        llm_output = json.dumps({
            "improved_code": "def foo():\n    '''Doc.'''\n    return 1",
            "changes": [{"description": "Added docstring", "safety": "safe"}],
        })
        result = parse_improve_response(llm_output)
        assert "def foo" in result.improved_code
        assert len(result.changes) == 1

    def test_parse_compare_response(self):
        llm_output = json.dumps({
            "winner": "B",
            "rationale": "Better documented",
            "criteria_results": [{"criterion": "readability", "winner": "B", "reason": "Docstrings"}],
            "synthesis": "Use B with A's error handling",
        })
        result = parse_compare_response(llm_output)
        assert result.winner == "B"


class TestImprovementPlanning:
    def test_plan_from_analysis(self):
        src = "def foo(x): pass"
        analysis = analyze_source(src, filename="test.py")
        plan = plan_improvements(analysis)
        assert isinstance(plan, ImprovementPlan)
        assert len(plan.steps) > 0  # should have at least docstring + type hint steps
        assert any(s.change_type == "docstring" for s in plan.steps)
