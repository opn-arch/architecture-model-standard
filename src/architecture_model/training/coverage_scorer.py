"""
CoverageScorer: measures how well a model's relationships match manifest import reality.

Unlike InterfaceEnforcer (which silently patches), this ONLY produces scores.
It is a penalty signal for the training loop — not a repair mechanism.

Five dimensions:
1. edge_coverage — fraction of manifest import edges backed by model relationships
2. edge_precision — fraction of model relationships backed by manifest import edges
3. cohesion — mean internal coupling per component
4. directionality — fraction of relationships with correct import direction
5. test_alignment — fuzzy overlap between test-implied components and model components
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from architecture_model.core.types import ArchitectureModel, RelationType

if TYPE_CHECKING:
    from architecture_model.training.test_analyzer import TestStructure


@dataclass
class CoverageScore:
    """Multi-dimensional coverage quality score (all 0-1, higher is better)."""

    edge_coverage: float = 0.0      # manifest edges covered by model relationships
    edge_precision: float = 0.0     # model relationships backed by manifest edges
    cohesion: float = 0.0           # mean internal edges / possible internal per component
    directionality: float = 0.0     # relationships with correct import direction
    test_alignment: float = 0.0     # fuzzy overlap: test-implied components vs model components
    overall: float = 0.0            # weighted average

    # Detail for debugging/analysis
    missing_edges: list[tuple[str, str]] = field(default_factory=list)
    spurious_rels: list[tuple[str, str]] = field(default_factory=list)
    low_cohesion_components: list[str] = field(default_factory=list)


class CoverageScorer:
    """Scores model relationship quality against manifest import reality.

    Does NOT modify the model. Only produces a CoverageScore.
    """

    # Weights for overall score (sum to 1.0)
    EDGE_COVERAGE_WEIGHT: float = 0.30
    EDGE_PRECISION_WEIGHT: float = 0.20
    COHESION_WEIGHT: float = 0.20
    DIRECTIONALITY_WEIGHT: float = 0.15
    TEST_ALIGNMENT_WEIGHT: float = 0.15

    def score(
        self,
        model: ArchitectureModel,
        manifest: dict[str, Any],
        *,
        test_structure: TestStructure | None = None,
    ) -> CoverageScore:
        """Score the model's relationship coverage against manifest reality.

        Args:
            model: The architecture model to evaluate.
            manifest: Reality Manifest dict with modules, interfaces.
            test_structure: Optional test structure for test_alignment scoring.

        Returns:
            CoverageScore with 5 dimensions + detail.
        """
        # Build module→component mapping (reuse existing logic from oracle_coverage)
        module_map = self._build_module_map(manifest, model)

        # Build component relationship set from model
        model_rels = self._build_model_rel_set(model)

        # Build manifest edge set (aggregated to component level)
        manifest_edges, edge_directions = self._build_manifest_edge_set(manifest, module_map)

        # 1. Edge coverage: what fraction of manifest edges are in model?
        edge_cov, missing = self._compute_edge_coverage(manifest_edges, model_rels)

        # 2. Edge precision: what fraction of model rels are backed by manifest?
        edge_prec, spurious = self._compute_edge_precision(model_rels, manifest_edges)

        # 3. Cohesion: mean internal coupling per component
        cohesion_score, low_cohesion = self._compute_cohesion(manifest, module_map, model)

        # 4. Directionality: are relationships in the right direction?
        dir_score = self._compute_directionality(model_rels, edge_directions)

        # 5. Test alignment: do model components match test-implied components?
        test_align = self._compute_test_alignment(model, test_structure)

        # Overall weighted average
        overall = (
            self.EDGE_COVERAGE_WEIGHT * edge_cov
            + self.EDGE_PRECISION_WEIGHT * edge_prec
            + self.COHESION_WEIGHT * cohesion_score
            + self.DIRECTIONALITY_WEIGHT * dir_score
            + self.TEST_ALIGNMENT_WEIGHT * test_align
        )

        return CoverageScore(
            edge_coverage=edge_cov,
            edge_precision=edge_prec,
            cohesion=cohesion_score,
            directionality=dir_score,
            test_alignment=test_align,
            overall=overall,
            missing_edges=missing,
            spurious_rels=spurious,
            low_cohesion_components=low_cohesion,
        )

    def _build_module_map(self, manifest: dict, model: ArchitectureModel) -> dict[str, str]:
        """Map manifest module file paths to component IDs.

        Reuses the multi-strategy matching from ManifestCoverageComputer.
        """
        from architecture_model.training.oracle_coverage import ManifestCoverageComputer

        return ManifestCoverageComputer()._build_module_component_map(manifest, model)

    def _build_model_rel_set(self, model: ArchitectureModel) -> set[tuple[str, str]]:
        """Build set of (from_comp, to_comp) pairs from model relationships."""
        rels: set[tuple[str, str]] = set()
        for rel in model.relationships:
            rels.add((rel.from_id, rel.to_id))
        return rels

    def _build_manifest_edge_set(
        self, manifest: dict, module_map: dict[str, str]
    ) -> tuple[set[tuple[str, str]], dict[tuple[str, str], int]]:
        """Aggregate manifest file-level imports to component-level edges.

        Returns:
            - Set of (from_comp, to_comp) pairs
            - Dict of (from_comp, to_comp) -> edge count (for weighting)
        """
        edges: set[tuple[str, str]] = set()
        directions: dict[tuple[str, str], int] = {}

        for iface in manifest.get("interfaces", []):
            src_file = iface.get("source", "")
            tgt_file = iface.get("target", "")

            src_comp = module_map.get(src_file, "")
            tgt_comp = module_map.get(tgt_file, "")

            if src_comp and tgt_comp and src_comp != tgt_comp:
                pair = (src_comp, tgt_comp)
                edges.add(pair)
                directions[pair] = directions.get(pair, 0) + 1

        return edges, directions

    def _compute_edge_coverage(
        self, manifest_edges: set[tuple[str, str]], model_rels: set[tuple[str, str]]
    ) -> tuple[float, list[tuple[str, str]]]:
        """Fraction of manifest edges covered by model relationships (either direction)."""
        if not manifest_edges:
            return 1.0, []

        # Check both directions (model might have B->A for manifest's A->B)
        model_rels_bidir = model_rels | {(b, a) for a, b in model_rels}

        covered = 0
        missing: list[tuple[str, str]] = []

        for edge in manifest_edges:
            if edge in model_rels_bidir:
                covered += 1
            else:
                missing.append(edge)

        return covered / len(manifest_edges), missing

    def _compute_edge_precision(
        self, model_rels: set[tuple[str, str]], manifest_edges: set[tuple[str, str]]
    ) -> tuple[float, list[tuple[str, str]]]:
        """Fraction of model relationships backed by manifest import edges."""
        if not model_rels:
            return 1.0, []

        # A model relationship is "backed" if there's a manifest edge in either direction
        manifest_bidir = manifest_edges | {(b, a) for a, b in manifest_edges}

        backed = 0
        spurious: list[tuple[str, str]] = []

        for rel in model_rels:
            if rel in manifest_bidir:
                backed += 1
            else:
                # Also accept contains/realizes/constrains relationships as valid
                # (these don't need import backing)
                spurious.append(rel)

        return backed / len(model_rels), spurious

    def _compute_cohesion(
        self, manifest: dict, module_map: dict[str, str], model: ArchitectureModel
    ) -> tuple[float, list[str]]:
        """Compute mean internal cohesion per component.

        cohesion(C) = internal_edges / possible_internal_edges
        where internal_edges = import edges where both source and target are in C
        """
        # Group files by component
        comp_files: dict[str, set[str]] = {}
        for file_path, comp_id in module_map.items():
            if comp_id:
                comp_files.setdefault(comp_id, set()).add(file_path)

        if not comp_files:
            return 1.0, []

        # Build file-level edge set
        file_edges: set[tuple[str, str]] = set()
        for iface in manifest.get("interfaces", []):
            src = iface.get("source", "")
            tgt = iface.get("target", "")
            if src and tgt:
                file_edges.add((src, tgt))

        # Compute per-component cohesion
        cohesions: list[float] = []
        low_cohesion: list[str] = []

        comp_names = {c.id: c.name for c in model.entities.components}

        for comp_id, files in comp_files.items():
            if len(files) < 2:
                cohesions.append(1.0)  # Single-file components are trivially cohesive
                continue

            # Count internal edges
            internal = sum(1 for s, t in file_edges if s in files and t in files)
            possible = len(files) * (len(files) - 1)  # directed pairs

            coh = internal / possible if possible > 0 else 0.0
            cohesions.append(coh)

            if coh < 0.05 and len(files) >= 3:
                name = comp_names.get(comp_id, comp_id)
                low_cohesion.append(name)

        mean_cohesion = sum(cohesions) / len(cohesions) if cohesions else 1.0
        return mean_cohesion, low_cohesion

    def _compute_directionality(
        self, model_rels: set[tuple[str, str]], edge_directions: dict[tuple[str, str], int]
    ) -> float:
        """Fraction of model relationships with correct import direction.

        If manifest has A->B (more imports from A to B), model should have A depends_on B
        (or B exposes to A). We check if the model's direction matches the dominant
        import direction.
        """
        if not model_rels or not edge_directions:
            return 1.0

        correct = 0
        total = 0

        for rel in model_rels:
            a, b = rel
            forward_count = edge_directions.get((a, b), 0)
            reverse_count = edge_directions.get((b, a), 0)

            if forward_count == 0 and reverse_count == 0:
                continue  # Not checkable (structural relationship)

            total += 1
            # Model says A->B; manifest should have A importing B (forward)
            if forward_count >= reverse_count:
                correct += 1

        return correct / total if total > 0 else 1.0

    def _compute_test_alignment(
        self, model: ArchitectureModel, test_structure: TestStructure | None
    ) -> float:
        """Fuzzy overlap between test-implied components and model components.

        Uses word-level Jaccard matching: each test-implied name and model component
        name is normalized to a lowercase word set, then we find the best match
        for each test-implied component and average the scores.

        Returns 1.0 if no test_structure provided (neutral — doesn't penalize).
        """
        if test_structure is None or not test_structure.implied_components:
            return 1.0

        # Get model component names
        model_names = [c.name for c in model.entities.components]
        if not model_names:
            return 0.0

        # Normalize to lowercase word sets
        def to_word_set(name: str) -> set[str]:
            import re
            # Split on whitespace, underscores, hyphens, camelCase boundaries
            words = re.split(r'[\s_\-]+', name.lower())
            # Also split camelCase
            expanded: list[str] = []
            for word in words:
                parts = re.sub(r'([A-Z])', r' \1', word).split()
                expanded.extend(p.lower() for p in parts if p)
            return set(expanded) if expanded else {name.lower()}

        model_word_sets = [(name, to_word_set(name)) for name in model_names]

        # For each test-implied component, find best Jaccard match in model
        alignment_scores: list[float] = []
        for test_comp in test_structure.implied_components:
            test_words = to_word_set(test_comp)
            if not test_words:
                continue

            best_jaccard = 0.0
            for _model_name, model_words in model_word_sets:
                if not model_words:
                    continue
                intersection = test_words & model_words
                union = test_words | model_words
                jaccard = len(intersection) / len(union) if union else 0.0
                best_jaccard = max(best_jaccard, jaccard)

            alignment_scores.append(best_jaccard)

        return sum(alignment_scores) / len(alignment_scores) if alignment_scores else 0.0
