"""pipeline_v3.derive_triggers — Behavior-to-behavior trigger emission (Parts 17a2, 17a3).

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
   c. If exactly one candidate matches → collect ``TriggerEdge(A.id,
      match.id)`` in call-site order (per-source dedup preserves first
      occurrence). Ambiguous matches are skipped to bound noise.
3. Self-triggers (A → A) are dropped.

Composite detection (Part 17a3)
-------------------------------

A source behavior with ``>= COMPOSITE_MIN_TRIGGERS`` (default 3)
resolved outgoing trigger edges is treated as **composite**. Each of
its outgoing edges is tagged with ``sequence = 1..N`` in call-site
order (per the ``calls`` list from the AST scan). Behaviors below the
threshold emit edges with ``sequence = None``.

The threshold matches the plan heuristic: "a behavior whose owning
module calls >= 3 other behaviors in fixed order". Detection is
implicit — no separate ``is_composite`` flag; consumers detect
compositeness by observing at least one outgoing edge with a non-None
``sequence`` on any behavior.

Determinism
-----------

Output list sorted by ``(from_behavior, to_behavior)``. Edge identity
is ``(from, to)`` — parallel edges are not emitted. When sequences
are stamped, they reflect the source function's call-site order at
the time of derivation.

Non-scope for 17a3: Call-chain metadata on ``traces-to`` edges (17a4).
"""

from __future__ import annotations

from dataclasses import dataclass

from architecture_model.pipeline_v3.derive_behaviors import BehaviorCandidate
from architecture_model.pipeline_v3.scan import ScannedModule, ScanResult

__all__ = ["COMPOSITE_MIN_TRIGGERS", "TriggerEdge", "derive_triggers"]

#: Minimum number of unambiguously-resolved outgoing triggers required
#: for a source behavior to be treated as **composite** and receive
#: ``sequence:`` annotations on its outgoing edges. Below this
#: threshold, ``sequence`` remains ``None``.
COMPOSITE_MIN_TRIGGERS = 3


@dataclass(frozen=True)
class TriggerEdge:
    """A directed behavior→behavior trigger edge.

    Attributes:
        from_behavior: Source behavior id.
        to_behavior: Destination behavior id.
        sequence: 1-indexed ordinal position of the destination in the
            source behavior's outgoing flow, or ``None`` when the
            source has fewer than :data:`COMPOSITE_MIN_TRIGGERS`
            resolved outgoing triggers (i.e. is not treated as
            composite). Semantics mirror Part 16a's ``sequence:`` on
            declarative model triggers relationships.
    """

    from_behavior: str
    to_behavior: str
    sequence: int | None = None


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
        Edges whose source behavior resolved
        ``>= COMPOSITE_MIN_TRIGGERS`` outgoing targets carry a
        1-indexed ``sequence`` matching the source function's
        call-site order.
    """
    if not behaviors:
        return []

    # module → ScannedModule
    modules_by_name: dict[str, ScannedModule] = {m.name: m for m in scan.modules}

    # (module, function_name) → BehaviorCandidate (for exact-name lookup)
    beh_by_module_func: dict[tuple[str, str], BehaviorCandidate] = {}
    # function_name → list[BehaviorCandidate] (for imported-module fallback)
    beh_by_func: dict[str, list[BehaviorCandidate]] = {}
    for b in behaviors:
        beh_by_module_func[(b.owner_module, b.function_name)] = b
        beh_by_func.setdefault(b.function_name, []).append(b)

    # source_id → ordered list[target_id] (in call-site order, deduped)
    per_source_targets: dict[str, list[str]] = {}

    for src in behaviors:
        mod = modules_by_name.get(src.owner_module)
        if mod is None:
            continue
        calls = _function_calls_of(mod, src.function_name)
        if not calls:
            continue

        from_imports, module_imports = _parse_imports(mod.imports)

        ordered: list[str] = []
        seen_targets: set[str] = set()

        for callee_name in calls:
            # 1. Local resolution
            local = beh_by_module_func.get((src.owner_module, callee_name))
            if local is not None and local.id != src.id:
                if local.id not in seen_targets:
                    ordered.append(local.id)
                    seen_targets.add(local.id)
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
                if cand.owner_module in module_imports:
                    candidates.append(cand)
                    continue
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
                target_id = unique[0].id
                if target_id not in seen_targets:
                    ordered.append(target_id)
                    seen_targets.add(target_id)

        if ordered:
            per_source_targets[src.id] = ordered

    # Build TriggerEdges. Sources at or above the composite threshold
    # get 1-indexed sequences; others emit sequence=None.
    edges: list[TriggerEdge] = []
    for src_id, targets in per_source_targets.items():
        composite = len(targets) >= COMPOSITE_MIN_TRIGGERS
        for idx, tgt in enumerate(targets, start=1):
            edges.append(
                TriggerEdge(
                    from_behavior=src_id,
                    to_behavior=tgt,
                    sequence=idx if composite else None,
                )
            )

    edges.sort(key=lambda e: (e.from_behavior, e.to_behavior))
    return edges
