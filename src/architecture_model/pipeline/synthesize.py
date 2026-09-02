"""Synthesize stage — build per-system models and assemble System-of-Systems."""

from __future__ import annotations

import json
import hashlib
import re
import time
from copy import deepcopy
from dataclasses import asdict, dataclass, is_dataclass
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
    for field in (
        "description", "intent", "goals", "requirements", "rationale", "moes",
        "value_function", "failure_modes", "trade_offs", "interface_refs", "monitored",
    ):
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
    reserved = set(bases)
    used: set[str] = set()
    result: dict[str, str] = {}
    for base in sorted(bases):
        colliding = sorted(bases[base], key=lambda system: system.system_id)
        for system in colliding:
            candidate = base
            if len(colliding) > 1 or candidate in used:
                digest = hashlib.sha256(system.system_id.encode()).hexdigest()
                length = 8
                candidate = f"{base}-{digest[:length]}"
                while candidate in reserved or candidate in used:
                    length += 2
                    candidate = f"{base}-{digest[:length]}"
            result[system.system_id] = candidate
            used.add(candidate)
    return result


def _normalized_path(path: Any) -> str:
    """Normalize evidence paths for stable boundary comparisons."""
    return Path(str(path)).as_posix().lstrip("./")


def _paths_match(first: Any, second: Any) -> bool:
    """Match normalized paths across absolute and repository-relative forms."""
    left = _normalized_path(first)
    right = _normalized_path(second)
    return left == right or left.endswith(f"/{right}") or right.endswith(f"/{left}")


class _EntityIdAllocator:
    """Allocate deterministic schema-valid IDs in one global namespace."""

    def __init__(self, initial: set[str] | None = None) -> None:
        self.used = set(initial or ())
        self.assigned: dict[tuple[str, str], str] = {}

    def allocate(self, original_id: str, namespace: str = "", prefix: str = "") -> str:
        if not original_id:
            return original_id
        key = (namespace, original_id)
        if key in self.assigned:
            return self.assigned[key]
        candidate = _schema_id(original_id)
        if candidate in self.used:
            entity_prefix = prefix or original_id.split("-", 1)[0]
            entity_prefix = re.sub(r"[^A-Z]", "", entity_prefix.upper()) or "ID"
            digest = int.from_bytes(
                hashlib.sha256(f"{namespace}:{original_id}".encode()).digest()[:8], "big"
            )
            candidate = f"{entity_prefix}-{digest}"
            counter = 1
            while candidate in self.used:
                candidate = f"{entity_prefix}-{digest}{counter}"
                counter += 1
        self.used.add(candidate)
        self.assigned[key] = candidate
        return candidate


@dataclass(frozen=True)
class FileOwnership:
    """Canonical file ownership for one synthesis run.

    Component ties use stable component ID. Boundary ties prefer explicit
    component membership, then full systems, smaller boundaries, and stable ID.
    """

    component_by_file: dict[str, str]
    boundary_by_file: dict[str, str]


def _build_file_ownership(
    components: list[Any], boundaries: list[SystemBoundary],
) -> FileOwnership:
    component_by_file: dict[str, str] = {}
    for component in sorted(components, key=lambda item: item.id):
        for path in component.files:
            component_by_file.setdefault(_normalized_path(path), component.id)
    candidates: dict[str, list[SystemBoundary]] = {}
    for boundary in boundaries:
        for path in boundary.files:
            candidates.setdefault(_normalized_path(path), []).append(boundary)
    boundary_by_file = {}
    for path, options in candidates.items():
        component_id = component_by_file.get(path, "")
        boundary_by_file[path] = min(
            options,
            key=lambda boundary: (
                0 if component_id and component_id in boundary.component_ids else 1,
                0 if boundary.is_full_system else 1,
                len({_normalized_path(item) for item in boundary.files}),
                boundary.system_id,
            ),
        ).system_id
    return FileOwnership(component_by_file, boundary_by_file)


def _interface_type(value: str) -> str:
    """Map extraction interface categories to canonical schema values."""
    return {
        "rest": "REST",
        "websocket": "WebSocket",
        "event": "message-queue",
        "cli": "internal",
        "grpc": "internal",
        "library": "internal",
    }.get(value.lower(), value)


