"""WP-3: LLM entity review loop."""
from architecture_model.core.review import prepare_review_prompt, apply_review
from architecture_model.core.types import Component, Status


class TestEntityReview:
    def test_prepare_review_prompt_for_component(self):
        c = Component(id="COMP-1", name="Validator", status=Status.ACTIVE,
                      description="Validates models")
        prompt = prepare_review_prompt(c)
        assert "COMP-1" in prompt
        assert "Validator" in prompt
        assert "intent" in prompt.lower()  # should ask about missing fields

    def test_apply_review_sets_extension(self):
        c = Component(id="COMP-1", name="Validator", status=Status.ACTIVE)
        reviewed = apply_review(c, {"intent": "Ensure model correctness",
                                     "review_notes": "Good coverage"})
        assert reviewed.intent == "Ensure model correctness"
        assert reviewed.extensions.get("_llm_review") is not None

    def test_apply_review_preserves_existing_fields(self):
        c = Component(id="COMP-1", name="Validator", status=Status.ACTIVE,
                      description="Original description")
        reviewed = apply_review(c, {"intent": "New intent"})
        assert reviewed.description == "Original description"
