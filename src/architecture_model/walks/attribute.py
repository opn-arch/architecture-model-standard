"""architecture_model.walks.attribute — Attribute schema with categories.

Attributes drive decomposition. They come from users, requirements,
walks, and derived analysis, and they flow through a lifecycle:

    draft (Category A) → committed (B) → promised (C)

Categories per Q5=hybrid: schema defaults per attribute name; inline
override allowed when the semantics deviate.

Provenance per Q7=full: every attribute carries value, source,
confidence, verified_by from day one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

__all__ = [
    "Attribute",
    "AttributeCategory",
    "AttributeSource",
    "DEFAULT_CATEGORY",
    "default_category",
]


class AttributeCategory(str, Enum):
    """The three attribute categories.

    - A (authoring): private designer state; never promoted.
    - B (specification): internal commitments; promotable to C.
    - C (promise): external contracts; testable, contract-shaped.
    """

    A = "authoring"
    B = "specification"
    C = "promise"


class AttributeSource(str, Enum):
    """Where an attribute value came from — governs authority in rollup."""

    USER = "user"
    REQUIREMENT = "requirement"
    WALK = "walk"
    DERIVED = "derived"
    PIPELINE = "pipeline"


# Schema defaults — attribute name → category. Hybrid model (Q5=c): the
# schema provides defaults; individual entities may override inline.
DEFAULT_CATEGORY: dict[str, AttributeCategory] = {
    # Category A — authoring (never promoted)
    "intent": AttributeCategory.A,
    "rationale": AttributeCategory.A,
    "trade_offs": AttributeCategory.A,
    "assumptions": AttributeCategory.A,
    "open_questions": AttributeCategory.A,
    "risks": AttributeCategory.A,
    # Category B — specification (promotable)
    "goals": AttributeCategory.B,
    "requirements": AttributeCategory.B,
    "success_criteria": AttributeCategory.B,
    "failure_modes": AttributeCategory.B,
    "constraints": AttributeCategory.B,
    # Category C — promise (external contracts)
    "promises": AttributeCategory.C,
    "exposed_interfaces": AttributeCategory.C,
    "slos": AttributeCategory.C,
}


def default_category(name: str) -> AttributeCategory | None:
    """Return the schema-default category for a named attribute, or None."""
    return DEFAULT_CATEGORY.get(name)


@dataclass(frozen=True)
class Attribute:
    """A single categorized, provenance-tracked attribute value.

    Fields:
      value: the payload (string, list, dict — semantics per attribute).
      source: where the value came from.
      confidence: 0.0..1.0 estimate of reliability.
      verified_by: paths / references providing evidence.
      category: optional inline override; falls back to schema default.
    """

    value: Any
    source: AttributeSource = AttributeSource.USER
    confidence: float = 1.0
    verified_by: tuple[str, ...] = ()
    category: AttributeCategory | None = None

    def effective_category(self, name: str) -> AttributeCategory | None:
        """Return the effective category — inline override or schema default."""
        return self.category or default_category(name)

    def is_empty(self) -> bool:
        """True when the value is missing/empty (drives needs-enrichment)."""
        if self.value is None:
            return True
        if isinstance(self.value, (list, tuple, dict, set, str)):
            return len(self.value) == 0
        return False

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"value": self.value}
        if self.source != AttributeSource.USER:
            d["source"] = self.source.value
        if self.confidence != 1.0:
            d["confidence"] = self.confidence
        if self.verified_by:
            d["verified_by"] = list(self.verified_by)
        if self.category is not None:
            d["category"] = self.category.value
        return d

    @classmethod
    def from_dict(cls, raw: Any) -> "Attribute":
        """Parse an attribute from YAML/JSON.

        Accepts either a bare value (any non-dict) or a dict with the
        provenance fields. Bare values default to USER source and 1.0
        confidence.
        """
        if not isinstance(raw, dict) or "value" not in raw:
            return cls(value=raw)
        return cls(
            value=raw["value"],
            source=AttributeSource(raw.get("source", "user")),
            confidence=float(raw.get("confidence", 1.0)),
            verified_by=tuple(raw.get("verified_by", ())),
            category=(
                AttributeCategory(raw["category"]) if "category" in raw else None
            ),
        )
