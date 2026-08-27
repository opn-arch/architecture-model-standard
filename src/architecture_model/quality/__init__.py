"""Unified quality subsystem — monitoring, confidence, coverage, regen readiness, dashboard."""
from architecture_model.quality.monitoring import (
    FunctionMetrics, MetricsCollector, get_collector, monitored,
)
from architecture_model.quality.confidence import (
    compute_component_confidence, compute_model_confidence, model_confidence_summary,
)
from architecture_model.quality.coverage import coverage_report, CoverageResult
from architecture_model.quality.regen_readiness import compute_regen_readiness

__all__ = [
    "FunctionMetrics", "MetricsCollector", "get_collector", "monitored",
    "compute_component_confidence", "compute_model_confidence", "model_confidence_summary",
    "coverage_report", "CoverageResult",
    "compute_regen_readiness",
]
