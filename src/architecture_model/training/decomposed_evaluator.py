"""
Decomposed round-trip evaluator: per-system fidelity scoring.

When hierarchical decomposition is used, evaluates each system's generated code
independently against the real source files belonging to that system. This gives
fine-grained signal about which subsystems the model is struggling with.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from architecture_model.core.decomposer import DecompositionResult
from architecture_model.training.code_structure import (
    StructuralGraph,
    ClassInfo,
    FunctionInfo,
    ImportEdge,
    parse_code_structure,
    parse_multi_file_code,
)

logger = logging.getLogger(__name__)


@dataclass
class DecomposedRoundTripScore:
    """Per-system round-trip fidelity breakdown."""

    system_scores: dict[str, float]  # system_id → overall round-trip score
    system_details: dict[str, dict]  # system_id → {class_overlap, method_overlap, ...}
    overall: float  # Weighted average (by complexity_score)
    n_systems: int


def _jaccard(set_a: set[str], set_b: set[str]) -> float:
    """Jaccard similarity (case-insensitive)."""
    a = {s.lower() for s in set_a}
    b = {s.lower() for s in set_b}
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _import_overlap(original: StructuralGraph, generated: StructuralGraph) -> float:
    """Fraction of original import targets found in generated."""
    orig_imports = original.import_modules
    gen_imports = generated.import_modules
    if not orig_imports:
        return 1.0
    if not gen_imports:
        return 0.0
    matched = 0
    for orig_mod in orig_imports:
        for gen_mod in gen_imports:
            if (
                orig_mod == gen_mod
                or orig_mod.endswith(f".{gen_mod}")
                or gen_mod.endswith(f".{orig_mod}")
            ):
                matched += 1
                break
    return matched / len(orig_imports)


def _compute_system_score(reference: StructuralGraph, generated: StructuralGraph) -> dict:
    """Compare a generated graph against a reference graph for a single system.

    Returns a dict with individual metrics and an overall composite score.
    """
    class_overlap = _jaccard(reference.class_names, generated.class_names)
    method_overlap = _jaccard(reference.method_names, generated.method_names)
    function_overlap = _jaccard(reference.function_names, generated.function_names)
    import_similarity = _import_overlap(reference, generated)

    # Weighted composite (simplified from full RoundTripScore — no semantic metrics)
    overall = (
        0.30 * class_overlap
        + 0.25 * method_overlap
        + 0.20 * function_overlap
        + 0.15 * import_similarity
        + 0.10 * _module_ratio(reference, generated)
    )

    return {
        "class_overlap": class_overlap,
        "method_overlap": method_overlap,
        "function_overlap": function_overlap,
        "import_similarity": import_similarity,
        "module_ratio": _module_ratio(reference, generated),
        "overall": overall,
    }


def _module_ratio(original: StructuralGraph, generated: StructuralGraph) -> float:
    """Ratio of module counts (closer to 1.0 = similar decomposition level)."""
    orig_count = max(len(original.modules), 1)
    gen_count = max(len(generated.modules), 1)
    return min(orig_count, gen_count) / max(orig_count, gen_count)


def _build_reference_graph_for_system(
    system_id: str,
    decomposition: DecompositionResult,
    manifest: dict,
) -> StructuralGraph:
    """Build a StructuralGraph from the manifest modules that belong to a system.

    Filters manifest modules by the component names in the system's sub-model,
    then constructs a StructuralGraph from the matching module metadata.

    Args:
        system_id: The system ID to build a reference for.
        decomposition: The full decomposition result.
        manifest: Manifest dict with 'modules' list containing file metadata.

    Returns:
        StructuralGraph representing the real code structure for this system.
    """
    sub_model = decomposition.sub_models.get(system_id)
    if sub_model is None:
        return StructuralGraph()

    # Collect component names (lowercased) that belong to this system
    component_names = {
        comp.name.lower() for comp in sub_model.entities.components
    }

    # Filter manifest modules: match if module path contains a component name
    modules_list = manifest.get("modules", [])
    matched_modules: list[dict] = []

    for mod in modules_list:
        mod_path = mod.get("path", "").lower()
        # Check if any component name appears in the module path
        for comp_name in component_names:
            if comp_name in mod_path:
                matched_modules.append(mod)
                break

    # Build StructuralGraph from matched modules
    classes: list[ClassInfo] = []
    functions: list[FunctionInfo] = []
    imports: list[ImportEdge] = []
    module_names: list[str] = []

    for mod in matched_modules:
        mod_path = mod.get("path", "unknown")
        mod_name = mod_path.replace("/", ".").replace(".py", "")
        module_names.append(mod_name)

        # Classes from manifest module
        for cls_info in mod.get("classes", []):
            if isinstance(cls_info, dict):
                cls_name = cls_info.get("name", "")
                methods = cls_info.get("methods", [])
                bases = cls_info.get("bases", [])
            else:
                # Simple string class name
                cls_name = str(cls_info)
                methods = []
                bases = []
            if cls_name:
                classes.append(ClassInfo(
                    name=cls_name,
                    methods=methods,
                    bases=bases,
                    module=mod_name,
                ))

        # Functions from manifest module
        for func_info in mod.get("functions", []):
            if isinstance(func_info, dict):
                func_name = func_info.get("name", "")
                args = func_info.get("args", [])
            else:
                func_name = str(func_info)
                args = []
            if func_name:
                functions.append(FunctionInfo(
                    name=func_name,
                    args=args,
                    module=mod_name,
                ))

        # Imports from manifest module
        for imp in mod.get("imports", []):
            if isinstance(imp, str):
                imports.append(ImportEdge(from_module=mod_name, to_module=imp))
            elif isinstance(imp, dict):
                imports.append(ImportEdge(
                    from_module=mod_name,
                    to_module=imp.get("module", ""),
                ))

    return StructuralGraph(
        classes=classes,
        functions=functions,
        imports=imports,
        modules=module_names,
    )


class DecomposedRoundTripEvaluator:
    """Evaluates per-system round-trip fidelity for hierarchically decomposed models.

    For each system in the decomposition:
    1. Parses its generated code into a StructuralGraph
    2. Builds a reference StructuralGraph from the system's component files in the manifest
    3. Compares using jaccard/overlap metrics
    4. Weights by complexity_score for overall score
    """

    def evaluate(
        self,
        decomposition: DecompositionResult,
        per_system_code: dict[str, str],  # system_id → generated code
        original_graph: StructuralGraph,
        manifest: dict,
    ) -> DecomposedRoundTripScore:
        """Evaluate per-system fidelity.

        Args:
            decomposition: The decomposition result with top-level and sub-models.
            per_system_code: Mapping of system_id to generated code for that system.
            original_graph: The full original StructuralGraph (used as fallback).
            manifest: Manifest dict with 'modules' list for reference building.

        Returns:
            DecomposedRoundTripScore with per-system scores and weighted overall.
        """
        system_scores: dict[str, float] = {}
        system_details: dict[str, dict] = {}

        # Collect complexity scores for weighting
        complexity_weights: dict[str, float] = {}
        for sys in decomposition.top_level.entities.systems:
            complexity_weights[sys.id] = max(sys.complexity_score, 1.0)

        for sys in decomposition.top_level.entities.systems:
            sys_id = sys.id
            generated_code = per_system_code.get(sys_id, "")

            if not generated_code:
                # No code generated for this system — score 0
                system_scores[sys_id] = 0.0
                system_details[sys_id] = {
                    "class_overlap": 0.0,
                    "method_overlap": 0.0,
                    "function_overlap": 0.0,
                    "import_similarity": 0.0,
                    "module_ratio": 0.0,
                    "overall": 0.0,
                }
                continue

            # Parse generated code into StructuralGraph
            generated_graph = parse_code_structure(generated_code, module_name=f"gen_{sys_id}")

            # Build reference graph from manifest for this system
            reference_graph = _build_reference_graph_for_system(
                sys_id, decomposition, manifest
            )

            # If reference graph is empty, fall back to using the original_graph
            # filtered to system's expected classes (best effort)
            if not reference_graph.classes and not reference_graph.functions:
                reference_graph = self._fallback_reference(sys_id, decomposition, original_graph)

            # Compare
            details = _compute_system_score(reference_graph, generated_graph)
            system_scores[sys_id] = details["overall"]
            system_details[sys_id] = details

        # Compute weighted overall
        total_weight = sum(complexity_weights.get(sid, 1.0) for sid in system_scores)
        if total_weight > 0:
            overall = sum(
                system_scores[sid] * complexity_weights.get(sid, 1.0)
                for sid in system_scores
            ) / total_weight
        else:
            overall = 0.0

        return DecomposedRoundTripScore(
            system_scores=system_scores,
            system_details=system_details,
            overall=overall,
            n_systems=len(system_scores),
        )

    @staticmethod
    def _fallback_reference(
        system_id: str,
        decomposition: DecompositionResult,
        original_graph: StructuralGraph,
    ) -> StructuralGraph:
        """Build a fallback reference from the original graph using component symbols.

        When the manifest doesn't have module data for a system's components,
        we extract expected class/function names from the sub-model's component
        symbols and match against the original graph.
        """
        sub_model = decomposition.sub_models.get(system_id)
        if sub_model is None:
            return StructuralGraph()

        # Collect expected names from component symbols and functions
        expected_classes: set[str] = set()
        expected_functions: set[str] = set()
        for comp in sub_model.entities.components:
            for sym in comp.symbols:
                expected_classes.add(sym.name)
            for func_name in comp.functions:
                expected_functions.add(func_name)

        # Filter original graph to only include matching items
        filtered_classes = [
            c for c in original_graph.classes
            if c.name in expected_classes
        ]
        filtered_functions = [
            f for f in original_graph.functions
            if f.name in expected_functions
        ]

        return StructuralGraph(
            classes=filtered_classes,
            functions=filtered_functions,
            imports=[],
            modules=[],
        )
