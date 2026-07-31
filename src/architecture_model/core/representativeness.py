"""Representativeness metric: how well an architecture model represents the actual codebase."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath

from architecture_model.core.types import ArchitectureModel, Relationship
from architecture_model.manifest.types import InterfaceEdge, ModuleInfo
from architecture_model.monitoring import monitored


@dataclass
class RepresentativenessResult:
    file_coverage: float = 0.0
    relationship_accuracy: float = 0.0
    boundary_coherence: float = 0.0
    overall: float = 0.0
    uncovered_files: list[str] = field(default_factory=list)
    unverified_relationships: list[str] = field(default_factory=list)
    low_coherence_components: list[str] = field(default_factory=list)


def _is_trivial(m: ModuleInfo) -> bool:
    name = PurePosixPath(m.file).name
    if name in ("__version__.py", "__main__.py"):
        return True
    if name == "__init__.py" and m.line_count <= 5 and not m.functions and not m.classes:
        return True
    return False


def _files_match(model_file: str, manifest_file: str) -> bool:
    if model_file == manifest_file:
        return True
    return PurePosixPath(model_file).name == PurePosixPath(manifest_file).name


def _rel_type_matches(r: Relationship) -> bool:
    rtype = r.type
    if rtype in ("depends_on", "uses"):
        return True
    if hasattr(rtype, "value") and rtype.value in ("depends-on", "uses"):
        return True
    return False


@monitored(module="core.representativeness", quality=lambda r: {"overall": r.overall})
def compute_representativeness(
    model: ArchitectureModel,
    modules: list[ModuleInfo],
    interfaces: list[InterfaceEdge],
) -> RepresentativenessResult:
    result = RepresentativenessResult()
    components = model.entities.components if model.entities and model.entities.components else []

    # --- File Coverage ---
    non_trivial = [m for m in modules if not _is_trivial(m)]
    if not non_trivial:
        result.file_coverage = 0.0
    elif not components:
        result.file_coverage = 0.0
        result.uncovered_files = [m.file for m in non_trivial]
    else:
        all_comp_files = []
        for c in components:
            all_comp_files.extend(c.files or [])
        covered = []
        uncovered = []
        for m in non_trivial:
            if any(_files_match(cf, m.file) for cf in all_comp_files):
                covered.append(m.file)
            else:
                uncovered.append(m.file)
        result.file_coverage = len(covered) / len(non_trivial) * 100
        result.uncovered_files = uncovered

    # --- Relationship Accuracy ---
    relationships = model.relationships or []
    comp_map = {c.id: c for c in components}
    verifiable = []
    for r in relationships:
        if not _rel_type_matches(r):
            continue
        from_comp = comp_map.get(r.from_id)
        to_comp = comp_map.get(r.to_id)
        if from_comp and to_comp:
            verifiable.append((r, from_comp, to_comp))

    if not verifiable:
        result.relationship_accuracy = 100.0
    else:
        verified_count = 0
        for r, from_comp, to_comp in verifiable:
            from_files = set(from_comp.files or [])
            to_files = set(to_comp.files or [])
            found = False
            for edge in interfaces:
                src_match = any(_files_match(f, edge.source) for f in from_files)
                tgt_match = any(_files_match(f, edge.target) for f in to_files)
                if src_match and tgt_match:
                    found = True
                    break
            if found:
                verified_count += 1
            else:
                result.unverified_relationships.append(f"{r.from_id} → {r.to_id}")
        result.relationship_accuracy = verified_count / len(verifiable) * 100

    # --- Boundary Coherence ---
    if not components:
        result.boundary_coherence = 0.0
    else:
        cohesions = []
        for c in components:
            files = set(c.files or [])
            if len(files) <= 1:
                cohesions.append(1.0)
                continue
            internal = 0
            external = 0
            for edge in interfaces:
                src_in = any(_files_match(f, edge.source) for f in files)
                tgt_in = any(_files_match(f, edge.target) for f in files)
                if src_in and tgt_in:
                    internal += 1
                elif src_in or tgt_in:
                    external += 1
            if internal + external == 0:
                cohesions.append(1.0)
            else:
                coh = internal / (internal + external)
                cohesions.append(coh)
                if coh < 0.5:
                    result.low_coherence_components.append(c.name if hasattr(c, 'name') else c.id)
        result.boundary_coherence = (sum(cohesions) / len(cohesions)) * 100

    # --- Overall ---
    result.overall = (result.file_coverage + result.relationship_accuracy + result.boundary_coherence) / 3
    return result
