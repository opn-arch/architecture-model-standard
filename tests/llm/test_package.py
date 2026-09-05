def test_llm_package_importable():
    import architecture_model.llm as llm
    assert hasattr(llm, "__all__")


def test_llm_package_exports_provider_and_completion():
    from architecture_model.llm import LLMProvider, Completion
    assert LLMProvider is not None
    assert Completion is not None
