"""Tests for safe change classification and application."""
from architecture_model.quality.code_safety import (
    classify_suggestion, SafetyLevel, SafeChangeType,
    SAFE_CHANGE_TYPES,
)


class TestSafetyClassification:
    def test_docstring_is_safe(self):
        assert classify_suggestion("Add docstring to foo") == SafetyLevel.SAFE

    def test_refactor_is_risky(self):
        assert classify_suggestion("Rewrite the algorithm to use dynamic programming") == SafetyLevel.RISKY

    def test_type_hint_is_safe(self):
        assert classify_suggestion("Add type hint: x: int") == SafetyLevel.SAFE

    def test_remove_import_is_safe(self):
        assert classify_suggestion("Remove unused import os") == SafetyLevel.SAFE

    def test_change_logic_is_risky(self):
        assert classify_suggestion("Change the return value from None to empty list") == SafetyLevel.RISKY


class TestSafeChangeTypes:
    def test_all_types_registered(self):
        assert "docstring" in SAFE_CHANGE_TYPES
        assert "type_hint" in SAFE_CHANGE_TYPES
        assert "dead_import" in SAFE_CHANGE_TYPES
        assert "function_split" in SAFE_CHANGE_TYPES
        assert "error_handling" in SAFE_CHANGE_TYPES

    def test_extensible(self):
        # Should be a dict/registry pattern
        assert isinstance(SAFE_CHANGE_TYPES, dict)
