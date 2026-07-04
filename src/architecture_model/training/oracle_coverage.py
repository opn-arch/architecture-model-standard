"""
ManifestCoverageComputer: measures how well an ArchitectureModel covers a Reality Manifest.

This is the core learning signal for the oracle self-learning loop.
Coverage is significance-weighted:
- Large modules (by LOC) must be covered — weight by line_count
- Inter-block import edges weight more
- F-blocks should map to capabilities
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from architecture_model.core.types import ArchitectureModel


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class CoverageResult:
    """Result of a manifest coverage computation."""

    module_coverage: float = 0.0
    interface_coverage: float = 0.0
    block_coverage: float = 0.0
    overall: float = 0.0
    uncovered_modules: list[str] = field(default_factory=list)
    uncovered_interfaces: list[tuple[str, str]] = field(default_factory=list)
    uncovered_blocks: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Name matching helpers
# ---------------------------------------------------------------------------

_SPLIT_RE = re.compile(r"[-_\s./]+")


def _tokenize(name: str) -> set[str]:
    """Split a name into lowercase word tokens."""
    return {t.lower() for t in _SPLIT_RE.split(name) if t}


def _word_jaccard(a: str, b: str) -> float:
    """Compute Jaccard similarity between word-tokenized names."""
    tokens_a = _tokenize(a)
    tokens_b = _tokenize(b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def _name_matches(name: str, candidates: list[str], threshold: float = 0.4) -> bool:
    """Check if name matches any candidate via exact or word Jaccard."""
    name_lower = name.lower().strip()
    for candidate in candidates:
        candidate_lower = candidate.lower().strip()
        # Exact match
        if name_lower == candidate_lower:
            return True
        # Word Jaccard
        if _word_jaccard(name, candidate) >= threshold:
            return True
    return False


# ---------------------------------------------------------------------------
# ManifestCoverageComputer
# ---------------------------------------------------------------------------


class ManifestCoverageComputer:
    """Computes how well an ArchitectureModel covers a Reality Manifest."""

    # Minimum line count for a module to be considered significant
    MIN_LOC_THRESHOLD: int = 10

    # Weights for overall score
    MODULE_WEIGHT: float = 0.5
    INTERFACE_WEIGHT: float = 0.3
    BLOCK_WEIGHT: float = 0.2

    def compute(self, manifest: dict[str, Any], model: ArchitectureModel) -> CoverageResult:
        """Compute coverage of manifest by the architecture model.

        Args:
            manifest: Reality Manifest dict with modules, interfaces, functional_blocks.
            model: The ArchitectureModel to evaluate.

        Returns:
            CoverageResult with per-dimension scores and uncovered items.
        """
        module_cov, uncov_modules = self._compute_module_coverage(manifest, model)
        iface_cov, uncov_ifaces = self._compute_interface_coverage(manifest, model)
        block_cov, uncov_blocks = self._compute_block_coverage(manifest, model)

        # Overall weighted score
        # If all dimensions are empty, consider fully covered
        has_modules = bool(manifest.get("modules"))
        has_interfaces = bool(manifest.get("interfaces"))
        has_blocks = bool(manifest.get("functional_blocks"))

        if not has_modules and not has_interfaces and not has_blocks:
            overall = 1.0
        else:
            # Compute weighted average over non-empty dimensions
            total_weight = 0.0
            weighted_sum = 0.0
            if has_modules:
                total_weight += self.MODULE_WEIGHT
                weighted_sum += self.MODULE_WEIGHT * module_cov
            if has_interfaces:
                total_weight += self.INTERFACE_WEIGHT
                weighted_sum += self.INTERFACE_WEIGHT * iface_cov
            if has_blocks:
                total_weight += self.BLOCK_WEIGHT
                weighted_sum += self.BLOCK_WEIGHT * block_cov

            overall = weighted_sum / total_weight if total_weight > 0 else 1.0

        return CoverageResult(
            module_coverage=module_cov,
            interface_coverage=iface_cov,
            block_coverage=block_cov,
            overall=overall,
            uncovered_modules=uncov_modules,
            uncovered_interfaces=uncov_ifaces,
            uncovered_blocks=uncov_blocks,
        )

    def _compute_module_coverage(
        self, manifest: dict[str, Any], model: ArchitectureModel
    ) -> tuple[float, list[str]]:
        """Compute LOC-weighted module coverage.

        For each manifest module with line_count >= MIN_LOC_THRESHOLD,
        check if any component name matches (word Jaccard >= 0.4).
        Weight by LOC.
        """
        modules = manifest.get("modules", [])
        component_names = [c.name for c in model.entities.components]

        total_loc = 0
        covered_loc = 0
        uncovered: list[str] = []

        for mod in modules:
            loc = mod.get("line_count", 0)
            if loc < self.MIN_LOC_THRESHOLD:
                continue

            total_loc += loc
            mod_name = mod.get("name", "")

            if _name_matches(mod_name, component_names):
                covered_loc += loc
            else:
                uncovered.append(mod.get("file", ""))

        if total_loc == 0:
            return 1.0, []

        return covered_loc / total_loc, uncovered

    def _compute_interface_coverage(
        self, manifest: dict[str, Any], model: ArchitectureModel
    ) -> tuple[float, list[tuple[str, str]]]:
        """Compute interface coverage.

        For each manifest interface, check if a relationship exists between
        components matching the source/target module names.
        """
        interfaces = manifest.get("interfaces", [])
        if not interfaces:
            return 1.0, []

        modules = manifest.get("modules", [])
        # Build file->name mapping
        file_to_name: dict[str, str] = {}
        for mod in modules:
            file_to_name[mod.get("file", "")] = mod.get("name", "")

        component_names = [c.name for c in model.entities.components]
        # Build component id -> name and name -> id maps
        name_to_ids: dict[str, list[str]] = {}
        for comp in model.entities.components:
            name_lower = comp.name.lower().strip()
            name_to_ids.setdefault(name_lower, []).append(comp.id)

        covered = 0
        uncovered: list[tuple[str, str]] = []

        for iface in interfaces:
            source_file = iface.get("source", "")
            target_file = iface.get("target", "")
            source_name = file_to_name.get(source_file, "")
            target_name = file_to_name.get(target_file, "")

            if self._has_relationship_between(source_name, target_name, model):
                covered += 1
            else:
                uncovered.append((source_file, target_file))

        return covered / len(interfaces), uncovered

    def _has_relationship_between(
        self, source_name: str, target_name: str, model: ArchitectureModel
    ) -> bool:
        """Check if any relationship exists between components matching source and target names."""
        if not source_name or not target_name:
            return False

        component_names = [c.name for c in model.entities.components]

        # Find component IDs matching source
        source_ids: set[str] = set()
        for comp in model.entities.components:
            if _name_matches(source_name, [comp.name]):
                source_ids.add(comp.id)

        # Find component IDs matching target
        target_ids: set[str] = set()
        for comp in model.entities.components:
            if _name_matches(target_name, [comp.name]):
                target_ids.add(comp.id)

        if not source_ids or not target_ids:
            return False

        # Check if any relationship connects them
        for rel in model.relationships:
            if rel.from_id in source_ids and rel.to_id in target_ids:
                return True
            if rel.from_id in target_ids and rel.to_id in source_ids:
                return True

        return False

    def _compute_block_coverage(
        self, manifest: dict[str, Any], model: ArchitectureModel
    ) -> tuple[float, list[str]]:
        """Compute F-block coverage.

        For each F-block, check if a capability name matches.
        """
        blocks = manifest.get("functional_blocks", {})
        if not blocks:
            return 1.0, []

        capability_names = [c.name for c in model.entities.capabilities]

        covered = 0
        uncovered: list[str] = []

        for block_id, block_def in blocks.items():
            block_name = block_def.get("name", "")
            if _name_matches(block_name, capability_names):
                covered += 1
            else:
                uncovered.append(block_id)

        return covered / len(blocks), uncovered
