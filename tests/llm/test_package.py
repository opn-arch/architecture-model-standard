def test_llm_package_importable():
    import architecture_model.llm as llm
    assert hasattr(llm, "__all__")


def test_llm_package_exports_provider_and_completion():
    from architecture_model.llm import LLMProvider, Completion
    assert LLMProvider is not None
    assert Completion is not None


def test_completion_typed_dict_keys():
    from architecture_model.llm import Completion
    ann = Completion.__annotations__
    assert set(ann) == {
        "text",
        "tokens_prompt",
        "tokens_completion",
        "model",
        "finish_reason",
    }


def test_llm_provider_protocol_surface():
    from architecture_model.llm import LLMProvider
    for method in ("complete", "stream", "structured", "tokenize"):
        assert hasattr(LLMProvider, method), method


def test_llm_provider_runtime_checkable_by_duck_type():
    from architecture_model.llm import LLMProvider

    class Duck:
        name = "duck"
        def complete(self, prompt, *, model=None, max_tokens=4096, temperature=0.0):
            return {"text": "", "tokens_prompt": 0, "tokens_completion": 0,
                    "model": "d", "finish_reason": "stop"}
        def stream(self, prompt, *, model=None, max_tokens=4096, temperature=0.0):
            yield ""
        def structured(self, prompt, schema, *, model=None):
            return {}
        def tokenize(self, text):
            return len(text.split())

    d = Duck()
    assert isinstance(d, LLMProvider)
