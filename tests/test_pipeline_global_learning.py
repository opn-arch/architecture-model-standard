"""Tests for GlobalLearningStore cross-project learning."""
from __future__ import annotations

import pytest
from pathlib import Path

from architecture_model.pipeline.global_learning import (
    GlobalLearningStore,
    HeuristicRule,
    ArchetypePattern,
    WorkflowLesson,
)


@pytest.fixture
def store(tmp_path: Path) -> GlobalLearningStore:
    return GlobalLearningStore(tmp_path / "global_learning")


class TestHeuristicRules:
    def test_add_and_get(self, store: GlobalLearningStore) -> None:
        rule = HeuristicRule(
            id="H1", stage="observe", condition="file_count > 100",
            action="increase_timeout", rationale="large repos need more time",
            learned_from="repo-a",
        )
        store.add_heuristic(rule)
        rules = store.get_heuristics()
        assert len(rules) == 1
        assert rules[0].id == "H1"
        assert rules[0].stage == "observe"

    def test_filter_by_stage(self, store: GlobalLearningStore) -> None:
        store.add_heuristic(HeuristicRule(
            id="H1", stage="observe", condition="c1", action="a1",
            rationale="r1", learned_from="repo-a",
        ))
        store.add_heuristic(HeuristicRule(
            id="H2", stage="infer", condition="c2", action="a2",
            rationale="r2", learned_from="repo-b",
        ))
        assert len(store.get_heuristics(stage="observe")) == 1
        assert len(store.get_heuristics(stage="infer")) == 1
        assert len(store.get_heuristics(stage="allocate")) == 0

    def test_validate_on(self, store: GlobalLearningStore) -> None:
        store.add_heuristic(HeuristicRule(
            id="H1", stage="observe", condition="c", action="a",
            rationale="r", learned_from="repo-a",
        ))
        store.validate_heuristic("H1", "repo-b")
        rules = store.get_heuristics()
        assert "repo-b" in rules[0].validated_on


class TestArchetypePatterns:
    def test_add_and_get(self, store: GlobalLearningStore) -> None:
        pattern = ArchetypePattern(
            id="A1", name="monolith", indicators=["single_module", "high_coupling"],
            problem="hard to decompose", solution="split by domain",
        )
        store.add_archetype(pattern)
        patterns = store.get_archetypes()
        assert len(patterns) == 1
        assert patterns[0].name == "monolith"

    def test_match_indicators(self, store: GlobalLearningStore) -> None:
        store.add_archetype(ArchetypePattern(
            id="A1", name="monolith", indicators=["single_module", "high_coupling"],
            problem="p", solution="s",
        ))
        store.add_archetype(ArchetypePattern(
            id="A2", name="microservice", indicators=["many_modules", "low_coupling"],
            problem="p", solution="s",
        ))
        matches = store.match_archetypes(["high_coupling", "circular_deps"])
        assert len(matches) == 1
        assert matches[0].id == "A1"


class TestWorkflowLessons:
    def test_add_and_get(self, store: GlobalLearningStore) -> None:
        lesson = WorkflowLesson(
            id="W1", trigger="test_failure", diagnosis="missing import",
            fix_applied="added import", validation="tests pass",
        )
        store.add_workflow(lesson)
        lessons = store.get_workflows()
        assert len(lessons) == 1
        assert lessons[0].trigger == "test_failure"


class TestPersistence:
    def test_survives_reload(self, tmp_path: Path) -> None:
        path = tmp_path / "global_learning"
        store1 = GlobalLearningStore(path)
        store1.add_heuristic(HeuristicRule(
            id="H1", stage="observe", condition="c", action="a",
            rationale="r", learned_from="repo-a",
        ))
        store2 = GlobalLearningStore(path)
        rules = store2.get_heuristics()
        assert len(rules) == 1
        assert rules[0].id == "H1"

    def test_replace_existing_id(self, store: GlobalLearningStore) -> None:
        store.add_heuristic(HeuristicRule(
            id="H1", stage="observe", condition="old", action="a",
            rationale="r", learned_from="repo-a",
        ))
        store.add_heuristic(HeuristicRule(
            id="H1", stage="observe", condition="new", action="a",
            rationale="r", learned_from="repo-a",
        ))
        rules = store.get_heuristics()
        assert len(rules) == 1
        assert rules[0].condition == "new"


class TestStageIntegration:
    def test_context_has_global_learning(self, store, tmp_path):
        from architecture_model.pipeline.protocol import PipelineContext
        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path)
        ctx.global_learning = store
        assert ctx.global_learning is store

    def test_infer_uses_heuristic_threshold(self, store, tmp_path):
        from architecture_model.pipeline.infer import InferStage
        from architecture_model.pipeline.protocol import PipelineContext

        store.add_heuristic(HeuristicRule(
            id="HR-TEST", stage="infer", condition="module_count > 30",
            action="use package_group strategy", rationale="test",
            learned_from="test", validated_on=[],
            threshold={"parameter": "LARGE_REPO_MODULE_THRESHOLD", "value": 30},
        ))

        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path)
        ctx.global_learning = store
        threshold = InferStage._get_large_repo_threshold(ctx)
        assert threshold == 30

    def test_infer_default_without_heuristic(self, tmp_path):
        from architecture_model.pipeline.infer import InferStage, _LARGE_REPO_MODULE_THRESHOLD
        from architecture_model.pipeline.protocol import PipelineContext

        ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path)
        threshold = InferStage._get_large_repo_threshold(ctx)
        assert threshold == _LARGE_REPO_MODULE_THRESHOLD
