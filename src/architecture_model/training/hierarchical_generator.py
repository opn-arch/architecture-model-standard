"""Hierarchical code generation: decompose → per-system generate → stitch."""

from __future__ import annotations

import yaml
from typing import Optional

from architecture_model.core.decomposer import DecompositionResult, decompose_model
from architecture_model.core.merger import compact_for_generation
from architecture_model.core.parser import dump_model
from architecture_model.training.surrogate import Surrogate


class HierarchicalGenerator:
    """Generates code from a decomposed model by processing each system independently.

    For repos that exceed the 7B model's effective context:
    1. Decompose into systems (each 3-5 components)
    2. Generate code per system independently
    3. Stitch results together

    Falls back to single-call generation for simple models (no systems).
    """

    def __init__(self, surrogate: Surrogate) -> None:
        self._surrogate = surrogate

    async def generate(self, decomposition: DecompositionResult) -> str:
        """Generate code from a decomposed model.

        For each system: serialize sub-model → generate_code() → collect.
        For remaining top-level components: serialize → generate_code() → collect.
        Returns concatenated code from all parts.
        """
        parts: list[str] = []

        # Generate code for each system's sub-model
        for sys in decomposition.top_level.entities.systems:
            sub_model = decomposition.sub_models.get(sys.id)
            if sub_model is None:
                continue

            # Compact and serialize the sub-model
            compacted = compact_for_generation(sub_model)
            sub_dict = dump_model(compacted)
            sub_yaml = yaml.dump(sub_dict, default_flow_style=False, sort_keys=False, allow_unicode=True)

            # Generate code for this system
            code = await self._surrogate.generate_code(sub_yaml)
            if code:
                parts.append(f"# === System: {sys.name} ===\n{code}")

        # Generate code for remaining top-level components (if any)
        if decomposition.top_level.entities.components:
            # Build a mini-model with just the remaining components
            from architecture_model.core.types import ArchitectureModel, Entities

            remainder = ArchitectureModel(
                meta=decomposition.top_level.meta,
                entities=Entities(components=decomposition.top_level.entities.components),
                relationships=[
                    r for r in decomposition.top_level.relationships
                    if not any(
                        r.from_id == s.id or r.to_id == s.id
                        for s in decomposition.top_level.entities.systems
                    )
                ],
            )
            compacted = compact_for_generation(remainder)
            rem_dict = dump_model(compacted)
            rem_yaml = yaml.dump(rem_dict, default_flow_style=False, sort_keys=False, allow_unicode=True)

            code = await self._surrogate.generate_code(rem_yaml)
            if code:
                parts.append(code)

        return "\n\n".join(parts)

    async def generate_from_model(
        self,
        model: 'ArchitectureModel',
        manifest: dict,
    ) -> str:
        """Convenience: decompose model then generate hierarchically.

        If the model doesn't need decomposition (no systems identified),
        falls back to standard single-call generation.
        """
        from architecture_model.core.types import ArchitectureModel

        decomposition = decompose_model(model, manifest)

        if not decomposition.top_level.entities.systems:
            # No systems — fall back to single-call generation
            compacted = compact_for_generation(model)
            model_dict = dump_model(compacted)
            model_yaml = yaml.dump(model_dict, default_flow_style=False, sort_keys=False, allow_unicode=True)
            return await self._surrogate.generate_code(model_yaml)

        return await self.generate(decomposition)
