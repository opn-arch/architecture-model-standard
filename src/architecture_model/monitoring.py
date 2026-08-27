"""Backward-compatible re-export. Canonical location: architecture_model.quality.monitoring"""
from architecture_model.quality.monitoring import *  # noqa: F401,F403
from architecture_model.quality.monitoring import (  # explicit re-exports for type checkers
    FunctionMetrics, MetricsCollector, get_collector, monitored,
)
