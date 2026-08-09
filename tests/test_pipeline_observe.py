"""Tests for the observe pipeline stage."""
import pytest
from pathlib import Path
from architecture_model.pipeline.observe import ObserveStage
from architecture_model.pipeline.protocol import PipelineContext


class TestObserveStage:
    def test_observe_empty_dir(self, tmp_path):
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        stage = ObserveStage()
        result = stage.run(ctx)
        assert result.output.modules == []
        assert result.quality.score >= 0

    def test_observe_simple_python_file(self, tmp_path):
        src = tmp_path / "src" / "app"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text("")
        (src / "main.py").write_text('''
"""Main application module."""
import os

API_VERSION = "1.0"

def hello(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}"

class Config:
    DEBUG = True
''')
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        stage = ObserveStage()
        result = stage.run(ctx)

        assert len(result.output.modules) >= 1
        main_mod = next(m for m in result.output.modules if "main" in str(m.path))
        assert len(main_mod.functions) == 1
        assert main_mod.functions[0].name == "hello"
        assert main_mod.functions[0].body_hint != ""
        assert len(main_mod.classes) == 1
        assert len(main_mod.constants) >= 1

    def test_observe_discovers_routes(self, tmp_path):
        (tmp_path / "api.py").write_text('''
from fastapi import APIRouter
router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}
''')
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        stage = ObserveStage()
        result = stage.run(ctx)
        assert len(result.output.routes) >= 1

    def test_observe_quality_metrics(self, tmp_path):
        (tmp_path / "app.py").write_text("def f(): pass")
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        stage = ObserveStage()
        result = stage.run(ctx)
        assert "parse_success_rate" in result.quality.sub_scores
        assert "symbol_density" in result.quality.sub_scores

    def test_observe_emits_uncertainties_for_dynamic_imports(self, tmp_path):
        (tmp_path / "loader.py").write_text('''
import importlib
mod = importlib.import_module(name)
''')
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
        stage = ObserveStage()
        result = stage.run(ctx)
        categories = [u.category for u in result.uncertainties]
        assert "dynamic_import" in categories

    def test_observe_name_and_requires(self):
        stage = ObserveStage()
        assert stage.name == "observe"
        assert stage.requires == []

    def test_observe_scoped_only_processes_scoped_files(self, tmp_path):
        """When scope_files is set, observe only scans those files."""
        (tmp_path / "included.py").write_text("def included(): pass")
        (tmp_path / "excluded.py").write_text("def excluded(): pass")

        ctx = PipelineContext(
            repo_path=tmp_path,
            output_dir=tmp_path / ".arch",
            scope_files=[tmp_path / "included.py"],
        )
        stage = ObserveStage()
        result = stage.run(ctx)

        paths = [str(m.path) for m in result.output.modules]
        assert any("included" in p for p in paths)
        assert not any("excluded" in p for p in paths)
        assert len(result.output.modules) == 1