def _evidence_files(metadata: dict[str, Any]) -> set[str]:
    """Collect every file selector supported by structured resolutions."""
    files: set[str] = set()
    for field in ("source_files", "files_sent"):
        value = metadata.get(field, [])
        if isinstance(value, (str, Path)):
            value = [value]
        files.update(_normalized_path(path) for path in value)
    allocations = metadata.get("file_allocations", {})
    if isinstance(allocations, dict):
        for values in allocations.values():
            if isinstance(values, (str, Path)):
                values = [values]
            files.update(_normalized_path(path) for path in values)
    elif isinstance(allocations, list):
        for allocation in allocations:
            if isinstance(allocation, dict):
                values = allocation.get("files")
                if values is None:
                    values = [allocation.get("file") or allocation.get("source_file")]
                if isinstance(values, (str, Path)):
                    values = [values]
                files.update(_normalized_path(path) for path in values if path)
            elif allocation:
                files.add(_normalized_path(allocation))
    return files


def _scoped_evidence(
    ctx: PipelineContext, boundary: SystemBoundary, ownership: FileOwnership | None = None,
) -> tuple[list[Any], list[LLMCallRecord]]:
    """Select boundary-local corrections and their exact LLM provenance."""
    boundary_files = {
        _normalized_path(path) for path in boundary.files
        if ownership is None
        or ownership.boundary_by_file.get(_normalized_path(path), boundary.system_id)
        == boundary.system_id
    }
    calls_by_resolution: dict[str, list[LLMCallRecord]] = {}
    for call in ctx.llm_calls:
        if call.resolution_id:
            calls_by_resolution.setdefault(call.resolution_id, []).append(call)

    def _matches(evidence: Any) -> bool:
        if evidence.metadata.get("shared") is True or evidence.metadata.get("project_wide") is True:
            return True
        files = _evidence_files(evidence.metadata)
        resolution_id = str(evidence.metadata.get("resolution_id", ""))
        calls = calls_by_resolution.get(resolution_id, [])
        if len(calls) == 1:
            files.update(_normalized_path(path) for path in calls[0].files_sent)
        return bool(files & boundary_files)

    corrections = []
    for evidence in ctx.prior_corrections:
        if not _matches(evidence):
            continue
        scoped = deepcopy(evidence)
        allocations = scoped.metadata.get("file_allocations")
        if isinstance(allocations, dict):
            scoped.metadata["file_allocations"] = {
                target: [
                    str(path) for path in (values if isinstance(values, list) else [values])
                    if _normalized_path(path) in boundary_files
                ]
                for target, values in allocations.items()
            }
            scoped.metadata["file_allocations"] = {
                target: values
                for target, values in scoped.metadata["file_allocations"].items()
                if values
            }
        elif isinstance(allocations, list) and allocations and isinstance(allocations[0], dict):
            groups = []
            for allocation in allocations:
                values = allocation.get("files", [])
                values = values if isinstance(values, list) else [values]
                scoped_values = [
                    str(path) for path in values
                    if _normalized_path(path) in boundary_files
                ]
                if scoped_values:
                    group = deepcopy(allocation)
                    group["files"] = scoped_values
                    groups.append(group)
            scoped.metadata["file_allocations"] = groups
        for field in ("source_files", "files_sent"):
            if field in scoped.metadata:
                values = scoped.metadata[field]
                values = values if isinstance(values, list) else [values]
                scoped.metadata[field] = [
                    str(path) for path in values
                    if _normalized_path(path) in boundary_files
                ]
        corrections.append(scoped)
    resolution_ids = {
        str(evidence.metadata.get("resolution_id"))
        for evidence in corrections
        if evidence.metadata.get("resolution_id")
    }
    calls = [
        resolution_calls[0]
        for resolution_id in resolution_ids
        if len(resolution_calls := calls_by_resolution.get(resolution_id, [])) == 1
    ]
    return corrections, calls


