"""Synthesize stage — build per-system models and assemble System-of-Systems."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import yaml

from architecture_model.pipeline.decompose_types import DecomposeResult, SystemBoundary
from architecture_model.pipeline.lessons import LessonEntry, generate_lessons
from architecture_model.pipeline.protocol import (
    Diagnostic,
    LLMCallRecord,
    PipelineContext,
    QualityMetrics,
    StageResult,
)
from architecture_model.pipeline.report import generate_pipeline_report
from architecture_model.pipeline.synthesize_types import (
    SoSModel,
    SynthesizeResult,
    SystemModel,
)

FULL_PIPELINE_STAGES = [
    "observe",
    "infer",
    "allocate",
    "relate",
    "specify",
    "contract",
    "validate",
]
ABBREVIATED_STAGES = ["observe", "infer"]


def _decide_stages(boundary: SystemBoundary) -> list[str]:
    """Decide which pipeline stages to run based on system complexity."""
    if len(boundary.files) >= 8:
        return list(FULL_PIPELINE_STAGES)
    return list(ABBREVIATED_STAGES)


def _slugify(name: str) -> str:
    """Convert name to filesystem-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _build_system_model_yaml(
    boundary: SystemBoundary, results: dict[str, StageResult]
) -> str:
    """Build a YAML model string from scoped pipeline results."""
    components: list[dict[str, Any]] = []
    capabilities: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []

    # Extract from allocate results
    alloc_result = results.get("allocate")
    if alloc_result and alloc_result.output:
        output = alloc_result.output
        if hasattr(output, "components"):
            for comp in output.components:
                comp_dict: dict[str, Any] = {"id": comp.id, "name": comp.name}
                if hasattr(comp, "files") and comp.files:
                    comp_dict["files"] = [str(f) for f in comp.files]
                components.append(comp_dict)

    # Extract from infer results
    infer_result = results.get("infer")
    if infer_result and infer_result.output:
        output = infer_result.output
        if hasattr(output, "capabilities"):
            for cap in output.capabilities:
                cap_dict: dict[str, Any] = {"id": cap.id, "name": cap.name}
                capabilities.append(cap_dict)

    # Extract from relate results
    relate_result = results.get("relate")
    if relate_result and relate_result.output:
        output = relate_result.output
        if hasattr(output, "relationships"):
            for rel in output.relationships:
                relationships.append(
                    {
                        "from": rel.from_id,
                        "to": rel.to_id,
                        "type": rel.rel_type,
                    }
                )

    model_dict: dict[str, Any] = {
        "meta": {
            "schema_version": "2.0",
            "system": boundary.name,
            "system_id": boundary.system_id,
        },
        "entities": {},
        "relationships": relationships,
    }
    if components:
        model_dict["entities"]["components"] = components
    if capabilities:
        model_dict["entities"]["capabilities"] = capabilities

    return yaml.dump(model_dict, default_flow_style=False, sort_keys=False)


def _build_manifest_json(results: dict[str, StageResult]) -> str:
    """Build manifest JSON from observe results."""
    observe_result = results.get("observe")
    if not observe_result or not observe_result.output:
        return "{}"

    output = observe_result.output
    modules: list[dict[str, Any]] = []
    if hasattr(output, "modules"):
        for mod in output.modules:
            mod_dict: dict[str, Any] = {"file": str(mod.file_path)}
            if hasattr(mod, "functions"):
                mod_dict["functions"] = len(mod.functions)
            if hasattr(mod, "classes"):
                mod_dict["classes"] = len(mod.classes)
            modules.append(mod_dict)

    return json.dumps({"modules": modules}, indent=2)


def _build_sos_model(
    systems: list[SystemModel],
    inlines: list[SystemBoundary],
    decompose: DecomposeResult,
    top_results: dict[str, StageResult],
) -> SoSModel:
    """Assemble the System-of-Systems model."""
    # Extract top-level actors and capabilities from infer stage
    actors: list[dict[str, Any]] = []
    capabilities: list[dict[str, Any]] = []
    behaviors: list[dict[str, Any]] = []

    infer_result = top_results.get("infer")
    if infer_result and infer_result.output:
        output = infer_result.output
        if hasattr(output, "actors"):
            for actor in output.actors:
                actors.append({"id": getattr(actor, "id", ""), "name": getattr(actor, "name", "")})
        if hasattr(output, "capabilities"):
            for cap in output.capabilities:
                capabilities.append({"id": getattr(cap, "id", ""), "name": getattr(cap, "name", "")})
        if hasattr(output, "behaviors"):
            for beh in output.behaviors:
                behaviors.append({"id": getattr(beh, "id", ""), "name": getattr(beh, "name", "")})

    # Inter-system interfaces from decompose edges
    inter_system_interfaces: list[dict[str, Any]] = []
    for from_sys, to_sys, rel_type in decompose.inter_system_edges:
        inter_system_interfaces.append(
            {"from": from_sys, "to": to_sys, "type": rel_type}
        )

    # Build SoS YAML
    sos_dict: dict[str, Any] = {
        "meta": {
            "schema_version": "2.0",
            "system_of_systems": True,
        },
        "entities": {
            "systems": [
                {
                    "id": s.system_id,
                    "name": s.name,
                    "model_path": f"{_slugify(s.name)}/.architecture-model.yaml",
                }
                for s in systems
            ],
        },
        "relationships": inter_system_interfaces,
    }
    if actors:
        sos_dict["entities"]["actors"] = actors
    if capabilities:
        sos_dict["entities"]["capabilities"] = capabilities

    # Add inline components
    if inlines:
        sos_dict["entities"]["inline_components"] = [
            {"id": i.system_id, "name": i.name, "files": i.files}
            for i in inlines
        ]

    sos_yaml = yaml.dump(sos_dict, default_flow_style=False, sort_keys=False)

    return SoSModel(
        model_yaml=sos_yaml,
        actors=actors,
        emergent_capabilities=capabilities,
        cross_system_behaviors=behaviors,
        inter_system_interfaces=inter_system_interfaces,
    )


