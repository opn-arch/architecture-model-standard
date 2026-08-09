"""Tests for the infer pipeline stage."""
import pytest
from pathlib import Path
from architecture_model.pipeline.infer import InferStage
from architecture_model.pipeline.observe import ObserveStage
from architecture_model.pipeline.protocol import PipelineContext, StageResult, QualityMetrics


def _run_observe_then_infer(tmp_path):
    """Helper: run observe, cache result, then run infer."""
    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".arch")
    observe = ObserveStage()
    obs_result = observe.run(ctx)
    ctx.cache["observe"] = obs_result
    infer = InferStage()
    return infer.run(ctx)


class TestInferStage:
    def test_infer_name_and_requires(self):
        stage = InferStage()
        assert stage.name == "infer"
        assert stage.requires == ["observe"]

    def test_infer_routes_grouped_by_prefix(self, tmp_path):
        (tmp_path / "api.py").write_text('''
from fastapi import APIRouter
router = APIRouter()

@router.get("/users")
def list_users():
    """List users."""
    pass

@router.post("/users")
def create_user():
    """Create user."""
    pass

@router.get("/articles")
def list_articles():
    """List articles."""
    pass
''')
        result = _run_observe_then_infer(tmp_path)
        caps = result.output.capabilities
        # Should have at least 2 capabilities (users, articles)
        cap_names = [c.name.lower() for c in caps]
        assert any("user" in n for n in cap_names)
        assert any("article" in n for n in cap_names)

    def test_infer_actors_from_routes(self, tmp_path):
        (tmp_path / "api.py").write_text('''
from fastapi import APIRouter
router = APIRouter()

@router.get("/items")
def get_items():
    pass
''')
        result = _run_observe_then_infer(tmp_path)
        assert len(result.output.actors) >= 1
        assert result.output.actors[0].name == "API Consumer"

    def test_infer_behaviors_from_routes(self, tmp_path):
        (tmp_path / "api.py").write_text('''
from fastapi import APIRouter
router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok"}
''')
        result = _run_observe_then_infer(tmp_path)
        assert len(result.output.behaviors) >= 1
        assert result.output.behaviors[0].name == "GET /health"

    def test_infer_quality_metrics(self, tmp_path):
        (tmp_path / "app.py").write_text("def f(): pass")
        result = _run_observe_then_infer(tmp_path)
        assert "capability_coverage" in result.quality.sub_scores
        assert "actor_completeness" in result.quality.sub_scores

    def test_infer_emits_uncertainties_for_ambiguous_modules(self, tmp_path):
        # Module with few functions — not enough to trigger domain cap inference
        (tmp_path / "mystery.py").write_text('''
def do_something():
    pass

def do_another():
    pass
''')
        result = _run_observe_then_infer(tmp_path)
        categories = [u.category for u in result.uncertainties]
        assert "ambiguous_module" in categories

    def test_infer_domain_modules_as_capabilities(self, tmp_path):
        (tmp_path / "payments.py").write_text('''
def process_payment():
    pass

def refund_payment():
    pass

def validate_card():
    pass
''')
        result = _run_observe_then_infer(tmp_path)
        cap_names = [c.name.lower() for c in result.output.capabilities]
        assert any("payment" in n for n in cap_names)
