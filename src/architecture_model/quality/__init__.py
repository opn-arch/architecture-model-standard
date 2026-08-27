"""Unified quality subsystem — monitoring, confidence, coverage, regen readiness, code review, dashboard."""
from architecture_model.quality.monitoring import (
    FunctionMetrics, MetricsCollector, get_collector, monitored,
)
from architecture_model.quality.confidence import (
    compute_component_confidence, compute_model_confidence, model_confidence_summary,
)
from architecture_model.quality.coverage import coverage_report, CoverageResult
from architecture_model.quality.regen_readiness import compute_regen_readiness


def __getattr__(name: str):
    """Lazy imports to avoid circular dependency (dashboard → validator → monitoring → quality)."""
    _lazy = {
        "quality_report": ("architecture_model.quality.dashboard", "quality_report"),
        "QualityReport": ("architecture_model.quality.dashboard", "QualityReport"),
        "analyze_source": ("architecture_model.quality.code_review", "analyze_source"),
        "analyze_file": ("architecture_model.quality.code_review", "analyze_file"),
        "CodeAnalysis": ("architecture_model.quality.code_review", "CodeAnalysis"),
        "improve": ("architecture_model.quality.code_improver", "improve"),
        "ImprovementReport": ("architecture_model.quality.code_improver", "ImprovementReport"),
        "classify_suggestion": ("architecture_model.quality.code_safety", "classify_suggestion"),
        "SafetyLevel": ("architecture_model.quality.code_safety", "SafetyLevel"),
        "code_to_model_feedback": ("architecture_model.quality.model_feedback", "code_to_model_feedback"),
        "ModelFeedback": ("architecture_model.quality.model_feedback", "ModelFeedback"),
    }
    if name in _lazy:
        import importlib
        mod_name, attr = _lazy[name]
        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Monitoring
    "FunctionMetrics", "MetricsCollector", "get_collector", "monitored",
    # Confidence
    "compute_component_confidence", "compute_model_confidence", "model_confidence_summary",
    # Coverage
    "coverage_report", "CoverageResult",
    # Regen readiness
    "compute_regen_readiness",
    # Dashboard
    "quality_report", "QualityReport",
    # Code review
    "analyze_source", "analyze_file", "CodeAnalysis",
    # Code improvement
    "improve", "ImprovementReport",
    # Safety
    "classify_suggestion", "SafetyLevel",
    # Model feedback
    "code_to_model_feedback", "ModelFeedback",
]
