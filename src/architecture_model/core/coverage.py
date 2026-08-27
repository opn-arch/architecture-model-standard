"""Backward-compatible re-export. Canonical location: architecture_model.quality.coverage"""
from architecture_model.quality.coverage import *  # noqa: F401,F403
from architecture_model.quality.coverage import (  # explicit re-exports for type checkers
    CoverageCheck,
    CoverageResult,
    coverage_report,
    _check_component_coverage,
    _check_relationship_accuracy,
    _check_relationship_accuracy_legacy,
    _check_dependency_accuracy,
    _check_capability_coverage,
    _check_interface_coverage,
    _check_staleness,
    _check_source_block_quality,
    _check_requirement_traceability,
)
