"""
Round-trip (autoencoder) evaluator for architecture model quality.

Measures structural fidelity of the code → model → code round trip.
If the extracted model is good, regenerated code should structurally match
the original. This provides a self-supervised quality signal without oracle.

The "autoencoder bottleneck": code → UAM model → code. Information loss
during round-trip indicates the model missed architectural structure.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from architecture_model.core.types import ArchitectureModel
from architecture_model.training.code_structure import (
    StructuralGraph,
    parse_multi_file_code,
    parse_code_structure,
)
from architecture_model.training.surrogate import Surrogate

logger = logging.getLogger(__name__)


@dataclass
class RoundTripScore:
    """Round-trip structural fidelity score."""

    # Hard metrics (AST-based, exact string matching)
    class_overlap: float  # Jaccard of class names
    method_overlap: float  # Jaccard of method names (ClassName.method)
    function_overlap: float  # Jaccard of top-level function names
    import_similarity: float  # Fraction of original imports found in generated
    module_ratio: float  # min(gen/orig, orig/gen) ∈ [0,1] for decomposition level

    # Soft metrics (embedding-based, semantic matching)
    semantic_class_match: float  # Avg best cosine sim between class names
    intent_coverage: float  # Fraction of original classes with semantic match in generated

    # Composite
    overall: float

    @staticmethod
    def compute_overall(
        class_overlap: float,
        method_overlap: float,
        function_overlap: float,
        import_similarity: float,
        module_ratio: float,
        semantic_class_match: float,
        intent_coverage: float,
    ) -> float:
        """Weighted composite score."""
        return (
            0.20 * class_overlap
            + 0.15 * method_overlap
            + 0.10 * function_overlap
            + 0.10 * import_similarity
            + 0.10 * module_ratio
            + 0.15 * semantic_class_match
            + 0.20 * intent_coverage
        )


class RoundTripEvaluator:
    """Evaluates round-trip fidelity: code → model → code → compare.

    The "autoencoder bottleneck" — if the extracted architecture model
    captures all structural intent, code generated from it should
    structurally match the original.
    """

    def __init__(
        self,
        surrogate: Surrogate,
        semantic_matcher: Optional[object] = None,  # SemanticMatcher (optional)
    ) -> None:
        self._surrogate = surrogate
        self._semantic_matcher = semantic_matcher

    async def evaluate(
        self,
        original_code: str,
        model: ArchitectureModel,
    ) -> RoundTripScore:
        """Full round-trip evaluation.

        1. Forward pass: generate code from model YAML
        2. Parse both original and generated code into StructuralGraphs
        3. Compare structures (hard + soft metrics)
        4. Return composite score

        Args:
            original_code: The original source code (multi-file format from pipeline).
            model: The extracted ArchitectureModel to evaluate.

        Returns:
            RoundTripScore with all metrics populated.
        """
        # 1. Forward pass: model → code
        model_yaml = model.to_yaml()
        generated_code = await self._surrogate.generate_code(model_yaml)

        # 2. Parse structures
        original_graph = parse_multi_file_code(original_code)
        generated_graph = parse_code_structure(generated_code, module_name="generated")

        # 3. Hard metrics
        class_overlap = self._jaccard(original_graph.class_names, generated_graph.class_names)
        method_overlap = self._jaccard(original_graph.method_names, generated_graph.method_names)
        function_overlap = self._jaccard(
            original_graph.function_names, generated_graph.function_names
        )
        import_similarity = self._import_overlap(original_graph, generated_graph)
        module_ratio = self._module_ratio(original_graph, generated_graph)

        # 4. Soft metrics (if semantic matcher available)
        semantic_class_match = 0.0
        intent_coverage = 0.0

        if self._semantic_matcher is not None:
            orig_names = list(original_graph.class_names)
            gen_names = list(generated_graph.class_names)

            if orig_names and gen_names:
                try:
                    matches = await self._semantic_matcher.match_names(orig_names, gen_names)
                    if matches:
                        semantic_class_match = sum(m.score for m in matches) / len(orig_names)
                    intent_coverage = await self._semantic_matcher.intent_coverage(
                        orig_names, gen_names
                    )
                except Exception as e:
                    logger.debug("Semantic matching failed: %s", e)

        # 5. Composite
        overall = RoundTripScore.compute_overall(
            class_overlap=class_overlap,
            method_overlap=method_overlap,
            function_overlap=function_overlap,
            import_similarity=import_similarity,
            module_ratio=module_ratio,
            semantic_class_match=semantic_class_match,
            intent_coverage=intent_coverage,
        )

        return RoundTripScore(
            class_overlap=class_overlap,
            method_overlap=method_overlap,
            function_overlap=function_overlap,
            import_similarity=import_similarity,
            module_ratio=module_ratio,
            semantic_class_match=semantic_class_match,
            intent_coverage=intent_coverage,
            overall=overall,
        )

    @staticmethod
    def _jaccard(set_a: set[str], set_b: set[str]) -> float:
        """Jaccard similarity (case-insensitive)."""
        a = {s.lower() for s in set_a}
        b = {s.lower() for s in set_b}
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    @staticmethod
    def _import_overlap(original: StructuralGraph, generated: StructuralGraph) -> float:
        """Fraction of original import targets found in generated."""
        orig_imports = original.import_modules
        gen_imports = generated.import_modules
        if not orig_imports:
            return 1.0
        if not gen_imports:
            return 0.0
        # Check how many original imports appear in generated (partial match OK)
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

    @staticmethod
    def _module_ratio(original: StructuralGraph, generated: StructuralGraph) -> float:
        """Ratio of module counts (closer to 1.0 = similar decomposition level)."""
        orig_count = max(len(original.modules), 1)
        gen_count = max(len(generated.modules), 1)
        return min(orig_count, gen_count) / max(orig_count, gen_count)
