"""Tests for learning store integration with coordinator."""
import pytest
from pathlib import Path
from architecture_model.pipeline.coordinator import PipelineCoordinator
from architecture_model.pipeline.learning import LearningStore, Correction
from architecture_model.pipeline.observe import ObserveStage
from architecture_model.pipeline.infer import InferStage
from architecture_model.pipeline.allocate import AllocateStage
from architecture_model.pipeline.relate import RelateStage
from architecture_model.pipeline.validate import ValidateStage
from architecture_model.pipeline.protocol import PipelineContext


def _make_coordinator(learning_path: Path):
    store = LearningStore(learning_path)
    stages = {
        "observe": ObserveStage(),
        "infer": InferStage(),
        "allocate": AllocateStage(),
        "relate": RelateStage(),
        "validate": ValidateStage(),
    }
    return PipelineCoordinator(stages, learning_store=store), store


class TestLearningIntegration:
    def test_run_all_records_quality_history(self, tmp_path):
        (tmp_path / "app.py").write_text("def main(): pass")
        learning_path = tmp_path / ".architecture" / "learning"
        coord, store = _make_coordinator(learning_path)
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".architecture")
        coord.run_all(ctx)

        # Should have recorded a run
        trend = store.get_trend("observe")
        assert len(trend.values) == 1

    def test_get_prior_evidence_from_corrections(self, tmp_path):
        learning_path = tmp_path / ".architecture" / "learning"
        coord, store = _make_coordinator(learning_path)

        # Add a correction
        store.add_correction(Correction(
            timestamp="2026-08-09", module="allocate", entity_id="COMP-1",
            correction_type="rename", before={"name": "Old"}, after={"name": "New"},
            reason="Better name",
        ))

        evidence = coord.get_prior_evidence()
        assert len(evidence) == 1
        assert evidence[0].source == "user_correction"

    def test_get_calibration_overrides(self, tmp_path):
        learning_path = tmp_path / ".architecture" / "learning"
        coord, store = _make_coordinator(learning_path)

        store.set_calibration("allocate", "boundary_coherence_threshold", 40.0)
        cal = coord.get_calibration("allocate")
        assert cal["boundary_coherence_threshold"] == 40.0

    def test_coordinator_without_learning_store(self, tmp_path):
        """Coordinator works fine without a learning store."""
        (tmp_path / "app.py").write_text("def main(): pass")
        stages = {"observe": ObserveStage(), "infer": InferStage()}
        coord = PipelineCoordinator(stages)
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / ".architecture")
        results = coord.run_all(ctx)
        assert "observe" in results
