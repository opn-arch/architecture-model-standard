"""Test that _files_match uses full path, not just basename."""
from architecture_model.core.representativeness import _files_match


def test_files_match_exact_path():
    assert _files_match("src/app/utils.py", "src/app/utils.py")


def test_files_match_basename_collision():
    """Different dirs with same basename should NOT match."""
    assert not _files_match("src/app/utils.py", "src/worker/utils.py")


def test_files_match_init_collision():
    """Different __init__.py files should NOT match."""
    assert not _files_match("src/app/__init__.py", "src/worker/__init__.py")


def test_files_match_suffix_match():
    """Should match when one path is a suffix of the other."""
    assert _files_match("app/utils.py", "src/app/utils.py")
    assert _files_match("src/app/utils.py", "app/utils.py")


def test_files_match_no_false_positive_substring():
    """utils.py should not match my_utils.py."""
    assert not _files_match("src/utils.py", "src/my_utils.py")
