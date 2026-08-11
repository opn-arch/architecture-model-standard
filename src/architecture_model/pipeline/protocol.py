"""Protocol types for the modular extraction pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeVar

if TYPE_CHECKING:
    from .learning import LearningStore

T = TypeVar("T")

SOURCE_WEIGHTS: dict[str, float] = {
    "ast": 1.0,
    "user_confirmation": 1.0,
    "user_correction": 1.0,
    "test": 0.95,
    "config": 0.9,
    "netlist": 0.95,
    "cad": 0.95,
    "plc_program": 0.95,
    "io_list": 0.9,
    "documentation": 0.8,
    "datasheet": 0.85,
    "material_spec": 0.9,
    "sil_assessment": 0.9,
    "drawing": 0.85,
    "schematic": 0.9,
    "git_history": 0.7,
    "llm_analysis": 0.6,
    "search_result": 0.5,
}


@dataclass
class Evidence:
    """Provenance for a model claim."""

    source: str
    confidence: float
    raw: str
    location: str = ""

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")


@dataclass
class Claim(Generic[T]):
    """A model assertion with provenance."""

    value: T
    evidence: list[Evidence] = field(default_factory=list)
    uncertain: bool = False

    @property
    def confidence(self) -> float:
        if not self.evidence:
            return 0.0
        total = sum(
            e.confidence * SOURCE_WEIGHTS.get(e.source, 0.5) for e in self.evidence
        )
        result = total / len(self.evidence)
        return min(result, 1.0)


@dataclass
class Uncertainty:
    """Something a module couldn't determine."""

    category: str
    description: str
    context: dict[str, Any] = field(default_factory=dict)
    suggested_fallback: str = "llm_analysis"
    priority: str = "enriching"


@dataclass
class Diagnostic:
    """Issue/warning/info from a stage."""

    severity: str
    code: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityMetrics:
    """Per-stage quality scores."""

    score: float
    sub_scores: dict[str, float] = field(default_factory=dict)
    thresholds: dict[str, float] = field(default_factory=dict)
    llm_prompt: str = ""

    @property
    def passes(self) -> bool:
        return all(
            self.sub_scores.get(k, 0.0) >= v for k, v in self.thresholds.items()
        )


@dataclass
class StageResult(Generic[T]):
    """Complete output of a stage."""

    output: T
    quality: QualityMetrics
    diagnostics: list[Diagnostic] = field(default_factory=list)
    uncertainties: list[Uncertainty] = field(default_factory=list)
    input_hash: str = ""
    duration_ms: int = 0
    version: str = "1.0"


@dataclass
class PipelineContext:
    """Shared state across pipeline stages."""

    repo_path: Path
    output_dir: Path
    domain: str = "software"
    scope: str = ""
    scope_files: list[Path] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    cache: dict[str, StageResult] = field(default_factory=dict)
    prior_corrections: list[Evidence] = field(default_factory=list)
    learning_store: LearningStore | None = field(default=None, repr=False)
    calibration: dict[str, Any] = field(default_factory=dict)
    llm_calls: list[LLMCallRecord] = field(default_factory=list)

    def has(self, stage_name: str) -> bool:
        return stage_name in self.cache

    def get(self, stage_name: str) -> StageResult | None:
        return self.cache.get(stage_name)


@dataclass
class LLMCallRecord:
    """Record of a single LLM invocation during pipeline execution."""

    stage: str
    purpose: str
    timestamp: str = ""
    files_sent: list[str] = field(default_factory=list)
    slices_sent: list[str] = field(default_factory=list)
    prompt_template: str = ""
    prompt_tokens: int = 0
    context_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    duration_ms: int = 0
    cached: bool = False
    output_used: bool = True
    confidence: float = 0.0
    items_produced: int = 0
    notes: str = ""


class Stage(Protocol[T]):
    """Protocol that every pipeline module implements."""

    name: str
    version: str
    requires: list[str]

    def run(self, context: PipelineContext) -> StageResult[T]: ...
    def can_run(self, context: PipelineContext) -> bool: ...
    def output_path(self, context: PipelineContext) -> Path: ...
