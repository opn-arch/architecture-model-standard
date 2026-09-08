from pathlib import Path


def test_pipeline_context_accepts_llm_provider_none_default():
    from architecture_model.pipeline.protocol import PipelineContext
    ctx = PipelineContext(repo_path=Path("/tmp"), output_dir=Path("/tmp"))
    assert ctx.llm_provider is None


def test_pipeline_context_accepts_llm_provider_when_set():
    from architecture_model.pipeline.protocol import PipelineContext
    from architecture_model.llm import LLMProvider

    class Stub:
        name = "stub"
        def complete(self, *a, **kw): raise NotImplementedError
        def stream(self, *a, **kw):   raise NotImplementedError
        def structured(self, *a, **kw): raise NotImplementedError
        def tokenize(self, t): return 0

    ctx = PipelineContext(repo_path=Path("/tmp"), output_dir=Path("/tmp"), llm_provider=Stub())
    assert isinstance(ctx.llm_provider, LLMProvider)
