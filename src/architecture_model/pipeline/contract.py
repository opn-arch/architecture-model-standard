"""Contract pipeline stage — maps test files to components as behavioral contracts."""
from __future__ import annotations

import time
from pathlib import Path

from .allocate_types import AllocationResult
from .contract_types import ContractResult, TestContract
from .observe_types import Inventory
from .protocol import (
    Diagnostic,
    PipelineContext,
    QualityMetrics,
    StageResult,
    Uncertainty,
)


class ContractStage:
    """Maps test files to architecture components as behavioral contracts."""

    name: str = "contract"
    requires: list[str] = ["observe", "allocate"]

    def run(self, ctx: PipelineContext) -> StageResult[ContractResult]:
        start = time.time()
        diagnostics: list[Diagnostic] = []
        uncertainties: list[Uncertainty] = []

        observe_result = ctx.get("observe")
        allocate_result = ctx.get("allocate")
        if not all([observe_result, allocate_result]):
            raise RuntimeError("contract requires observe and allocate")

        inventory: Inventory = observe_result.output
        allocation: AllocationResult = allocate_result.output

        contracts: list[TestContract] = []

        # Build lookup structures for matching
        stem_to_comp: dict[str, str] = {}  # file stem → comp id
        name_to_comp: dict[str, str] = {}  # lowercase comp name → comp id
        dir_to_comp: dict[str, str] = {}   # directory name → comp id
        for comp in allocation.components:
            name_to_comp[comp.name.lower()] = comp.id
            for f in comp.files:
                stem_to_comp[f.stem] = comp.id
                # Track directory parts as potential component identifiers
                for part in f.parts[:-1]:  # exclude filename
                    if part.lower() not in ("src", "lib", "pkg", ""):
                        dir_to_comp[part.lower()] = comp.id

        # Match test files to components
        components_with_tests: set[str] = set()
        for test_file in inventory.test_files:
            matched = False
            for target in test_file.targets:
                comp_id = _match_target(target, test_file.path, stem_to_comp, name_to_comp)
                if comp_id:
                    contracts.append(TestContract(
                        test_file=str(test_file.path),
                        target_component=comp_id,
                    ))
                    components_with_tests.add(comp_id)
                    matched = True
            # Fallback: match by directory name (e.g., tests/core/test_foo.py)
            if not matched:
                comp_id = _match_by_directory(test_file.path, name_to_comp, dir_to_comp)
                if comp_id:
                    contracts.append(TestContract(
                        test_file=str(test_file.path),
                        target_component=comp_id,
                    ))
                    components_with_tests.add(comp_id)

        total_comps = len(allocation.components)
        coverage_ratio = (len(components_with_tests) / total_comps * 100) if total_comps > 0 else 100.0

        result = ContractResult(
            contracts=contracts,
            coverage_ratio=coverage_ratio,
        )

        quality = QualityMetrics(
            score=int(coverage_ratio),
            sub_scores={
                "test_coverage_ratio": coverage_ratio,
                "contract_count": float(len(contracts)),
            },
            thresholds={"test_coverage_ratio": 50.0},
        )

        duration_ms = int((time.time() - start) * 1000)

        return StageResult(
            output=result,
            quality=quality,
            diagnostics=diagnostics,
            uncertainties=uncertainties,
            input_hash=str(len(inventory.test_files)),
            duration_ms=duration_ms,
            version="1.0",
            summary=f"Extracted {len(contracts)} contracts from {len(inventory.test_files)} test files.",
        )


def _match_target(
    target: str,
    test_path: Path,
    stem_to_comp: dict[str, str],
    name_to_comp: dict[str, str],
) -> str:
    """Match a test target to a component using multiple strategies.

    Strategies (in priority order):
    1. Exact stem match: target == file stem in component
    2. Suffix-style match: X_test.py already resolved to target "X"
    3. Component name match: target == component name (case-insensitive)
    4. Substring match: component name is contained in target
    """
    # 1. Exact stem match (existing behavior)
    if target in stem_to_comp:
        return stem_to_comp[target]

    # 2. Component name exact match
    if target.lower() in name_to_comp:
        return name_to_comp[target.lower()]

    # 3. Substring: target contains a component name (e.g., "basic_click" contains "click")
    # Use longest match to avoid false positives
    best_match = ""
    best_id = ""
    for comp_name, comp_id in name_to_comp.items():
        if len(comp_name) >= 3 and comp_name in target.lower():
            if len(comp_name) > len(best_match):
                best_match = comp_name
                best_id = comp_id
    if best_id:
        return best_id

    # 4. Substring: file stem contained in target (e.g., stem "click" in target "basic_click")
    # Use longest match to avoid false positives
    best_stem = ""
    best_id = ""
    for stem, comp_id in stem_to_comp.items():
        if len(stem) >= 3 and stem in target:
            if len(stem) > len(best_stem):
                best_stem = stem
                best_id = comp_id
    if best_id:
        return best_id

    # 5. Reverse: target contained in a file stem
    for stem, comp_id in stem_to_comp.items():
        if len(target) >= 3 and target in stem:
            return comp_id

    return ""


def _match_by_directory(test_path: Path, name_to_comp: dict[str, str], dir_to_comp: dict[str, str]) -> str:
    """Match test file by its parent directory name matching a component name or dir."""
    for part in test_path.parts:
        lower = part.lower()
        if lower in ("tests", "test", ""):
            continue
        if lower in name_to_comp:
            return name_to_comp[lower]
        if lower in dir_to_comp:
            return dir_to_comp[lower]
    return ""
