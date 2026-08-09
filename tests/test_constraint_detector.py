"""Tests for constraint detection from config files."""
from architecture_model.extract.constraint_detector import detect_constraints
from pathlib import Path


def test_detect_constraints_empty_dir(tmp_path):
    constraints = detect_constraints(tmp_path)
    assert constraints == []


def test_detect_python_version_constraint(tmp_path):
    (tmp_path / "pyproject.toml").write_text('''
[project]
name = "myapp"
requires-python = ">=3.11"
dependencies = ["fastapi>=0.100"]
''')
    constraints = detect_constraints(tmp_path)
    assert len(constraints) >= 1
    # Should find python version constraint
    names = [c.name for c in constraints]
    assert any("python" in n.lower() or "Python" in n for n in names)
