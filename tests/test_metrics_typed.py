"""Tests for typed MetricsResult from compute_metrics."""

from pathlib import Path

from architecture_model.manifest.types import MetricsResult


def test_compute_metrics_returns_metrics_result(tmp_path):
    (tmp_path / "foo.py").write_text("x = 1\n")
    from architecture_model.manifest.metrics import compute_metrics

    result = compute_metrics(tmp_path)
    assert isinstance(result, MetricsResult)
    assert "total_python_files" in result.values
    assert result.values["total_python_files"] >= 1


def test_compute_metrics_backward_compat(tmp_path):
    (tmp_path / "bar.py").write_text("y = 2\n")
    from architecture_model.manifest.metrics import compute_metrics

    d = compute_metrics(tmp_path).to_dict()
    assert isinstance(d, dict)
    assert "total_python_files" in d
