"""Tests for from_artifacts extraction and table_parser."""
from architecture_model.extract.table_parser import parse_tables
from architecture_model.extract.from_artifacts import extract_from_artifacts
from pathlib import Path


def test_parse_tables_simple():
    md = """| Name | Type |
|------|------|
| Foo  | bar  |
| Baz  | qux  |"""
    tables = parse_tables(md)
    assert len(tables) == 1
    assert len(tables[0]) == 2
    assert tables[0][0]["name"] == "Foo"


def test_extract_from_artifacts_empty(tmp_path):
    result = extract_from_artifacts(tmp_path)
    # Should return empty or minimal result without crashing
    assert result is not None
