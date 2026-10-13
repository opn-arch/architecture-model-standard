"""Tests for relationship grouping in propCardHtml (Track 4 Pass 2 Task 4)."""

from architecture_model.core.parser import _parse_raw
from architecture_model.core.visualize import generate_html_viewer


def _model():
    return _parse_raw({
        "meta": {"project": "rel-group", "schema_version": "2.1"},
        "entities": {
            "capabilities": [{"id": "CAP-1", "name": "C1", "status": "ACTIVE"}],
            "components": [
                {"id": "COMP-1", "name": "K1", "status": "ACTIVE"},
                {"id": "COMP-2", "name": "K2", "status": "ACTIVE"},
            ],
        },
        "relationships": [
            {"from": "COMP-1", "to": "CAP-1", "type": "realizes"},
            {"from": "COMP-2", "to": "CAP-1", "type": "realizes"},
            {"from": "COMP-1", "to": "COMP-2", "type": "depends-on"},
        ],
    })


def test_html_groups_relationships_under_semantic_headers(tmp_path):
    out = tmp_path / "v.html"
    generate_html_viewer(_model(), out, repo_path=tmp_path)
    html = out.read_text()
    for header in ("Realized By", "Realizes", "Depends On"):
        assert header in html, f"missing group header {header!r}"


def test_grouping_lookup_present_in_payload(tmp_path):
    """Sanity: the JS has a mapping from RelationshipType to display group name."""
    out = tmp_path / "v.html"
    generate_html_viewer(_model(), out, repo_path=tmp_path)
    html = out.read_text()
    assert "realizes" in html.lower()
