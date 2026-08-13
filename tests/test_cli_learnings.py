"""Tests for learnings CLI command."""
from pathlib import Path
from unittest.mock import patch

from architecture_model.cli.main import main


def test_learnings_empty(tmp_path):
    with patch("architecture_model.cli.main.GLOBAL_LEARNING_PATH", tmp_path / "empty"):
        result = main(["learnings"])
    assert result == 0


def test_learnings_shows_heuristics(tmp_path, capsys):
    from architecture_model.pipeline.global_learning import GlobalLearningStore, HeuristicRule

    path = tmp_path / "learning"
    store = GlobalLearningStore(path)
    store.add_heuristic(HeuristicRule(
        id="HR-001", stage="infer", condition="module_count > 50",
        action="package grouping", rationale="r", learned_from="django",
        validated_on=["django"], threshold={},
    ))

    with patch("architecture_model.cli.main.GLOBAL_LEARNING_PATH", path):
        result = main(["learnings"])
    assert result == 0
    output = capsys.readouterr().out
    assert "HR-001" in output
    assert "module_count > 50" in output
    assert "django" in output
