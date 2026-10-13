"""Tests for Linked Requirements section in drill-down (Track 4 Pass 2 Task 6).

Schema discovery note (T5): the real ``derived_requirements.yaml`` produced by
this repo's pipeline stores requirement text in ``name`` (not ``text`` or
``description``), and links to components via ``component_id`` (with
``entity_id`` / ``traces_to`` accepted as fallbacks by ``_load_requirements``).
The fixture below uses the real ``name`` field; the JS render block uses a
``name || text || description || id`` fallback chain so both real data and
legacy shapes render correctly.
"""

from pathlib import Path

import yaml

from architecture_model.core.parser import _parse_raw
from architecture_model.core.visualize import generate_html_viewer


def test_html_contains_linked_requirements_section(tmp_path):
    """When derived_requirements.yaml links entity_id, HTML shows the section."""
    (tmp_path / ".architecture").mkdir()
    (tmp_path / ".architecture" / "derived_requirements.yaml").write_text(
        yaml.safe_dump({
            "requirements": [
                # Real schema uses `name` for display text; `entity_id` is an
                # accepted link fallback alongside the canonical `component_id`.
                {"id": "REQ-42", "name": "Must be fast", "entity_id": "COMP-1"},
            ],
        })
    )
    model = _parse_raw({
        "meta": {"project": "req-render", "schema_version": "2.1"},
        "entities": {
            "components": [{"id": "COMP-1", "name": "Fast", "status": "ACTIVE"}],
        },
    })
    out = tmp_path / "v.html"
    generate_html_viewer(model, out, repo_path=tmp_path)
    html = out.read_text()
    # The payload key must be present
    assert "requirements_by_entity" in html
    # The specific requirement id must be present in the payload
    assert "REQ-42" in html
    # The header text must be present in the JS renderer
    assert "Linked Requirements" in html
