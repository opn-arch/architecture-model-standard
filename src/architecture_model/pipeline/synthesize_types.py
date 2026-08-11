"""Output types for the synthesize pipeline stage."""
from __future__ import annotations

from dataclasses import dataclass, field

from architecture_model.pipeline.protocol import LLMCallRecord, StageResult


@dataclass
class SystemModel:
    """A complete autonomous system model produced by scoped pipeline run."""

    system_id: str
    name: str
    model_yaml: str = ""
    manifest_json: str = ""
    pipeline_report_md: str = ""
    lessons_md: str = ""
    stage_results: dict[str, StageResult] = field(default_factory=dict)
    llm_calls: list[LLMCallRecord] = field(default_factory=list)


@dataclass
class SoSModel:
    """The System-of-Systems top-level model."""

    model_yaml: str = ""
    actors: list[dict] = field(default_factory=list)
    emergent_capabilities: list[dict] = field(default_factory=list)
    cross_system_behaviors: list[dict] = field(default_factory=list)
    inter_system_interfaces: list[dict] = field(default_factory=list)
    constraints: list[dict] = field(default_factory=list)


@dataclass
class SynthesizeResult:
    """Complete synthesis output."""

    sos_model: SoSModel | None = None
    sos_model_yaml: str = ""
    system_models: list[SystemModel] = field(default_factory=list)
    top_manifest_json: str = ""
    pipeline_report_md: str = ""
    lessons_md: str = ""
    all_llm_calls: list[LLMCallRecord] = field(default_factory=list)
