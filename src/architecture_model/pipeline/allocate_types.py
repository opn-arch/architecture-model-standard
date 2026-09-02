"""Output types for the allocate pipeline stage."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ComponentAllocation:
    """A component with files allocated to it."""
    id: str
    name: str
    capability_id: str = ""  # which capability seeded this
    files: list[Path] = field(default_factory=list)
    layer: str = ""  # inferred layer (web, service, data, infra)
    evidence: list[str] = field(default_factory=list)


@dataclass
class AllocationResult:
    """Complete file→component mapping."""
    components: list[ComponentAllocation] = field(default_factory=list)
    unallocated: list[Path] = field(default_factory=list)  # files with no home
    file_coverage: float = 0.0  # percentage of files allocated
    boundary_coherence: float = 0.0  # cross-boundary import ratio
