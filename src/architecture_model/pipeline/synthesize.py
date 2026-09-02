"""Synthesize stage — build per-system models and assemble System-of-Systems."""

from __future__ import annotations

import json
import hashlib
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from architecture_model.pipeline.cache import PipelineCache
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


def _capability_dict(
    cap: Any, existing: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Serialize inferred capability semantics without replacing richer existing fields."""
    result = dict(existing or {})
    result.setdefault("id", getattr(cap, "id", ""))
    result.setdefault("name", getattr(cap, "name", ""))
    result.setdefault("status", "ACTIVE")
    for field in ("description", "intent", "goals", "failure_modes", "monitored"):
        value = getattr(cap, field, None)
        if value and not result.get(field):
            result[field] = value
    return result


def _merge_capabilities(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge capabilities by ID, filling missing fields without overwriting rich data."""
    merged: dict[str, dict[str, Any]] = {}
    for capability in (item for group in groups for item in group):
        capability_id = capability.get("id", "")
        current = merged.setdefault(capability_id, {})
        for field, value in capability.items():
            if value and not current.get(field):
                current[field] = value
    return list(merged.values())


def _requirement_key(requirement: dict[str, Any]) -> str:
    source_file = str(requirement.get("source_file", ""))
    extensions = requirement.get("extensions", {})
    source_type = (
        extensions.get("source_type", "") if isinstance(extensions, dict) else ""
    )
    combined = (
        " ".join(str(requirement.get(field, "")) for field in ("name", "text"))
        + f" {source_type}"
    )
    constant = re.search(r"\b[A-Z][A-Z0-9_]{2,}\b", combined)
    if constant and ("constant" in source_type or "constraint" in combined.lower()):
        semantic = f"constant:{source_file}:{constant.group(0)}"
        return hashlib.sha256(semantic.encode("utf-8")).hexdigest()[:16]
    text = " ".join(
        str(requirement.get("text") or requirement.get("name", "")).lower().split()
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _requirement_dict(req: Any) -> dict[str, Any]:
    """Serialize a specify-stage requirement as a loadable Requirement entity."""
    source_file = str(getattr(req, "source_file", ""))
    moe = getattr(req, "moe", "")
    result: dict[str, Any] = {
        "id": getattr(req, "id", ""),
        "name": getattr(req, "name", ""),
        "status": getattr(req, "status", "ACTIVE") or "ACTIVE",
        "text": getattr(req, "text", ""),
        "rationale": getattr(req, "rationale", ""),
        "priority": getattr(req, "priority", "should") or "should",
        "source_file": source_file,
        "source_doc": source_file,
        "moe": moe,
        "moes": [moe] if moe else [],
        "value_function": getattr(req, "value_function", ""),
        "extensions": {"source_type": getattr(req, "source_type", "")},
    }
    result["content_hash"] = _requirement_key(result)
    return {key: value for key, value in result.items() if value not in ("", [], {})}


def _requirement_richness(requirement: dict[str, Any]) -> tuple[int, int]:
    """Score semantic completeness before using length as a stable tie-breaker."""
    semantic_fields = (
        "text",
        "rationale",
        "moe",
        "moes",
        "value_function",
        "source_file",
        "source_doc",
        "priority",
        "status",
    )
    populated = sum(bool(requirement.get(field)) for field in semantic_fields)
    return populated, sum(
        len(str(requirement.get(field, ""))) for field in semantic_fields
    )


def _merge_requirements(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate requirements semantically and retain the richest values."""
    merged: dict[str, dict[str, Any]] = {}
    for requirement in (item for group in groups for item in group):
        key = _requirement_key(requirement)
        candidate = dict(requirement)
        candidate["content_hash"] = key
        current = merged.get(key)
        if current is None:
            merged[key] = candidate
            continue
        richer, poorer = (
            (candidate, current)
            if _requirement_richness(candidate) > _requirement_richness(current)
            else (current, candidate)
        )
        result = dict(richer)
        for field, value in poorer.items():
            if field == "extensions" and isinstance(value, dict):
                extensions = result.setdefault("extensions", {})
                for ext_key, ext_value in value.items():
                    extensions.setdefault(ext_key, ext_value)
            elif value and not result.get(field):
                result[field] = value
        result["id"] = richer["id"]
        result["content_hash"] = key
        merged[key] = result
    used_ids: dict[str, str] = {}
    for key, requirement in merged.items():
        requirement_id = requirement.get("id") or f"REQ-{key.upper()}"
        if requirement_id in used_ids and used_ids[requirement_id] != key:
            requirement_id = f"{requirement_id}-{key[:8].upper()}"
        requirement["id"] = requirement_id
        used_ids[requirement_id] = key
    return list(merged.values())


def _decide_stages(boundary: SystemBoundary) -> list[str]:
    """Decide which pipeline stages to run based on system complexity."""
    if boundary.is_full_system:
        return list(FULL_PIPELINE_STAGES)
    return list(ABBREVIATED_STAGES)


def _slugify(name: str) -> str:
    """Convert name to filesystem-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _schema_id(entity_id: str) -> str:
    """Normalize generated IDs only when they violate the schema pattern."""
    if re.fullmatch(r"[A-Z]+-[A-Z]?-?\d+|[a-z][a-z0-9-]+", entity_id):
        return entity_id
    return _slugify(entity_id)


def _system_slugs(systems: list[SystemModel]) -> dict[str, str]:
    """Allocate stable unique filesystem slugs keyed by system ID."""
    bases: dict[str, list[SystemModel]] = {}
    for system in systems:
        bases.setdefault(_slugify(system.name) or "system", []).append(system)
    result: dict[str, str] = {}
    for base, colliding in bases.items():
        for system in colliding:
            suffix = hashlib.sha256(system.system_id.encode()).hexdigest()[:8]
            result[system.system_id] = (
                f"{base}-{suffix}" if len(colliding) > 1 else base
            )
    return result


def _build_system_model_yaml(
    boundary: SystemBoundary,
    results: dict[str, StageResult],
    project_name: str = "",
) -> str:
    """Build a YAML model string from scoped pipeline results."""
    components: list[dict[str, Any]] = []
    capabilities: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []

    id_remap: dict[str, str] = {}

    def _register_id(original_id: str) -> str:
        """Register and return one canonical subsystem ID mapping."""
        if not original_id:
            return original_id
        return id_remap.setdefault(original_id, _schema_id(original_id))

    # Extract from allocate results
    alloc_result = results.get("allocate")
    if alloc_result and alloc_result.output:
        output = alloc_result.output
        if hasattr(output, "components"):
            for comp in output.components:
                namespaced_id = _register_id(comp.id)
                comp_dict: dict[str, Any] = {
                    "id": namespaced_id, "name": comp.name, "status": "ACTIVE"
                }
                if hasattr(comp, "files") and comp.files:
                    comp_dict["files"] = [str(f) for f in comp.files]
                components.append(comp_dict)

    # Extract from infer results
    infer_result = results.get("infer")
    if infer_result and infer_result.output:
        output = infer_result.output
        if hasattr(output, "capabilities"):
            for cap in output.capabilities:
                cap_dict = _capability_dict(cap)
                cap_dict["id"] = _register_id(cap.id)
                capabilities.append(cap_dict)

    cap_ids = {c["id"] for c in capabilities}
    comp_ids = {c["id"] for c in components}
    file_set = set(boundary.files)

    # Extract behaviors from infer results (filter by capability_id)
    behaviors: list[dict[str, Any]] = []
    if infer_result and infer_result.output:
        output = infer_result.output
        if hasattr(output, "behaviors"):
            for beh in output.behaviors:
                capability_id = (
                    _register_id(beh.capability_id) if beh.capability_id else ""
                )
                if capability_id and capability_id not in cap_ids:
                    continue
                beh_dict: dict[str, Any] = {
                    "id": _register_id(beh.id),
                    "name": beh.name,
                    "status": "ACTIVE",
                }
                if beh.behavior_type:
                    beh_dict["behavior_type"] = beh.behavior_type
                for field in (
                    "description", "intent", "trigger", "preconditions",
                    "postconditions", "frequency", "pattern", "steps", "source_file",
                ):
                    value = getattr(beh, field, None)
                    if value:
                        beh_dict[field] = value
                if beh.actor_id:
                    beh_dict["actor_id"] = _register_id(beh.actor_id)
                if capability_id:
                    beh_dict["capability_id"] = capability_id
                if beh.triggers:
                    beh_dict["triggers"] = beh.triggers
                existing_structured = getattr(beh, "structured_steps", None)
                if existing_structured:
                    beh_dict["structured_steps"] = existing_structured
                behaviors.append(beh_dict)

    # Extract actors from infer results (all are system-wide)
    actors: list[dict[str, Any]] = []
    if infer_result and infer_result.output:
        output = infer_result.output
        if hasattr(output, "actors"):
            for actor in output.actors:
                actor_dict: dict[str, Any] = {
                    "id": _register_id(actor.id),
                    "name": actor.name,
                    "status": "ACTIVE",
                }
                if actor.actor_type:
                    actor_dict["actor_type"] = actor.actor_type
                if actor.evidence_source:
                    actor_dict["evidence_source"] = actor.evidence_source
                actors.append(actor_dict)

    # Extract interfaces from specify results (filter by component_id)
    interfaces: list[dict[str, Any]] = []
    specify_result = results.get("specify")
    if specify_result and specify_result.output:
        output = specify_result.output
        if hasattr(output, "interfaces"):
            for iface in output.interfaces:
                namespaced_comp_id = _register_id(iface.component_id)
                if namespaced_comp_id not in comp_ids:
                    continue
                iface_dict: dict[str, Any] = {
                    "id": _register_id(iface.id),
                    "name": iface.name,
                    "status": "ACTIVE",
                    "interface_type": iface.interface_type,
                    "component_id": namespaced_comp_id,
                }
                if iface.methods:
                    iface_dict["methods"] = iface.methods
                if iface.description:
                    iface_dict["description"] = iface.description
                interfaces.append(iface_dict)

    requirements: list[dict[str, Any]] = []
    if (
        specify_result
        and specify_result.output
        and hasattr(specify_result.output, "requirements")
    ):
        requirements = _merge_requirements(
            [_requirement_dict(req) for req in specify_result.output.requirements]
        )
        requirement_source_by_key = {
            _requirement_key(_requirement_dict(req)): req.source_file
            for req in specify_result.output.requirements
        }
        for requirement in requirements:
            requirement["id"] = _register_id(requirement["id"])
        file_to_comp = {
            str(source): _register_id(comp.id)
            for comp in getattr(getattr(alloc_result, "output", None), "components", [])
            for source in comp.files
        }
        for requirement in requirements:
            component_id = file_to_comp.get(
                str(requirement_source_by_key.get(requirement["content_hash"], ""))
            )
            if component_id and component_id in comp_ids:
                relationships.append(
                    {"from": component_id, "to": requirement["id"], "type": "satisfies"}
                )

    # Extract constraints from observe results (filter by source file)
    constraints: list[dict[str, Any]] = []
    observe_result = results.get("observe")
    if observe_result and observe_result.output:
        output = observe_result.output
        if hasattr(output, "constraints"):
            for i, con in enumerate(output.constraints):
                if con.source not in file_set:
                    continue
                con_dict: dict[str, Any] = {
                    "id": _register_id(f"CON-{i + 1}"),
                    "name": con.name,
                    "status": "ACTIVE",
                    "value": con.value,
                    "source": con.source,
                }
                if con.constraint_type:
                    con_dict["constraint_type"] = con.constraint_type
                constraints.append(con_dict)

    # Derive layers from unique layer values on components
    layers: list[dict[str, Any]] = []
    seen_layers: set[str] = set()
    if (
        alloc_result
        and alloc_result.output
        and hasattr(alloc_result.output, "components")
    ):
        for comp in alloc_result.output.components:
            layer = getattr(comp, "layer", "")
            if layer and layer not in seen_layers:
                seen_layers.add(layer)
                original_layer_id = f"LAYER-{layer.upper()}"
                layers.append({
                    "id": _register_id(original_layer_id), "name": layer, "status": "ACTIVE"
                })

    # Extract from relate results
    relate_result = results.get("relate")
    if relate_result and relate_result.output:
        output = relate_result.output
        if hasattr(output, "relationships"):
            for rel in output.relationships:
                from_id = id_remap.get(rel.from_id)
                to_id = id_remap.get(rel.to_id)
                if not from_id or not to_id:
                    continue
                relationships.append(
                    {
                        "from": from_id,
                        "to": to_id,
                        "type": rel.rel_type,
                    }
                )

    file_to_comp = {
        str(source): _register_id(comp.id)
        for comp in getattr(getattr(alloc_result, "output", None), "components", [])
        for source in comp.files
    }
    relationship_keys = {
        (rel["from"], rel["to"], rel["type"]) for rel in relationships
    }
    for behavior in behaviors:
        component_id = file_to_comp.get(str(behavior.get("source_file", "")))
        capability_id = behavior.get("capability_id", "")
        if component_id and behavior.get("steps") and not behavior.get("structured_steps"):
            behavior["structured_steps"] = [
                {"order": order, "action": action, "component_ref": component_id}
                for order, action in enumerate(behavior["steps"], 1)
            ]
        for target_id, rel_type in (
            (capability_id, "realizes"), (behavior["id"], "traces-to")
        ):
            key = (component_id, target_id, rel_type)
            if component_id and target_id and key not in relationship_keys:
                relationships.append({"from": component_id, "to": target_id, "type": rel_type})
                relationship_keys.add(key)

    model_dict: dict[str, Any] = {
        "meta": {
            "project": project_name or boundary.name,
            "schema_version": "2.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "system": boundary.name,
            "system_id": boundary.system_id,
            "parent_model": "../../.architecture-model.yaml",
            "refines_component": boundary.system_id,
            "source_artifacts": list(boundary.files),
        },
        "entities": {},
        "relationships": relationships,
    }
    if components:
        model_dict["entities"]["components"] = components
    if capabilities:
        model_dict["entities"]["capabilities"] = capabilities
    if behaviors:
        model_dict["entities"]["behaviors"] = behaviors
    if actors:
        model_dict["entities"]["actors"] = actors
    if interfaces:
        model_dict["entities"]["interfaces"] = interfaces
    if constraints:
        model_dict["entities"]["constraints"] = constraints
    if requirements:
        model_dict["entities"]["requirements"] = requirements
    if layers:
        model_dict["entities"]["layers"] = layers

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
            mod_dict: dict[str, Any] = {"file": str(mod.path)}
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
    project_name: str = "",
) -> SoSModel:
    """Assemble the System-of-Systems model."""
    # Actors remain top-level external context. Internal inferred entities stay
    # in their self-contained subsystem models.
    actors: list[dict[str, Any]] = []
    capabilities: list[dict[str, Any]] = []
    behaviors: list[dict[str, Any]] = []

    infer_result = top_results.get("infer")
    if infer_result and infer_result.output:
        output = infer_result.output
        if hasattr(output, "actors"):
            for actor in output.actors:
                actors.append(
                    {
                        "id": _schema_id(getattr(actor, "id", "")),
                        "name": getattr(actor, "name", ""),
                        "status": "ACTIVE",
                    }
                )

    # Inter-system interfaces from decompose edges
    inter_system_interfaces: list[dict[str, Any]] = []
    for from_sys, to_sys, rel_type in decompose.inter_system_edges:
        inter_system_interfaces.append(
            {"from": _schema_id(from_sys), "to": _schema_id(to_sys), "type": rel_type}
        )

    # Build SoS YAML
    slugs = _system_slugs([system for system in systems if system.model_yaml])
    source_artifacts = [
        f".architecture-models/{slugs[system.system_id]}/.architecture-model.yaml"
        for system in systems if system.model_yaml
    ] + [str(path) for boundary in inlines for path in boundary.files]
    sos_dict: dict[str, Any] = {
        "meta": {
            "project": project_name or "System-of-Systems",
            "schema_version": "2.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "system_of_systems": True,
            "source_artifacts": source_artifacts,
        },
        "entities": {
            "systems": [
                {
                    "id": _schema_id(s.system_id),
                    "name": s.name,
                    "status": "ACTIVE",
                    "sub_model_ref": f".architecture-models/{slugs[s.system_id]}/.architecture-model.yaml",
                }
                for s in systems if s.model_yaml
            ],
        },
        "relationships": inter_system_interfaces,
    }
    if actors:
        sos_dict["entities"]["actors"] = actors
    if capabilities:
        sos_dict["entities"]["capabilities"] = capabilities
    if behaviors:
        sos_dict["entities"]["behaviors"] = behaviors
    # Add inline components
    if inlines:
        sos_dict["entities"]["components"] = [
            {"id": _schema_id(i.system_id), "name": i.name, "status": "ACTIVE", "files": i.files}
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


def _collect_lessons(
    results: dict[str, StageResult], llm_calls: list[LLMCallRecord]
) -> list[LessonEntry]:
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
        full_boundaries = [boundary for boundary in decompose_result.systems if boundary.is_full_system]
        boundary_slugs = _system_slugs([
            SystemModel(system_id=boundary.system_id, name=boundary.name, model_yaml="pending")
            for boundary in full_boundaries
        ])

        # Process full systems
        for boundary in full_boundaries:

            stages = _decide_stages(boundary)
            last_stage = stages[-1]

            # Check for pre-existing scoped cache (from agent's enriched MCP runs)
            slug = boundary_slugs[boundary.system_id]
            scoped_cache_dir = ctx.output_dir.parent / slug
            scoped_cache = PipelineCache(scoped_cache_dir)
            if scoped_cache.exists():
                # Use pre-existing enriched results from agent's scoped pipeline run
                sub_results = scoped_cache.load_all()
                sub_llm_calls = scoped_cache.load_llm_calls()

                model_yaml = _build_system_model_yaml(boundary, sub_results, ctx.repo_path.name)
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
                diagnostics.append(
                    Diagnostic(
                        severity="info",
                        code="SCOPED_CACHE_USED",
                        message=f"Used pre-existing scoped cache for {boundary.name}",
                    )
                )
            elif coordinator is not None:
                # Create scoped context and run deterministically
                sub_ctx = PipelineContext(
                    repo_path=ctx.repo_path,
                    output_dir=ctx.output_dir / slug,
                    scope=boundary.system_id,
                    scope_files=[Path(f) for f in boundary.files],
                    config=ctx.config,
                    domain=ctx.domain,
                    invocation_source=ctx.invocation_source,
                    invocation="synthesize",
                    parent_run_id=ctx.run_id or None,
                )

                sub_results = coordinator.run_to(last_stage, sub_ctx)
                sub_llm_calls = list(sub_ctx.llm_calls)

                model_yaml = _build_system_model_yaml(boundary, sub_results, ctx.repo_path.name)
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
                # No coordinator and no cached results — create minimal system model
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

        # Build SoS model
        sos = _build_sos_model(
            system_models,
            decompose_result.inline_components,
            decompose_result,
            ctx.cache,
            project_name=ctx.repo_path.name,
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

        # Per-subsystem quality from decompose
        decompose_result = ctx.get("decompose")
        subsys_quality: dict[str, QualityMetrics] = {}
        if decompose_result:
            subsys_quality = dict(decompose_result.quality.component_scores)

        duration = int((time.monotonic() - t0) * 1000)
        quality = QualityMetrics(
            score=100.0 if system_models else 50.0,
            sub_scores={
                "system_count": float(len([s for s in system_models if s.model_yaml])),
                "sos_complete": 100.0 if sos.model_yaml else 0.0,
            },
            component_scores=subsys_quality,
        )

        return StageResult(
            output=synth_result,
            quality=quality,
            diagnostics=diagnostics,
            uncertainties=[],
            duration_ms=duration,
            summary=f"Ran {len(system_models)} sub-pipelines and produced system-of-systems model.",
        )
