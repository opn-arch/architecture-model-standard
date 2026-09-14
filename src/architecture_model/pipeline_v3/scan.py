"""pipeline_v3.scan — Reality scan stage (T0.14 Phase 6.1).

Delegates AST scanning to the existing :mod:`architecture_model.manifest`
generator and lifts the result into a Promise-graph-friendly shape
(:class:`ScanResult` / :class:`ScannedModule`) with deterministic ordering.

This is intentionally a THIN bridge — the manifest module has full test
coverage of AST semantics; duplicating that work would create drift.
Later stages of pipeline_v3 consume the normalized shape without ever
touching Manifest / ModuleInfo directly, so any future replacement of
the scan backend is a local change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from architecture_model.manifest.generator import generate_manifest

__all__ = ["ScannedModule", "ScanResult", "scan_repo"]


@dataclass(frozen=True)
class ScannedModule:
    """A single Python module as seen by the scan stage.

    Attributes are the subset of ``ModuleInfo`` that downstream stages
    (derive_promises, cluster, link) consume. Functions and classes are
    kept as dicts (their raw :meth:`ModuleInfo.to_dict` form) so this
    module stays independent of the manifest type surface.
    """

    file: str
    name: str
    docstring: str | None
    functions: list[dict[str, Any]] = field(default_factory=list)
    classes: list[dict[str, Any]] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    line_count: int = 0


@dataclass(frozen=True)
class ScanResult:
    """Deterministic scan output for a repository."""

    source_root: Path
    modules: list[ScannedModule] = field(default_factory=list)

    @property
    def module_count(self) -> int:
        return len(self.modules)


def _dotted_name(file_str: str, repo_root: Path) -> str:
    """Derive a dotted Python module name from a repo-relative path.

    E.g. ``repo/pkg/core.py`` under repo root becomes ``pkg.core``;
    ``repo/pkg/__init__.py`` becomes ``pkg``. Bridges the gap between
    the manifest generator's human-friendly display name (e.g. "Core")
    and pipeline_v3's need for a stable, unambiguous module identifier.
    """
    p = Path(file_str)
    try:
        rel = p.resolve().relative_to(Path(repo_root).resolve())
    except ValueError:
        rel = p
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else p.stem


def _lift_module(mi: Any, repo_root: Path) -> ScannedModule:
    """Convert a :class:`ModuleInfo` to a :class:`ScannedModule`."""
    d = mi.to_dict()
    return ScannedModule(
        file=d["file"],
        name=_dotted_name(d["file"], repo_root),
        docstring=d.get("docstring"),
        functions=list(d.get("functions") or []),
        classes=list(d.get("classes") or []),
        imports=list(d.get("imports") or []),
        line_count=int(d.get("line_count") or 0),
    )


def scan_repo(repo_path: Path) -> ScanResult:
    """Scan ``repo_path`` and return a deterministic :class:`ScanResult`.

    Modules are sorted by dotted name. Test modules (files whose basename
    starts with ``test_``) are excluded — they are captured separately
    by the manifest ``tests`` field, not treated as first-class production
    modules for Promise derivation.
    """
    repo_root = Path(repo_path)
    manifest = generate_manifest(repo_root)
    lifted = [_lift_module(mi, repo_root) for mi in manifest.modules]
    # Exclude test modules by filename convention
    lifted = [m for m in lifted if not Path(m.file).name.startswith("test_")]
    lifted.sort(key=lambda m: m.name)
    return ScanResult(source_root=Path(repo_path), modules=lifted)
