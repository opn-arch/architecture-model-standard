"""Tests for the context.md generator."""
import pytest
from pathlib import Path
from architecture_model.pipeline.context_gen import generate_context, write_context
from architecture_model.pipeline.observe import ObserveStage
from architecture_model.pipeline.infer import InferStage
from architecture_model.pipeline.allocate import AllocateStage
from architecture_model.pipeline.relate import RelateStage
from architecture_model.pipeline.validate import ValidateStage
from architecture_model.pipeline.protocol import PipelineContext


def _run_pipeline(tmp_path):
    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".architecture")
    ctx.cache["observe"] = ObserveStage().run(ctx)
    ctx.cache["infer"] = InferStage().run(ctx)
    ctx.cache["allocate"] = AllocateStage().run(ctx)
    ctx.cache["relate"] = RelateStage().run(ctx)
    ctx.cache["validate"] = ValidateStage().run(ctx)
    return ctx


class TestContextGenerator:
    def test_generate_context_has_header(self, tmp_path):
        (tmp_path / "app.py").write_text("def main(): pass")
        ctx = _run_pipeline(tmp_path)
        content = generate_context(ctx)
        assert f"# Architecture Context: {tmp_path.name}" in content

    def test_generate_context_has_score(self, tmp_path):
        (tmp_path / "app.py").write_text("def main(): pass")
        ctx = _run_pipeline(tmp_path)
        content = generate_context(ctx)
        assert "Score:" in content

    def test_generate_context_has_metrics(self, tmp_path):
        (tmp_path / "app.py").write_text("def main(): pass")
        ctx = _run_pipeline(tmp_path)
        content = generate_context(ctx)
        assert "Modules:" in content

    def test_write_context_creates_file(self, tmp_path):
        (tmp_path / "app.py").write_text("def main(): pass")
        ctx = _run_pipeline(tmp_path)
        path = write_context(ctx)
        assert path.exists()
        assert "Architecture Context" in path.read_text()

    def test_context_includes_capabilities(self, tmp_path):
        (tmp_path / "api.py").write_text('''
from fastapi import APIRouter
router = APIRouter()
@router.get("/users")
def list_users(): pass
''')
        ctx = _run_pipeline(tmp_path)
        content = generate_context(ctx)
        assert "Capabilities" in content
