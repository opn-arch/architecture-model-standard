"""Tests for project-local learning persistence."""
import pytest
from pathlib import Path
from architecture_model.pipeline.learning import (
    Correction, ResolutionOutcome, Calibration, QualityTrend,
    LearningStore,
)
from architecture_model.pipeline.protocol import Evidence, Uncertainty


class TestLearningStore:
    def test_save_and_load_correction(self, tmp_path):
        store = LearningStore(tmp_path / ".architecture" / "learning")
        correction = Correction(
            timestamp="2026-08-09T10:00:00",
            module="allocate",
            entity_id="COMP-UTILS",
            correction_type="split",
            before={"files": ["a.py", "b.py", "c.py"]},
            after={"COMP-LOG": ["a.py"], "COMP-HELP": ["b.py", "c.py"]},
            reason="Logging and helpers are different concerns",
        )
        store.add_correction(correction)
        loaded = store.get_corrections()
        assert len(loaded) == 1
        assert loaded[0].entity_id == "COMP-UTILS"

    def test_corrections_as_evidence(self, tmp_path):
        store = LearningStore(tmp_path / ".architecture" / "learning")
        store.add_correction(Correction(
            timestamp="2026-08-09", module="allocate", entity_id="COMP-X",
            correction_type="rename", before={"name": "Old"}, after={"name": "New"},
            reason="Better name",
        ))
        evidence = store.corrections_as_evidence()
        assert len(evidence) == 1
        assert evidence[0].source == "user_correction"
        assert evidence[0].confidence == 1.0

    def test_save_and_load_calibration(self, tmp_path):
        store = LearningStore(tmp_path / ".architecture" / "learning")
        store.set_calibration("allocate", "boundary_coherence_threshold", 50.0,
                             reason="Cross-cutting design intentional")
        cal = store.get_calibration("allocate")
        assert cal["boundary_coherence_threshold"] == 50.0

    def test_record_quality_history(self, tmp_path):
        store = LearningStore(tmp_path / ".architecture" / "learning")
        store.record_run("2026-08-09", {"observe": 95.0, "allocate": 72.0})
        store.record_run("2026-08-10", {"observe": 95.0, "allocate": 58.0})
        trend = store.get_trend("allocate")
        assert trend.direction == "degrading"

    def test_save_resolution_outcome(self, tmp_path):
        store = LearningStore(tmp_path / ".architecture" / "learning")
        outcome = ResolutionOutcome(
            uncertainty=Uncertainty(
                category="orphan_file", description="x.py orphaned",
                suggested_fallback="ask_user", priority="blocking",
            ),
            resolution=Evidence(source="user_confirmation", confidence=1.0, raw="It's a script"),
            method="ask_user",
            attempts=1,
            duration_ms=5000,
        )
        store.add_resolution(outcome)
        resolutions = store.get_resolutions(category="orphan_file")
        assert len(resolutions) == 1
        assert resolutions[0].method == "ask_user"
