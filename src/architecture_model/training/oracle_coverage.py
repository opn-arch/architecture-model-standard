"""
ManifestCoverageComputer: measures how well an ArchitectureModel covers a Reality Manifest.

This is the core learning signal for the oracle self-learning loop.

The fundamental challenge: manifest module names (from docstrings, e.g. "Annotated handlers")
live at a different abstraction level than model component names (architectural, e.g.
"Validation Engine"). Pure name matching fails here.

Instead we use a multi-strategy approach:
1. File-path matching: component.files contains the module's file path
2. Path-word overlap: component name words appear in the module's file path segments
3. Layer directory coverage: module's directory falls under a layer's directories
4. Responsibility matching: module functions/name appear in component responsibilities/description

Coverage is significance-weighted by LOC for modules.
Interface coverage checks structural preservation: if A imports B in manifest,
do the covering components have a relationship?
Block coverage matches F-blocks to capabilities OR layers.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from architecture_model.core.types import ArchitectureModel, RelationType


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
# Name/path matching helpers
# ---------------------------------------------------------------------------

_SPLIT_RE = re.compile(r"[-_\s./()]+")
_CAMEL_RE = re.compile(r"(?<=[a-z])(?=[A-Z])")


def _tokenize(name: str) -> set[str]:
    """Split a name into lowercase word tokens, handling camelCase too."""
    # First split on camelCase boundaries
    expanded = _CAMEL_RE.sub(" ", name)
    return {t.lower() for t in _SPLIT_RE.split(expanded) if t and len(t) > 1}


def _path_tokens(filepath: str) -> set[str]:
    """Extract meaningful tokens from a file path."""
    # Remove extension
    stem = os.path.splitext(filepath)[0]
    # Split on path separators and word boundaries
    parts = PurePosixPath(stem).parts
    tokens: set[str] = set()
    for part in parts:
        # Skip generic dirs like 'src', 'lib', 'tests'
        if part in ("src", "lib", "tests", "test", "__pycache__"):
            continue
        tokens.update(_tokenize(part))
    return tokens


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
    """Check if name matches any candidate via exact, containment, or word Jaccard.

    For short names (1-2 tokens), uses subset containment: if ALL name tokens
    appear in the candidate, it's a match. This handles "Internal" matching
    "Internal Implementation Layer".
    """
    name_lower = name.lower().strip()
    name_tokens = _tokenize(name)

    for candidate in candidates:
        candidate_lower = candidate.lower().strip()
        # Exact match
        if name_lower == candidate_lower:
            return True
        # Containment: short name's tokens are all in candidate
        if name_tokens and len(name_tokens) <= 2:
            candidate_tokens = _tokenize(candidate)
            if name_tokens <= candidate_tokens:  # subset check
                return True
        # Word Jaccard
        if _word_jaccard(name, candidate) >= threshold:
            return True
    return False


# ---------------------------------------------------------------------------
# ManifestCoverageComputer
# ---------------------------------------------------------------------------


class ManifestCoverageComputer:
    """Computes how well an ArchitectureModel covers a Reality Manifest.

    Uses multi-strategy matching to bridge the abstraction gap between
    file-level manifest data and architectural model components.
    """

    # Minimum line count for a module to be considered significant
    MIN_LOC_THRESHOLD: int = 10

    # Weights for overall score
    MODULE_WEIGHT: float = 0.5
    INTERFACE_WEIGHT: float = 0.3
    BLOCK_WEIGHT: float = 0.2

    # Matching thresholds
    PATH_OVERLAP_THRESHOLD: float = 0.3  # min word overlap for path matching
    NAME_MATCH_THRESHOLD: float = 0.4    # min Jaccard for name matching

    def compute(self, manifest: dict[str, Any], model: ArchitectureModel) -> CoverageResult:
        """Compute coverage of manifest by the architecture model.

        Args:
            manifest: Reality Manifest dict with modules, interfaces, functional_blocks.
            model: The ArchitectureModel to evaluate.

        Returns:
            CoverageResult with per-dimension scores and uncovered items.
        """
        # Build the module→component mapping (the foundation for all coverage checks)
        module_map = self._build_module_component_map(manifest, model)

        module_cov, uncov_modules = self._compute_module_coverage(manifest, model, module_map)
        iface_cov, uncov_ifaces = self._compute_interface_coverage(manifest, model, module_map)
        block_cov, uncov_blocks = self._compute_block_coverage(manifest, model)

        # Overall weighted score
        has_modules = bool(manifest.get("modules"))
        has_interfaces = bool(manifest.get("interfaces"))
        has_blocks = bool(manifest.get("functional_blocks"))

        if not has_modules and not has_interfaces and not has_blocks:
            overall = 1.0
        else:
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

    # -----------------------------------------------------------------------
    # Module→Component Mapping (multi-strategy)
    # -----------------------------------------------------------------------

    def _build_module_component_map(
        self, manifest: dict[str, Any], model: ArchitectureModel
    ) -> dict[str, str]:
        """Map each manifest module file to a covering component ID.

        Strategies (tried in order, first match wins):
        1. Explicit: component.files contains the module file path
        2. Path-word overlap: component name tokens overlap with file path tokens
        3. Layer directory: module's directory falls under a layer's directories,
           and the component belongs to that layer
        4. Name match: module name matches component name (legacy, for backwards compat)

        Returns:
            Dict mapping module file path → component ID (empty string if uncovered).
        """
        modules = manifest.get("modules", [])
        components = model.entities.components

        # Precompute component data
        comp_files: dict[str, set[str]] = {}  # comp_id -> set of file paths
        comp_name_tokens: dict[str, set[str]] = {}  # comp_id -> name word tokens
        comp_resp_tokens: dict[str, set[str]] = {}  # comp_id -> responsibility tokens

        for comp in components:
            comp_files[comp.id] = {f.lower() for f in (comp.files or [])}
            comp_name_tokens[comp.id] = _tokenize(comp.name)
            # Also include description words
            resp_words = _tokenize(comp.description) if comp.description else set()
            for r in (comp.responsibilities or []):
                resp_words.update(_tokenize(r))
            comp_resp_tokens[comp.id] = resp_words

        # Layer directory mapping
        layer_dirs: dict[str, list[str]] = {}  # layer_id -> list of directory prefixes
        for layer in model.entities.layers:
            layer_dirs[layer.id] = [d.lower().rstrip("/") for d in (layer.directories or [])]

        # Layer→component mapping (via .layer field AND relationships)
        layer_to_comps: dict[str, set[str]] = {}
        for comp in components:
            if comp.layer:
                layer_to_comps.setdefault(comp.layer, set()).add(comp.id)
        for rel in model.relationships:
            if rel.type in (RelationType.CONTAINS, RelationType.ALLOCATED_TO):
                if rel.from_id in layer_dirs:
                    layer_to_comps.setdefault(rel.from_id, set()).add(rel.to_id)

        # Map each module
        mapping: dict[str, str] = {}

        for mod in modules:
            file_path = mod.get("file", "")
            if not file_path:
                continue

            file_lower = file_path.lower()
            covered_by = ""

            # Strategy 1: Explicit file listing
            for comp_id, files in comp_files.items():
                if file_lower in files or file_path in files:
                    covered_by = comp_id
                    break
                # Also check if any listed file is a prefix/match
                for f in files:
                    if file_lower.endswith(f) or f.endswith(file_lower):
                        covered_by = comp_id
                        break
                if covered_by:
                    break

            # Strategy 2: Path-word overlap with component name
            if not covered_by:
                path_toks = _path_tokens(file_path)
                if path_toks:
                    best_overlap = 0.0
                    best_comp = ""
                    for comp_id, name_toks in comp_name_tokens.items():
                        if not name_toks:
                            continue
                        overlap = len(path_toks & name_toks) / len(name_toks)
                        if overlap > best_overlap:
                            best_overlap = overlap
                            best_comp = comp_id
                    # Also check responsibilities
                    for comp_id, resp_toks in comp_resp_tokens.items():
                        if not resp_toks:
                            continue
                        overlap = len(path_toks & resp_toks) / min(len(path_toks), len(resp_toks))
                        if overlap > best_overlap:
                            best_overlap = overlap
                            best_comp = comp_id

                    if best_overlap >= self.PATH_OVERLAP_THRESHOLD:
                        covered_by = best_comp

            # Strategy 3: Layer directory containment
            if not covered_by:
                file_dir = str(PurePosixPath(file_lower).parent)
                for layer_id, dirs in layer_dirs.items():
                    for d in dirs:
                        if file_dir.startswith(d) or file_dir == d:
                            # File is under this layer's directory
                            # Assign to any component in this layer
                            comps_in_layer = layer_to_comps.get(layer_id, set())
                            if comps_in_layer:
                                covered_by = next(iter(comps_in_layer))
                                break
                    if covered_by:
                        break

            # Strategy 4: Name matching (legacy fallback)
            if not covered_by:
                mod_name = mod.get("name", "")
                if mod_name:
                    comp_names = [c.name for c in components]
                    if _name_matches(mod_name, comp_names, self.NAME_MATCH_THRESHOLD):
                        # Find which component matched
                        for comp in components:
                            if _name_matches(mod_name, [comp.name], self.NAME_MATCH_THRESHOLD):
                                covered_by = comp.id
                                break

            mapping[file_path] = covered_by

        return mapping

    # -----------------------------------------------------------------------
    # Module Coverage
    # -----------------------------------------------------------------------

    def _compute_module_coverage(
        self, manifest: dict[str, Any], model: ArchitectureModel,
        module_map: dict[str, str]
    ) -> tuple[float, list[str]]:
        """Compute LOC-weighted module coverage using the module→component map."""
        modules = manifest.get("modules", [])

        total_loc = 0
        covered_loc = 0
        uncovered: list[str] = []

        for mod in modules:
            loc = mod.get("line_count", 0)
            if loc < self.MIN_LOC_THRESHOLD:
                continue

            total_loc += loc
            file_path = mod.get("file", "")

            if module_map.get(file_path):
                covered_loc += loc
            else:
                uncovered.append(file_path)

        if total_loc == 0:
            return 1.0, []

        return covered_loc / total_loc, uncovered

    # -----------------------------------------------------------------------
    # Interface Coverage (structural graph preservation)
    # -----------------------------------------------------------------------

    def _compute_interface_coverage(
        self, manifest: dict[str, Any], model: ArchitectureModel,
        module_map: dict[str, str]
    ) -> tuple[float, list[tuple[str, str]]]:
        """Compute interface coverage via structural graph preservation.

        For each import edge (A→B) in the manifest, check if the components
        covering module A and module B have any relationship between them
        (in either direction). This tests structural preservation rather than
        name matching.
        """
        interfaces = manifest.get("interfaces", [])
        if not interfaces:
            return 1.0, []

        # Build set of component pairs that have relationships
        related_pairs: set[tuple[str, str]] = set()
        for rel in model.relationships:
            related_pairs.add((rel.from_id, rel.to_id))
            related_pairs.add((rel.to_id, rel.from_id))  # bidirectional check

        covered = 0
        uncovered: list[tuple[str, str]] = []

        for iface in interfaces:
            source_file = iface.get("source", "")
            target_file = iface.get("target", "")

            source_comp = module_map.get(source_file, "")
            target_comp = module_map.get(target_file, "")

            if not source_comp or not target_comp:
                # If either module is uncovered, the edge is uncovered
                uncovered.append((source_file, target_file))
                continue

            if source_comp == target_comp:
                # Same component covers both — internal dependency, counts as covered
                covered += 1
            elif (source_comp, target_comp) in related_pairs:
                covered += 1
            else:
                uncovered.append((source_file, target_file))

        return covered / len(interfaces), uncovered

    # -----------------------------------------------------------------------
    # Block Coverage
    # -----------------------------------------------------------------------

    def _compute_block_coverage(
        self, manifest: dict[str, Any], model: ArchitectureModel
    ) -> tuple[float, list[str]]:
        """Compute F-block coverage.

        F-blocks (directory groups) should map to either capabilities OR layers
        in the model. We check both.
        """
        blocks = manifest.get("functional_blocks", {})
        if not blocks:
            return 1.0, []

        # Candidates: capability names + layer names
        candidate_names = (
            [c.name for c in model.entities.capabilities] +
            [l.name for l in model.entities.layers]
        )

        covered = 0
        uncovered: list[str] = []

        for block_id, block_def in blocks.items():
            block_name = block_def.get("name", "")
            if _name_matches(block_name, candidate_names, self.NAME_MATCH_THRESHOLD):
                covered += 1
            else:
                uncovered.append(block_id)

        return covered / len(blocks), uncovered
