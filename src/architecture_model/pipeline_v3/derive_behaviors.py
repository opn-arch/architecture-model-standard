"""pipeline_v3.derive_behaviors — Behavior derivation stage (Part 17a1).

Consumes :class:`ScanResult` from the scan stage and produces a flat
list of :class:`BehaviorCandidate` records, one per public
module-level function (or class method) with a non-empty docstring.

Design
------

* Behavior granularity is **per public function with a docstring**.
  Private functions (name starts with ``_``) and undocumented functions
  are ignored to bound model size and noise.
* Behaviors are collected from ``ScannedModule.functions`` (module-level)
  and from each ``ScannedModule.classes[*].method_details`` (class
  methods). Class methods are surfaced only when the manifest scanner
  populated ``method_details`` — the top-level ``functions`` list is
  authoritative for module-level defs.
* Owner is the module dotted name (later rebound to the owning cluster
  by :mod:`containerize`, mirroring the derive_promises pattern).
* Identity: ``BEH-<sha1(owner_module + ":" + function_name)[:8]>``.
* Determinism: output sorted by ``(owner_module, function_name)``.

Non-scope for 17a1: behavior promises, composite detection, trigger
edges. Those land in 17a2/17a3/17a4.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from architecture_model.pipeline_v3.scan import ScannedModule, ScanResult

__all__ = [
    "BehaviorCandidate",
    "derive_behaviors",
    "derive_behaviors_for_module",
]


@dataclass(frozen=True)
class BehaviorCandidate:
    """A behavior derived from a single public documented function.

    Attributes:
        id: Deterministic ``BEH-<sha1[:8]>`` id.
        name: Function name (the source symbol).
        description: First non-empty line of the function docstring,
            trimmed. Never empty (undocumented functions are filtered
            before construction).
        owner_module: Dotted module name that defines the function.
            Rebound to a component id in the containerize stage.
        function_name: Same as ``name``; kept as a distinct field so
            call-chain enrichment (17a4) can key by symbol without
            re-parsing ``name``.
        class_name: Owning class name if the source is a method,
            otherwise ``None``.
    """

    id: str
    name: str
    description: str
    owner_module: str
    function_name: str
    class_name: str | None = None


def _behavior_id(owner_module: str, function_name: str) -> str:
    """Return the deterministic ``BEH-<sha1[:8]>`` id for a candidate."""
    payload = f"{owner_module}:{function_name}".encode("utf-8")
    return "BEH-" + hashlib.sha1(payload).hexdigest()[:8]


def _first_line(doc: str) -> str:
    """Return the first non-empty stripped line of ``doc``, or ``""``."""
    for line in doc.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _is_public(name: str) -> bool:
    """True iff ``name`` is non-empty and does not start with underscore."""
    return bool(name) and not name.startswith("_")


def _candidate_from_function(
    func: dict[str, Any],
    owner_module: str,
    class_name: str | None = None,
) -> BehaviorCandidate | None:
    """Return a BehaviorCandidate for ``func`` or ``None`` if it fails
    the public+documented filter."""
    name = (func.get("name") or "").strip()
    if not _is_public(name):
        return None
    doc = (func.get("docstring") or "").strip()
    if not doc:
        return None
    description = _first_line(doc)
    if not description:
        return None
    return BehaviorCandidate(
        id=_behavior_id(owner_module, name),
        name=name,
        description=description,
        owner_module=owner_module,
        function_name=name,
        class_name=class_name,
    )


def derive_behaviors_for_module(mod: ScannedModule) -> list[BehaviorCandidate]:
    """Derive BehaviorCandidates for a single ScannedModule.

    Emits one BehaviorCandidate per public documented module-level
    function and per public documented class method (when the scan
    populated ``method_details``).

    Deterministic order: module-level functions first, sorted by name;
    then class methods sorted by ``(class_name, method_name)``.
    """
    out: list[BehaviorCandidate] = []

    # Module-level functions
    for func in sorted(mod.functions, key=lambda f: (f.get("name") or "")):
        cand = _candidate_from_function(func, mod.name)
        if cand is not None:
            out.append(cand)

    # Class methods (only when method_details present)
    for cls in sorted(mod.classes, key=lambda c: (c.get("name") or "")):
        cls_name = (cls.get("name") or "").strip()
        if not _is_public(cls_name):
            continue
        methods = cls.get("method_details") or []
        for meth in sorted(methods, key=lambda m: (m.get("name") or "")):
            cand = _candidate_from_function(meth, mod.name, class_name=cls_name)
            if cand is not None:
                out.append(cand)

    return out


def derive_behaviors(scan: ScanResult) -> list[BehaviorCandidate]:
    """Derive BehaviorCandidates for every module in ``scan``.

    Modules are visited in ``scan.modules`` order (which the scan stage
    sorts by dotted name). Within a module, module-level functions come
    first (sorted by name), then class methods (sorted by class then
    method name).

    Duplicate ids (same ``owner_module`` + ``function_name`` — possible
    if a module defines both a top-level function and a same-named
    method) collapse to first-seen.
    """
    seen: set[str] = set()
    out: list[BehaviorCandidate] = []
    for mod in scan.modules:
        for cand in derive_behaviors_for_module(mod):
            if cand.id in seen:
                continue
            seen.add(cand.id)
            out.append(cand)
    return out
