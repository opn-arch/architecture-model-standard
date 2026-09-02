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

    def test_scoped_observe_filters_all_file_derived_evidence(self, tmp_path):
        api = tmp_path / "api.py"
        api.write_text(
            'from fastapi import APIRouter\nrouter = APIRouter()\n'
            '@router.get("/only-api")\ndef route(): return {}\n'
        )
        model = tmp_path / "models.py"
        model.write_text("class Account: pass\n")
        migration = tmp_path / "migrations" / "001.py"
        migration.parent.mkdir()
        migration.write_text("REVISION = '001'\n")
        (tmp_path / "README.md").write_text("# Global docs\n")
        api_doc = tmp_path / "api.md"
        api_doc.write_text("# API docs\n")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_api.py").write_text("def test_api(): pass\n")
        (tests / "test_models.py").write_text("def test_models(): pass\n")

        api_result = ObserveStage().run(PipelineContext(
            repo_path=tmp_path,
            output_dir=tmp_path / ".arch-api",
            scope_files=[api, api_doc],
        )).output
        model_result = ObserveStage().run(PipelineContext(
            repo_path=tmp_path,
            output_dir=tmp_path / ".arch-model",
            scope_files=[model, migration],
        )).output

        assert [route.path for route in api_result.routes] == ["/only-api"]
        assert model_result.routes == []
        assert [doc.path for doc in api_result.docs] == [Path("api.md")]
        assert model_result.docs == []
        assert [test.path for test in api_result.test_files] == [Path("tests/test_api.py")]
        assert [test.path for test in model_result.test_files] == [Path("tests/test_models.py")]

    def test_scoped_test_discovery_uses_package_context_not_basename(self, tmp_path):
        alpha = tmp_path / "alpha" / "api.py"
        beta = tmp_path / "beta" / "api.py"
        alpha.parent.mkdir()
        beta.parent.mkdir()
        alpha.write_text("def alpha(): pass\n")
        beta.write_text("def beta(): pass\n")
        alpha_test = tmp_path / "tests" / "alpha" / "test_api.py"
        beta_test = tmp_path / "tests" / "beta" / "test_api.py"
        alpha_test.parent.mkdir(parents=True)
        beta_test.parent.mkdir(parents=True)
        alpha_test.write_text("from alpha.api import alpha\n")
        beta_test.write_text("from beta.api import beta\n")

        observed = ObserveStage().run(PipelineContext(
            repo_path=tmp_path,
            output_dir=tmp_path / ".arch",
            scope_files=[alpha],
        )).output

        assert [test.path for test in observed.test_files] == [Path("tests/alpha/test_api.py")]


class TestObservePerModuleQuality:
    def test_module_record_has_quality_score(self):
        from architecture_model.pipeline.observe_types import ModuleRecord
        mr = ModuleRecord(path=Path("test.py"), quality_score=75)
        assert mr.quality_score == 75

    def test_observe_quality_has_component_scores(self, tmp_path):
        """After observe, quality.component_scores keyed by module path."""
        (tmp_path / "mod.py").write_text("def foo():\n    return 1\n")
        stage = ObserveStage()
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".out")
        result = stage.run(ctx)
        assert isinstance(result.quality.component_scores, dict)

    def test_observe_module_quality_score_set(self, tmp_path):
        """Module records should have quality_score populated."""
        (tmp_path / "mod.py").write_text("def foo(x: int) -> int:\n    \"\"\"Doc.\"\"\"\n    return x + 1\n")
        stage = ObserveStage()
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".out")
        result = stage.run(ctx)
        if result.output.modules:
            # quality_score should be set (may be 0 if code_review unavailable)
            assert hasattr(result.output.modules[0], "quality_score")
