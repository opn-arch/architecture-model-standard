"""Output types for the infer pipeline stage."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InferredCapability:
    """A capability inferred from code patterns."""
    id: str
    name: str
    description: str = ""
    evidence_source: str = ""  # "routes", "domain_module", "test_pattern"
    sub_capabilities: list[str] = field(default_factory=list)
    intent: str = ""
    goals: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    monitored: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)
    source_key: str = ""


@dataclass
class InferredActor:
    """An external actor inferred from auth/interface patterns."""
    id: str
    name: str
    actor_type: str = "human"  # human | system | timer
    evidence_source: str = ""


@dataclass
class InferredBehavior:
    """A use case / workflow inferred from trigger chains."""
    id: str
    name: str
    actor_id: str = ""
    capability_id: str = ""
    steps: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    behavior_type: str = "use_case"  # use_case | workflow | route_handler
    source_file: str = ""
    intent: str = ""


@dataclass
class InferenceResult:
    """Complete inference output — capabilities, actors, behaviors."""
    capabilities: list[InferredCapability] = field(default_factory=list)
    actors: list[InferredActor] = field(default_factory=list)
    behaviors: list[InferredBehavior] = field(default_factory=list)
