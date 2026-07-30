"""Test manifest-based function confidence scoring."""
from architecture_model.core.confidence import compute_function_confidence


def test_empty_function_low_confidence():
    # Simulate a FunctionInfo-like object
    class FI:
        name = "foo"
        signature = "()"
        calls = []
        docstring = None
        raises = []
    score = compute_function_confidence(FI())
    assert score < 0.3


def test_documented_function_medium():
    class FI:
        name = "foo"
        signature = "(x: int, y: str) -> bool"
        calls = ["validate", "process"]
        docstring = "Does the thing."
        raises = []
    score = compute_function_confidence(FI())
    assert 0.5 <= score <= 0.9


def test_full_function_high():
    class FI:
        name = "foo"
        signature = "(x: int, y: str) -> bool"
        calls = ["validate", "process"]
        docstring = "Validates and processes input."
        raises = ["ValueError", "TypeError"]
    score = compute_function_confidence(FI())
    assert score >= 0.8


def test_no_params_lower():
    class FI1:
        name = "foo"
        signature = "()"
        calls = []
        docstring = "Does stuff."
        raises = []
    class FI2:
        name = "bar"
        signature = "(x: int) -> str"
        calls = []
        docstring = "Does stuff."
        raises = []
    score1 = compute_function_confidence(FI1())
    score2 = compute_function_confidence(FI2())
    assert score2 > score1
