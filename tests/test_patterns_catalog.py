"""Test pattern catalog loading."""
from architecture_model.patterns import load_patterns, get_pattern


def test_load_patterns_returns_dict():
    patterns = load_patterns()
    assert isinstance(patterns, dict)
    assert len(patterns) >= 10


def test_pattern_has_required_fields():
    patterns = load_patterns()
    for name, p in patterns.items():
        assert "description" in p, f"{name} missing description"
        assert "indicators" in p, f"{name} missing indicators"
        assert isinstance(p["indicators"], list)


def test_get_pattern_returns_none_for_unknown():
    assert get_pattern("nonexistent-xyz") is None


def test_get_pattern_returns_dict_for_known():
    p = get_pattern("entity-platform")
    assert p is not None
    assert "description" in p
