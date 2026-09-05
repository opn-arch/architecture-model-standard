"""Transactional package publication with generation-based storage.

Purpose
-------
Publish an architecture package as an immutable, content-addressed
"generation" directory and atomically switch a ``CURRENT`` symlink to point
at it. Every publication is journaled so an interrupted publish can be
detected and cleaned up post-crash.

Layout on disk::

    <package_root>/
      package.yaml
      generations/
        0000001/
          model/.architecture-model.yaml
          manifest/manifest.json
          slices/...             (optional bundle inputs)
          views/...              (optional)
          artifacts/...          (optional)
          digest.json            (auto-written)
        0000002/
          ...
      CURRENT -> generations/0000002    (symlink)
      .locks/publication.lock            (FileLock file)

Invariants
----------
* A generation directory, once committed, is immutable — never rewritten.
* ``CURRENT`` is switched atomically (temp symlink + ``os.replace``).
* The journal is the source of truth for crash recovery: a
  ``package.publish.begin`` without a matching commit/abort means the
  publish was interrupted.
* Per-file digests are computed on raw bytes with sha256; the root digest
  is the canonical-JSON digest of ``{"files": <sorted map>}``.
* ``digest.json`` bytes are added to the tree AFTER the root digest is
  fixed; the map inside ``digest.json`` does not include ``digest.json``
  itself.

Locking
-------
A single ``FileLock`` at ``<pkg>/.locks/publication.lock`` serializes
concurrent publishers on the same host. On timeout the specialized
:class:`PublicationLockTimeout` is raised.

Non-goals (Phase 1)
-------------------
* Garbage collection of old generations — future retention task.
* Cross-host coordination — same limitations as :class:`FileLock`.
* Rollback of ``CURRENT`` — recovery only cleans staging leftovers.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Mapping

from architecture_model.lifecycle.atomic_store import (
    switch_current,
    write_tree_atomic,
)
from architecture_model.lifecycle.journal import (
    PACKAGE_PUBLISH_ABORT,
    PACKAGE_PUBLISH_BEGIN,
    PACKAGE_PUBLISH_COMMIT,
    Journal,
)
from architecture_model.lifecycle.locks import FileLock, LockTimeout
from architecture_model.lifecycle.package import ArchitecturePackage
from architecture_model.lifecycle.serialization import canonical_json
from architecture_model.lifecycle.versions import SchemaVersions

GENERATION_ZERO_PAD = 7
_GEN_RE = re.compile(r"^\d{7}$")


class PublicationError(RuntimeError):
    """Base class for publication errors."""


class PublicationLockTimeout(PublicationError):
    """Raised when the publication lock cannot be acquired in time."""


class PublicationInProgress(PublicationError):
    """Raised when a target generation directory already exists."""


@dataclass(frozen=True)
class PackageBundle:
    """Payload for a single publication."""

    model_bytes: bytes
    manifest_bytes: bytes
    extra_files: Mapping[PurePosixPath, bytes] = field(default_factory=dict)


@dataclass(frozen=True)
class PublicationResult:
    """Outcome of a successful publication."""

    generation: int
    generation_dir: Path
    current_path: Path
    root_digest: str
    files: dict[str, str]


def _bytes_digest(b: bytes) -> str:
    return f"{SchemaVersions.DIGEST_ALGO}:{hashlib.sha256(b).hexdigest()}"


def _journal_path(pkg: ArchitecturePackage, override: Path | None) -> Path:
    if override is not None:
        return Path(override)
    return pkg.root / ".architecture" / "journal.jsonl"


def generation_dir(pkg: ArchitecturePackage, n: int) -> Path:
    """Return the path to generation ``n`` within ``pkg``'s ``generations/`` directory."""
    return pkg.root / "generations" / f"{n:0{GENERATION_ZERO_PAD}d}"


# Deprecated alias — retained for one release cycle. Use ``generation_dir`` instead.
_generation_dir = generation_dir


def list_generations(pkg: ArchitecturePackage) -> list[int]:
    """Return sorted list of committed generation numbers."""
    gens_dir = pkg.root / "generations"
    if not gens_dir.is_dir():
        return []
    out: list[int] = []
    for entry in gens_dir.iterdir():
        if entry.is_dir() and _GEN_RE.match(entry.name):
            out.append(int(entry.name))
    out.sort()
    return out


def read_current_generation(pkg: ArchitecturePackage) -> int | None:
    """Return the generation number pointed at by ``CURRENT``, or None."""
    current = pkg.root / "CURRENT"
    if not current.is_symlink() and not current.exists():
        return None
    try:
        target = os.readlink(str(current))
    except OSError:
        return None
    name = PurePosixPath(target).name
    if not _GEN_RE.match(name):
        return None
    return int(name)


