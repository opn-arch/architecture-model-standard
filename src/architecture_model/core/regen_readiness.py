"""Backward-compatible re-export. Canonical location: architecture_model.quality.regen_readiness"""
from architecture_model.quality.regen_readiness import *  # noqa: F401,F403
from architecture_model.quality.regen_readiness import (  # explicit re-exports for type checkers
    compute_regen_readiness,
    compute_component_readiness,
    compute_function_readiness,
    RegenReadiness,
    ComponentReadiness,
    FunctionReadiness,
    _is_trivial_hint,
    _classify_hint,
    _count_test_references,
)