def _build_system_model_yaml(
    boundary: SystemBoundary,
    results: dict[str, StageResult],
    project_name: str = "",
    ownership: FileOwnership | None = None,
) -> str:
    """Build a YAML model string from scoped pipeline results."""
    components: list[dict[str, Any]] = []
    capabilities: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []

    id_remap: dict[str, str] = {}
    selected_component_ids: set[str] = set()
    allocator = _EntityIdAllocator()

    def _register_id(original_id: str, prefix: str = "") -> str:
        """Register and return one canonical subsystem ID mapping."""
        if not original_id:
            return original_id
        if original_id in id_remap:
            return id_remap[original_id]
        candidate = allocator.allocate(original_id, prefix=prefix)
        id_remap[original_id] = candidate
        return candidate

    file_set = {_normalized_path(path) for path in boundary.files}

    # Extract from allocate results
    alloc_result = results.get("allocate")
    allocation_components = list(
        getattr(getattr(alloc_result, "output", None), "components", [])
    )
    if ownership is None:
        ownership = _build_file_ownership(allocation_components, [boundary])
    file_owner = ownership.component_by_file
    local_component_ids = {component.id for component in allocation_components}
    if alloc_result and alloc_result.output:
        output = alloc_result.output
        if hasattr(output, "components"):
            for comp in sorted(
                output.components,
                key=lambda item: (item.id, item.name, tuple(sorted(map(str, item.files)))),
            ):
                comp_files = {
                    _normalized_path(path)
                    for path in getattr(comp, "files", [])
                    if (
                        file_owner.get(_normalized_path(path)) == comp.id
                        or file_owner.get(_normalized_path(path)) not in local_component_ids
                    )
                    and (
                        ownership.boundary_by_file.get(
                            _normalized_path(path), boundary.system_id
                        ) == boundary.system_id
                        or (_is_shared(comp) and boundary.system_id == "shared")
                    )
                }
                if file_set and not comp_files.intersection(file_set):
                    continue
                namespaced_id = _register_id(comp.id, "COMP")
                selected_component_ids.add(comp.id)
                comp_dict: dict[str, Any] = {
                    "id": namespaced_id, "name": comp.name, "status": "ACTIVE"
                }
                if hasattr(comp, "files") and comp.files:
                    comp_dict["files"] = [
                        str(path) for path in comp.files
                        if (
                            file_owner.get(_normalized_path(path)) == comp.id
                            or file_owner.get(_normalized_path(path)) not in local_component_ids
                        )
                        and (
                            ownership.boundary_by_file.get(
                                _normalized_path(path), boundary.system_id
                            ) == boundary.system_id
                            or (_is_shared(comp) and boundary.system_id == "shared")
                        )
                        and (not file_set or _normalized_path(path) in file_set)
                    ]
                typed_interfaces = getattr(comp, "interfaces", None)
                if typed_interfaces:
                    comp_dict["interfaces"] = [
                        asdict(item) if is_dataclass(item) else dict(item)
                        for item in typed_interfaces
                    ]
                components.append(comp_dict)
    for component in components:
        for interface in component.get("interfaces", []):
            target = interface.get("target_component", "")
            if target:
                interface["target_component"] = _register_id(target)

    comp_ids = {c["id"] for c in components}
    raw_relationships = getattr(
        getattr(results.get("relate"), "output", None), "relationships", []
    )
    realized_cap_ids = {
        rel.to_id for rel in raw_relationships
        if rel.from_id in selected_component_ids and rel.rel_type == "realizes"
    }

    # Extract from infer results
    infer_result = results.get("infer")
    selected_capability_ids: set[str] = set()
    capability_inputs: dict[str, Any] = {}
    inferred_actors = sorted(
        getattr(getattr(infer_result, "output", None), "actors", []),
        key=lambda item: (item.id, item.name),
    )
    for actor in inferred_actors:
        _register_id(actor.id, "ACT")
    if infer_result and infer_result.output:
        output = infer_result.output
        if hasattr(output, "capabilities"):
            for cap in sorted(output.capabilities, key=lambda item: (item.id, item.name)):
                cap_sources = {
                    _normalized_path(path) for path in getattr(cap, "source_files", [])
                }
                realized_by_selected = cap.id in realized_cap_ids
                selected_owned_files = {
                    path for component in components for path in component.get("files", [])
                }
                if file_set and not any(
                    _paths_match(source, scoped) for source in cap_sources for scoped in file_set
                ) and not (
                    realized_by_selected
                    and not cap_sources
                    and selected_owned_files
                    and selected_owned_files.issubset(file_set)
                ):
                    continue
                cap_dict = _capability_dict(cap)
                selected_capability_ids.add(cap.id)
                cap_dict["id"] = _register_id(cap.id, "CAP")
                capability_inputs[cap_dict["id"]] = cap
                capabilities.append(cap_dict)

    cap_ids = {c["id"] for c in capabilities}

    # Extract behaviors from infer results (filter by capability_id)
    behaviors: list[dict[str, Any]] = []
    if infer_result and infer_result.output:
        output = infer_result.output
        if hasattr(output, "behaviors"):
            for beh in sorted(output.behaviors, key=lambda item: (item.id, item.name)):
                source_file = _normalized_path(getattr(beh, "source_file", ""))
                if (
                    file_set
                    and (
                        (source_file and not any(_paths_match(source_file, path) for path in file_set))
                        or (
                            not source_file
                            and beh.capability_id not in selected_capability_ids
                            and not boundary.is_full_system
                        )
                    )
                ):
                    continue
                capability_id = (
                    _register_id(beh.capability_id) if beh.capability_id else ""
                )
                if capability_id and capability_id not in cap_ids:
                    continue
                beh_dict: dict[str, Any] = {
                    "id": _register_id(beh.id, "BEH"),
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
                        beh_dict[field] = str(value) if field == "source_file" else value
                if beh.actor_id:
                    beh_dict["actor_id"] = _register_id(beh.actor_id)
                if capability_id:
                    beh_dict["capability_id"] = capability_id
                if beh.triggers:
                    beh_dict["triggers"] = beh.triggers
                existing_structured = getattr(beh, "structured_steps", None)
                if existing_structured:
                    beh_dict["structured_steps"] = [
                        {
                            **(asdict(step) if is_dataclass(step) else dict(step)),
                            "component_ref": _register_id(
                                getattr(step, "component_ref", "")
                                if is_dataclass(step)
                                else step.get("component_ref", "")
                            ),
                        }
                        for step in existing_structured
                    ]
                behaviors.append(beh_dict)

    # Extract actors from infer results (all are system-wide)
    actors: list[dict[str, Any]] = []
    if infer_result and infer_result.output:
        output = infer_result.output
        if hasattr(output, "actors"):
            for actor in inferred_actors:
                actor_dict: dict[str, Any] = {
                    "id": _register_id(actor.id, "ACT"),
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
            for iface in sorted(output.interfaces, key=lambda item: (item.id, item.name)):
                if iface.component_id not in selected_component_ids:
                    continue
                namespaced_comp_id = _register_id(iface.component_id)
                if namespaced_comp_id not in comp_ids:
                    continue
                iface_dict: dict[str, Any] = {
                    "id": _register_id(iface.id, "IF"),
                    "name": iface.name,
                    "status": "ACTIVE",
                    "type": _interface_type(iface.interface_type),
                    "provider": namespaced_comp_id,
                }
                if iface.methods:
                    iface_dict["methods"] = iface.methods
                if iface.description:
                    iface_dict["description"] = iface.description
                interfaces.append(iface_dict)
                relationships.append(
                    {"from": namespaced_comp_id, "to": iface_dict["id"], "type": "exposes"}
                )

    requirements: list[dict[str, Any]] = []
    if (
        specify_result
        and specify_result.output
        and hasattr(specify_result.output, "requirements")
    ):
        direct_requirement_ids = {
            rel.to_id for rel in raw_relationships
            if rel.rel_type == "satisfies"
            and rel.from_id in selected_component_ids | selected_capability_ids
        }
        direct_requirement_ids.update(
            rel.to_id for rel in raw_relationships
            if rel.rel_type == "satisfies"
            and rel.from_id in {
                getattr(behavior, "id", "")
                for behavior in getattr(getattr(infer_result, "output", None), "behaviors", [])
                if _normalized_path(getattr(behavior, "source_file", "")) in file_set
            }
        )
        scoped_requirements = sorted([
            req for req in specify_result.output.requirements
            if not file_set
            or _normalized_path(req.source_file) in file_set
            or req.id in direct_requirement_ids
        ], key=lambda item: (item.id, item.name, str(item.source_file)))
        requirements = _merge_requirements([_requirement_dict(req) for req in scoped_requirements])
        requirement_source_by_key = {
            _requirement_key(_requirement_dict(req)): req.source_file
            for req in scoped_requirements
        }
        for requirement in requirements:
            requirement["id"] = _register_id(requirement["id"], "REQ")
        file_to_comp = {
            _normalized_path(path): component["id"]
            for component in components for path in component.get("files", [])
        }
        for requirement in requirements:
            component_id = file_to_comp.get(
                _normalized_path(requirement_source_by_key.get(requirement["content_hash"], ""))
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
                if file_set and _normalized_path(con.source) not in file_set:
                    continue
                con_dict: dict[str, Any] = {
                    "id": _register_id(f"CON-{i + 1}", "CON"),
                    "name": con.name,
                    "status": "ACTIVE",
                    "value": con.value,
                    "source": con.source,
                }
                if con.constraint_type:
                    con_dict["constraint_type"] = con.constraint_type
                constraints.append(con_dict)
                component_id = next(
                    (
                        comp["id"] for comp in components
                        if _normalized_path(con.source)
                        in {_normalized_path(path) for path in comp.get("files", [])}
                    ),
                    "",
                )
                if component_id:
                    relationships.append(
                        {"from": component_id, "to": con_dict["id"], "type": "constrained-by"}
                    )

    # Derive layers from unique layer values on components
    layers: list[dict[str, Any]] = []
    seen_layers: set[str] = set()
    if (
        alloc_result
        and alloc_result.output
        and hasattr(alloc_result.output, "components")
    ):
        for comp in alloc_result.output.components:
            if comp.id not in selected_component_ids:
                continue
            layer = getattr(comp, "layer", "")
            if layer and layer not in seen_layers:
                seen_layers.add(layer)
                original_layer_id = f"LAYER-{layer.upper()}"
                layers.append({
                    "id": _register_id(original_layer_id, "LAY"), "name": layer, "status": "ACTIVE"
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

    component_files = [
        (path, component["id"])
        for component in components for path in component.get("files", [])
    ]
    relationship_keys = {
        (rel["from"], rel["to"], rel["type"]) for rel in relationships
    }
    for behavior in behaviors:
        component_id = next((
            component_id for path, component_id in component_files
            if _paths_match(path, behavior.get("source_file", ""))
        ), "")
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

    capabilities_by_id = {capability["id"]: capability for capability in capabilities}
    requirements_by_file: dict[str, list[str]] = {}
    requirements_by_id = {requirement["id"]: requirement for requirement in requirements}
    for requirement in requirements:
        requirements_by_file.setdefault(
            _normalized_path(requirement.get("source_file", "")), []
        ).append(requirement["id"])
    interfaces_by_component: dict[str, list[str]] = {}
    for interface in interfaces:
        interfaces_by_component.setdefault(interface["provider"], []).append(interface["id"])
    realized_by_component: dict[str, list[dict[str, Any]]] = {}
    for relationship in relationships:
        if relationship["type"] == "realizes" and relationship["to"] in capabilities_by_id:
            realized_by_component.setdefault(relationship["from"], []).append(
                capabilities_by_id[relationship["to"]]
            )

    def _unique(values: list[Any]) -> list[Any]:
        return list(dict.fromkeys(value for value in values if value))

    for component in components:
        realized = realized_by_component.get(component["id"], [])
        owned_files = [_normalized_path(path) for path in component.get("files", [])]
        requirement_ids = _unique(
            [
                relationship["to"] for relationship in relationships
                if relationship["from"] == component["id"]
                and relationship["type"] == "satisfies"
                and relationship["to"] in requirements_by_id
            ]
            + [
                requirement_id
                for path in owned_files for requirement_id in requirements_by_file.get(path, [])
            ]
        )
        interface_ids = interfaces_by_component.get(component["id"], [])
        if realized:
            owned_file_set = {_normalized_path(path) for path in component.get("files", [])}
            primary = min(
                realized,
                key=lambda capability: (
                    -len(
                        owned_file_set
                        & {
                            _normalized_path(path)
                            for path in getattr(
                                capability_inputs.get(capability["id"]), "source_files", []
                            )
                        }
                    ),
                    -float(getattr(capability_inputs.get(capability["id"]), "confidence", 0.0)),
                    capability["id"],
                ),
            )
            if primary.get("intent"):
                component["intent"] = primary["intent"]
            for field in ("goals", "failure_modes", "monitored", "moes", "trade_offs"):
                values = _unique([
                    value for capability in realized for value in capability.get(field, [])
                ])
                if values:
                    component[field] = values
            other_intents = _unique([
                capability.get("intent")
                for capability in realized
                if capability is not primary
            ])
            if other_intents:
                component["goals"] = _unique(component.get("goals", []) + other_intents)
            value_functions = _unique([
                capability.get("value_function") for capability in realized
            ])
            if value_functions:
                component["value_function"] = value_functions[0]
            component["responsibilities"] = _unique(
                [capability["name"] for capability in realized]
                + [goal for capability in realized for goal in capability.get("goals", [])]
            )
            component.setdefault("extensions", {})["x-semantic-derivation"] = {
                "method": "realized_capabilities",
                "capabilities": [capability["id"] for capability in realized],
                "primary_capability": primary["id"],
            }
        if requirement_ids:
            component["requirements"] = requirement_ids
            requirement_sources = [requirements_by_id[item] for item in requirement_ids]
            if not component.get("rationale"):
                rationales = _unique([item.get("rationale") for item in requirement_sources])
                if rationales:
                    component["rationale"] = "; ".join(rationales)
            if not component.get("moes"):
                moes = _unique([
                    moe for item in requirement_sources
                    for moe in item.get("moes", []) or [item.get("moe")]
                ])
                if moes:
                    component["moes"] = moes
            if not component.get("value_function"):
                value_functions = _unique([
                    item.get("value_function") for item in requirement_sources
                ])
                if value_functions:
                    component["value_function"] = value_functions[0]
            component.setdefault("extensions", {}).setdefault(
                "x-semantic-derivation", {"method": "source_ownership"}
            )["requirements"] = requirement_ids
        if interface_ids:
            component["interface_refs"] = interface_ids

    direct_refs: dict[str, dict[str, list[str]]] = {}
    for relationship in relationships:
        if relationship["to"] in requirements_by_id:
            direct_refs.setdefault(relationship["from"], {}).setdefault("requirements", []).append(
                relationship["to"]
            )
        if relationship["to"] in {interface["id"] for interface in interfaces}:
            direct_refs.setdefault(relationship["from"], {}).setdefault("interface_refs", []).append(
                relationship["to"]
            )

    for capability in capabilities:
        raw_capability = capability_inputs.get(capability["id"])
        source_files = {
            _normalized_path(path) for path in getattr(raw_capability, "source_files", [])
        }
        requirement_ids = _unique(
            direct_refs.get(capability["id"], {}).get("requirements", [])
            + [
                requirement_id for path in source_files
                for requirement_id in requirements_by_file.get(path, [])
            ]
        )
        interface_ids = _unique(
            direct_refs.get(capability["id"], {}).get("interface_refs", [])
        )
        if requirement_ids:
            capability["requirements"] = _unique(capability.get("requirements", []) + requirement_ids)
        if interface_ids:
            capability["interface_refs"] = _unique(capability.get("interface_refs", []) + interface_ids)

    for behavior in behaviors:
        source_file = _normalized_path(behavior.get("source_file", ""))
        requirement_ids = _unique(
            direct_refs.get(behavior["id"], {}).get("requirements", [])
            + requirements_by_file.get(source_file, [])
        )
        interface_ids = _unique(direct_refs.get(behavior["id"], {}).get("interface_refs", []))
        if requirement_ids:
            behavior["requirements"] = requirement_ids
        if interface_ids:
            behavior["interface_refs"] = interface_ids

    local_ids = {
        entity["id"]
        for group in (
            components, capabilities, behaviors, actors, interfaces,
            constraints, requirements, layers,
        )
        for entity in group
    }
    relationships = [
        relationship for relationship in relationships
        if relationship["from"] in local_ids and relationship["to"] in local_ids
    ]

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


def _rewrite_inline_refs(value: Any, id_remap: dict[str, str]) -> Any:
    """Rewrite entity references throughout an inline projection."""
    if isinstance(value, list):
        return [_rewrite_inline_refs(item, id_remap) for item in value]
    if not isinstance(value, dict):
        return value
    reference_fields = {
        "from", "to", "component_ref", "component_id", "provider", "consumer",
        "actor_id", "capability_id", "parent_id", "target_component",
    }
    list_reference_fields = {
        "requirements", "interface_refs", "component_ids", "children", "triggers",
    }
    rewritten: dict[str, Any] = {}
    for key, item in value.items():
        if key in reference_fields and isinstance(item, str):
            rewritten[key] = id_remap.get(item, item)
        elif key in list_reference_fields and isinstance(item, list):
            rewritten[key] = [id_remap.get(ref, ref) for ref in item]
        else:
            rewritten[key] = _rewrite_inline_refs(item, id_remap)
    return rewritten


def _is_shared(entity: Any) -> bool:
    """Return whether a pipeline entity is explicitly project-wide."""
    extensions = getattr(entity, "extensions", {})
    return getattr(entity, "shared", False) is True or (
        isinstance(extensions, dict) and extensions.get("shared") is True
    )


def _exclusive_full_boundaries(
    boundaries: list[SystemBoundary], ownership: FileOwnership,
) -> list[SystemBoundary]:
    """Clone full boundaries with one deterministic owner per source file."""
    result = []
    for boundary in boundaries:
        scoped = deepcopy(boundary)
        scoped.files = [
            path for path in boundary.files
            if ownership.boundary_by_file.get(_normalized_path(path)) == boundary.system_id
        ]
        if scoped.files:
            result.append(scoped)
    return result


def _build_sos_model(
    systems: list[SystemModel],
    inlines: list[SystemBoundary],
    decompose: DecomposeResult,
    top_results: dict[str, StageResult],
    project_name: str = "",
    ownership: FileOwnership | None = None,
) -> SoSModel:
    """Assemble the System-of-Systems model."""
    # Actors remain top-level external context. Internal inferred entities stay
    # in their self-contained subsystem models.
    raw_actors: list[Any] = []
    capabilities: list[dict[str, Any]] = []
    behaviors: list[dict[str, Any]] = []

    if ownership is None:
        ownership = _build_file_ownership(
            list(getattr(getattr(top_results.get("allocate"), "output", None), "components", [])),
            list(decompose.systems) + list(inlines),
        )
    infer_result = top_results.get("infer")
    if infer_result and infer_result.output:
        output = infer_result.output
        if hasattr(output, "actors"):
            raw_actors = list(output.actors)

    # Build SoS YAML
    systems = sorted(
        [system for system in systems if system.model_yaml],
        key=lambda system: (system.system_id, system.name),
    )
    slugs = _system_slugs(systems)
    allocator = _EntityIdAllocator()
    system_id_remap = {
        system.system_id: allocator.allocate(system.system_id, namespace="root", prefix="SYS")
        for system in systems
    }
    actor_id_remap = {
        actor.id: allocator.allocate(actor.id, prefix="ACT")
        for actor in sorted(raw_actors, key=lambda item: (item.id, item.name))
    }
    actors = [
        {
            "id": actor_id_remap[actor.id],
            "name": actor.name,
            "status": "ACTIVE",
        }
        for actor in sorted(raw_actors, key=lambda item: (item.id, item.name))
    ]
    inter_system_interfaces: list[dict[str, Any]] = []
    for from_sys, to_sys, rel_type in decompose.inter_system_edges:
        inter_system_interfaces.append({
            "from": system_id_remap.get(from_sys, allocator.allocate(from_sys, "root", "SYS")),
            "to": system_id_remap.get(to_sys, allocator.allocate(to_sys, "root", "SYS")),
            "type": rel_type,
        })
    source_artifacts = sorted([
        f".architecture-models/{slugs[system.system_id]}/.architecture-model.yaml"
        for system in systems
    ] + [str(path) for boundary in inlines for path in boundary.files])
    system_entities = [
        {
            "id": system_id_remap[s.system_id],
            "name": s.name,
            "status": "ACTIVE",
            "sub_model_ref": f".architecture-models/{slugs[s.system_id]}/.architecture-model.yaml",
        }
        for s in systems
    ]
    sos_dict: dict[str, Any] = {
        "meta": {
            "project": project_name or "System-of-Systems",
            "schema_version": "2.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "system_of_systems": True,
            "source_artifacts": source_artifacts,
        },
        "entities": {
            "systems": system_entities,
        },
        "relationships": inter_system_interfaces,
    }
    if actors:
        sos_dict["entities"]["actors"] = actors
    if capabilities:
        sos_dict["entities"]["capabilities"] = capabilities
    if behaviors:
        sos_dict["entities"]["behaviors"] = behaviors
    allocator.used.update({
        entity["id"]
        for group in sos_dict["entities"].values()
        for entity in group
        if entity.get("id")
    })
    inline_relationships: list[dict[str, Any]] = []
    allocation_output = getattr(getattr(top_results.get("allocate"), "output", None), "components", [])
    inference_output = getattr(top_results.get("infer"), "output", None)
    shared_components = [component for component in allocation_output if _is_shared(component)]
    shared_capabilities = [
        capability for capability in getattr(inference_output, "capabilities", [])
        if _is_shared(capability)
    ]
    shared_ids = {
        entity.id for entity in shared_components + shared_capabilities
    }
    if shared_components:
        shared_results = dict(top_results)
        shared_results["allocate"] = StageResult(
            output=type(getattr(top_results["allocate"], "output"))(
                components=shared_components
            ),
            quality=top_results["allocate"].quality,
        )
        if inference_output is not None:
            shared_results["infer"] = StageResult(
                output=type(inference_output)(
                    capabilities=shared_capabilities,
                    actors=[],
                    behaviors=[
                        behavior for behavior in getattr(inference_output, "behaviors", [])
                        if _is_shared(behavior)
                    ],
                ),
                quality=top_results["infer"].quality,
            )
        relate_output = getattr(getattr(top_results.get("relate"), "output", None), "relationships", [])
        shared_results["relate"] = StageResult(
            output=type(getattr(top_results["relate"], "output"))(
                relationships=[
                    relationship for relationship in relate_output
                    if relationship.from_id in shared_ids and relationship.to_id in shared_ids
                ]
            ),
            quality=top_results["relate"].quality,
        )
        shared_files = sorted({
            str(path) for component in shared_components for path in component.files
        })
        shared_projection = yaml.safe_load(_build_system_model_yaml(
            SystemBoundary("shared", "Shared", files=shared_files, is_full_system=False),
            shared_results,
            project_name,
            ownership,
        ))
        for group_name, entities in shared_projection.get("entities", {}).items():
            if group_name != "actors":
                sos_dict["entities"].setdefault(group_name, []).extend(entities)
                allocator.used.update(entity["id"] for entity in entities if entity.get("id"))
        inline_relationships.extend(shared_projection.get("relationships", []))
    for boundary in sorted(inlines, key=lambda item: (item.system_id, item.name)):
        owned_files = [
            path for path in boundary.files
            if ownership.boundary_by_file.get(_normalized_path(path)) == boundary.system_id
        ]
        if not owned_files:
            continue
        owned_boundary = deepcopy(boundary)
        owned_boundary.files = owned_files
        projection = yaml.safe_load(
            _build_system_model_yaml(owned_boundary, top_results, project_name, ownership)
        )
        projected_entities = projection.get("entities", {})
        if not projected_entities.get("components"):
            projected_entities["components"] = [{
                "id": _schema_id(boundary.system_id),
                "name": boundary.name,
                "status": "ACTIVE",
                "files": list(owned_files),
            }]
        id_remap: dict[str, str] = dict(actor_id_remap)
        for group_name, entities in projected_entities.items():
            if group_name == "actors":
                continue
            for entity in entities:
                original_id = entity.get("id", "")
                if original_id:
                    prefix = {
                        "components": "COMP", "capabilities": "CAP", "behaviors": "BEH",
                        "interfaces": "IF", "requirements": "REQ", "constraints": "CON",
                        "layers": "LAY", "systems": "SYS",
                    }.get(group_name, "")
                    id_remap[original_id] = allocator.allocate(
                        original_id, namespace=boundary.system_id, prefix=prefix,
                    )
        for group_name, entities in projected_entities.items():
            if group_name == "actors":
                continue
            target = sos_dict["entities"].setdefault(group_name, [])
            for entity in entities:
                rewritten = _rewrite_inline_refs(entity, id_remap)
                if entity.get("id"):
                    rewritten["id"] = id_remap[entity["id"]]
                target.append(rewritten)
        inline_relationships.extend(
            _rewrite_inline_refs(relationship, id_remap)
            for relationship in projection.get("relationships", [])
        )
    sos_dict["relationships"].extend(inline_relationships)

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
        all_boundaries = list(decompose_result.systems) + list(decompose_result.inline_components)
        ownership = _build_file_ownership(
            list(getattr(getattr(ctx.get("allocate"), "output", None), "components", [])),
            all_boundaries,
        )
        full_boundaries = _exclusive_full_boundaries(
            [boundary for boundary in decompose_result.systems if boundary.is_full_system],
            ownership,
        )
        scoped_decompose = deepcopy(decompose_result)
        scoped_decompose.systems = full_boundaries
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

                model_yaml = _build_system_model_yaml(
                    boundary, sub_results, ctx.repo_path.name, ownership
                )
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
                prior_corrections, provenance_calls = _scoped_evidence(
                    ctx, boundary, ownership
                )
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
                    prior_corrections=prior_corrections,
                    llm_calls=provenance_calls,
                )

                sub_results = coordinator.run_to(last_stage, sub_ctx)
                sub_llm_calls = list(sub_ctx.llm_calls)

                model_yaml = _build_system_model_yaml(
                    boundary, sub_results, ctx.repo_path.name, ownership
                )
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
            scoped_decompose,
            ctx.cache,
            project_name=ctx.repo_path.name,
            ownership=ownership,
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
