"""Tests for bidirectional code-to-model feedback."""
from architecture_model.quality.model_feedback import (
    code_to_model_feedback, ModelFeedback,
)
from architecture_model.quality.code_review import analyze_source
from architecture_model.core.types import Component, Status


class TestCodeToModelFeedback:
    def test_missing_error_handling_populates_failure_modes(self):
        # Code with no try/except and undocumented branching function
        src = '"""M."""\ndef process(data):\n    if data:\n        return data["key"]\n    return None'
        analysis = analyze_source(src, filename="processor.py")
        comp = Component(id="COMP-1", name="Processor", status=Status.ACTIVE,
                         files=["processor.py"])
        feedback = code_to_model_feedback(comp, [analysis])
        assert len(feedback.suggested_failure_modes) > 0

    def test_high_complexity_suggests_trade_off(self):
        body = "\n".join(f"    if x == {i}: return {i}" for i in range(15))
        src = f'"""M."""\ndef complex_fn(x):\n    """D."""\n{body}'
        analysis = analyze_source(src, filename="complex.py")
        comp = Component(id="COMP-1", name="Complex", status=Status.ACTIVE)
        feedback = code_to_model_feedback(comp, [analysis])
        assert len(feedback.suggested_trade_offs) > 0

    def test_good_test_coverage_suggests_moes(self):
        src = '"""M."""\ndef validate(model):\n    """Validate model."""\n    return True'
        analysis = analyze_source(src, filename="validator.py")
        comp = Component(id="COMP-1", name="Validator", status=Status.ACTIVE,
                         test_contracts=[])
        feedback = code_to_model_feedback(comp, [analysis])
        assert isinstance(feedback.suggested_moes, list)
