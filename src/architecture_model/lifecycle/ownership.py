"""Canonical package ownership + shared-file declarations.

Purpose
-------
Every source file in an architecture package tree must have a single
canonical owner package. This module computes the mapping from file paths
to owner ``architecture_id`` s, enforces that overlap is only permitted
when explicitly declared via ``shared_paths``, and records
slug-remap provenance so renames remain auditable.

Key rules
---------
* A file is "claimed" by a package when it matches any pattern in that
  package's ``owned_paths``. Patterns are POSIX-style globs interpreted
  via :func:`fnmatch.fnmatchcase`, applied to the file's path *relative
  to the claiming package's own root* (not the source root).
* If multiple packages claim the same file, the overlap is legal only
  when at least one of them declares a matching ``shared_paths`` entry
  whose ``owners`` set exactly equals the claimants. Any other overlap
  is a conflict.
* Files matched by no ``owned_paths`` pattern are recorded as
  ``unowned``. Callers decide whether that's an error.

Invariants
----------
* Deterministic output: ``files`` is sorted lexicographically by path;
  ``conflicts`` and ``unowned`` are also sorted by path. Two runs on the
  same tree return identical results.
* No filesystem writes except from :func:`record_remap`. Ownership
  computation is a pure read of the on-disk tree.

Excluded from the walk (never appear in ``files`` or ``unowned``):
    * any directory named ``__pycache__``
    * any directory whose name starts with ``.`` (covers ``.git``,
      ``.architecture``, ``.architecture-models`` and similar tool dirs)
    * any file with the ``.pyc`` suffix
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable

import yaml

from architecture_model.lifecycle.atomic_store import write_atomic
from architecture_model.lifecycle.package import (
    ArchitecturePackage,
    iter_descendants,
)
from architecture_model.lifecycle.serialization import canonical_yaml_load

__all__ = [
    "FileOwnership",
    "OwnershipMap",
    "OwnershipError",
    "OwnershipConflict",
    "UnownedFile",
    "compute_ownership",
    "assert_no_conflicts",
    "record_remap",
    "load_remaps",
]


@dataclass(frozen=True)
class FileOwnership:
    """Ownership record for a single file.

    ``path`` is POSIX-style, relative to the source root. ``owners`` is a
    sorted tuple of ``architecture_id`` s. ``shared`` is True only when
    multiple owners are legitimized by a matching ``shared_paths`` entry.
    """

    path: str
    owners: tuple[str, ...]
    shared: bool


class OwnershipError(ValueError):
    """Base class for ownership errors."""


class OwnershipConflict(OwnershipError):
    """A file is claimed by multiple packages without a shared declaration."""

    def __init__(
        self,
        path: str,
        owners: tuple[str, ...],
        message: str | None = None,
    ) -> None:
        self.path = path
        self.owners = owners
        super().__init__(
            message or f"conflicting owners for {path!r}: {list(owners)}"
        )


class UnownedFile(OwnershipError):
    """A source file matches no package's ``owned_paths``."""


@dataclass
class OwnershipMap:
    """Result of :func:`compute_ownership`."""

    files: dict[str, FileOwnership] = field(default_factory=dict)
    conflicts: list[OwnershipConflict] = field(default_factory=list)
    unowned: list[str] = field(default_factory=list)


