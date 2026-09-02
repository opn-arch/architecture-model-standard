"""Protocol types for the modular extraction pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeVar

if TYPE_CHECKING:
    from .global_learning import GlobalLearningStore
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
    metadata: dict[str, Any] = field(default_factory=dict)

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
        total = sum(e.confidence * SOURCE_WEIGHTS.get(e.source, 0.5) for e in self.evidence)
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
    """Per-stage quality scores with optional per-component breakdown."""

    score: float
    sub_scores: dict[str, float] = field(default_factory=dict)
    thresholds: dict[str, float] = field(default_factory=dict)
    component_scores: dict[str, "QualityMetrics"] = field(default_factory=dict)
    llm_prompt: str = ""

    @property
    def passes(self) -> bool:
        return all(self.sub_scores.get(k, 0.0) >= v for k, v in self.thresholds.items())

    @property
    def worst_component(self) -> tuple[str, float] | None:
        if not self.component_scores:
            return None
        worst = min(self.component_scores.items(), key=lambda kv: kv[1].score)
        return (worst[0], worst[1].score)


class GateSeverity(Enum):
    SOFT = "soft"    # warn and continue
    HARD = "hard"    # block pipeline progression


@dataclass
class GateResult:
    passed: bool
    blocks: bool
    message: str
    metric: str
    actual: float
    threshold: float


@dataclass
class QualityGate:
    metric: str
    threshold: float
    severity: GateSeverity = GateSeverity.SOFT
    direction: str = "gte"  # "gte" = actual >= threshold; "lte" = actual <= threshold

    def evaluate(self, quality: QualityMetrics) -> GateResult:
        actual = quality.sub_scores.get(self.metric, 0.0)
        if self.direction == "lte":
            passed = actual <= self.threshold
        else:
            passed = actual >= self.threshold
        blocks = (not passed) and (self.severity == GateSeverity.HARD)
        verb = "PASS" if passed else ("BLOCKED" if blocks else "WARN")
        message = f"{verb}: {self.metric} = {actual:.1f} (threshold: {self.threshold:.1f})"
        return GateResult(
            passed=passed, blocks=blocks, message=message,
            metric=self.metric, actual=actual, threshold=self.threshold,
        )


class QualityGateError(Exception):
    """Raised when a hard quality gate blocks pipeline progression."""
    def __init__(self, message: str, gate_results: list[GateResult] | None = None):
        super().__init__(message)
        self.gate_results = gate_results or []


@dataclass
class StageQualityReview:
    """Record of quality review after a stage completes."""
    stage: str
    quality: QualityMetrics
    gate_results: list[GateResult]
    llm_review: str = ""
    suggestions: list[str] = field(default_factory=list)
    component_reviews: dict[str, str] = field(default_factory=dict)


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
    summary: str = ""


@dataclass
class PipelineContext:
    """Shared state across pipeline stages."""

    repo_path: Path
    output_dir: Path
    domain: str = "software"
    scope: str = ""
    invocation_source: str = "library"
    invocation: str = ""
    parent_run_id: str | None = None
    run_id: str = ""
    scope_files: list[Path] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    cache: dict[str, StageResult] = field(default_factory=dict)
    prior_corrections: list[Evidence] = field(default_factory=list)
    learning_store: LearningStore | None = field(default=None, repr=False)
    global_learning: GlobalLearningStore | None = field(default=None, repr=False)
    calibration: dict[str, Any] = field(default_factory=dict)
    llm_calls: list[LLMCallRecord] = field(default_factory=list)
    enrichment_log: list[EnrichmentRecord] = field(default_factory=list)
    review_log: list[StageQualityReview] = field(default_factory=list)
    refinement_logs: list[Any] = field(default_factory=list)
    history_warnings: list[str] = field(default_factory=list)
    # LLM enrichment callback: stages can call this for naming, classification, etc.
    # Signature: async (stage: str, prompt: str, context: dict) -> str
    # If None, stages use heuristic fallbacks (deterministic mode).
    llm_callback: Any = field(default=None, repr=False)

    def has(self, stage_name: str) -> bool:
        return stage_name in self.cache

    def get(self, stage_name: str) -> StageResult | None:
        return self.cache.get(stage_name)

    async def llm_enrich(self, stage: str, prompt: str, context: dict | None = None) -> str | None:
        """Call LLM enrichment if callback is registered. Returns None if no LLM available."""
        if self.llm_callback is None:
            return None
        import time as _time

        start = _time.time()
        try:
            result = await self.llm_callback(stage, prompt, context or {})
            duration_ms = int((_time.time() - start) * 1000)
            self.llm_calls.append(
                LLMCallRecord(
                    stage=stage,
                    purpose=prompt[:100],
                    timestamp=_time.strftime("%Y-%m-%dT%H:%M:%S"),
                    duration_ms=duration_ms,
                    confidence=0.7,
                    items_produced=1,
                    notes=result[:200] if result else "",
                )
            )
            return result
        except Exception:
            return None


@dataclass
class LLMCallRecord:
    """Record of a single LLM invocation during pipeline execution."""

    stage: str
    purpose: str
    resolution_id: str = ""
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


@dataclass
class EnrichmentRecord:
    """Record of a single LLM enrichment applied to an entity."""

    entity_id: str
    entity_type: str  # capability, component, etc.
    stage: str
    old_value: str
    new_value: str
    prompt: str
    response: str
    timestamp: str
    model: str = ""
    duration_ms: int = 0
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArtifactReview:
    """LLM review of a generated artifact."""

    artifact_path: str
    review_summary: str
    comments: list[str]
    prompt_sent: str
    response_received: str
    timestamp: str
    model: str = ""
    duration_ms: int = 0
    token_count: int = 0


class Stage(Protocol[T]):
    """Protocol that every pipeline module implements."""

    name: str
    version: str
    requires: list[str]

    def run(self, context: PipelineContext) -> StageResult[T]: ...
    def can_run(self, context: PipelineContext) -> bool: ...
    def output_path(self, context: PipelineContext) -> Path: ...
