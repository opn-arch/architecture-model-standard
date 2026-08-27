"""E2E: python-dotenv pipeline with quality gates and per-component quality."""
import pytest
from pathlib import Path
from architecture_model.pipeline.coordinator import PipelineCoordinator
from architecture_model.pipeline.protocol import PipelineContext


DOTENV_REPO = Path(__file__).resolve().parents[2] / "projects" / "python-dotenv"


@pytest.fixture(scope="module")
def dotenv_repo():
    if not DOTENV_REPO.exists():
        pytest.skip("python-dotenv not cloned in projects/")
    return DOTENV_REPO


class TestE2EPythonDotenv:
    def test_pipeline_with_quality_gates(self, dotenv_repo, tmp_path):
        from architecture_model.pipeline.observe import ObserveStage
        from architecture_model.pipeline.infer import InferStage
        from architecture_model.pipeline.allocate import AllocateStage
        from architecture_model.pipeline.relate import RelateStage
        from architecture_model.pipeline.specify import SpecifyStage
        from architecture_model.pipeline.contract import ContractStage

        ctx = PipelineContext(repo_path=dotenv_repo, output_dir=tmp_path / ".arch")
        stages = {
            "observe": ObserveStage(),
            "infer": InferStage(),
            "allocate": AllocateStage(),
            "relate": RelateStage(),
            "specify": SpecifyStage(),
            "contract": ContractStage(),
        }
        coord = PipelineCoordinator(stages)
        results = coord.run_all(ctx)

        # Per-stage quality
        for name, result in results.items():
            assert result.quality.score >= 0

        # Review log populated
        assert len(ctx.review_log) >= len(stages)

        # Per-component quality after allocate
        assert isinstance(results["allocate"].quality.component_scores, dict)

        # No hard gate failures (if we get here, none blocked)
        for review in ctx.review_log:
            assert not any(gr.blocks for gr in review.gate_results)

    def test_observe_has_module_quality(self, dotenv_repo, tmp_path):
        from architecture_model.pipeline.observe import ObserveStage

        ctx = PipelineContext(repo_path=dotenv_repo, output_dir=tmp_path / ".arch")
        result = ObserveStage().run(ctx)
        # Should find modules
        assert len(result.output.modules) > 0
        # Should have component_scores
        assert isinstance(result.quality.component_scores, dict)

    def test_quality_dashboard_with_pipeline(self, dotenv_repo, tmp_path):
        """Run pipeline then generate quality dashboard."""
        from architecture_model.pipeline.observe import ObserveStage
        from architecture_model.pipeline.infer import InferStage
        from architecture_model.pipeline.allocate import AllocateStage
        from architecture_model.pipeline.relate import RelateStage
        from architecture_model.pipeline.specify import SpecifyStage
        from architecture_model.pipeline.contract import ContractStage
        from architecture_model.pipeline.validate import ValidateStage

        ctx = PipelineContext(repo_path=dotenv_repo, output_dir=tmp_path / ".arch")
        stages = {
            "observe": ObserveStage(),
            "infer": InferStage(),
            "allocate": AllocateStage(),
            "relate": RelateStage(),
            "specify": SpecifyStage(),
            "contract": ContractStage(),
            "validate": ValidateStage(),
        }
        coord = PipelineCoordinator(stages)
        results = coord.run_all(ctx)

        # Build a minimal model for dashboard
        from architecture_model.core.types import ArchitectureModel, Entities, ModelMeta
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="python-dotenv", generated_at="2026-01-01"),
            entities=Entities(),
            relationships=[],
        )
        from architecture_model.quality.dashboard import quality_report
        report = quality_report(model, pipeline_results=results)
        assert report.pipeline_quality is not None
        assert "observe" in report.pipeline_quality
        assert report.pipeline_quality["observe"] >= 0


class TestE2EPythonDotenvQualityLoop:
    def test_update_summary(self, dotenv_repo, tmp_path):
        """Generate update summary for python-dotenv."""
        from architecture_model.quality.update_summary import subsystem_summary
        from architecture_model.core.types import ArchitectureModel, Entities, ModelMeta, Component, Capability, Status
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="python-dotenv", generated_at="2026-01-01"),
            entities=Entities(
                components=[Component(id="COMP-1", name="DotEnv", status=Status.ACTIVE, intent="Load .env files")],
                capabilities=[Capability(id="CAP-1", name="Env Loading", status=Status.ACTIVE, intent="Load env vars")],
            ),
            relationships=[],
        )
        summary = subsystem_summary("python-dotenv", model)
        assert summary is not None
        assert "python-dotenv" in str(summary)
