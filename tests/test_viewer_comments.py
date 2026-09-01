"""Tests for viewer comment textarea, localStorage persistence, and YAML export/import."""

import tempfile
from pathlib import Path

import pytest

from architecture_model.core.parser import _parse_raw
from architecture_model.core.visualize import generate_html_viewer


@pytest.fixture
def minimal_model():
    return _parse_raw(
        {
            "meta": {"project": "test-proj", "schema_version": "1.3"},
            "entities": {
                "components": [
                    {"id": "COMP-1", "name": "Foo", "status": "ACTIVE"},
                ],
            },
            "relationships": [],
        }
    )


@pytest.fixture
def html_output(minimal_model, tmp_path):
    out = tmp_path / "viewer.html"
    generate_html_viewer(minimal_model, out)
    return out.read_text()


def test_comment_textarea_class(html_output):
    assert "comment-textarea" in html_output


def test_comment_section_css(html_output):
    assert ".comment-section" in html_output


def test_localstorage_reference(html_output):
    assert "localStorage" in html_output


def test_export_comments_function(html_output):
    assert "exportComments" in html_output


def test_import_comments_function(html_output):
    assert "importComments" in html_output


def test_toolbar_buttons_present(html_output):
    assert "Export Comments" in html_output
    assert "Import Comments" in html_output


def test_save_comment_function(html_output):
    assert "saveComment" in html_output


def test_comment_placeholder(html_output):
    assert "Add notes about this entity" in html_output
