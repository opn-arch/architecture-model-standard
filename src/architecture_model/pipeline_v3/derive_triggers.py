"""pipeline_v3.derive_triggers — Behavior-to-behavior trigger emission (Part 17a2).

Consumes :class:`ScanResult` + list of :class:`BehaviorCandidate` and
produces a list of :class:`TriggerEdge` values connecting behaviors
whose source functions call each other.

Algorithm
---------

For each BehaviorCandidate ``A`` owned by module ``M_A`` with function
``fn_A``:

1. Look up ``fn_A``'s ``calls`` list from the scanned module's function
   dict. ``calls`` is a de-duped list of bare callee names (both
   ``foo()`` and ``obj.foo()`` surface as ``"foo"`` — the manifest
   scanner does not preserve receivers).
2. For each callee name ``x``:
   a. **Local resolution** — a public function ``x`` defined in ``M_A``
      that also has a BehaviorCandidate → target = that candidate.
   b. **Imported resolution** — search behaviors whose ``function_name
      == x`` AND whose ``owner_module`` is imported by ``M_A``:
      - ``from M import x`` in ``M_A.imports`` → candidate.owner_module
        must equal ``M``.
      - ``import M`` in ``M_A.imports`` → any behavior in module ``M``
        (any function name matching) qualifies.
   c. If exactly one candidate matches → emit ``TriggerEdge(A.id,
      match.id)``. Ambiguous matches are skipped to bound noise.
3. Self-triggers (A → A) are dropped.

Determinism
-----------

Output list sorted by ``(from_behavior, to_behavior)``. Duplicates
collapsed at emit time.

Non-scope for 17a2: ``sequence:`` field on emitted edges (composite
detection — 17a3). Call-chain metadata on ``traces-to`` (17a4).
"""

from __future__ import annotations

from dataclasses import dataclass

from architecture_model.pipeline_v3.derive_behaviors import BehaviorCandidate
from architecture_model.pipeline_v3.scan import ScannedModule, ScanResult

__all__ = ["TriggerEdge", "derive_triggers"]


@dataclass(frozen=True)
class TriggerEdge:
    """A directed behavior→behavior trigger edge."""

    from_behavior: str
    to_behavior: str


def _parse_imports(imports: list[str]) -> tuple[dict[str, set[str]], set[str]]:
    """Return ``(from_imports, module_imports)``.

    ``from_imports``: ``module → set of imported symbol names`` derived
    from ``from M import x[, y]`` (both single and multi-symbol).

    ``module_imports``: set of module names imported via ``import M``
    or bare dotted-name form (as normalized by upstream stages).
    """
    from_imports: dict[str, set[str]] = {}
    module_imports: set[str] = set()

    for raw in imports:
        s = raw.strip()
        if not s:
            continue
        if s.startswith("from "):
            # "from M import X" or "from M import X, Y"
            parts = s.split(None, 3)
            # ["from", "M", "import", "X, Y"]
            if len(parts) >= 4 and parts[2] == "import":
                mod = parts[1]
                symbols = {
                    sym.strip().split(" as ")[0]
                    for sym in parts[3].split(",")
                    if sym.strip()
                }
                from_imports.setdefault(mod, set()).update(symbols)
        elif s.startswith("import "):
            parts = s.split()
            if len(parts) >= 2:
                # Strip "as alias" tail if present
                module_imports.add(parts[1].split(".")[0])
                # Also record the full dotted name for exact-match resolution
                module_imports.add(parts[1])
        else:
            # Bare dotted name (as emitted by upstream normalization)
            module_imports.add(s)

    return from_imports, module_imports


def _function_calls_of(mod: ScannedModule, function_name: str) -> list[str]:
    """Return the ``calls`` list for ``function_name`` in ``mod``.

    Looks at module-level functions first, then class methods (via
    ``method_details``). Returns ``[]`` when not found or when the
    function has no captured calls.
    """
    for fn in mod.functions:
        if (fn.get("name") or "") == function_name:
            return list(fn.get("calls") or [])
    for cls in mod.classes:
        for meth in cls.get("method_details") or []:
            if (meth.get("name") or "") == function_name:
                return list(meth.get("calls") or [])
    return []


def derive_triggers(
    scan: ScanResult,
    behaviors: list[BehaviorCandidate],
) -> list[TriggerEdge]:
    """Derive behavior-to-behavior ``triggers`` edges.

    Args:
        scan: ScanResult carrying module-level ``calls`` metadata.
        behaviors: BehaviorCandidates from :func:`derive_behaviors`.

    Returns:
        Deterministically sorted, deduped list of ``TriggerEdge``.
    """
    if not behaviors:
        return []

    # module → ScannedModule
    modules_by_name: dict[str, ScannedModule] = {m.name: m for m in scan.modules}

    # module → list[BehaviorCandidate] (for imported-resolution)
    behs_by_module: dict[str, list[BehaviorCandidate]] = {}
    # (module, function_name) → BehaviorCandidate (for exact-name lookup)
    beh_by_module_func: dict[tuple[str, str], BehaviorCandidate] = {}
    # function_name → list[BehaviorCandidate] (for ambiguous fallback)
    beh_by_func: dict[str, list[BehaviorCandidate]] = {}
    for b in behaviors:
        behs_by_module.setdefault(b.owner_module, []).append(b)
        beh_by_module_func[(b.owner_module, b.function_name)] = b
        beh_by_func.setdefault(b.function_name, []).append(b)

    edges: set[tuple[str, str]] = set()

    for src in behaviors:
        mod = modules_by_name.get(src.owner_module)
        if mod is None:
            continue
        calls = _function_calls_of(mod, src.function_name)
        if not calls:
            continue

        from_imports, module_imports = _parse_imports(mod.imports)

        for callee_name in calls:
            # 1. Local resolution
            local = beh_by_module_func.get((src.owner_module, callee_name))
            if local is not None and local.id != src.id:
                edges.add((src.id, local.id))
                continue

            # 2. Imported resolution — collect candidates
            candidates: list[BehaviorCandidate] = []

            # 2a. from M import callee_name → M/callee_name behaviors
            for imp_mod, syms in from_imports.items():
                if callee_name in syms:
                    hit = beh_by_module_func.get((imp_mod, callee_name))
                    if hit is not None and hit.id != src.id:
                        candidates.append(hit)

            # 2b. import M → any behavior in M matching callee_name
            for cand in beh_by_func.get(callee_name, []):
                if cand.id == src.id:
                    continue
                # Match if candidate's module appears (in whole or as a
                # prefix segment) in the caller's module_imports set.
                if cand.owner_module in module_imports:
                    candidates.append(cand)
                    continue
                # Also match when the caller imported a parent package
                # and the candidate lives in a submodule.
                for imp in module_imports:
                    if cand.owner_module == imp or cand.owner_module.startswith(
                        imp + "."
                    ):
                        candidates.append(cand)
                        break

            # Deduplicate candidates by id preserving order
            seen: set[str] = set()
            unique = [c for c in candidates
                      if not (c.id in seen or seen.add(c.id))]

            # Only emit when unambiguous (single distinct match)
            if len(unique) == 1:
                edges.add((src.id, unique[0].id))

    return sorted(
        (TriggerEdge(from_behavior=a, to_behavior=b) for a, b in edges),
        key=lambda e: (e.from_behavior, e.to_behavior),
    )
