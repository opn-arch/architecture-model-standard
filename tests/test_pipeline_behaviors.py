"""Tests for pipeline behavior hierarchy in the architecture model."""
import pytest
from pathlib import Path
from architecture_model.core.parser import load_model

MODEL_PATH = Path(__file__).parent.parent / ".architecture-model.yaml"

@pytest.fixture
def model():
    return load_model(MODEL_PATH)

class TestPipelineBehaviorHierarchy:
    def test_top_level_pipeline_behavior_exists(self, model):
        beh_ids = {b.id for b in model.entities.behaviors}
        assert "BEH-P1" in beh_ids

    def test_all_10_stage_behaviors_exist(self, model):
        beh_ids = {b.id for b in model.entities.behaviors}
        for i in range(1, 11):
            assert f"BEH-P1.{i}" in beh_ids, f"Missing BEH-P1.{i}"

    def test_llm_refinement_behavior_exists(self, model):
        beh_ids = {b.id for b in model.entities.behaviors}
        assert "BEH-P1.R" in beh_ids

    def test_observe_sub_behaviors(self, model):
        beh_ids = {b.id for b in model.entities.behaviors}
        for i in range(1, 12):
            assert f"BEH-P1.1.{i}" in beh_ids, f"Missing BEH-P1.1.{i}"

    def test_contains_relationships_wire_hierarchy(self, model):
        contains = [(r.from_id, r.to_id) for r in model.relationships
                    if getattr(r.type, 'value', r.type) == 'contains']
        assert ("BEH-P1", "BEH-P1.1") in contains
        assert ("BEH-P1", "BEH-P1.10") in contains

    def test_traces_to_relationships(self, model):
        traces = [(r.from_id, r.to_id) for r in model.relationships
                  if getattr(r.type, 'value', r.type) == 'traces-to']
        assert ("COMP-2.2", "BEH-P1.1") in traces

    def test_pipeline_behavior_count(self, model):
        pipeline_behs = [b for b in model.entities.behaviors if b.id.startswith("BEH-P1")]
        assert len(pipeline_behs) >= 70
