"""pipeline_v3.derive_promises — Attribute derivation stage (T0.14 Phase 6.2).

Consumes :class:`ScanResult` from the scan stage and produces a flat list
of :class:`Promise` records. Each :class:`ScannedModule` contributes three
Promises, one per canonical scan-derived attribute:

    - ``intent``    ← module docstring
    - ``delivers``  ← sorted list of public function names
    - ``provides``  ← sorted list of public class names

Missing signals produce :class:`PromiseStatus.TYPED_GAP` Promises with
typed ``gap_type`` labels so downstream chain-closure can categorize the
gap without ambiguity. Owner entity is the module's dotted name (as
computed by :func:`architecture_model.pipeline_v3.scan._dotted_name`).

Design notes:
    - "Public" = name does not start with underscore.
    - `delivers`/`provides` content is sorted for deterministic hashing.
    - The three attributes are emitted in a fixed order (intent, delivers,
      provides) so per-module Promise ordering is stable independent of
      dict-iteration order.
"""

from __future__ import annotations

from typing import Any

from architecture_model.core.promise import Promise, PromiseStatus
from architecture_model.pipeline_v3.scan import ScannedModule, ScanResult

__all__ = ["derive_promises", "derive_promises_for_module"]

_PROVENANCE = "pipeline_v3.derive_promises"


def _public_names(items: list[dict[str, Any]]) -> list[str]:
    """Return sorted list of ``name`` fields for items whose name does not
    start with an underscore. Missing/blank names are skipped."""
    out = [
        (it.get("name") or "").strip()
        for it in items
        if (it.get("name") or "").strip() and not (it.get("name") or "").startswith("_")
    ]
    return sorted(out)


def _intent_promise(mod: ScannedModule) -> Promise:
    doc = (mod.docstring or "").strip()
    if doc:
        return Promise(
            attribute="intent",
            content=doc,
            owner_entity=mod.name,
            status=PromiseStatus.OPEN,
            provenance=_PROVENANCE,
        )
    return Promise(
        attribute="intent",
        content="",
        owner_entity=mod.name,
        status=PromiseStatus.TYPED_GAP,
        gap_type="missing-intent",
        provenance=_PROVENANCE,
    )


def _delivers_promise(mod: ScannedModule) -> Promise:
    names = _public_names(mod.functions)
    if names:
        return Promise(
            attribute="delivers",
            content=names,
            owner_entity=mod.name,
            status=PromiseStatus.OPEN,
            provenance=_PROVENANCE,
        )
    return Promise(
        attribute="delivers",
        content=[],
        owner_entity=mod.name,
        status=PromiseStatus.TYPED_GAP,
        gap_type="no-public-functions",
        provenance=_PROVENANCE,
    )


def _provides_promise(mod: ScannedModule) -> Promise:
    names = _public_names(mod.classes)
    if names:
        return Promise(
            attribute="provides",
            content=names,
            owner_entity=mod.name,
            status=PromiseStatus.OPEN,
            provenance=_PROVENANCE,
        )
    return Promise(
        attribute="provides",
        content=[],
        owner_entity=mod.name,
        status=PromiseStatus.TYPED_GAP,
        gap_type="no-public-classes",
        provenance=_PROVENANCE,
    )


def derive_promises_for_module(mod: ScannedModule) -> list[Promise]:
    """Derive the three canonical Promises for a single ScannedModule.

    Order is fixed: ``[intent, delivers, provides]``.
    """
    return [_intent_promise(mod), _delivers_promise(mod), _provides_promise(mod)]


def derive_promises(scan: ScanResult) -> list[Promise]:
    """Derive Promises for every module in ``scan``.

    Modules are visited in the order they appear in ``scan.modules`` (which
    the scan stage sorts by dotted name). Within a module, Promises are
    emitted in the fixed order ``intent → delivers → provides``.
    """
    out: list[Promise] = []
    for m in scan.modules:
        out.extend(derive_promises_for_module(m))
    return out
