"""Output types for the relate pipeline stage."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DerivedRelationship:
    """A relationship derived from code evidence."""
    from_id: str
    to_id: str
    rel_type: str  # realizes, depends-on, contains, exposes, etc.
    evidence_source: str = ""  # "import", "call", "inheritance", "config"
    confidence: float = 1.0


@dataclass
class RelateResult:
    """All derived relationships between architecture entities."""
    relationships: list[DerivedRelationship] = field(default_factory=list)
