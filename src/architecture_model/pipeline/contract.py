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

        # Build module→comp map by stem name
        stem_to_comp: dict[str, str] = {}
        for comp in allocation.components:
            for f in comp.files:
                stem_to_comp[f.stem] = comp.id

        # Match test files to components
        components_with_tests: set[str] = set()
        for test_file in inventory.test_files:
            for target in test_file.targets:
                comp_id = stem_to_comp.get(target, "")
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
        )
