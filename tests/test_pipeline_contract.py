"""Tests for contract pipeline stage — test file to component matching."""
from pathlib import Path

from architecture_model.pipeline.contract import _match_target


# --- _match_target tests ---

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


# --- Scoped test file discovery tests ---

def test_find_tests_for_scope_flat_layout(tmp_path):
    """Scoped observe should discover test files in flat tests/ dir targeting scope stems."""
    from architecture_model.pipeline.observe import _find_tests_for_scope

    # Create flat layout: colorama/ansi.py + tests/test_ansi.py
    (tmp_path / "colorama").mkdir()
    (tmp_path / "colorama" / "ansi.py").write_text("# ansi module")
    (tmp_path / "colorama" / "winterm.py").write_text("# winterm module")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_ansi.py").write_text("# test ansi")
    (tmp_path / "tests" / "test_winterm.py").write_text("# test winterm")
    (tmp_path / "tests" / "test_unrelated.py").write_text("# unrelated")

    scope_stems = {"ansi", "winterm", "__init__"}
    results = _find_tests_for_scope(tmp_path, scope_stems)

    targets = {r.targets[0] for r in results}
    assert targets == {"ansi", "winterm"}
    assert len(results) == 2


def test_find_tests_for_scope_suffix_style(tmp_path):
    """Should also find <stem>_test.py files."""
    from architecture_model.pipeline.observe import _find_tests_for_scope

    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "parser_test.py").write_text("# test parser")

    results = _find_tests_for_scope(tmp_path, {"parser"})
    assert len(results) == 1
    assert results[0].targets == ["parser"]


def test_find_tests_for_scope_no_test_dir(tmp_path):
    """Should return empty if no tests/ directory exists."""
    from architecture_model.pipeline.observe import _find_tests_for_scope

    results = _find_tests_for_scope(tmp_path, {"ansi"})
    assert results == []
