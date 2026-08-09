"""Output types for the validate pipeline stage."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationIssue:
    """A specific validation issue found."""
    severity: str  # error, warning, info
    message: str
    entity_id: str = ""
    rule: str = ""


@dataclass
class ValidateResult:
    """Validation output for the complete model."""
    score: int  # 0-100
    issues: list[ValidationIssue] = field(default_factory=list)
    is_valid: bool = True
