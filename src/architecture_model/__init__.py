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
]
