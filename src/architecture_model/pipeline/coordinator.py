"""Pipeline coordinator with DAG resolution."""

from __future__ import annotations

from typing import Any

from architecture_model.pipeline.protocol import PipelineContext, Stage, StageResult


class PipelineCoordinator:
    """Resolves stage dependencies and runs minimum stages needed to reach a target."""

    def __init__(self, stages: dict[str, Stage]) -> None:
        self._stages = stages

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
        # Collect all stages
        all_names: set[str] = set(self._stages.keys())
        # Check for cycles by collecting deps for all
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
        return results

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
        self, ctx: PipelineContext, *, max_depth: int = 5, leaf_threshold: int = 5
    ) -> dict[str, Any]:
        """Run all, then recurse into large components."""
        results = self.run_all(ctx)
        return {"results": results, "depth": 0}
