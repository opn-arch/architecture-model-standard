"""ArchitecturePackage descriptor and recursive loader.

A ``package.yaml`` file marks a self-contained architecture package: it
names the package, points at the package's canonical model and reality
manifest, and lists any nested child packages. Packages compose into a
tree; every architecture_id in that tree must be unique and the tree
must be acyclic.

This module provides:

* :class:`ArchitecturePackage` — the pydantic descriptor model.
* :func:`load_package` — parse one ``package.yaml`` (no recursion).
* :func:`iter_descendants` — depth-first traversal with cycle and
  duplicate-id detection.
* :func:`resolve` — look up a package by architecture_id.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from architecture_model.lifecycle.serialization import canonical_yaml_load
from architecture_model.lifecycle.versions import SchemaVersions

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


class PackageLoadError(ValueError):
    """Base class for package-loader errors."""


class PackageCycleError(PackageLoadError):
    """Raised when the package graph contains a cycle."""


class PackageDuplicateIdError(PackageLoadError):
    """Raised when two distinct packages share an architecture_id."""


class PackagePathTraversalError(PackageLoadError):
    """Raised when model_ref/manifest_ref escapes the package root."""


class PackageVersionError(PackageLoadError):
    """Raised when contract_version does not match the frozen version."""


class SharedPath(BaseModel):
    """A path shared by multiple packages (co-owned code region)."""

    model_config = ConfigDict(extra="forbid")

    path: str
    owners: list[str]


class PackageRef(BaseModel):
    """A reference to an external architecture package."""

    model_config = ConfigDict(extra="forbid")

    architecture_id: str
    at: str | None = None


class PackageMetadata(BaseModel):
    """Free-form metadata attached to a package descriptor."""

    model_config = ConfigDict(extra="forbid")

    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class ArchitecturePackage(BaseModel):
    """Parsed ``package.yaml`` descriptor.

    Attributes match the on-disk YAML schema. ``root`` is a runtime-only
    attribute populated by :func:`load_package` — it is not serialized.
    """

    model_config = ConfigDict(extra="forbid")

    architecture_id: str
    name: str
    slug: str
    contract_version: str
    model_ref: str
    manifest_ref: str
    children: list[str] = Field(default_factory=list)
    owned_paths: list[str] = Field(default_factory=list)
    shared_paths: list[SharedPath] = Field(default_factory=list)
    refs: list[PackageRef] = Field(default_factory=list)
    revisions_dir: str = "revisions"
    metadata: PackageMetadata = Field(default_factory=PackageMetadata)
    federated_ref: bool = False

    # Runtime-only; populated by load_package. Not serialized.
    root: Path | None = Field(default=None, exclude=True, repr=False)

    @property
    def id(self) -> str:
        """Alias for architecture_id; consistent with entity ID convention."""
        return self.architecture_id

    @field_validator("contract_version")
    @classmethod
    def _check_version(cls, v: str) -> str:
        if v != SchemaVersions.PACKAGE:
            raise PackageVersionError(
                f"contract_version {v!r} does not match frozen "
                f"SchemaVersions.PACKAGE ({SchemaVersions.PACKAGE!r})"
            )
        return v

    @field_validator("architecture_id", "slug")
    @classmethod
    def _check_identifier(cls, v: str) -> str:
        if not (_SLUG_RE.match(v) or _UUID_RE.match(v)):
            raise ValueError(
                f"invalid identifier {v!r}: must be lowercase kebab-case "
                "([a-z0-9][a-z0-9-]*) or a UUID"
            )
        return v

    @field_validator("model_ref", "manifest_ref")
    @classmethod
    def _check_relative_ref(cls, v: str) -> str:
        if not v:
            raise ValueError("ref must be a non-empty relative path")
        p = Path(v)
        if p.is_absolute():
            raise PackagePathTraversalError(
                f"ref {v!r} must be relative, not absolute"
            )
        if ".." in p.parts:
            raise PackagePathTraversalError(
                f"ref {v!r} must not contain '..' traversal"
            )
        return v


def _package_dir(path: Path) -> Path:
    """Return the directory containing package.yaml given a file or dir."""
    if path.is_file() or path.name == "package.yaml":
        return path.parent
    return path


def load_package(path: Path | str) -> ArchitecturePackage:
    """Load a single ``package.yaml`` (no recursion into children).

    Accepts either the ``package.yaml`` file path or the directory
    containing it. Validates that ``model_ref`` and ``manifest_ref``
    resolve strictly inside the package root; child descendants are
    loaded lazily by :func:`iter_descendants`.
    """
    p = Path(path).resolve()
    pkg_dir = _package_dir(p).resolve()
    yaml_path = pkg_dir / "package.yaml"
    text = yaml_path.read_text(encoding="utf-8")
    data = canonical_yaml_load(text)
    if not isinstance(data, dict):
        raise PackageLoadError(
            f"{yaml_path}: top-level YAML must be a mapping, got {type(data).__name__}"
        )
    try:
        pkg = ArchitecturePackage(**data)
    except ValidationError as e:
        # Surface embedded lifecycle errors (raised inside validators)
        # as their own exception type so callers can catch them directly.
        for err in e.errors():
            ctx = err.get("ctx", {})
            exc = ctx.get("error") if isinstance(ctx, dict) else None
            if isinstance(exc, PackageVersionError):
                raise exc
            if isinstance(exc, PackagePathTraversalError):
                raise exc
        raise
    pkg.root = pkg_dir

    root_resolved = pkg_dir.resolve()
    for ref_name in ("model_ref", "manifest_ref"):
        ref_val = getattr(pkg, ref_name)
        target = (pkg_dir / ref_val).resolve()
        if not target.is_relative_to(root_resolved):
            raise PackagePathTraversalError(
                f"{yaml_path}: {ref_name}={ref_val!r} resolves outside "
                f"package root {root_resolved}"
            )
    return pkg


def iter_descendants(
    pkg: ArchitecturePackage, *, include_self: bool = False
) -> Iterator[ArchitecturePackage]:
    """Depth-first traversal of the package tree.

    Children are visited in lexical order by ``slug`` for deterministic
    output. Raises :class:`PackageCycleError` if the traversal revisits
    a package it is currently descending into, and
    :class:`PackageDuplicateIdError` if two distinct package
    directories yield the same architecture_id.
    """
    if pkg.root is None:
        raise PackageLoadError(
            "package.root not set; use load_package() to construct packages"
        )

    seen_ids: dict[str, Path] = {}
    on_stack: set[str] = set()

    def walk(current: ArchitecturePackage, emit: bool) -> Iterator[ArchitecturePackage]:
        aid = current.architecture_id
        if aid in on_stack:
            raise PackageCycleError(
                f"cycle detected at architecture_id={aid!r} "
                f"({current.root})"
            )
        assert current.root is not None
        cur_root = current.root.resolve()
        if aid in seen_ids and seen_ids[aid] != cur_root:
            raise PackageDuplicateIdError(
                f"duplicate architecture_id={aid!r}: "
                f"{seen_ids[aid]} vs {cur_root}"
            )
        seen_ids[aid] = cur_root
        on_stack.add(aid)
        try:
            if emit:
                yield current
            loaded_children: list[ArchitecturePackage] = []
            for child_rel in current.children:
                loaded_children.append(load_package(current.root / child_rel))
            loaded_children.sort(key=lambda c: c.slug)
            for child in loaded_children:
                yield from walk(child, emit=True)
        finally:
            on_stack.discard(aid)

    yield from walk(pkg, emit=include_self)


def resolve(
    pkg: ArchitecturePackage, architecture_id: str
) -> ArchitecturePackage | None:
    """Return the package with the given architecture_id, or None.

    Searches ``pkg`` and all descendants.
    """
    for candidate in iter_descendants(pkg, include_self=True):
        if candidate.architecture_id == architecture_id:
            return candidate
    return None
