"""Reality Manifest Generator — modular package.

Public API:
    generate_manifest        — full AST scan of the project
    load_or_generate_manifest — cached generation with 1-hour TTL
    get_manifest_slice       — focused markdown slice for artifact injection
    print_summary            — terminal summary display
"""

from architecture_model.manifest.blocks import process_block
from architecture_model.manifest.display import print_summary
from architecture_model.manifest.generator import (
    generate_manifest,
    load_or_generate_manifest,
)
from architecture_model.manifest.interfaces import derive_interfaces
from architecture_model.manifest.metrics import compute_metrics
from architecture_model.manifest.scanner import scan_file
from architecture_model.manifest.slicers import get_manifest_slice
from architecture_model.manifest.types import (
    BlockManifest,
    ClassInfo,
    DecoratedFunction,
    FunctionInfo,
    ImportDetail,
    InterfaceEdge,
    Manifest,
    MetricsResult,
    ModuleInfo,
    ModuleStatus,
    ScanReport,
    SubFunctionEntry,
)

__all__ = [
    "generate_manifest",
    "load_or_generate_manifest",
    "get_manifest_slice",
    "print_summary",
    # Types
    "Manifest",
    "ScanReport",
    "ModuleInfo",
    "ModuleStatus",
    "FunctionInfo",
    "ClassInfo",
    "ImportDetail",
    "DecoratedFunction",
    "InterfaceEdge",
    "BlockManifest",
    "SubFunctionEntry",
    "MetricsResult",
    # Functions
    "scan_file",
    "derive_interfaces",
    "compute_metrics",
    "process_block",
]