def _walk_files(source_root: Path) -> Iterable[Path]:
    """Yield every real file under ``source_root``, applying exclusions."""
    for path in sorted(source_root.rglob("*")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(source_root).parts
        # Skip any file whose parent chain contains an excluded dir.
        skip = False
        for part in rel_parts[:-1]:
            if part == "__pycache__" or part.startswith("."):
                skip = True
                break
        if skip:
            continue
        if path.suffix == ".pyc":
            continue
        yield path


def _pkg_rel_prefix(pkg_root: Path, source_root: Path) -> str:
    """POSIX prefix of the package's root relative to source_root, or ""."""
    try:
        rel = pkg_root.relative_to(source_root)
    except ValueError:
        return ""
    s = rel.as_posix()
    return "" if s == "." else s


def compute_ownership(
    root_pkg: ArchitecturePackage,
    *,
    source_root: Path | None = None,
) -> OwnershipMap:
    """Compute the file-ownership map for a package tree.

    See module docstring for semantics and exclusions.
    """
    if source_root is None:
        if root_pkg.root is None:
            raise OwnershipError(
                "root_pkg.root is not set; load via load_package()"
            )
        source_root = root_pkg.root
    source_root = Path(source_root).resolve()

    # Collect every package once (root + descendants).
    packages = list(iter_descendants(root_pkg, include_self=True))

    # Per-package info + shared declarations keyed by file rel-to-source-root.
    pkg_info: list[tuple[str, Path, list[str]]] = []
    shared_declarations: dict[str, frozenset[str]] = {}
    for p in packages:
        assert p.root is not None
        p_root = p.root.resolve()
        try:
            p_root.relative_to(source_root)
        except ValueError:
            # Package outside the source_root — its owned_paths cannot
            # apply to files under source_root.
            continue
        pkg_info.append((p.architecture_id, p_root, list(p.owned_paths)))

        prefix = _pkg_rel_prefix(p_root, source_root)
        for sp in p.shared_paths:
            joined = f"{prefix}/{sp.path}" if prefix else sp.path
            key = PurePosixPath(joined).as_posix()
            shared_declarations[key] = frozenset(sp.owners)

    # Walk and claim.
    file_claimants: dict[str, set[str]] = {}
    all_files: list[str] = []
    for fp in _walk_files(source_root):
        rel_source = fp.relative_to(source_root).as_posix()
        all_files.append(rel_source)
        fp_resolved = fp.resolve()
        claimants: set[str] = set()
        for aid, p_root, patterns in pkg_info:
            try:
                rel_to_pkg = fp_resolved.relative_to(p_root).as_posix()
            except ValueError:
                continue
            for pat in patterns:
                if fnmatch.fnmatchcase(rel_to_pkg, pat):
                    claimants.add(aid)
                    break
        if claimants:
            file_claimants[rel_source] = claimants

    mp = OwnershipMap()
    unowned: list[str] = []
    for rel in all_files:
        if rel not in file_claimants:
            unowned.append(rel)
            continue
        claimants = file_claimants[rel]
        owners_tuple = tuple(sorted(claimants))
        shared = False
        is_conflict = False
        if len(claimants) > 1:
            declared = shared_declarations.get(rel)
            if declared is not None and declared == claimants:
                shared = True
            else:
                is_conflict = True
        mp.files[rel] = FileOwnership(
            path=rel, owners=owners_tuple, shared=shared
        )
        if is_conflict:
            mp.conflicts.append(OwnershipConflict(rel, owners_tuple))

    mp.files = dict(sorted(mp.files.items()))
    mp.conflicts.sort(key=lambda c: c.path)
    mp.unowned = sorted(unowned)
    return mp


def assert_no_conflicts(mp: OwnershipMap) -> None:
    """Raise :class:`OwnershipConflict` if ``mp.conflicts`` is non-empty."""
    if not mp.conflicts:
        return
    first = mp.conflicts[0]
    lines = [f"  {c.path}: {list(c.owners)}" for c in mp.conflicts]
    msg = (
        f"{len(mp.conflicts)} ownership conflict(s):\n"
        + "\n".join(lines)
    )
    raise OwnershipConflict(first.path, first.owners, msg)


def _default_remaps_path(root_pkg: ArchitecturePackage) -> Path:
    if root_pkg.root is None:
        raise OwnershipError(
            "root_pkg.root is not set; load via load_package()"
        )
    return root_pkg.root / ".architecture" / "remaps.yaml"


def record_remap(
    root_pkg: ArchitecturePackage,
    old_slug: str,
    new_slug: str,
    *,
    remaps_path: Path | None = None,
) -> Path:
    """Append a slug-remap entry to the package's remaps.yaml.

    Writes atomically via :func:`atomic_store.write_atomic`. Returns the
    resolved path written.
    """
    path = Path(remaps_path) if remaps_path is not None else _default_remaps_path(root_pkg)
    existing = load_remaps(path)
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "architecture_id": root_pkg.architecture_id,
        "old_slug": old_slug,
        "new_slug": new_slug,
    }
    existing.append(entry)
    data = yaml.safe_dump(
        existing, sort_keys=False, default_flow_style=False
    ).encode("utf-8")
    write_atomic(path, data)
    return path


def load_remaps(remaps_path: Path) -> list[dict]:
    """Load a remaps.yaml list. Returns ``[]`` when the file is missing."""
    p = Path(remaps_path)
    if not p.exists():
        return []
    text = p.read_text(encoding="utf-8")
    data = canonical_yaml_load(text)
    if data is None:
        return []
    if not isinstance(data, list):
        raise OwnershipError(
            f"remaps file must be a YAML list, got {type(data).__name__}"
        )
    return data
