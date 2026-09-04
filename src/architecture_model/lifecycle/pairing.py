"""Model/manifest revision pairing helpers.

Purpose
-------
Enforce an immutable one-to-one binding between an architecture model
and its reality manifest. A model captures intent (capabilities,
components, relationships); a manifest captures ground truth (AST-derived
modules, functions, imports). Because a model's meaning is anchored in
the manifest it was authored against, the two artifacts must travel
together and mutations to either must be detectable.

This module supplies pure helpers to:

* compute stable content digests for models and manifests, excluding
  volatile bookkeeping fields;
* stamp a matching pair with cross-references (``model.meta.manifest_digest``
  and ``manifest.pairing.model_digest``);
* verify that a given (model, manifest) pair is still consistent.

Invariants
----------
* **Idempotent stamp.** ``stamp_pairing`` may be called on already-stamped
  inputs and produces the same digests, because pre-existing pointers are
  stripped before recomputation.
* **Volatile fields excluded.** Timestamps and detached signature blocks
  do not participate in the digest, so re-serializing or re-signing does
  not break pairing.
* **Content addressed.** Digests are computed via the T2 canonical
  serializer, so ``sha256-v1`` is the algorithm tag stored in
  ``manifest.pairing.algo``.

Non-goals
---------
* This module does **not** touch disk.
* It does **not** wire into ``manifest.generator`` or ``core.parser``.
  Future publishers may call these helpers; Phase 1 keeps them pure.
"""

from __future__ import annotations

import copy
from typing import Any, Mapping

from architecture_model.lifecycle.serialization import digest
from architecture_model.lifecycle.versions import SchemaVersions

MODEL_VOLATILE_PATHS: tuple[tuple[str, ...], ...] = (
    ("meta", "generated_at"),
    ("meta", "signatures"),
)
MANIFEST_VOLATILE_PATHS: tuple[tuple[str, ...], ...] = (
    ("generated_at",),
    ("signatures",),
)


class PairingMismatch(ValueError):
    """Raised when a (model, manifest) pair fails digest verification."""


def compute_model_digest(model: Mapping[str, Any]) -> str:
    """Return the content digest of ``model`` excluding volatile fields."""
    return digest(model, exclude_paths=MODEL_VOLATILE_PATHS)


def compute_manifest_digest(manifest: Mapping[str, Any]) -> str:
    """Return the content digest of ``manifest`` excluding volatile fields."""
    return digest(manifest, exclude_paths=MANIFEST_VOLATILE_PATHS)


def _model_without_pointer(model: Mapping[str, Any]) -> dict:
    m = copy.deepcopy(dict(model))
    meta = m.get("meta")
    if isinstance(meta, dict) and "manifest_digest" in meta:
        meta = dict(meta)
        meta.pop("manifest_digest", None)
        m["meta"] = meta
    return m


def _manifest_without_pairing(manifest: Mapping[str, Any]) -> dict:
    m = copy.deepcopy(dict(manifest))
    m.pop("pairing", None)
    return m


def stamp_pairing(model: dict, manifest: dict) -> tuple[dict, dict]:
    """Attach pairing metadata to deep copies of ``model`` and ``manifest``.

    Idempotent: any pre-existing pairing pointers are stripped before the
    digests are recomputed, so stamping twice yields identical results.
    """
    model_out = copy.deepcopy(model)
    manifest_out = copy.deepcopy(manifest)

    model_stripped = _model_without_pointer(model_out)
    manifest_stripped = _manifest_without_pairing(manifest_out)

    model_digest = compute_model_digest(model_stripped)
    manifest_digest = compute_manifest_digest(manifest_stripped)

    manifest_out["pairing"] = {
        "model_digest": model_digest,
        "algo": SchemaVersions.DIGEST_ALGO,
    }
    meta = model_out.setdefault("meta", {})
    meta["manifest_digest"] = manifest_digest

    return model_out, manifest_out


def verify_pairing(model: Mapping[str, Any], manifest: Mapping[str, Any]) -> None:
    """Raise :class:`PairingMismatch` unless the pair is consistent."""
    pairing = manifest.get("pairing")
    if not isinstance(pairing, Mapping) or "model_digest" not in pairing:
        raise PairingMismatch("pairing metadata missing on manifest")
    meta = model.get("meta")
    if not isinstance(meta, Mapping) or "manifest_digest" not in meta:
        raise PairingMismatch("pairing metadata missing on model")

    expected_model = pairing["model_digest"]
    expected_manifest = meta["manifest_digest"]

    actual_model = compute_model_digest(_model_without_pointer(model))
    if actual_model != expected_model:
        raise PairingMismatch(
            f"model digest mismatch: expected {expected_model}, got {actual_model}"
        )

    actual_manifest = compute_manifest_digest(_manifest_without_pairing(manifest))
    if actual_manifest != expected_manifest:
        raise PairingMismatch(
            f"manifest digest mismatch: expected {expected_manifest}, got {actual_manifest}"
        )


def assert_cross_system_files(manifest: Mapping[str, Any]) -> list[str]:
    """Return ``manifest['cross_system_files']`` or an empty list.

    Light accessor for root manifests; not a validator.
    """
    value = manifest.get("cross_system_files", [])
    if value is None:
        return []
    return list(value)