def _collect_lessons(results: dict[str, StageResult], llm_calls: list[LLMCallRecord]) -> list[LessonEntry]:
    """Collect lesson entries from all stage results."""
    entries: list[LessonEntry] = []
    for stage_name, result in results.items():
        entries.extend(LessonEntry.from_diagnostics(stage_name, result.diagnostics))
        entries.extend(LessonEntry.from_uncertainties(stage_name, result.uncertainties))
    # LLM call lessons grouped by stage
    stage_calls: dict[str, list[LLMCallRecord]] = {}
    for call in llm_calls:
        stage_calls.setdefault(call.stage, []).append(call)
    for stage_name, calls in stage_calls.items():
        entries.extend(LessonEntry.from_llm_calls(stage_name, calls))
    return entries


class SynthesizeStage:
    name = "synthesize"
    version = "1.0"
    requires = ["decompose", "observe", "infer", "allocate", "relate"]

    def can_run(self, ctx: PipelineContext) -> bool:
        return ctx.has("decompose")

    def output_path(self, ctx: PipelineContext) -> Path:
        return ctx.output_dir / "synthesize.yaml"

    def run(self, ctx: PipelineContext) -> StageResult[SynthesizeResult]:
        t0 = time.monotonic()
        diagnostics: list[Diagnostic] = []
        all_llm_calls: list[LLMCallRecord] = []

        decompose_result: DecomposeResult = ctx.get("decompose").output
        coordinator = ctx.config.get("coordinator")

        system_models: list[SystemModel] = []

        # Process full systems
        for boundary in decompose_result.systems:
            if not boundary.is_full_system:
                continue

            stages = _decide_stages(boundary)
            last_stage = stages[-1]

            if coordinator is not None:
                # Create scoped context
                sub_ctx = PipelineContext(
                    repo_path=ctx.repo_path,
                    output_dir=ctx.output_dir / _slugify(boundary.name),
                    scope=boundary.system_id,
                    scope_files=[Path(f) for f in boundary.files],
                    config=ctx.config,
                    domain=ctx.domain,
                )

                sub_results = coordinator.run_to(last_stage, sub_ctx)
                sub_llm_calls = list(sub_ctx.llm_calls)

                model_yaml = _build_system_model_yaml(boundary, sub_results)
                manifest_json = _build_manifest_json(sub_results)
                report_md = generate_pipeline_report(
                    sub_results,
                    system_name=boundary.name,
                    llm_calls=sub_llm_calls,
                )
                lesson_entries = _collect_lessons(sub_results, sub_llm_calls)
                lessons_md = generate_lessons(lesson_entries, system_name=boundary.name)

                sm = SystemModel(
                    system_id=boundary.system_id,
                    name=boundary.name,
                    model_yaml=model_yaml,
                    manifest_json=manifest_json,
                    pipeline_report_md=report_md,
                    lessons_md=lessons_md,
                    stage_results=sub_results,
                    llm_calls=sub_llm_calls,
                )
                all_llm_calls.extend(sub_llm_calls)
            else:
                # No coordinator — create minimal system model
                sm = SystemModel(
                    system_id=boundary.system_id,
                    name=boundary.name,
                )
                diagnostics.append(
                    Diagnostic(
                        severity="info",
                        code="NO_COORDINATOR",
                        message=f"No coordinator available; skipped scoped run for {boundary.name}",
                    )
                )

            system_models.append(sm)

        # Inline components — minimal models, no scoped run
        for boundary in decompose_result.inline_components:
            sm = SystemModel(
                system_id=boundary.system_id,
                name=boundary.name,
            )
            system_models.append(sm)

        # Build SoS model
        sos = _build_sos_model(
            system_models,
            decompose_result.inline_components,
            decompose_result,
            ctx.cache,
        )

        # Top-level reports
        top_report = generate_pipeline_report(
            ctx.cache,
            system_name="System-of-Systems",
            llm_calls=all_llm_calls,
        )
        top_lessons = generate_lessons(
            _collect_lessons(ctx.cache, all_llm_calls),
            system_name="System-of-Systems",
        )

        synth_result = SynthesizeResult(
            sos_model=sos,
            sos_model_yaml=sos.model_yaml,
            system_models=system_models,
            pipeline_report_md=top_report,
            lessons_md=top_lessons,
            all_llm_calls=all_llm_calls,
        )

        duration = int((time.monotonic() - t0) * 1000)
        quality = QualityMetrics(
            score=100.0 if system_models else 50.0,
            sub_scores={
                "system_count": float(len([s for s in system_models if s.model_yaml])),
                "sos_complete": 100.0 if sos.model_yaml else 0.0,
            },
        )

        return StageResult(
            output=synth_result,
            quality=quality,
            diagnostics=diagnostics,
            uncertainties=[],
            duration_ms=duration,
        )
