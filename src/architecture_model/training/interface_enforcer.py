"""InterfaceEnforcer: inject manifest-derived dependency relationships into an ArchitectureModel.

The manifest (from AST scanning) typically has hundreds of import edges, but
LLM-generated models only cover a fraction. This class bridges the gap by
deterministically aggregating file-level imports into component-level
dependency edges and injecting any that are missing from the model.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from architecture_model.core.types import (
    ArchitectureModel,
    Relationship,
    RelationType,
    Strength,
)
from architecture_model.training.oracle_coverage import ManifestCoverageComputer


# Keywords in target function names that indicate an API-style interface.
_API_KEYWORDS = frozenset([
    "get", "post", "put", "delete", "send", "receive",
    "publish", "subscribe", "emit", "connect", "request",
    "fetch", "query", "execute", "call", "invoke",
])


@dataclass
class EnforcementResult:
    """Result of enforce(): the enriched model plus counters."""

    model: ArchitectureModel  # enriched model (original not mutated)
    added_count: int          # new relationships injected
    skipped_count: int        # skipped because relationship already existed
    internal_count: int       # skipped because both modules in same component


class InterfaceEnforcer:
    """Aggregate file-level imports into component edges and inject missing relationships."""

    def enforce(
        self, model: ArchitectureModel, manifest: dict[str, Any]
    ) -> EnforcementResult:
        """Inject missing dependency relationships derived from manifest imports.

        Args:
            model: The ArchitectureModel to enrich (not mutated).
            manifest: Reality Manifest dict with modules, interfaces, functional_blocks.

        Returns:
            EnforcementResult with enriched model copy and summary counters.
        """
        # 1. Reuse ManifestCoverageComputer's file->component mapping
        module_map = ManifestCoverageComputer()._build_module_component_map(manifest, model)

        # 2. Build file->module lookup for function-name access
        file_to_module: dict[str, dict] = {}
        for mod in manifest.get("modules", []):
            f = mod.get("file", "")
            if f:
                file_to_module[f] = mod

        # 3. Aggregate interfaces into component-level edges
        #    Key: (from_comp_id, to_comp_id) -> list of target files
        edge_targets: dict[tuple[str, str], list[str]] = {}
        edge_counts: dict[tuple[str, str], int] = {}
        internal_count = 0

        for iface in manifest.get("interfaces", []):
            src_file = iface.get("source", "")
            tgt_file = iface.get("target", "")
            src_comp = module_map.get(src_file, "")
            tgt_comp = module_map.get(tgt_file, "")

            if not src_comp or not tgt_comp:
                continue  # unmapped

            if src_comp == tgt_comp:
                internal_count += 1
                continue

            key = (src_comp, tgt_comp)
            edge_counts[key] = edge_counts.get(key, 0) + 1
            edge_targets.setdefault(key, []).append(tgt_file)

        # 4. Build set of existing related pairs (both directions)
        existing_pairs: set[tuple[str, str]] = set()
        for rel in model.relationships:
            existing_pairs.add((rel.from_id, rel.to_id))
            existing_pairs.add((rel.to_id, rel.from_id))

        # 5. For each new edge, infer type/strength and create Relationship
        new_rels: list[Relationship] = []
        skipped_count = 0

        for (from_id, to_id), count in edge_counts.items():
            if (from_id, to_id) in existing_pairs:
                skipped_count += 1
                continue

            # Collect target functions across all target files for this edge
            target_funcs: list[str] = []
            for tgt_file in edge_targets[(from_id, to_id)]:
                mod = file_to_module.get(tgt_file)
                if mod:
                    target_funcs.extend(mod.get("functions", []))

            # Check bidirectional
            is_bidirectional = (to_id, from_id) in edge_counts

            # Infer relationship type
            rel_type = self._infer_type(target_funcs, is_bidirectional)

            # Infer strength from edge count
            strength = self._infer_strength(count)

            new_rels.append(Relationship(
                type=rel_type,
                from_id=from_id,
                to_id=to_id,
                description="manifest-inferred dependency",
                strength=strength,
            ))

            # Mark this pair as existing so reverse isn't double-counted
            existing_pairs.add((from_id, to_id))
            existing_pairs.add((to_id, from_id))

        # 6. Build enriched model (do not mutate original)
        enriched = copy.deepcopy(model)
        enriched.relationships = list(model.relationships) + new_rels

        return EnforcementResult(
            model=enriched,
            added_count=len(new_rels),
            skipped_count=skipped_count,
            internal_count=internal_count,
        )

    @staticmethod
    def _infer_type(target_funcs: list[str], is_bidirectional: bool) -> RelationType:
        """Infer relationship type from target functions and directionality."""
        if is_bidirectional:
            return RelationType.DEPENDS_ON

        # Check for API-like function names
        for func_name in target_funcs:
            name_lower = func_name.lower()
            for kw in _API_KEYWORDS:
                if kw in name_lower:
                    return RelationType.CONSUMES

        return RelationType.DEPENDS_ON

    @staticmethod
    def _infer_strength(edge_count: int) -> Strength:
        """Infer coupling strength from number of import edges."""
        if edge_count >= 5:
            return Strength.STRONG
        if edge_count >= 2:
            return Strength.MODERATE
        return Strength.WEAK
