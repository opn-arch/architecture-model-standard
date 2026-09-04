"""ZIP bundle artifact renderer (T18 commit 2).

Purpose
-------
Aggregate multiple already-rendered artifact byte payloads into a single
deterministic ZIP archive, together with a ``manifest.json`` describing
the bundle contents and their sha256 digests.

Purity contract
---------------
Writes to an in-memory :class:`io.BytesIO` — no filesystem, network,
environment, or logging side effects.

Signature difference
--------------------
Unlike the per-view renderers (``svg``, ``markdown``, ``html``,
``ai-context``), :func:`render_zip` needs an out-of-band way to fetch
the bytes of each sibling artifact named in ``artifact.bundle_refs``.
It therefore takes a keyword-only ``resolve_artifact`` callable:

    resolve_artifact(bundle_ref_id: str) -> bytes

If ``resolve_artifact`` is ``None`` the renderer raises
:class:`ValueError`. If the callable returns ``None`` or raises
:class:`KeyError` for a given id, :class:`BundleResolutionError` (a
:class:`ValueError` subclass) is raised.

Registry entry
--------------
:func:`render_zip` is registered under the ``"zip"`` key of
:data:`architecture_model.lifecycle.renderers.DEFAULT_RENDERERS` so
callers can discover it uniformly, but invoking it via the ordinary
``(view, artifact)`` registry call signature will raise ``ValueError``
because ``resolve_artifact`` cannot be supplied that way. Phase 2
orchestrators are expected to detect ``renderer == "zip"`` and invoke
:func:`render_zip` directly with the resolver.

Determinism
-----------
* Every ZipInfo ``date_time`` is fixed to the ZIP epoch minimum
  ``(1980, 1, 1, 0, 0, 0)``.
* Bundle entries and manifest ``bundles`` are sorted by id.
* The manifest ``produced_at`` timestamp is the only source of
  nondeterminism between calls; tests freeze
  :func:`datetime.datetime.now` to compare byte-identical output.
"""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Callable

from architecture_model.lifecycle.artifact_spec import (
    ArtifactSpec,
    compute_artifact_spec_digest,
)
from architecture_model.lifecycle.view_projection import ProjectedView

_NAME = "zip"
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


class BundleResolutionError(ValueError):
    """Raised when a bundle_ref cannot be resolved to bytes."""


def _check_renderer(artifact: ArtifactSpec) -> None:
    if artifact.renderer != _NAME:
        raise ValueError(
            f"renderer mismatch: expected {_NAME!r}, got {artifact.renderer!r}"
        )


def _rfc3339_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def render_zip(
    views: list[ProjectedView],
    artifact: ArtifactSpec,
    *,
    resolve_artifact: Callable[[str], bytes] | None = None,
) -> bytes:
    """Build a deterministic ZIP archive of resolved bundle_refs.

    ``views`` is accepted for signature symmetry with other renderers
    but is not consulted — a zip artifact aggregates sibling artifacts
    identified by ``artifact.bundle_refs``, not raw views. The parameter
    is retained so registry callers can pass an arbitrary list.
    """
    _check_renderer(artifact)
    if resolve_artifact is None:
        raise ValueError("zip renderer requires resolve_artifact callable")
    del views  # unused; see docstring

    bundle_refs = artifact.bundle_refs or []
    resolved: list[tuple[str, bytes]] = []
    for ref in bundle_refs:
        try:
            payload = resolve_artifact(ref)
        except KeyError as exc:
            raise BundleResolutionError(
                f"cannot resolve bundle_ref {ref!r}"
            ) from exc
        if payload is None:
            raise BundleResolutionError(f"cannot resolve bundle_ref {ref!r}")
        resolved.append((ref, payload))

    resolved.sort(key=lambda pair: pair[0])

    manifest = {
        "artifact_id": artifact.id,
        "artifact_digest": compute_artifact_spec_digest(artifact),
        "contract_version": artifact.contract_version,
        "renderer": _NAME,
        "bundles": [
            {
                "id": ref_id,
                "path": f"artifacts/{ref_id}",
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            for ref_id, payload in resolved
        ],
        "produced_at": _rfc3339_now(),
    }
    manifest_bytes = json.dumps(
        manifest, indent=2, sort_keys=True
    ).encode("utf-8")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for ref_id, payload in resolved:
            info = zipfile.ZipInfo(filename=f"artifacts/{ref_id}", date_time=_ZIP_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, payload)
        manifest_info = zipfile.ZipInfo(filename="manifest.json", date_time=_ZIP_EPOCH)
        manifest_info.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(manifest_info, manifest_bytes)

    return buf.getvalue()


__all__ = ["BundleResolutionError", "render_zip"]
