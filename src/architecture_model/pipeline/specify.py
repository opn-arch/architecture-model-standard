"""Specify pipeline stage — derives interface specifications from routes and exports."""

from __future__ import annotations

import re
import time
from collections import defaultdict
from pathlib import Path

from .allocate_types import AllocationResult
from .observe_types import Inventory, RouteRecord
from .protocol import (
    Diagnostic,
    PipelineContext,
    QualityMetrics,
    StageResult,
    Uncertainty,
)
from .specify_types import DerivedRequirement, InterfaceSpec, SpecifyResult


def _name_library_interface(
    comp_id: str,
    comp_name: str,
    public_symbols: dict[str, str],
    module_stems: list[str],
) -> str:
    """Generate a descriptive interface name from component metadata."""
    # Strategy 1: Single dominant class
    classes = [name for name, sig in public_symbols.items() if sig.startswith("class ")]
    if len(classes) == 1:
        return f"{classes[0]} API"
    # Strategy 2: Use component name
    if comp_name and comp_name != comp_id:
        return f"{comp_name} API"
    # Strategy 3: Use module stem
    if module_stems:
        stem = module_stems[0].replace("_", " ").title()
        return f"{stem} API"
    # Fallback
    return f"{comp_id} Library API"


# Patterns indicating constraint language in docstrings
_CONSTRAINT_PATTERNS = [
    re.compile(r"(must\s+.+?)(?:\.|$)", re.IGNORECASE),
    re.compile(r"(should\s+not\s+.+?)(?:\.|$)", re.IGNORECASE),
    re.compile(r"(requires?\s+.+?)(?:\.|$)", re.IGNORECASE),
    re.compile(r"(at\s+most\s+.+?)(?:\.|$)", re.IGNORECASE),
    re.compile(r"(at\s+least\s+.+?)(?:\.|$)", re.IGNORECASE),
]

# Constant names that imply requirements (thresholds, limits, config)
_REQ_CONSTANT_PATTERN = re.compile(
    r"^(MAX|MIN|TIMEOUT|LIMIT|BATCH|RETRY|RETRIES|THRESHOLD|DEFAULT|RATE|INTERVAL|TTL|CAPACITY)"
    r"|"
    r"(MAX|MIN|TIMEOUT|LIMIT|BATCH|RETRY|RETRIES|THRESHOLD|RATE|INTERVAL|TTL|CAPACITY|SIZE|COUNT|DEPTH|LENGTH)$",
    re.IGNORECASE,
)


def _constant_value_function(name: str, value: str) -> tuple[str, str]:
    """Return a deterministic value function and its interpretation convention."""
    try:
        target = float(value)
    except (TypeError, ValueError):
        return "", ""
    target_text = str(int(target)) if target.is_integer() else str(target)
    upper_bound = re.search(
        r"(?:^|_)(?:MAX|TIMEOUT|LIMIT|TTL)(?:_|$)", name, re.IGNORECASE
    )
    if upper_bound:
        return (
            f"V(actual) = min(1, {target_text} / max(actual, 1e-9))",
            "Value convention: actual is the observed value; values at or below the upper bound score 1.",
        )
    return (
        f"V(actual) = max(0, 1 - abs(actual - {target_text}) / max(abs({target_text}), 1))",
        "Value convention: direction is ambiguous, so value is normalized target achievement and peaks at the declared target.",
    )


