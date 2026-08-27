"""Tests for per-stage LLM review."""

from architecture_model.pipeline.stage_review import (
    build_review_prompt, parse_review_response,
    build_semantic_review_prompt, parse_correction_response,
    Correction, CorrectionResult,
)
from architecture_model.pipeline.protocol import QualityMetrics, GateResult


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


class TestBuildSemanticReviewPrompt:
    def test_includes_stage_summary(self):
        qm = QualityMetrics(score=70, sub_scores={"parse_success_rate": 85.0})
        prompt = build_semantic_review_prompt(
            stage_name="observe", quality=qm, gate_results=[],
            components=[{"id": "COMP-1", "name": "Core", "intent": "Parse models", "file_count": 9, "quality": 85}],
            modules=[{"path": "core/parser.py", "functions": 5, "quality": 91}],
        )
        assert "observe" in prompt
        assert "COMP-1" in prompt
        assert "core/parser.py" in prompt
        assert "Parse models" in prompt

    def test_includes_gate_results(self):
        qm = QualityMetrics(score=70)
        gate = GateResult(passed=False, blocks=False, message="WARN: code_quality_avg = 45.0", metric="code_quality_avg", actual=45.0, threshold=50.0)
        prompt = build_semantic_review_prompt(
            stage_name="observe", quality=qm, gate_results=[gate],
            components=[], modules=[],
        )
        assert "WARN" in prompt
        assert "code_quality_avg" in prompt

    def test_requests_json_response(self):
        qm = QualityMetrics(score=70)
        prompt = build_semantic_review_prompt("observe", qm, [], [], [])
        assert "JSON" in prompt or "json" in prompt


class TestParseCorrectionResponse:
    def test_parse_valid_corrections(self):
        response = '{"stage_assessment": "Good", "corrections": [{"entity_id": "COMP-1", "field": "intent", "action": "improve", "value": "Better intent", "confidence": 0.9}], "warnings": [], "suggestions": ["Add more tests"]}'
        result = parse_correction_response(response)
        assert len(result.corrections) == 1
        assert result.corrections[0].entity_id == "COMP-1"
        assert result.corrections[0].confidence == 0.9
        assert result.stage_assessment == "Good"

    def test_parse_empty_response(self):
        result = parse_correction_response("")
        assert result.corrections == []

    def test_parse_invalid_json(self):
        result = parse_correction_response("not json at all")
        assert result.corrections == []
        assert result.raw == "not json at all"

    def test_parse_json_in_markdown(self):
        response = '```json\n{"stage_assessment": "OK", "corrections": [], "warnings": [], "suggestions": []}\n```'
        result = parse_correction_response(response)
        assert result.stage_assessment == "OK"
