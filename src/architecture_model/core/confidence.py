"""Backward-compatible re-export. Canonical location: architecture_model.quality.confidence"""
from architecture_model.quality.confidence import *  # noqa: F401,F403
from architecture_model.quality.confidence import (  # explicit re-exports for type checkers
    compute_component_confidence,
    compute_model_confidence,
    model_confidence_summary,
    compute_behavior_confidence,
    compute_capability_confidence,
    compute_interface_confidence,
    aggregate_block_confidence,
    compute_function_confidence,
)