def _derive_requirements(inventory: Inventory) -> list[DerivedRequirement]:
    """Derive requirements from constants, test names, and docstring constraints."""
    reqs: list[DerivedRequirement] = []
    counter = 0

    # 1. From constants
    for mod in inventory.modules:
        for const in mod.constants:
            if _REQ_CONSTANT_PATTERN.search(const.name):
                counter += 1
                readable = const.name.replace("_", " ").lower()
                value_function, convention = _constant_value_function(
                    const.name, const.value
                )
                reqs.append(
                    DerivedRequirement(
                        id=f"REQ-C{counter}",
                        name=f"{const.name} constraint",
                        text=f"System must respect {readable} = {const.value}",
                        rationale=f"Defined as constant in {mod.path}. {convention}".strip(),
                        moe=f"Verify {const.name} is respected in all call sites",
                        source_file=str(mod.path),
                        source_type="constant",
                        value_function=value_function,
                        priority="must",
                    )
                )

    # 2. From test function names
    for mod in inventory.modules:
        path_str = str(mod.path)
        is_test = "test_" in mod.path.name or mod.path.name.startswith("test")
        if not is_test:
            continue
        for func in mod.functions:
            if func.name.startswith("test_"):
                counter += 1
                # Convert test_validates_input -> "validates input"
                behavior = func.name[5:].replace("_", " ")
                reqs.append(
                    DerivedRequirement(
                        id=f"REQ-T{counter}",
                        name=f"Tested: {behavior}",
                        text=f"System must {behavior}",
                        rationale=f"Verified by test {func.name} in {mod.path}",
                        moe=f"Test {func.name} passes",
                        source_file=path_str,
                        source_type="test",
                    )
                )

    # 3. From docstring constraints
    for mod in inventory.modules:
        # Check module docstring
        _extract_docstring_reqs(
            mod.docstring, str(mod.path), "module", mod.path.stem, reqs, counter
        )
        counter += len(reqs) - counter  # sync counter (lazy but correct)
        # Check function docstrings
        for func in mod.functions:
            if func.docstring:
                before = len(reqs)
                for pat in _CONSTRAINT_PATTERNS:
                    for match in pat.finditer(func.docstring):
                        counter += 1
                        constraint_text = match.group(1).strip()
                        reqs.append(
                            DerivedRequirement(
                                id=f"REQ-D{counter}",
                                name=f"Docstring constraint: {func.name}",
                                text=constraint_text,
                                rationale=f"Documented in {func.name}() docstring in {mod.path}",
                                moe=f"Verify {func.name}() satisfies: {constraint_text}",
                                source_file=str(mod.path),
                                source_type="docstring",
                            )
                        )
        # Check class method docstrings
        for cls in mod.classes:
            for method in cls.method_details:
                if method.docstring:
                    for pat in _CONSTRAINT_PATTERNS:
                        for match in pat.finditer(method.docstring):
                            counter += 1
                            constraint_text = match.group(1).strip()
                            reqs.append(
                                DerivedRequirement(
                                    id=f"REQ-D{counter}",
                                    name=f"Docstring constraint: {cls.name}.{method.name}",
                                    text=constraint_text,
                                    rationale=f"Documented in {cls.name}.{method.name}() docstring in {mod.path}",
                                    moe=f"Verify {cls.name}.{method.name}() satisfies: {constraint_text}",
                                    source_file=str(mod.path),
                                    source_type="docstring",
                                )
                            )

    return reqs


def _extract_docstring_reqs(
    docstring: str | None,
    source_file: str,
    context_type: str,
    context_name: str,
    reqs: list[DerivedRequirement],
    counter: int,
) -> None:
    """Extract constraint requirements from a docstring."""
    if not docstring:
        return
    for pat in _CONSTRAINT_PATTERNS:
        for match in pat.finditer(docstring):
            counter += 1
            constraint_text = match.group(1).strip()
            reqs.append(
                DerivedRequirement(
                    id=f"REQ-D{counter}",
                    name=f"Docstring constraint: {context_name}",
                    text=constraint_text,
                    rationale=f"Documented in {context_type} {context_name} docstring in {source_file}",
                    moe=f"Verify {context_name} satisfies: {constraint_text}",
                    source_file=source_file,
                    source_type="docstring",
                )
            )


