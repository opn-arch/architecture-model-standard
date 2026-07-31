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
    behavioral_coverage: float = 0.0
    overall: float = 0.0
    uncovered_files: list[str] = field(default_factory=list)
    unverified_relationships: list[str] = field(default_factory=list)
    low_coherence_components: list[str] = field(default_factory=list)
    uncaptured_behaviors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "file_coverage": self.file_coverage,
            "relationship_accuracy": self.relationship_accuracy,
            "boundary_coherence": self.boundary_coherence,
            "behavioral_coverage": self.behavioral_coverage,
            "overall": self.overall,
            "uncovered_files": self.uncovered_files,
            "unverified_relationships": self.unverified_relationships,
            "low_coherence_components": self.low_coherence_components,
            "uncaptured_behaviors": self.uncaptured_behaviors,
        }


def _is_trivial(m: ModuleInfo) -> bool:
    name = PurePosixPath(m.file).name
    if name in ("__version__.py", "__main__.py"):
        return True
    # __init__.py with no functions and no classes = re-export file (trivial)
    if name == "__init__.py" and not m.functions and not m.classes:
        return True
    # Vendor directories are third-party code, not part of project architecture
    parts = PurePosixPath(m.file).parts
    if "vendor" in parts or "_vendor" in parts or "vendored" in parts:
        return True
    # Modules with no public functions and no classes (only private internals)
    if not m.functions and not m.classes:
        return True
    return False


def _files_match(model_file: str, manifest_file: str) -> bool:
    # Normalize: strip leading ./
    a = model_file.lstrip("./") if model_file.startswith("./") else model_file
    b = manifest_file.lstrip("./") if manifest_file.startswith("./") else manifest_file
    if a == b:
        return True
    # Suffix match: one path ends with /other (handles src/ prefix differences)
    if a.endswith("/" + b) or b.endswith("/" + a):
        return True
    return False


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
                # Single-file components: check if it's an __init__.py (re-export hub)
                # These are architectural connectors with inherently low cohesion
                if files and all(PurePosixPath(f).name == "__init__.py" for f in files):
                    continue  # Skip from coherence calculation
                cohesions.append(1.0)
                continue
            # Skip components that are predominantly __init__.py re-export hubs
            init_count = sum(1 for f in files if PurePosixPath(f).name == "__init__.py")
            if init_count > len(files) / 2:
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
        result.boundary_coherence = (sum(cohesions) / len(cohesions)) * 100 if cohesions else 100.0

    # --- Behavioral Coverage ---
    # A function is "complex" if it has call_order or control_flow (meaning our
    # behavioral extractor found something to capture). Functions that only have
    # `calls` from nested closures or builtins are not complex at their own level.
    # Coverage = % of complex functions that have BOTH call_order and control_flow,
    # or at minimum one of them populated.
    # Simpler: if call_order or control_flow is populated, it's captured.
    # "Uncaptured" = functions where the OLD calls field has non-builtin entries
    # but call_order is empty AND no control_flow — these might indicate our
    # extractor missed something.
    _BUILTINS = frozenset({
        "print", "len", "str", "int", "float", "bool", "list", "dict", "set",
        "tuple", "range", "enumerate", "zip", "map", "filter", "sorted", "reversed",
        "min", "max", "sum", "abs", "round", "isinstance", "issubclass", "hasattr",
        "getattr", "setattr", "delattr", "type", "id", "repr", "hash", "iter",
        "next", "super", "object", "property", "staticmethod", "classmethod",
        "vars", "dir", "any", "all", "ord", "chr", "hex", "oct", "bin",
        "format", "input", "open", "NotImplementedError", "ValueError",
        "TypeError", "KeyError", "RuntimeError", "AttributeError", "ImportError",
        "OSError", "IOError", "StopIteration", "Exception",
    })

    complex_funcs = []
    for m in modules:
        # Skip vendor/trivial modules for behavioral coverage
        if _is_trivial(m):
            continue
        for f in m.functions:
            if not hasattr(f, 'call_order'):
                continue
            if f.call_order or f.control_flow:
                complex_funcs.append((m.name, f, True))  # captured
            elif f.calls:
                # Has old-style calls but no new behavioral data
                non_builtin = [c for c in f.calls if c not in _BUILTINS]
                if non_builtin:
                    complex_funcs.append((m.name, f, False))  # potentially uncaptured
        for cls in m.classes:
            for method in getattr(cls, 'method_details', []):
                if not hasattr(method, 'call_order'):
                    continue
                if method.call_order or method.control_flow:
                    complex_funcs.append((m.name, method, True))
                elif method.calls:
                    non_builtin = [c for c in method.calls if c not in _BUILTINS]
                    if non_builtin:
                        complex_funcs.append((m.name, method, False))

    if complex_funcs:
        captured = sum(1 for _, _, is_captured in complex_funcs if is_captured)
        for mod_name, f, is_captured in complex_funcs:
            if not is_captured:
                result.uncaptured_behaviors.append(f"{mod_name}.{f.name}")
        result.behavioral_coverage = (captured / len(complex_funcs)) * 100
    else:
        result.behavioral_coverage = 100.0  # No complex functions = vacuously true

    # --- Overall ---
    result.overall = (
        result.file_coverage + result.relationship_accuracy +
        result.boundary_coherence + result.behavioral_coverage
    ) / 4
    return result


@dataclass
class HierarchicalRepresentativenessResult:
    """Representativeness at root + per-block level."""
    root: RepresentativenessResult = field(default_factory=RepresentativenessResult)
    blocks: dict[str, RepresentativenessResult] = field(default_factory=dict)
    overall: float = 0.0

    def to_dict(self) -> dict:
        return {
            "root": self.root.to_dict(),
            "blocks": {k: v.to_dict() for k, v in self.blocks.items()},
            "overall": self.overall,
        }


def compute_hierarchical_representativeness(
    root_model: ArchitectureModel,
    sub_models: dict[str, ArchitectureModel],
    recursive_manifests: dict[str, "RecursiveManifest"],
) -> HierarchicalRepresentativenessResult:
    """Verify representativeness at every level of decomposition.
    
    Root level: checks that all blocks are represented and cross-block relationships
    match real import dependencies.
    
    Block level: standard file_coverage + relationship_accuracy + boundary_coherence
    within each block's scope.
    """
    from architecture_model.manifest.types import RecursiveManifest

    result = HierarchicalRepresentativenessResult()

    # --- Root level ---
    # Collect all modules across all blocks for root-level check
    all_modules = []
    all_interfaces = []
    for rm in recursive_manifests.values():
        all_modules.extend(rm.manifest.modules)
        all_interfaces.extend(rm.manifest.interfaces)

    result.root = compute_representativeness(root_model, all_modules, all_interfaces)

    # --- Per-block level ---
    block_scores: list[float] = []
    for block_id, rm in recursive_manifests.items():
        if block_id in sub_models:
            sub_model = sub_models[block_id]
            block_result = compute_representativeness(
                sub_model, rm.manifest.modules, rm.manifest.interfaces
            )
            result.blocks[block_id] = block_result
            block_scores.append(block_result.overall)

    # --- Overall ---
    if block_scores:
        result.overall = (result.root.overall + sum(block_scores) / len(block_scores)) / 2
    else:
        result.overall = result.root.overall

    return result
