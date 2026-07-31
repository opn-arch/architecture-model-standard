"""
Architecture Model Standard — universal machine-readable architectural spine.

This package implements a YAML-based architecture model that serves as the
single source of architectural truth for LLM-driven system engineering.

Entity Types: actors, capabilities, behaviors, interfaces, constraints, layers, components
Relationship Types: realizes, contains, depends-on, exposes, consumes, traces-to, allocated-to, constrained-by
"""

__version__ = "0.4.0"

from architecture_model.core.parser import load_model
from architecture_model.core.validator import validate_model
from architecture_model.manifest.generator import generate_manifest
from architecture_model.core.slicer import slice_by_fblock, slice_by_layer
from architecture_model.core.test_affinity import test_affinity_decompose
from architecture_model.core.merger import compose_enriched_model
from architecture_model.core.coverage import coverage_report
from architecture_model.orchestration.pipeline import run_pipeline
from architecture_model.patterns import load_patterns, get_pattern
from architecture_model.orchestration.enrichment_context import format_enrichment_prompt
from architecture_model.orchestration.auto_enrich import enrich_from_manifest
from architecture_model.monitoring import FunctionMetrics, MetricsCollector, get_collector, monitored
from architecture_model.core.confidence import (
    compute_component_confidence,
    compute_behavior_confidence,
    compute_capability_confidence,
    compute_interface_confidence,
    compute_function_confidence,
    compute_model_confidence,
    aggregate_block_confidence,
    model_confidence_summary,
)
from architecture_model.monitoring_checks import (
    check_decompose_idempotency,
    check_cluster_stability,
    check_pattern_indicators,
    ConsistencyResult,
)

__all__ = [
    "__version__",
    "load_model",
    "validate_model",
    "generate_manifest",
    "slice_by_fblock",
    "slice_by_layer",
    "test_affinity_decompose",
    "compose_enriched_model",
    "coverage_report",
    "run_pipeline",
    "load_patterns",
    "get_pattern",
    "format_enrichment_prompt",
    "enrich_from_manifest",
    "FunctionMetrics",
    "MetricsCollector",
    "get_collector",
    "monitored",
    "check_decompose_idempotency",
    "check_cluster_stability",
    "check_pattern_indicators",
    "ConsistencyResult",
    "compute_component_confidence",
    "compute_behavior_confidence",
    "compute_capability_confidence",
    "compute_interface_confidence",
    "compute_function_confidence",
    "compute_model_confidence",
    "aggregate_block_confidence",
    "model_confidence_summary",
]