class SpecifyStage:
    """Derives interface specifications from observed routes and module exports."""

    name: str = "specify"
    requires: list[str] = ["observe", "allocate"]

    def run(self, ctx: PipelineContext) -> StageResult[SpecifyResult]:
        start = time.time()
        diagnostics: list[Diagnostic] = []
        uncertainties: list[Uncertainty] = []

        observe_result = ctx.get("observe")
        allocate_result = ctx.get("allocate")
        if not all([observe_result, allocate_result]):
            raise RuntimeError("specify requires observe and allocate")

        inventory: Inventory = observe_result.output
        allocation: AllocationResult = allocate_result.output

        interfaces: list[InterfaceSpec] = []
        iface_counter = 0

        # Build file→comp map and name/stems lookups
        file_to_comp: dict[Path, str] = {}
        comp_id_to_name: dict[str, str] = {}
        comp_id_to_stems: dict[str, list[str]] = {}
        for comp in allocation.components:
            comp_id_to_name[comp.id] = comp.name
            comp_id_to_stems[comp.id] = [f.stem for f in comp.files]
            for f in comp.files:
                file_to_comp[f] = comp.id

        # Group routes by component
        comp_routes: dict[str, list[RouteRecord]] = defaultdict(list)
        for route in inventory.routes:
            comp_id = file_to_comp.get(route.file, "")
            if comp_id:
                comp_routes[comp_id].append(route)

        # One REST interface per component with routes
        for comp_id, routes in comp_routes.items():
            iface_counter += 1
            methods = [f"{r.method} {r.path}" for r in routes]
            interfaces.append(
                InterfaceSpec(
                    id=f"IF-{iface_counter}",
                    name=f"{comp_id} REST API",
                    component_id=comp_id,
                    interface_type="rest",
                    methods=methods,
                    description=f"{len(routes)} endpoints",
                )
            )

        # CLI interfaces
        for mod in inventory.modules:
            has_cli = any(
                "click" in imp or "typer" in imp or "argparse" in imp
                for imp in mod.imports
            )
            if has_cli:
                comp_id = file_to_comp.get(mod.path, "")
                if comp_id:
                    iface_counter += 1
                    interfaces.append(
                        InterfaceSpec(
                            id=f"IF-{iface_counter}",
                            name=f"{mod.path.stem} CLI",
                            component_id=comp_id,
                            interface_type="cli",
                        )
                    )

        # Library API interfaces — detect public symbols consumed cross-component
        # Build per-component public symbols: comp_id -> {symbol_name: signature}
        comp_public: dict[str, dict[str, str]] = defaultdict(dict)
        # Map module dotted-style paths for import matching
        mod_path_to_comp: dict[str, str] = {}
        for mod in inventory.modules:
            comp_id = file_to_comp.get(mod.path, "")
            if not comp_id:
                continue
            # Build a dotted key from the file path stem for import matching
            stem = mod.path.stem
            parts = list(mod.path.parts)
            mod_path_to_comp[str(mod.path)] = comp_id
            for func in mod.functions:
                if not func.name.startswith("_"):
                    comp_public[comp_id][func.name] = func.signature or f"{func.name}()"
            for cls in mod.classes:
                if not cls.name.startswith("_"):
                    comp_public[comp_id][cls.name] = f"class {cls.name}"

        # Check cross-component consumption via import edges
        # comp_id -> set of symbols consumed by OTHER components
        comp_consumed: dict[str, set[str]] = defaultdict(set)
        for edge in inventory.edges:
            src_comp = file_to_comp.get(edge.source, "")
            tgt_comp = file_to_comp.get(edge.target, "")
            if src_comp and tgt_comp and src_comp != tgt_comp:
                # src imports from tgt — tgt's symbols are consumed
                for sym in edge.symbols:
                    if sym in comp_public.get(tgt_comp, {}):
                        comp_consumed[tgt_comp].add(sym)

        # Also check via raw import strings when edges are not populated
        if not inventory.edges:
            # Build dotted-path -> comp_id for import matching
            # e.g. Path("auth/core.py") -> "auth.core" -> COMP-AUTH
            dotted_to_comp: dict[str, str] = {}
            for mod in inventory.modules:
                cid = file_to_comp.get(mod.path, "")
                if cid:
                    # Convert path to dotted module name
                    p = mod.path.with_suffix("")
                    dotted = ".".join(p.parts)
                    dotted_to_comp[dotted] = cid
                    # Also register just the stem for simple imports
                    dotted_to_comp[mod.path.stem] = cid
            for mod in inventory.modules:
                src_comp = file_to_comp.get(mod.path, "")
                if not src_comp:
                    continue
                for imp in mod.imports:
                    # imp is a dotted module path like "auth.core"
                    # Try exact match, then progressively shorter prefixes
                    tgt_comp = dotted_to_comp.get(imp, "")
                    if not tgt_comp:
                        # Try base module name
                        base = imp.split(".")[0]
                        tgt_comp = dotted_to_comp.get(base, "")
                    if tgt_comp and tgt_comp != src_comp:
                        # Mark all public symbols of target as consumed
                        for sym in comp_public.get(tgt_comp, {}):
                            comp_consumed[tgt_comp].add(sym)

        # Emit one library interface per component with >=1 consumed public symbols
        for comp_id, consumed in comp_consumed.items():
            if len(consumed) >= 1:
                iface_counter += 1
                methods = sorted(
                    f"{sym}: {comp_public[comp_id][sym]}"
                    for sym in consumed
                    if sym in comp_public[comp_id]
                )
                iface_name = _name_library_interface(
                    comp_id,
                    comp_id_to_name.get(comp_id, comp_id),
                    comp_public.get(comp_id, {}),
                    comp_id_to_stems.get(comp_id, []),
                )
                interfaces.append(
                    InterfaceSpec(
                        id=f"IF-{iface_counter}",
                        name=iface_name,
                        component_id=comp_id,
                        interface_type="library",
                        methods=methods,
                        description=f"{len(consumed)} public symbols consumed by other components",
                    )
                )

        # Fallback: components with public exports but no interface yet
        comps_with_iface_so_far = {i.component_id for i in interfaces}
        for comp_id, symbols in comp_public.items():
            if comp_id not in comps_with_iface_so_far and symbols:
                iface_counter += 1
                methods = sorted(
                    f"{sym}: {sig}" for sym, sig in list(symbols.items())[:10]
                )
                iface_name = _name_library_interface(
                    comp_id,
                    comp_id_to_name.get(comp_id, comp_id),
                    symbols,
                    comp_id_to_stems.get(comp_id, []),
                )
                interfaces.append(
                    InterfaceSpec(
                        id=f"IF-{iface_counter}",
                        name=iface_name,
                        component_id=comp_id,
                        interface_type="library",
                        methods=methods,
                        description=f"{len(symbols)} public symbols exported",
                    )
                )

        result = SpecifyResult(
            interfaces=interfaces, requirements=_derive_requirements(inventory)
        )

        # Quality: % of components with at least one interface
        comp_ids = {c.id for c in allocation.components}
        comps_with_iface = {i.component_id for i in interfaces}
        coverage = len(comps_with_iface) / max(len(comp_ids), 1)
        score = max(50, int(coverage * 100))

        # Per-component quality: interface counts per component
        alloc_quality = ctx.get("allocate")
        comp_quality: dict[str, QualityMetrics] = {}
        if alloc_quality:
            base_scores = alloc_quality.quality.component_scores
            iface_per_comp: dict[str, int] = {}
            for i in interfaces:
                iface_per_comp[i.component_id] = (
                    iface_per_comp.get(i.component_id, 0) + 1
                )
            for comp in allocation.components:
                base = base_scores.get(comp.id)
                sub = dict(base.sub_scores) if base else {}
                sub["interface_count"] = float(iface_per_comp.get(comp.id, 0))
                comp_quality[comp.id] = QualityMetrics(
                    score=base.score if base else 50.0,
                    sub_scores=sub,
                    component_scores=base.component_scores if base else {},
                )

        quality = QualityMetrics(
            score=score,
            sub_scores={
                "interface_count": float(len(interfaces)),
                "rest_count": float(
                    sum(1 for i in interfaces if i.interface_type == "rest")
                ),
                "cli_count": float(
                    sum(1 for i in interfaces if i.interface_type == "cli")
                ),
                "library_count": float(
                    sum(1 for i in interfaces if i.interface_type == "library")
                ),
                "component_coverage": round(coverage, 2),
            },
            thresholds={},
            component_scores=comp_quality,
        )

        duration_ms = int((time.time() - start) * 1000)

        return StageResult(
            output=result,
            quality=quality,
            diagnostics=diagnostics,
            uncertainties=uncertainties,
            input_hash=str(len(inventory.routes)),
            duration_ms=duration_ms,
            version="1.0",
            summary=f"Specified {len(interfaces)} interfaces ({coverage:.0f}% component coverage).",
        )
