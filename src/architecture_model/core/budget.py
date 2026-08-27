"""Token estimation and budget-aware model reduction."""
import copy
from architecture_model.core.types import ArchitectureModel
from architecture_model.monitoring import monitored


@monitored("core.budget")
def estimate_tokens(model: ArchitectureModel) -> int:
    """Estimate token count from YAML serialization. ~4 chars per token."""
    yaml_str = model.to_yaml()
    return len(yaml_str) // 4


@monitored("core.budget")
def reduce_to_budget(model: ArchitectureModel, max_tokens: int) -> ArchitectureModel:
    """Progressively reduce model detail to fit within token budget.

    Reduction order (least valuable first):
    1. Drop body_hint from signatures
    2. Drop test_contracts
    3. Truncate signatures to top-N
    4. Truncate descriptions to 100 chars
    5. Drop constants
    """
    reduced = copy.deepcopy(model)
    if estimate_tokens(reduced) <= max_tokens:
        return reduced

    # Phase 1: Drop body_hints
    for comp in reduced.entities.components:
        for sig in comp.signatures:
            sig.body_hint = ""
    if estimate_tokens(reduced) <= max_tokens:
        return reduced

    # Phase 2: Drop test_contracts
    for comp in reduced.entities.components:
        comp.test_contracts = []
    if estimate_tokens(reduced) <= max_tokens:
        return reduced

    # Phase 3: Truncate signatures to top 10
    for comp in reduced.entities.components:
        comp.signatures = comp.signatures[:10]
    if estimate_tokens(reduced) <= max_tokens:
        return reduced

    # Phase 4: Truncate descriptions
    for comp in reduced.entities.components:
        if len(comp.description) > 100:
            comp.description = comp.description[:100] + "..."
    if estimate_tokens(reduced) <= max_tokens:
        return reduced

    # Phase 5: Drop constants
    for comp in reduced.entities.components:
        comp.constants = []

    return reduced
