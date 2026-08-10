"""Pipeline coordinator with DAG resolution and recursive decomposition."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from architecture_model.pipeline.learning import LearningStore
from architecture_model.pipeline.protocol import PipelineContext, Stage, StageResult


class PipelineCoordinator:
    """Resolves stage dependencies and runs minimum stages needed to reach a target."""

    def __init__(self, stages: dict[str, Stage], learning_store: LearningStore | None = None) -> None:
        self._stages = stages
        self._learning = learning_store

    def resolve_order(self, target: str) -> list[str]:
        """Topological sort of deps needed to reach target."""
        if target not in self._stages:
            raise KeyError(f"Unknown stage: {target}")

        needed: set[str] = set()
        self._collect_deps(target, needed, set())
        return self._topo_sort(needed)

    def _collect_deps(self, name: str, needed: set[str], visiting: set[str]) -> None:
        if name in needed:
            return
        if name not in self._stages:
            raise KeyError(f"Unknown stage: {name}")
        if name in visiting:
            raise RuntimeError(f"Circular dependency detected involving: {name}")
        visiting.add(name)
        for dep in self._stages[name].requires:
            self._collect_deps(dep, needed, visiting)
        visiting.discard(name)
        needed.add(name)

    def _topo_sort(self, names: set[str]) -> list[str]:
        """Kahn's algorithm on the subset."""
        in_degree: dict[str, int] = {n: 0 for n in names}
        for n in names:
            for dep in self._stages[n].requires:
                if dep in names:
                    in_degree[n] += 1

        queue = sorted(n for n, d in in_degree.items() if d == 0)
        result: list[str] = []
        while queue:
            node = queue.pop(0)
            result.append(node)
            for n in sorted(names):
                if node in self._stages[n].requires and n not in result:
                    in_degree[n] -= 1
                    if in_degree[n] == 0:
                        queue.append(n)

        if len(result) != len(names):
            raise RuntimeError("Circular dependency detected")
        return result

    def run_to(self, target: str, ctx: PipelineContext) -> dict[str, StageResult]:
        """Run minimum stages to produce target. Skips cached."""
        order = self.resolve_order(target)
        results: dict[str, StageResult] = {}
        for name in order:
            if ctx.has(name):
                results[name] = ctx.cache[name]
                continue
            stage = self._stages[name]
            result = stage.run(ctx)
            ctx.cache[name] = result
            results[name] = result
        return results

    def run_stage(self, stage_name: str, ctx: PipelineContext) -> StageResult:
        """Run single stage + its deps. Returns target's result."""
        results = self.run_to(stage_name, ctx)
        return results[stage_name]

    def run_all(self, ctx: PipelineContext) -> dict[str, StageResult]:
        """Run all stages in dep order. Detects circular deps."""
        # Inject learning data into context
        if self._learning and not ctx.prior_corrections:
            ctx.prior_corrections = self._learning.corrections_as_evidence()
        if self._learning and not ctx.learning_store:
            ctx.learning_store = self._learning
        if self._learning and not ctx.calibration:
            # Load calibration for all modules
            for stage_name in self._stages:
                cal = self._learning.get_calibration(stage_name)
                if cal:
                    ctx.calibration[stage_name] = cal

        all_names: set[str] = set(self._stages.keys())
        visiting: set[str] = set()
        visited: set[str] = set()
        for name in all_names:
            self._check_cycle(name, visiting, visited)

        order = self._topo_sort(all_names)
        results: dict[str, StageResult] = {}
        for name in order:
            if ctx.has(name):
                results[name] = ctx.cache[name]
                continue
            stage = self._stages[name]
            result = stage.run(ctx)
            ctx.cache[name] = result
            results[name] = result

        # Record quality history
        self._record_quality(results)

        return results

    def _record_quality(self, results: dict[str, StageResult]) -> None:
        """Record stage quality scores to learning store."""
        if not self._learning:
            return
        scores = {name: float(r.quality.score) for name, r in results.items()}
        self._learning.record_run(datetime.now().isoformat()[:10], scores)

    def get_prior_evidence(self) -> list:
        """Get corrections from learning store as prior evidence for stages."""
        if not self._learning:
            return []
        return self._learning.corrections_as_evidence()

    def get_calibration(self, module: str) -> dict[str, float]:
        """Get calibration overrides for a module."""
        if not self._learning:
            return {}
        return self._learning.get_calibration(module)

    def _check_cycle(self, name: str, visiting: set[str], visited: set[str]) -> None:
        if name in visited:
            return
        if name in visiting:
            raise RuntimeError(f"Circular dependency detected involving: {name}")
        visiting.add(name)
        for dep in self._stages[name].requires:
            if dep in self._stages:
                self._check_cycle(dep, visiting, visited)
        visiting.discard(name)
        visited.add(name)

    def run_recursive(
        self, ctx: PipelineContext, *, max_depth: int = 3, leaf_threshold: int = 5
    ) -> dict[str, Any]:
        """Run all stages, write artifacts, then recurse into large components.

        For each component with more files than leaf_threshold, creates a
        sub-context scoped to that component's files and re-runs the pipeline.
        Artifacts are written at each level.
        """
        from .artifacts import write_artifacts
        from .context_gen import write_context

        results = self.run_all(ctx)

        # Write artifacts at current level
        write_artifacts(ctx)
        write_context(ctx)

        # Recurse into large components
        subsystems: dict[str, dict[str, Any]] = {}
        allocate_result = ctx.get("allocate")
        if allocate_result and max_depth > 0:
            from .allocate_types import AllocationResult
            allocation: AllocationResult = allocate_result.output

            for comp in allocation.components:
                if len(comp.files) > leaf_threshold:
                    # Create sub-context scoped to component files
                    sub_dir = ctx.output_dir / "subsystems" / comp.id.lower()
                    sub_ctx = PipelineContext(
                        repo_path=ctx.repo_path,
                        output_dir=sub_dir,
                        scope=comp.id,
                        scope_files=comp.files,
                    )
                    # Run recursively at reduced depth
                    sub_result = self.run_recursive(
                        sub_ctx, max_depth=max_depth - 1, leaf_threshold=leaf_threshold
                    )
                    subsystems[comp.id] = sub_result

        return {
            "results": results,
            "depth": max_depth,
            "subsystems": subsystems,
            "artifacts_dir": str(ctx.output_dir),
        }
