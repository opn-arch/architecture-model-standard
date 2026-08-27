"""Tests for auto-correction applier."""
from architecture_model.pipeline.auto_correct import apply_corrections, CorrectionLog
from architecture_model.pipeline.stage_review import Correction


class TestApplyCorrections:
    def _make_model_dict(self):
        return {
            "entities": {
                "components": [
                    {"id": "COMP-1", "name": "Core", "intent": "", "status": "ACTIVE"},
                ],
                "capabilities": [
                    {"id": "CAP-F1", "name": "Parsing", "moes": []},
                ],
            }
        }

    def test_auto_applies_high_confidence_intent(self):
        model = self._make_model_dict()
        corrections = [Correction("COMP-1", "intent", "improve", "Parse YAML models", 0.9)]
        log = apply_corrections(model, corrections)
        assert log.applied == 1
        assert model["entities"]["components"][0]["intent"] == "Parse YAML models"

    def test_skips_low_confidence(self):
        model = self._make_model_dict()
        corrections = [Correction("COMP-1", "intent", "improve", "New intent", 0.5)]
        log = apply_corrections(model, corrections)
        assert log.applied == 0
        assert log.skipped == 1

    def test_applies_moe_addition(self):
        model = self._make_model_dict()
        corrections = [Correction("CAP-F1", "moes", "add", ["All YAML parsed correctly"], 0.85)]
        log = apply_corrections(model, corrections)
        assert log.applied == 1
        assert model["entities"]["capabilities"][0]["moes"] == ["All YAML parsed correctly"]

    def test_skips_structural_changes(self):
        model = self._make_model_dict()
        corrections = [Correction("COMP-1", "name", "improve", "NewName", 0.95)]
        log = apply_corrections(model, corrections, structural_fields={"name"})
        assert log.applied == 0
        assert log.skipped == 1

    def test_log_tracks_before_after(self):
        model = self._make_model_dict()
        corrections = [Correction("COMP-1", "intent", "improve", "Better intent", 0.9)]
        log = apply_corrections(model, corrections)
        assert len(log.entries) == 1
        assert log.entries[0]["old"] == ""
        assert log.entries[0]["new"] == "Better intent"
