"""Tests for the allocate pipeline stage."""
import pytest
from pathlib import Path
from architecture_model.pipeline.allocate import AllocateStage
from architecture_model.pipeline.observe import ObserveStage
from architecture_model.pipeline.infer import InferStage
from architecture_model.pipeline.protocol import PipelineContext


def _run_pipeline(tmp_path):
    """Run observe → infer → allocate."""
    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
    obs = ObserveStage()
    ctx.cache["observe"] = obs.run(ctx)
    inf = InferStage()
    ctx.cache["infer"] = inf.run(ctx)
    alloc = AllocateStage()
    return alloc.run(ctx), ctx


class TestAllocateStage:
    def test_allocate_name_and_requires(self):
        stage = AllocateStage()
        assert stage.name == "allocate"
        assert "observe" in stage.requires
        assert "infer" in stage.requires

    def test_allocate_empty_project(self, tmp_path):
        result, _ = _run_pipeline(tmp_path)
        assert result.output.components == []
        assert result.output.file_coverage == 100.0

    def test_allocate_seeds_from_capabilities(self, tmp_path):
        # Create files matching capability names
        (tmp_path / "users.py").write_text('''
from fastapi import APIRouter
router = APIRouter()

@router.get("/users")
def list_users():
    pass

@router.post("/users")
def create_user():
    pass
''')
        (tmp_path / "articles.py").write_text('''
from fastapi import APIRouter
router = APIRouter()

@router.get("/articles")
def list_articles():
    pass
''')
        result, _ = _run_pipeline(tmp_path)
        assert len(result.output.components) >= 1
        assert result.output.file_coverage > 0

    def test_allocate_file_coverage(self, tmp_path):
        (tmp_path / "app.py").write_text("def main(): pass")
        (tmp_path / "utils.py").write_text("def helper(): pass")
        result, _ = _run_pipeline(tmp_path)
        # All files should be allocated (even if to Infrastructure)
        assert result.output.file_coverage == 100.0

    def test_allocate_quality_metrics(self, tmp_path):
        (tmp_path / "app.py").write_text("def f(): pass")
        result, _ = _run_pipeline(tmp_path)
        assert "file_coverage" in result.quality.sub_scores
        assert "boundary_coherence" in result.quality.sub_scores
        assert "component_count" in result.quality.sub_scores
