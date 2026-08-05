"""Language-agnostic source analysis protocol.

These types represent the MINIMUM data needed for hierarchical decomposition.
They can be populated by:
- Python AST scanner (automatic, via from_manifest)
- External tools (Madge for JS, go-callvis for Go)
- Agent reading code (any language)
- JSON ingestion via architect_ingest MCP tool

The hierarchical pipeline (grouping → fblocks → representativeness → interface
contracts) operates entirely on SourceGraph. Language-specific scanners produce
SourceGraph as their output format.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.manifest.types import Manifest


@dataclass
class ExportedSymbol:
    """A symbol exported by a source file."""

    name: str
    kind: str = "function"  # function | class | constant | type | interface
    signature: str = ""  # e.g. "(config: Config) -> Result"
    doc: str = ""  # first line of docstring


@dataclass
class SourceUnit:
    """Language-agnostic representation of a source file.

    This is the minimal unit for hierarchical decomposition.
    """

    file: str  # relative path from repo root
    has_content: bool = True  # False = trivial (re-export, empty, generated)
    exports: list[ExportedSymbol] = field(default_factory=list)
    language: str = ""  # python | typescript | go | rust | java | ""

    @property
    def export_names(self) -> list[str]:
        return [e.name for e in self.exports]


@dataclass
class DependencyEdge:
    """A directed dependency between two source files."""

    source: str  # source file path
    target: str  # target file path
    symbols: list[str] = field(default_factory=list)  # which symbols are imported


@dataclass
class SourceGraph:
    """Complete source-level understanding of a repository.

    This is the language-agnostic equivalent of Manifest.
    Can be produced by any scanner or by the agent directly.
    """

    units: list[SourceUnit] = field(default_factory=list)
    edges: list[DependencyEdge] = field(default_factory=list)
    root: str = ""  # repository root path
    language: str = ""  # primary language

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> SourceGraph:
        """Parse from JSON (agent or tool output).

        Accepts two JSON formats:
        - Canonical: {"units": [...], "edges": [...]}
        - Shorthand: {"files": [...], "dependencies": [...]}

        Each file/unit can have exports as strings or dicts:
        - String: just the name (assumes function)
        - Dict: {"name": "x", "kind": "class", "signature": "..."}
        """
        units = []
        for u in data.get("units", data.get("files", [])):
            exports = []
            for e in u.get("exports", []):
                if isinstance(e, str):
                    exports.append(ExportedSymbol(name=e))
                elif isinstance(e, dict):
                    exports.append(ExportedSymbol(
                        name=e["name"],
                        kind=e.get("kind", "function"),
                        signature=e.get("signature", ""),
                        doc=e.get("doc", ""),
                    ))
            units.append(SourceUnit(
                file=u["file"],
                has_content=u.get("has_content", True),
                exports=exports,
                language=u.get("language", data.get("language", "")),
            ))

        edges = []
        for e in data.get("edges", data.get("dependencies", [])):
            if isinstance(e, dict):
                edges.append(DependencyEdge(
                    source=e["source"],
                    target=e["target"],
                    symbols=e.get("symbols", []),
                ))
            elif isinstance(e, (list, tuple)) and len(e) >= 2:
                edges.append(DependencyEdge(source=e[0], target=e[1]))

        return cls(
            units=units,
            edges=edges,
            root=data.get("root", ""),
            language=data.get("language", ""),
        )

    @classmethod
    def from_manifest(cls, manifest: "Manifest") -> SourceGraph:
        """Convert a Python Manifest to a SourceGraph.

        This is the bridge between the existing Python AST scanner
        and the language-agnostic protocol.
        """
        units = []
        for m in manifest.modules:
            exports = []
            for f in m.functions:
                if not f.name.startswith("_"):
                    exports.append(ExportedSymbol(
                        name=f.name,
                        kind="function",
                        signature=f.signature or "",
                        doc=(f.docstring or "").split("\n")[0] if f.docstring else "",
                    ))
            for c in m.classes:
                if not c.name.startswith("_"):
                    # Try to get __init__ signature from method_details
                    init_sig = ""
                    for md in getattr(c, "method_details", []) or []:
                        if md.name == "__init__":
                            init_sig = md.signature or ""
                            break
                    exports.append(ExportedSymbol(
                        name=c.name,
                        kind="class",
                        signature=init_sig,
                    ))
            units.append(SourceUnit(
                file=m.file,
                has_content=bool(m.functions or m.classes),
                exports=exports,
                language="python",
            ))

        edges = [
            DependencyEdge(source=e.source, target=e.target, symbols=[])
            for e in manifest.interfaces
        ]
        return cls(units=units, edges=edges, language="python")

    def to_json(self) -> dict[str, Any]:
        """Serialize to JSON for persistence or transport."""
        return {
            "root": self.root,
            "language": self.language,
            "units": [
                {
                    "file": u.file,
                    "has_content": u.has_content,
                    "language": u.language,
                    "exports": [
                        {"name": e.name, "kind": e.kind, "signature": e.signature, "doc": e.doc}
                        for e in u.exports
                    ],
                }
                for u in self.units
            ],
            "edges": [
                {"source": e.source, "target": e.target, "symbols": e.symbols}
                for e in self.edges
            ],
        }
