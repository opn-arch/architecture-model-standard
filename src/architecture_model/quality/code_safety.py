"""Safe change classification and application for auto-improvement."""
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
import re


class SafetyLevel(Enum):
    SAFE = "safe"       # auto-apply, verify with tests
    CAUTIOUS = "cautious"  # auto-apply but flag for review
    RISKY = "risky"     # requires human review


@dataclass
class SafeChangeType:
    name: str
    description: str
    safety: SafetyLevel
    keywords: list[str]  # for classification


# Registry of safe change types — extensible
SAFE_CHANGE_TYPES: dict[str, SafeChangeType] = {
    "docstring": SafeChangeType(
        name="docstring", description="Add missing docstrings",
        safety=SafetyLevel.SAFE,
        keywords=["docstring", "documentation", "doc comment"],
    ),
    "type_hint": SafeChangeType(
        name="type_hint", description="Add missing type annotations",
        safety=SafetyLevel.SAFE,
        keywords=["type hint", "type annotation", "typing", "annotate"],
    ),
    "dead_import": SafeChangeType(
        name="dead_import", description="Remove unused imports",
        safety=SafetyLevel.SAFE,
        keywords=["unused import", "dead import", "remove import"],
    ),
    "function_split": SafeChangeType(
        name="function_split", description="Split long functions into smaller ones",
        safety=SafetyLevel.CAUTIOUS,
        keywords=["split function", "extract function", "break up", "decompose function"],
    ),
    "error_handling": SafeChangeType(
        name="error_handling", description="Add missing error handling",
        safety=SafetyLevel.CAUTIOUS,
        keywords=["error handling", "try except", "exception", "raise"],
    ),
}


def classify_suggestion(description: str) -> SafetyLevel:
    """Classify a code change suggestion as safe, cautious, or risky."""
    desc_lower = description.lower()

    # Check against known safe change types
    for change_type in SAFE_CHANGE_TYPES.values():
        for keyword in change_type.keywords:
            if keyword in desc_lower:
                return change_type.safety

    # Risky indicators
    risky_patterns = [
        r"rewrite", r"change.*return", r"change.*logic", r"replace.*algorithm",
        r"modify.*behavior", r"remove.*function", r"delete", r"restructure",
        r"dynamic programming", r"redesign",
    ]
    for pattern in risky_patterns:
        if re.search(pattern, desc_lower):
            return SafetyLevel.RISKY

    # Default: risky (conservative)
    return SafetyLevel.RISKY


def register_safe_change(name: str, description: str, keywords: list[str],
                          safety: SafetyLevel = SafetyLevel.SAFE) -> None:
    """Register a new safe change type (extensibility hook)."""
    SAFE_CHANGE_TYPES[name] = SafeChangeType(
        name=name, description=description, safety=safety, keywords=keywords,
    )
