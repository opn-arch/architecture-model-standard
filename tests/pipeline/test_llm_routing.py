"""B1.2.7 — pipeline stages route LLM calls through ctx.llm_provider when set."""
import asyncio
from pathlib import Path
import pytest

from architecture_model.pipeline.protocol import PipelineContext


class _StubProvider:
    name = "stub"
    def __init__(self):
        self.calls: list[str] = []
    def complete(self, prompt, *, model=None, max_tokens=4096, temperature=0.0):
        self.calls.append(prompt)
        return {"text": "provider-response", "tokens_prompt": 1,
                "tokens_completion": 1, "model": "stub-model",
                "finish_reason": "stop"}
    def stream(self, prompt, **kw): yield "provider-response"
    def structured(self, prompt, schema, **kw): return {}
    def tokenize(self, t): return 1


def test_llm_enrich_uses_ctx_llm_provider_when_set(tmp_path):
    stub = _StubProvider()
    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path, llm_provider=stub)
    result = asyncio.run(ctx.llm_enrich("infer", "test prompt", {}))
    assert result == "provider-response"
    assert stub.calls == ["test prompt"]
    # confirms telemetry log written
    assert len(ctx.llm_calls) == 1
    assert ctx.llm_calls[0].stage == "infer"


def test_llm_enrich_falls_back_to_llm_callback_when_provider_none(tmp_path):
    calls = []

    async def _cb(stage, prompt, context):
        calls.append((stage, prompt))
        return "callback-response"

    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path, llm_callback=_cb)
    result = asyncio.run(ctx.llm_enrich("infer", "test prompt", {}))
    assert result == "callback-response"
    assert calls == [("infer", "test prompt")]


def test_llm_enrich_returns_none_when_both_none(tmp_path):
    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path)
    result = asyncio.run(ctx.llm_enrich("infer", "x", {}))
    assert result is None


def test_llm_enrich_provider_exception_returns_none(tmp_path):
    class _Boom:
        name = "boom"
        def complete(self, *a, **kw): raise RuntimeError("boom")
        def stream(self, *a, **kw): yield ""
        def structured(self, *a, **kw): return {}
        def tokenize(self, t): return 0

    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path, llm_provider=_Boom())
    result = asyncio.run(ctx.llm_enrich("infer", "x", {}))
    assert result is None
