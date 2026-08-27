"""Output types for the observe pipeline stage.

These types represent the raw factual inventory of a codebase —
zero inference, pure observation from AST scanning and config parsing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FunctionRecord:
    name: str
    signature: str
    body_hint: str
    calls: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    docstring: str | None = None
    line_number: int = 0


@dataclass
class ClassRecord:
    name: str
    bases: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    method_details: list[FunctionRecord] = field(default_factory=list)
    attributes: dict[str, str] = field(default_factory=dict)
    decorators: list[str] = field(default_factory=list)
    is_abstract: bool = False


@dataclass
class ConstantRecord:
    name: str
    value: str
    type: str = ""
    context: str = ""  # class name if class-level


@dataclass
class ImportEdge:
    source: Path
    target: Path
    symbols: list[str] = field(default_factory=list)


@dataclass
class RouteRecord:
    method: str
    path: str
    function_name: str
    file: Path
    docstring: str = ""
    is_authenticated: bool = False
    framework: str = ""


@dataclass
class ConstraintRecord:
    name: str
    value: str
    source: str  # file path where discovered
    constraint_type: str = ""  # "technology" | "version" | "timeout" | ...


@dataclass
class TestFileRecord:
    path: Path
    targets: list[str] = field(default_factory=list)  # module names this tests


@dataclass
class DocRecord:
    path: Path
    title: str = ""
    summary: str = ""  # first paragraph


@dataclass
class ModuleRecord:
    path: Path
    language: str = "python"
    functions: list[FunctionRecord] = field(default_factory=list)
    classes: list[ClassRecord] = field(default_factory=list)
    constants: list[ConstantRecord] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    line_count: int = 0
    docstring: str | None = None
    quality_score: int = 0  # 0-100 from code_review.analyze_source


@dataclass
class Inventory:
    """Complete factual record of a codebase. Zero inference."""
    modules: list[ModuleRecord] = field(default_factory=list)
    edges: list[ImportEdge] = field(default_factory=list)
    routes: list[RouteRecord] = field(default_factory=list)
    constraints: list[ConstraintRecord] = field(default_factory=list)
    test_files: list[TestFileRecord] = field(default_factory=list)
    docs: list[DocRecord] = field(default_factory=list)
