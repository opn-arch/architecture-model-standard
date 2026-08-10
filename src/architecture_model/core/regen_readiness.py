"""Regen readiness static metric module.

Computes how ready an enriched architecture model is for blind regeneration
by analyzing body_hint coverage, test contracts, constants, and signatures.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from architecture_model.core.types import (
    ArchitectureModel, Component, FunctionSignature, TestContract,
)


@dataclass
class FunctionReadiness:
    name: str
    score: float  # 0-100
    has_body_hint: bool
    body_hint_quality: str  # "trivial" | "short" | "complex" | "none"
    called_in_tests: int
    blockers: list[str] = field(default_factory=list)


@dataclass
class ComponentReadiness:
    id: str
    name: str
    score: float  # 0-100
    functions: list[FunctionReadiness] = field(default_factory=list)
    body_hint_coverage: float = 0.0
    body_hint_trivial_ratio: float = 0.0
    test_contract_count: int = 0
    constant_coverage: float = 0.0
    signature_coverage: float = 0.0
    dep_stub_coverage: float = 0.0
    blockers: list[str] = field(default_factory=list)


@dataclass
class RegenReadiness:
    overall: float  # 0-100
    grade: str  # A, B, C, D, F
    components: list[ComponentReadiness] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    recommendation: str = ""


def _is_trivial_hint(sig: FunctionSignature) -> bool:
    """A hint is trivial if it's a single return/assignment."""
    if sig.complexity == "TRIVIAL":
        return True
    hint = sig.body_hint
    if not hint:
        return False
    return not hint.startswith("[") and ";" not in hint


def _classify_hint(sig: FunctionSignature) -> str:
    """Classify body_hint quality."""
    if not sig.body_hint:
        return "none"
    if _is_trivial_hint(sig):
        return "trivial"
    if sig.body_hint.startswith("["):
        return "complex"
    return "short"


def _count_test_references(name: str, test_contracts: list[TestContract]) -> int:
    """Count how many test contracts reference a function by name."""
    count = 0
    for tc in test_contracts:
        if name in tc.test_method or name in tc.assertion:
            count += 1
    return count


def compute_function_readiness(sig: FunctionSignature, test_contracts: list[TestContract]) -> FunctionReadiness:
    """Compute readiness for a single function."""
    quality = _classify_hint(sig)
    has_hint = bool(sig.body_hint)
    called_in_tests = _count_test_references(sig.name, test_contracts)

    # Base score
    if not has_hint:
        score = 20.0
    elif quality == "trivial":
        score = 80.0
    elif quality == "short":
        score = 65.0
    else:  # complex
        score = 45.0

    # Test bonus
    score += min(20, called_in_tests * 7)
    score = min(100.0, score)

    blockers: list[str] = []
    if called_in_tests >= 3 and not has_hint:
        blockers.append(f"critical: {sig.name} called in {called_in_tests} tests but no body_hint")

    return FunctionReadiness(
        name=sig.name,
        score=score,
        has_body_hint=has_hint,
        body_hint_quality=quality,
        called_in_tests=called_in_tests,
        blockers=blockers,
    )


