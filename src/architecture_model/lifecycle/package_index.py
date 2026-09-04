"""Root architecture package index.

Purpose
-------
Provide a fast, deterministic lookup table from ``architecture_id`` / slug /
source-file path to the on-disk package that owns it. Instead of re-walking
the package tree on every query, callers rebuild the index once after any
structural change and then consume it as a flat list.

The index lives at ``<repo_root>/.architecture/package-index.yaml`` by
convention. Tests may override the location via ``index_path``.

Invariants
----------
* The index file is written via :func:`atomic_store.write_atomic`, so
  readers never observe a partially written index.
* Every rebuild records an ``index.rebuild.commit`` event on the journal
  at ``<repo_root>/.architecture/journal.jsonl``.
* Entries are sorted by ``slug`` for byte-stable output.
* ``entry.root`` is a POSIX-style path *relative to* ``repo_root``.
* ``contract_version`` matches :data:`SchemaVersions.PACKAGE`.

Non-goals
---------
* Federated cross-repo indexes — Phase 1 indexes one repo root at a time.
* Generation tracking — ``current_generation`` is always ``None`` here;
  Task 8 populates it once revision publishing exists.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from architecture_model.lifecycle import journal as journal_mod
from architecture_model.lifecycle.atomic_store import write_atomic
from architecture_model.lifecycle.journal import Journal
from architecture_model.lifecycle.package import (
    ArchitecturePackage,
    load_package,
)
from architecture_model.lifecycle.serialization import canonical_yaml_load
from architecture_model.lifecycle.versions import SchemaVersions


@dataclass(frozen=True)
class IndexEntry:
    architecture_id: str
    slug: str
    root: str  # POSIX-style path relative to repo_root
    current_generation: int | None
    parent_id: str | None


def _default_index_path(repo_root: Path) -> Path:
    return repo_root / ".architecture" / "package-index.yaml"


def _collect_entries(
    pkg: ArchitecturePackage, repo_root: Path
) -> list[IndexEntry]:
    """Depth-first walk yielding entries with parent_ids.

    Uses the same child-loading semantics as
    :func:`architecture_model.lifecycle.package.iter_descendants` (children
    sorted by slug), but tracks the parent architecture_id.
    """
    repo_resolved = repo_root.resolve()
    entries: list[IndexEntry] = []

    def walk(current: ArchitecturePackage, parent_id: str | None) -> None:
        assert current.root is not None
        rel = current.root.resolve().relative_to(repo_resolved)
        entries.append(
            IndexEntry(
                architecture_id=current.architecture_id,
                slug=current.slug,
                root=rel.as_posix(),
                current_generation=None,
                parent_id=parent_id,
            )
        )
        loaded_children: list[ArchitecturePackage] = []
        for child_rel in current.children:
            loaded_children.append(load_package(current.root / child_rel))
        loaded_children.sort(key=lambda c: c.slug)
        for child in loaded_children:
            walk(child, current.architecture_id)

    walk(pkg, None)
    return entries


def rebuild_index(
    repo_root: Path,
    root_package: ArchitecturePackage,
    *,
    index_path: Path | None = None,
) -> Path:
    """Rebuild the index for ``root_package`` under ``repo_root``.

    Writes atomically and records a journal event. Returns the final
    path written.
    """
    repo_root = Path(repo_root)
    entries = _collect_entries(root_package, repo_root)
    entries.sort(key=lambda e: e.slug)

    generated_at = (
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    )
    payload: dict = {
        "contract_version": SchemaVersions.PACKAGE,
        "generated_at": generated_at,
        "repo_root": str(repo_root.resolve()),
        "entries": [asdict(e) for e in entries],
    }
    text = yaml.safe_dump(
        payload, sort_keys=True, default_flow_style=False
    )
    target = index_path if index_path is not None else _default_index_path(repo_root)
    target = Path(target)
    write_atomic(target, text.encode("utf-8"), fsync=True)

    journal = Journal(repo_root / ".architecture" / "journal.jsonl")
    journal.record(
        journal_mod.INDEX_REBUILD_COMMIT,
        {
            "repo_root": str(repo_root.resolve()),
            "index_path": str(target),
            "entry_count": len(entries),
            "contract_version": SchemaVersions.PACKAGE,
        },
    )
    return target


def load_index(path: Path) -> list[IndexEntry]:
    """Load an index file and return its entries.

    Raises :class:`ValueError` if ``contract_version`` does not match the
    frozen :data:`SchemaVersions.PACKAGE`.
    """
    text = Path(path).read_text(encoding="utf-8")
    data = canonical_yaml_load(text)
    if not isinstance(data, dict):
        raise ValueError(
            f"{path}: index YAML must be a mapping, got {type(data).__name__}"
        )
    version = data.get("contract_version")
    if version != SchemaVersions.PACKAGE:
        raise ValueError(
            f"{path}: contract_version {version!r} does not match frozen "
            f"SchemaVersions.PACKAGE ({SchemaVersions.PACKAGE!r})"
        )
    raw_entries = data.get("entries", []) or []
    entries: list[IndexEntry] = []
    for raw in raw_entries:
        entries.append(
            IndexEntry(
                architecture_id=raw["architecture_id"],
                slug=raw["slug"],
                root=raw["root"],
                current_generation=raw.get("current_generation"),
                parent_id=raw.get("parent_id"),
            )
        )
    return entries


def find_by_id(
    entries: list[IndexEntry], architecture_id: str
) -> IndexEntry | None:
    """Return the entry with the matching architecture_id, or None."""
    for e in entries:
        if e.architecture_id == architecture_id:
            return e
    return None


def find_by_slug(entries: list[IndexEntry], slug: str) -> IndexEntry | None:
    """Return the entry with the matching slug, or None."""
    for e in entries:
        if e.slug == slug:
            return e
    return None


def find_containing(
    entries: list[IndexEntry], repo_root: Path, source_path: Path
) -> IndexEntry | None:
    """Return the deepest package entry containing ``source_path``.

    Walks upward from ``source_path.resolve()``; at each ancestor
    directory, checks whether any entry's ``(repo_root / entry.root)``
    equals that directory. The first (deepest) match wins.
    """
    repo_resolved = Path(repo_root).resolve()
    entry_roots: dict[Path, IndexEntry] = {
        (repo_resolved / e.root).resolve(): e for e in entries
    }
    try:
        current = Path(source_path).resolve()
    except OSError:
        return None
    # Walk up until we hit filesystem root
    while True:
        if current in entry_roots:
            return entry_roots[current]
        if current.parent == current:
            return None
        current = current.parent
