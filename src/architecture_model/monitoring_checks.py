"""Backward-compatible re-export. Canonical location: architecture_model.quality.monitoring_checks"""
from architecture_model.quality.monitoring_checks import *  # noqa: F401,F403
from architecture_model.quality.monitoring_checks import (  # explicit re-exports for type checkers
    ConsistencyResult,
    check_decompose_idempotency,
    check_cluster_stability,
    check_pattern_indicators,
)
