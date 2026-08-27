"""Tests for contract pipeline stage — test file to component matching."""
from pathlib import Path

from architecture_model.pipeline.contract import _match_target


def test_match_strips_test_prefix():
    """Target with test_ prefix should match component via substring (strategy 4)."""
    stem_to_comp = {"ansi": "COMP-2", "winterm": "COMP-3"}
    name_to_comp = {"ansi": "COMP-2", "winterm": "COMP-3"}
    result = _match_target("test_ansi", Path("tests/test_ansi.py"), stem_to_comp, name_to_comp)
    assert result == "COMP-2"


def test_match_strips_test_suffix():
    """Target with _test suffix should match component via substring (strategy 4)."""
    stem_to_comp = {"parser": "COMP-1"}
    name_to_comp = {"parser": "COMP-1"}
    result = _match_target("parser_test", Path("tests/parser_test.py"), stem_to_comp, name_to_comp)
    assert result == "COMP-1"


def test_match_compound_test_name():
    """Compound test name like test_ansitowin32 should match component."""
    stem_to_comp = {"ansitowin32": "COMP-1"}
    name_to_comp = {"ansitowin32": "COMP-1"}
    result = _match_target("test_ansitowin32", Path("tests/test_ansitowin32.py"), stem_to_comp, name_to_comp)
    assert result == "COMP-1"


def test_match_exact_stem():
    """Pre-stripped target should match via exact stem (strategy 1)."""
    stem_to_comp = {"ansi": "COMP-2"}
    name_to_comp = {"ansi": "COMP-2"}
    result = _match_target("ansi", Path("tests/test_ansi.py"), stem_to_comp, name_to_comp)
    assert result == "COMP-2"


def test_match_no_match():
    """Unrelated target should return empty string."""
    stem_to_comp = {"ansi": "COMP-2"}
    name_to_comp = {"ansi": "COMP-2"}
    result = _match_target("foobar", Path("tests/test_foobar.py"), stem_to_comp, name_to_comp)
    assert result == ""
