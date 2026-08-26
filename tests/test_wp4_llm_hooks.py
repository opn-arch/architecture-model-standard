"""WP-4: LLM enrichment hooks in pipeline stages."""
import asyncio
from unittest.mock import AsyncMock
from architecture_model.pipeline.protocol import PipelineContext
from pathlib import Path


class TestLLMEnrichmentHook:
    def test_context_has_llm_callback(self):
        ctx = PipelineContext(repo_path=Path("/tmp"), output_dir=Path("/tmp"))
        assert ctx.llm_callback is None

    def test_context_llm_enrich_skips_when_no_callback(self):
        ctx = PipelineContext(repo_path=Path("/tmp"), output_dir=Path("/tmp"))
        result = asyncio.run(ctx.llm_enrich("infer", "describe this", {}))
        assert result is None

    def test_context_llm_enrich_calls_callback(self):
        mock = AsyncMock(return_value="A validation engine")
        ctx = PipelineContext(
            repo_path=Path("/tmp"), output_dir=Path("/tmp"),
            llm_callback=mock,
        )
        result = asyncio.run(ctx.llm_enrich("infer", "describe this", {"code": "..."}))
        mock.assert_called_once()
        assert result == "A validation engine"
