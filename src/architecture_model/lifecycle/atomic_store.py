"""Crash-safe atomic file and tree writes.

Purpose
-------
Provide primitives that ensure a target path never contains partially-written
data even under process crash, kill -9, or power loss (modulo fs guarantees).

Invariants
----------
* A final target path is only ever created via ``os.replace`` from a fully
  fsynced sibling temp file. Readers see either the previous state or the new
  state, never a half-written one.
* Temp/staging paths are removed on every error path.

Platform caveats
----------------
* Symlink swap in :func:`switch_current` is POSIX-only; Windows support is out
  of scope for Phase 1.
* Parent-directory fsync is best-effort and silently skipped on platforms that
  do not support ``os.O_DIRECTORY``.
"""

from __future__ import annotations

import os
import shutil
import uuid
from collections.abc import Mapping
from pathlib import Path


def _fsync_dir(directory: Path) -> None:
    """Best-effort fsync of ``directory`` metadata. Silent on unsupported OS."""
    o_directory = getattr(os, "O_DIRECTORY", None)
    if o_directory is None:
        return
    try:
        fd = os.open(str(directory), o_directory)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def write_atomic(path: Path, data: bytes, *, fsync: bool = True) -> None:
    """Atomically write ``data`` to ``path``.

    Uses a sibling temp file + ``os.replace``. On any error before replace, the
    temp file is removed and the exception re-raised, leaving the original
    ``path`` (if any) untouched.
    """
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    tmp = parent / f"{path.name}.tmp-{uuid.uuid4().hex}"
    try:
        fd = os.open(
            str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644
        )
        try:
            written = 0
            view = memoryview(data)
            while written < len(view):
                written += os.write(fd, view[written:])
            if fsync:
                os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(str(tmp), str(path))
    except BaseException:
        try:
            os.unlink(str(tmp))
        except FileNotFoundError:
            pass
        raise
    if fsync:
        _fsync_dir(parent)


def write_tree_atomic(root: Path, files: Mapping[Path, bytes]) -> None:
    """Publish a multi-file tree atomically under ``root``.

    Files are staged into a sibling ``<name>.staging-<uuid>`` directory, each
    written atomically. Once all files are on disk, the staging directory is
    renamed to ``root`` via ``os.replace``. If ``root`` already exists,
    ``FileExistsError`` is raised — callers should use ``switch_current`` for
    generation-based publishing.
    """
    if root.exists():
        raise FileExistsError(
            f"{root} already exists; use switch_current for generation-based "
            "publishing"
        )
    parent = root.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging = parent / f"{root.name}.staging-{uuid.uuid4().hex}"
    try:
        staging.mkdir()
        for rel, data in files.items():
            rel_p = Path(rel)
            if rel_p.is_absolute():
                raise ValueError(f"file key must be relative: {rel}")
            dest = staging / rel_p
            dest.parent.mkdir(parents=True, exist_ok=True)
            write_atomic(dest, data, fsync=True)
        os.replace(str(staging), str(root))
        _fsync_dir(parent)
    except BaseException:
        if staging.exists():
            shutil.rmtree(str(staging), ignore_errors=True)
        raise


def switch_current(pointer: Path, target: Path) -> None:
    """Atomically point symlink ``pointer`` at ``target``.

    ``target`` must exist. Uses temp-symlink + ``os.replace`` so readers see
    either the old target or the new one.
    """
    if not target.exists():
        raise FileNotFoundError(str(target))
    parent = pointer.parent
    parent.mkdir(parents=True, exist_ok=True)
    tmp = parent / f"{pointer.name}.tmp-{uuid.uuid4().hex}"
    try:
        parent_resolved = parent.resolve()
        target_resolved = target.resolve()
        try:
            link_target: str = str(
                Path(os.path.relpath(target_resolved, parent_resolved))
            )
        except ValueError:
            link_target = str(target_resolved)
        os.symlink(link_target, str(tmp))
        os.replace(str(tmp), str(pointer))
    except BaseException:
        try:
            os.unlink(str(tmp))
        except FileNotFoundError:
            pass
        raise
