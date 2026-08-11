"""Output types for the decompose pipeline stage."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SystemBoundary:
    """A detected system boundary — either autonomous system or inline component."""

    system_id: str
    name: str
    component_ids: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    complexity: float = 0.0
    is_full_system: bool = True  # False = inline component (too small for own system)


@dataclass
class DecomposeResult:
    """Complete system boundary detection output."""

    systems: list[SystemBoundary] = field(default_factory=list)
    inline_components: list[SystemBoundary] = field(default_factory=list)
    inter_system_edges: list[tuple[str, str, str]] = field(
        default_factory=list
    )  # (from_sys, to_sys, rel_type)
