"""Tests for per-stage LLM review."""

from architecture_model.pipeline.stage_review import build_review_prompt, parse_review_response
from architecture_model.pipeline.protocol import QualityMetrics


class TestBuildReviewPrompt:
    def test_includes_quality(self):
        qm = QualityMetrics(score=70, sub_scores={"parse_success_rate": 85.0})
        prompt = build_review_prompt("observe", qm, summary="Found 50 modules")
        assert "observe" in prompt
        assert "70" in prompt
        assert "parse_success_rate" in prompt

    def test_includes_component_scores(self):
        child = QualityMetrics(score=45, sub_scores={"complexity_avg": 12.0})
        qm = QualityMetrics(score=70, component_scores={"parser.py": child})
        prompt = build_review_prompt("observe", qm, summary="")
        assert "parser.py" in prompt
        assert "45" in prompt


class TestParseReviewResponse:
    def test_parse_review_response(self):
        response = "QUALITY: 7/10\nSUGGESTIONS:\n- Reduce complexity in parser.py\n- Add docstrings"
        result = parse_review_response(response)
        assert result.rating == 7
        assert len(result.suggestions) == 2

    def test_parse_empty_response(self):
        result = parse_review_response("")
        assert result.suggestions == []
        assert result.rating == 0

    def test_parse_no_suggestions(self):
        result = parse_review_response("QUALITY: 9/10\nLooks great!")
        assert result.rating == 9
        assert result.suggestions == []