def publish(
    pkg: ArchitecturePackage,
    bundle: PackageBundle,
    *,
    journal_path: Path | None = None,
    lock_timeout: float | None = 30.0,
) -> PublicationResult:
    """Publish ``bundle`` as the next generation of ``pkg``.

    Acquires a per-package publication lock, stages files under a new
    ``generations/<N>`` directory, records a begin event, commits via an
    atomic symlink swap of ``CURRENT``, then records a commit event. On
    any failure between begin and commit an abort event is journaled.
    """
    jpath = _journal_path(pkg, journal_path)
    journal = Journal(jpath)

    lock_path = pkg.root / ".locks" / "publication.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        lock = FileLock(lock_path, timeout=lock_timeout)
        lock.__enter__()
    except LockTimeout as e:
        raise PublicationLockTimeout(
            f"could not acquire publication lock {lock_path} within "
            f"{lock_timeout}s"
        ) from e

    try:
        n = max(list_generations(pkg), default=0) + 1
        gen_dir = generation_dir(pkg, n)
        if gen_dir.exists():
            raise PublicationInProgress(
                f"generation dir {gen_dir} already exists"
            )

        # Assemble raw file bytes (excluding digest.json)
        raw_files: dict[PurePosixPath, bytes] = {
            PurePosixPath("model/.architecture-model.yaml"): bundle.model_bytes,
            PurePosixPath("manifest/manifest.json"): bundle.manifest_bytes,
        }
        for rel, data in bundle.extra_files.items():
            rel_p = PurePosixPath(rel)
            if rel_p.is_absolute() or ".." in rel_p.parts:
                raise ValueError(
                    f"extra_files key must be a safe relative path: {rel}"
                )
            raw_files[rel_p] = bytes(data)

        # Per-file digests
        file_digests: dict[str, str] = {
            str(rel): _bytes_digest(data) for rel, data in raw_files.items()
        }
        sorted_files = dict(sorted(file_digests.items()))
        root_digest = _bytes_digest(
            canonical_json({"files": sorted_files})
        )

        digest_doc = {
            "contract_version": SchemaVersions.PACKAGE,
            "algo": SchemaVersions.DIGEST_ALGO,
            "root_digest": root_digest,
            "files": sorted_files,
        }
        digest_bytes = canonical_json(digest_doc) + b"\n"
        raw_files[PurePosixPath("digest.json")] = digest_bytes

        journal.record(PACKAGE_PUBLISH_BEGIN, {
            "architecture_id": pkg.architecture_id,
            "generation": n,
            "root_digest": root_digest,
        })

        try:
            tree = {Path(str(rel)): data for rel, data in raw_files.items()}
            write_tree_atomic(gen_dir, tree)
            switch_current(pkg.root / "CURRENT", gen_dir)
        except BaseException as e:
            journal.record(PACKAGE_PUBLISH_ABORT, {
                "architecture_id": pkg.architecture_id,
                "generation": n,
                "error": repr(e),
            })
            # Best-effort cleanup of a partial gen_dir. write_tree_atomic
            # is transactional (staging dir), so gen_dir either exists
            # fully or not at all. If it exists but CURRENT still points
            # elsewhere, remove it so a retry can reuse N.
            if gen_dir.exists():
                current = pkg.root / "CURRENT"
                try:
                    if current.is_symlink():
                        cur_target = (
                            current.parent / os.readlink(str(current))
                        ).resolve()
                    else:
                        cur_target = None
                except OSError:
                    cur_target = None
                if cur_target != gen_dir.resolve():
                    shutil.rmtree(str(gen_dir), ignore_errors=True)
            raise

        journal.record(PACKAGE_PUBLISH_COMMIT, {
            "architecture_id": pkg.architecture_id,
            "generation": n,
            "root_digest": root_digest,
        })

        # Compute digest of digest.json itself for the reported files map
        all_files_reported = dict(sorted_files)
        all_files_reported["digest.json"] = _bytes_digest(digest_bytes)

        return PublicationResult(
            generation=n,
            generation_dir=gen_dir,
            current_path=pkg.root / "CURRENT",
            root_digest=root_digest,
            files=all_files_reported,
        )
    finally:
        lock.__exit__(None, None, None)


def _interrupted_begins(
    journal: Journal, architecture_id: str
) -> list[dict]:
    """Return begin-events (payloads) that have no matching commit/abort."""
    open_gens: dict[int, dict] = {}
    for entry in journal.replay():
        payload = entry.get("payload") or {}
        if payload.get("architecture_id") != architecture_id:
            continue
        gen = payload.get("generation")
        if not isinstance(gen, int):
            continue
        event = entry.get("event")
        if event == PACKAGE_PUBLISH_BEGIN:
            open_gens[gen] = payload
        elif event in (PACKAGE_PUBLISH_COMMIT, PACKAGE_PUBLISH_ABORT):
            open_gens.pop(gen, None)
    return [open_gens[k] for k in sorted(open_gens)]


def recover(
    pkg: ArchitecturePackage, *, journal_path: Path | None = None
) -> None:
    """Detect interrupted publications and record abort events.

    ``CURRENT`` is not touched; it still points at the last successfully
    committed generation (if any). Orphan generation directories for
    interrupted N are removed if they are not the current target.
    """
    jpath = _journal_path(pkg, journal_path)
    journal = Journal(jpath)
    interrupted = _interrupted_begins(journal, pkg.architecture_id)
    if not interrupted:
        return

    current_gen = read_current_generation(pkg)
    for payload in interrupted:
        n = payload["generation"]
        gen_dir = generation_dir(pkg, n)
        if gen_dir.exists() and n != current_gen:
            shutil.rmtree(str(gen_dir), ignore_errors=True)
        # Also remove any leftover staging dirs for this N
        parent = gen_dir.parent
        if parent.is_dir():
            for entry in parent.iterdir():
                if entry.name.startswith(f"{gen_dir.name}.staging-"):
                    shutil.rmtree(str(entry), ignore_errors=True)
        journal.record(PACKAGE_PUBLISH_ABORT, {
            "architecture_id": pkg.architecture_id,
            "generation": n,
            "error": "recovered from crash",
        })
