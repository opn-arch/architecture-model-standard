"""Output types for the contract pipeline stage."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TestContract:
    """A test contract linking a test to a component."""
    test_file: str
    target_component: str
    assertions: int = 0
    description: str = ""


@dataclass
class ContractResult:
    """Test contracts mapped to components."""
    contracts: list[TestContract] = field(default_factory=list)
    coverage_ratio: float = 0.0  # components with tests / total components