def compute_component_readiness(component: Component) -> ComponentReadiness:
    """Compute readiness for a single component."""
    sigs = component.signatures
    test_contracts = component.test_contracts
    constants = component.constants

    # body_hint_coverage
    if sigs:
        hints_count = sum(1 for s in sigs if s.body_hint)
        body_hint_coverage = hints_count / len(sigs)
    else:
        body_hint_coverage = 0.0

    # body_hint_trivial_ratio
    sigs_with_hints = [s for s in sigs if s.body_hint]
    if sigs_with_hints:
        trivial_count = sum(1 for s in sigs_with_hints if _is_trivial_hint(s))
        body_hint_trivial_ratio = trivial_count / len(sigs_with_hints)
    else:
        body_hint_trivial_ratio = 0.0

    # test_contract_count
    test_contract_count = len(test_contracts)

    # constant_coverage
    # Extract constant names referenced in test assertions
    const_names = {c.name for c in constants}
    referenced_consts: set[str] = set()
    for tc in test_contracts:
        for cname in const_names:
            if cname in tc.assertion:
                referenced_consts.add(cname)
    if referenced_consts:
        defined = sum(1 for c in referenced_consts if c in const_names)
        constant_coverage = defined / len(referenced_consts)
    else:
        constant_coverage = 1.0  # nothing missing

    # signature_coverage
    # Extract function names from test_contracts
    test_func_refs: set[str] = set()
    for tc in test_contracts:
        # Look for function-like names in test_method and assertion
        words = re.findall(r'[a-z_][a-z0-9_]*', tc.test_method + " " + tc.assertion)
        test_func_refs.update(words)
    sig_names = {s.name for s in sigs}
    matched = test_func_refs & sig_names
    if test_func_refs:
        signature_coverage = len(matched) / max(1, len(test_func_refs & sig_names) or len(matched) or 1)
        # Simpler: how many test-referenced funcs have signatures
        relevant_refs = test_func_refs & sig_names
        signature_coverage = len(relevant_refs) / max(1, len(relevant_refs)) if relevant_refs else (1.0 if not test_func_refs else 0.0)
        # Actually: defined sigs / unique funcs called in tests
        # If no test refs match any sig names, could be 0
        all_possible = {w for w in test_func_refs if len(w) > 2}  # filter noise
        matching = all_possible & sig_names
        if all_possible:
            signature_coverage = len(matching) / len(all_possible) if all_possible else 1.0
        else:
            signature_coverage = 1.0
    else:
        signature_coverage = 1.0

    # dep_stub_coverage
    requires_interfaces = [i for i in component.interfaces if i.kind == "requires"]
    if requires_interfaces:
        dep_stub_coverage = len(requires_interfaces) / max(1, len(requires_interfaces))
    else:
        dep_stub_coverage = 1.0

    # Compute per-function readiness
    func_readiness = [compute_function_readiness(s, test_contracts) for s in sigs]

    # Weighted score
    score = (
        body_hint_coverage * 25
        + body_hint_trivial_ratio * 15
        + min(1.0, test_contract_count / 10) * 20
        + constant_coverage * 15
        + signature_coverage * 15
        + dep_stub_coverage * 10
    )

    blockers: list[str] = []
    for fr in func_readiness:
        blockers.extend(fr.blockers)

    return ComponentReadiness(
        id=component.id,
        name=component.name,
        score=score,
        functions=func_readiness,
        body_hint_coverage=body_hint_coverage,
        body_hint_trivial_ratio=body_hint_trivial_ratio,
        test_contract_count=test_contract_count,
        constant_coverage=constant_coverage,
        signature_coverage=signature_coverage,
        dep_stub_coverage=dep_stub_coverage,
        blockers=blockers,
    )


def compute_regen_readiness(model: ArchitectureModel) -> RegenReadiness:
    """Compute full system regen readiness from enriched model."""
    components = model.entities.components if model.entities else []

    comp_results: list[ComponentReadiness] = []
    for comp in components:
        cr = compute_component_readiness(comp)
        comp_results.append(cr)

    # Weighted average by file count
    total_weight = 0
    weighted_sum = 0.0
    for comp, cr in zip(components, comp_results):
        weight = max(1, len(comp.files))
        weighted_sum += cr.score * weight
        total_weight += weight

    overall = weighted_sum / total_weight if total_weight else 0.0

    # Grade
    if overall >= 90:
        grade = "A"
    elif overall >= 70:
        grade = "B"
    elif overall >= 50:
        grade = "C"
    elif overall >= 30:
        grade = "D"
    else:
        grade = "F"

    # Blockers
    blockers: list[str] = []
    for cr in comp_results:
        if cr.score < 50:
            blockers.append(f"{cr.name} (score={cr.score:.0f})")

    # Recommendation
    critical_blockers = [b for cr in comp_results for b in cr.blockers if "critical" in b]
    low_const = [cr for cr in comp_results if cr.constant_coverage < 0.5]

    if all(cr.score >= 90 for cr in comp_results) and comp_results:
        recommendation = "Ready for regeneration"
    elif critical_blockers:
        # Extract first critical
        recommendation = f"Enrich components: {critical_blockers[0]}"
    elif low_const:
        recommendation = f"Extract constants for {low_const[0].name}"
    else:
        recommendation = "Improve test coverage for low-scoring components"

    return RegenReadiness(
        overall=overall,
        grade=grade,
        components=comp_results,
        blockers=blockers,
        recommendation=recommendation,
    )
