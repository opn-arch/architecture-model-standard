"""Tests for full-pipeline init command."""
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from architecture_model.cli.main import main


def _create_mini_project(tmp: Path):
    """Create a minimal Python project for init."""
    (tmp / "app.py").write_text("def hello(): pass\n")
    (tmp / "utils.py").write_text("import app\ndef helper(): pass\n")


def test_init_runs_full_pipeline(tmp_path):
    """init should write config AND run pipeline."""
    _create_mini_project(tmp_path)
    
    with patch("sys.argv", ["architecture-model", "init", str(tmp_path)]):
        code = main()
    
    assert code == 0
    assert (tmp_path / ".architecture-model.yaml").exists()
    # Pipeline ran (produces manifests dir)
    assert (tmp_path / ".architecture-models").is_dir()


def test_init_config_only_flag(tmp_path):
    """--config-only should skip pipeline."""
    _create_mini_project(tmp_path)
    
    with patch("sys.argv", ["architecture-model", "init", str(tmp_path), "--config-only"]):
        code = main()
    
    assert code == 0
    assert (tmp_path / ".architecture-model.yaml").exists()
    assert not (tmp_path / ".architecture-models").is_dir()


def test_init_shows_compression_info(tmp_path, capsys):
    """init should display compression/token info after pipeline."""
    _create_mini_project(tmp_path)
    
    with patch("sys.argv", ["architecture-model", "init", str(tmp_path)]):
        main()
    
    captured = capsys.readouterr()
    # Should mention tokens or compression somewhere
    assert "token" in captured.out.lower() or "compression" in captured.out.lower()
