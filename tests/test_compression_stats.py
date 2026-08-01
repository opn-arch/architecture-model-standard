"""Tests for compression stats utility."""
from pathlib import Path
import pytest
from architecture_model.core.compression import compute_compression_stats, format_compression_summary


@pytest.fixture
def sample_project(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    for i in range(5):
        (src / f"module{i}.py").write_text("x" * 1000)
    models = tmp_path / ".architecture-models"
    models.mkdir()
    (models / "manifest.yaml").write_text("y" * 500)
    return tmp_path


def test_compression_stats_basic(sample_project):
    stats = compute_compression_stats(sample_project)
    assert stats["source_bytes"] == 5000
    assert stats["model_bytes"] == 500
    assert stats["compression_ratio"] == 10.0
    assert stats["source_tokens"] == 1250
    assert stats["model_tokens"] == 125
    assert stats["tokens_saved"] == 1125


def test_compression_stats_empty_project(tmp_path):
    stats = compute_compression_stats(tmp_path)
    assert stats["source_bytes"] == 0
    assert stats["compression_ratio"] == 0.0


def test_compression_stats_no_model(tmp_path):
    (tmp_path / "main.py").write_text("x" * 100)
    stats = compute_compression_stats(tmp_path)
    assert stats["source_bytes"] == 100
    assert stats["model_bytes"] == 0
    assert stats["compression_ratio"] == 0.0


def test_compression_stats_excludes_vendor(tmp_path):
    (tmp_path / "main.py").write_text("x" * 100)
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "lib.py").write_text("x" * 9000)
    stats = compute_compression_stats(tmp_path)
    assert stats["source_bytes"] == 100


def test_format_compression_summary():
    stats = {
        "source_bytes": 50000,
        "model_bytes": 1000,
        "compression_ratio": 50.0,
        "source_tokens": 12500,
        "model_tokens": 250,
        "tokens_saved": 12250,
    }
    summary = format_compression_summary(stats)
    assert "50.0x" in summary
    assert "12,250" in summary
