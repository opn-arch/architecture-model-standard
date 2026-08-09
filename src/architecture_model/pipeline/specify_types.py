"""Output types for the specify pipeline stage."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InterfaceSpec:
    """An interface specification derived from code."""
    id: str
    name: str
    component_id: str
    interface_type: str = "rest"  # rest, grpc, event, cli, library
    methods: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class SpecifyResult:
    """Interface specifications for the system."""
    interfaces: list[InterfaceSpec] = field(default_factory=list)
