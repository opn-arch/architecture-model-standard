"""Propagate enrichment data from sub-models to root model."""
import copy
from architecture_model.core.types import ArchitectureModel


def propagate_enrichment(root: ArchitectureModel, sub_models: list[ArchitectureModel]) -> ArchitectureModel:
    """Copy signatures, constants, test_contracts from sub-model components to root."""
    updated = copy.deepcopy(root)
    comp_map = {c.id: c for c in updated.entities.components}

    for sub in sub_models:
        parent_id = sub.meta.refines_component
        if not parent_id or parent_id not in comp_map:
            continue
        parent = comp_map[parent_id]
        for sub_comp in sub.entities.components:
            parent.signatures.extend(sub_comp.signatures)
            parent.test_contracts.extend(sub_comp.test_contracts)
            parent.constants.extend(sub_comp.constants)

    return updated
