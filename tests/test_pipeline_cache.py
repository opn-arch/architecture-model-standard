"""Tests for file-based pipeline cache."""

import json
from pathlib import Path

import pytest

from architecture_model.pipeline.cache import PipelineCache, _serialize, _deserialize
from architecture_model.pipeline.protocol import (
    Diagnostic,
    LLMCallRecord,
    PipelineContext,
    QualityMetrics,
    StageResult,
    Uncertainty,
)


@pytest.fixture
def cache_dir(tmp_path):
    return tmp_path / ".architecture" / "pipeline-cache"


@pytest.fixture
def cache(cache_dir):
    return PipelineCache(cache_dir)


def _make_result(score=0.85):
    """Create a minimal StageResult for testing."""
    from architecture_model.pipeline.observe_types import (
        ModuleRecord,
        Inventory,
        ImportEdge,
    )

    inv = Inventory(
        modules=[
            ModuleRecord(path=Path("src/foo.py"), line_count=100, imports=["os"]),
            ModuleRecord(path=Path("src/bar.py"), line_count=50),
        ],
        edges=[
            ImportEdge(
                source=Path("src/foo.py"), target=Path("src/bar.py"), symbols=["Bar"]
            )
        ],
    )
    return StageResult(
        output=inv,
        quality=QualityMetrics(score=score, sub_scores={"coverage": 0.9}),
        diagnostics=[
            Diagnostic(severity="warning", code="W001", message="test warning")
        ],
        uncertainties=[Uncertainty(category="naming", description="unclear name")],
        input_hash="abc123",
        duration_ms=150,
        summary="Observed test inventory.",
    )


class TestSerialize:
    def test_path_serialization(self):
        assert _serialize(Path("/foo/bar")) == "/foo/bar"

    def test_dataclass_serialization(self):
        d = Diagnostic(severity="info", code="I001", message="hi")
        result = _serialize(d)
        assert result["__dataclass__"] == "Diagnostic"
        assert result["severity"] == "info"

    def test_roundtrip_simple(self):
        d = Diagnostic(severity="info", code="I001", message="hi")
        serialized = _serialize(d)
        restored = _deserialize(serialized)
        assert restored.severity == "info"
        assert restored.code == "I001"


class TestPipelineCache:
    def test_save_and_load_stage(self, cache):
        result = _make_result()
        cache.save_stage("observe", result)

        loaded = cache.load_stage("observe")
        assert loaded is not None
        assert loaded.quality.score == 0.85
        assert loaded.duration_ms == 150
        assert loaded.input_hash == "abc123"
        assert loaded.summary == "Observed test inventory."
        assert len(loaded.diagnostics) == 1
        assert len(loaded.uncertainties) == 1

    def test_output_inventory_roundtrip(self, cache):
        result = _make_result()
        cache.save_stage("observe", result)

        loaded = cache.load_stage("observe")
        inv = loaded.output
        assert len(inv.modules) == 2
        assert inv.modules[0].path == Path("src/foo.py")
        assert inv.modules[0].line_count == 100
        assert len(inv.edges) == 1
        assert inv.edges[0].symbols == ["Bar"]

    def test_load_nonexistent(self, cache):
        assert cache.load_stage("observe") is None

    def test_load_all(self, cache):
        cache.save_stage("observe", _make_result(0.8))
        cache.save_stage("infer", _make_result(0.9))

        all_results = cache.load_all()
        assert "observe" in all_results
        assert "infer" in all_results
        assert all_results["observe"].quality.score == 0.8
        assert all_results["infer"].quality.score == 0.9

    def test_meta_tracking(self, cache):
        cache.save_stage("observe", _make_result())
        cache.save_stage("infer", _make_result())

        meta = cache._read_meta()
        assert meta["stages_completed"] == ["observe", "infer"]
        assert "last_updated" in meta

    def test_llm_calls_roundtrip(self, cache):
        calls = [
            LLMCallRecord(
                stage="observe",
                purpose="enrich modules",
                model="claude-sonnet-4",
                total_tokens=1500,
                files_sent=["src/foo.py"],
            ),
            LLMCallRecord(
                stage="infer",
                purpose="capability naming",
                model="claude-sonnet-4",
                total_tokens=800,
            ),
        ]
        cache.save_llm_calls(calls)
        loaded = cache.load_llm_calls()
        assert len(loaded) == 2
        assert loaded[0].stage == "observe"
        assert loaded[0].total_tokens == 1500
        assert loaded[0].files_sent == ["src/foo.py"]
        assert loaded[1].purpose == "capability naming"

    def test_hydrate_context(self, cache, tmp_path):
        cache.save_stage("observe", _make_result(0.85))
        cache.save_llm_calls(
            [LLMCallRecord(stage="observe", purpose="test", total_tokens=100)]
        )

        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / "out")
        loaded_stages = cache.hydrate_context(ctx)

        assert "observe" in loaded_stages
        assert ctx.has("observe")
        assert ctx.cache["observe"].quality.score == 0.85
        assert len(ctx.llm_calls) == 1

    def test_clear(self, cache):
        cache.save_stage("observe", _make_result())
        assert cache.exists()
        cache.clear()
        assert not cache.exists()

    def test_exists(self, cache):
        assert not cache.exists()
        cache.save_stage("observe", _make_result())
        assert cache.exists()
