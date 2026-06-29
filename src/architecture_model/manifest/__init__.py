"""Reality Manifest Generator — modular package.

Public API:
    generate_manifest        — full AST scan of the project
    load_or_generate_manifest — cached generation with 1-hour TTL
    get_manifest_slice       — focused markdown slice for artifact injection
    print_summary            — terminal summary display
"""

from architecture_model.manifest.display import print_summary
from architecture_model.manifest.generator import (
    generate_manifest,
    load_or_generate_manifest,
)
from architecture_model.manifest.slicers import get_manifest_slice

__all__ = [
    "generate_manifest",
    "load_or_generate_manifest",
    "get_manifest_slice",
    "print_summary",
]
