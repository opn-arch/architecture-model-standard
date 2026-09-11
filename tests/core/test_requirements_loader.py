"""Tests for _load_requirements helper (Track 4 Pass 2 Task 5).

Schema discovered in .architecture/derived_requirements.yaml:
    Top-level key: ``derived_requirements`` (list).
    Per-item link field: ``component_id`` (string; may be empty).
    Per-item identity: ``id``; text lives in ``name`` (plus ``evidence``).
Tests exercise the real schema plus the loader's totality guarantees.
"""

import yaml

from architecture_model.core.visualize import _load_requirements


def test_load_requirements_builds_entity_index(tmp_path):
    """A YAML with N requirements produces a component_id -> [requirement] dict."""
    req_dir = tmp_path / ".architecture"
    req_dir.mkdir()
    (req_dir / "derived_requirements.yaml").write_text(yaml.safe_dump({
        "derived_requirements": [
            {"id": "REQ-1", "name": "System must foo", "component_id": "COMP-1"},
            {"id": "REQ-2", "name": "System must bar", "component_id": "COMP-1"},
            {"id": "REQ-3", "name": "System must baz", "component_id": "CAP-1"},
            # Empty component_id must be ignored (matches real-file pattern).
            {"id": "REQ-4", "name": "Orphan", "component_id": ""},
        ],
    }))
    index = _load_requirements(tmp_path)
    assert set(index.keys()) == {"COMP-1", "CAP-1"}
    assert len(index["COMP-1"]) == 2
    assert index["CAP-1"][0]["id"] == "REQ-3"


def test_load_requirements_missing_file_returns_empty_index(tmp_path):
    """Missing derived_requirements.yaml -> empty dict, no exception."""
    index = _load_requirements(tmp_path)
    assert index == {}
