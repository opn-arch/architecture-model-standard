"""Typed dataclasses for manifest generation outputs.

Every function in the manifest pipeline should accept and return
typed objects, not raw dicts. This module defines those types.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ModuleStatus(str, Enum):
    """Status of a scanned module based on line count."""
    ACTIVE = "active"
    DORMANT = "dormant"
    MISSING = "missing"


@dataclass
class FunctionInfo:
    """A public function extracted from AST."""
    name: str
    signature: str
    calls: list[str] = field(default_factory=list)
    docstring: str | None = None
    raises: list[str] = field(default_factory=list)
    # Behavioral fields (populated by behavior.py extractors)
    call_order: list[str] = field(default_factory=list)
    control_flow: list[str] = field(default_factory=list)
    data_in: list[str] = field(default_factory=list)
    data_out: str = ""
    guards: list[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    """A class extracted from AST."""
    name: str
    bases: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    is_abstract: bool = False
    decorators: list[str] = field(default_factory=list)
    attributes: dict[str, str] = field(default_factory=dict)
    method_details: list[FunctionInfo] = field(default_factory=list)


@dataclass
class ImportDetail:
    """A detailed import statement."""
    module: str
    symbols: list[str] = field(default_factory=list)
    is_relative: bool = False


@dataclass
class DecoratedFunction:
    """A function with non-trivial decorators."""
    name: str
    decorators: list[str] = field(default_factory=list)
    is_method: bool = False
    class_name: str | None = None


@dataclass
class ModuleInfo:
    """Complete metadata for a single scanned Python file."""
    file: str
    name: str
    docstring: str | None
    functions: list[FunctionInfo]
    imports: list[str]
    line_count: int
    status: ModuleStatus
    classes: list[ClassInfo]
    exports: list[str] = field(default_factory=list)
    decorated_functions: list[DecoratedFunction] = field(default_factory=list)
    imports_detailed: list[ImportDetail] = field(default_factory=list)
    module_constants: dict[str, str] = field(default_factory=dict)
    module_assignments: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to legacy dict format for backward compatibility."""
        return {
            "file": self.file,
            "name": self.name,
            "docstring": self.docstring,
            "functions": [
                {
                    "name": f.name,
                    "signature": f.signature,
                    **({"calls": f.calls} if f.calls else {}),
                    **({"docstring": f.docstring} if f.docstring else {}),
                    **({"raises": f.raises} if f.raises else {}),
                }
                for f in self.functions
            ],
            "imports": self.imports,
            "line_count": self.line_count,
            "status": self.status.value,
            "classes": [
                {
                    "name": c.name, "bases": c.bases, "methods": c.methods,
                    "is_abstract": c.is_abstract, "decorators": c.decorators,
                    "attributes": c.attributes,
                }
                for c in self.classes
            ],
            "exports": self.exports,
            "decorated_functions": [
                {"name": d.name, "decorators": d.decorators,
                 "is_method": d.is_method, "class_name": d.class_name}
                for d in self.decorated_functions
            ],
            "imports_detailed": [
                {"module": i.module, "symbols": i.symbols, "is_relative": i.is_relative}
                for i in self.imports_detailed
            ],
            "module_constants": self.module_constants,
            "module_assignments": self.module_assignments,
        }


@dataclass
class InterfaceEdge:
    """A directed dependency between two modules."""
    source: str
    target: str
    import_path: str

    def to_dict(self) -> dict[str, str]:
        return {"source": self.source, "target": self.target, "import_path": self.import_path}


@dataclass
class SubFunctionEntry:
    """A file-level entry within a functional block."""
    id: str
    name: str
    file: str
    functions: list[str]
    inputs: list[str]
    outputs: list[str]
    status: str
    line_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "file": self.file,
            "functions": self.functions, "inputs": self.inputs,
            "outputs": self.outputs, "status": self.status,
            "line_count": self.line_count,
        }


@dataclass
class BlockManifest:
    """Manifest data for a single functional block."""
    name: str
    status: str
    description_source: str
    sub_functions: list[SubFunctionEntry] = field(default_factory=list)
    sub_blocks: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "status": self.status,
            "description_source": self.description_source,
            "sub_functions": [sf.to_dict() for sf in self.sub_functions],
            "sub_blocks": self.sub_blocks,
        }


@dataclass
class MetricsResult:
    """Project-level metrics from glob counting."""
    values: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, int]:
        return dict(self.values)


@dataclass
class ScanReport:
    """Observability report for a manifest scan operation."""
    files_attempted: int = 0
    files_succeeded: int = 0
    files_failed: int = 0
    parse_errors: list[str] = field(default_factory=list)
    functions_extracted: int = 0
    classes_extracted: int = 0
    constants_extracted: int = 0
    interfaces_derived: int = 0
    blocks_processed: int = 0
    unclaimed_files: int = 0

    @property
    def success_rate(self) -> float:
        if self.files_attempted == 0:
            return 1.0
        return self.files_succeeded / self.files_attempted

    def log_summary(self) -> None:
        logger.info(
            "Scan complete: %d/%d files (%.1f%%), %d funcs, %d classes, "
            "%d constants, %d interfaces, %d blocks, %d unclaimed, %d errors",
            self.files_succeeded, self.files_attempted, self.success_rate * 100,
            self.functions_extracted, self.classes_extracted,
            self.constants_extracted, self.interfaces_derived,
            self.blocks_processed, self.unclaimed_files, len(self.parse_errors),
        )


@dataclass
class Manifest:
    """Complete reality manifest with typed fields and observability."""
    generated_at: str
    project_root: str
    metrics: MetricsResult
    functional_blocks: dict[str, BlockManifest]
    modules: list[ModuleInfo]
    interfaces: list[InterfaceEdge]
    scan_report: ScanReport = field(default_factory=ScanReport)

    def to_dict(self) -> dict[str, Any]:
        """Convert to legacy dict format for JSON serialization."""
        return {
            "generated_at": self.generated_at,
            "project_root": self.project_root,
            "metrics": self.metrics.to_dict(),
            "functional_blocks": {k: v.to_dict() for k, v in self.functional_blocks.items()},
            "modules": [m.to_dict() for m in self.modules],
            "interfaces": [i.to_dict() for i in self.interfaces],
        }


@dataclass
class RecursiveManifest:
    """A manifest scoped to a single F-block / sub-system.
    
    Links to its parent model via parent_model path and component_id.
    Can contain child RecursiveManifests for deeper decomposition.
    """
    block_id: str
    block_name: str
    parent_model: str
    component_id: str
    manifest: Manifest
    children: dict[str, 'RecursiveManifest'] = field(default_factory=dict)
    block_dependencies: list[str] = field(default_factory=list)
    intra_chains: list[Any] = field(default_factory=list)  # list[EventChain]

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "block_name": self.block_name,
            "parent_model": self.parent_model,
            "component_id": self.component_id,
            "manifest": self.manifest.to_dict(),
            "children": {k: v.to_dict() for k, v in self.children.items()},
            "block_dependencies": self.block_dependencies,
            "intra_chains": [
                {"trigger": c.trigger, "steps": c.steps, "components_involved": c.components_involved}
                for c in self.intra_chains
            ],
        }
