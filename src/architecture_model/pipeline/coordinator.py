"""Pipeline coordinator with DAG resolution and recursive decomposition."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from architecture_model.pipeline.global_learning import GlobalLearningStore
from architecture_model.pipeline.learning import LearningStore
from architecture_model.pipeline.protocol import PipelineContext, Stage, StageResult


class PipelineCoordinator:
    """Resolves stage dependencies and runs minimum stages needed to reach a target."""

    def __init__(
        self,
        stages: dict[str, Stage],
        learning_store: LearningStore | None = None,
        global_learning: GlobalLearningStore | None = None,
    ) -> None:
        self._stages = stages
        self._learning = learning_store
        self._global_learning = global_learning

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
        if self._global_learning and not ctx.global_learning:
            ctx.global_learning = self._global_learning

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

    async def enrich_stage_output(self, stage_name: str, ctx: PipelineContext) -> list[str]:
        """Post-stage LLM enrichment: improve names/descriptions of low-quality outputs.

        Called by the MCP tool after a stage completes, if ctx.llm_callback is set.
        Returns list of changes made.
        """
        if ctx.llm_callback is None:
            return []

        result = ctx.get(stage_name)
        if result is None:
            return []

        changes: list[str] = []

        if stage_name == "infer":
            # Enrich capability names that are too generic
            from .infer_types import InferenceResult

            _GENERIC = {
                "Web Routes",
                "Domain Logic",
                "CLI Commands",
                "Core",
                "Scripts",
                "Src",
                "CLI Main",
                "CLI Runner",
                "Utils",
                "Helpers",
                "Lib",
                "App",
                "Main",
                "Services",
                "Models",
                "API",
                "Tests",
                "Config",
                "Common",
            }

            output: InferenceResult = result.output
            for cap in output.capabilities:
                # Enrich if name is in generic set OR is very short (1-2 words, <=12 chars)
                is_generic = cap.name in _GENERIC or (
                    len(cap.name) <= 12 and len(cap.name.split()) <= 2
                )
                if is_generic:
                    prompt = (
                        f"Given a software component with these files: {cap.evidence_source}, "
                        f"suggest a specific, descriptive name (2-4 words) that captures its "
                        f"primary business purpose. Current generic name: '{cap.name}'. "
                        f"Return ONLY the new name, nothing else."
                    )
                    new_name = await ctx.llm_enrich("infer", prompt, {"cap_id": cap.id})
                    if new_name and new_name.strip():
                        old = cap.name
                        cap.name = new_name.strip().strip('"').strip("'")
                        changes.append(f"CAP {cap.id}: '{old}' → '{cap.name}'")

        elif stage_name == "allocate":
            # Enrich component names
            from .allocate_types import AllocationResult

            output = result.output
            for comp in output.components:
                if comp.name and len(comp.name) <= 10:  # Short/generic names
                    files_str = ", ".join(str(f) for f in comp.files[:5])
                    prompt = (
                        f"Given a software component containing files: [{files_str}], "
                        f"suggest a clear 2-4 word name describing its responsibility. "
                        f"Return ONLY the name."
                    )
                    new_name = await ctx.llm_enrich("allocate", prompt, {"comp_id": comp.id})
                    if new_name and new_name.strip():
                        old = comp.name
                        comp.name = new_name.strip().strip('"').strip("'")
                        changes.append(f"COMP {comp.id}: '{old}' → '{comp.name}'")

        elif stage_name == "relate":
            # Enrich ambiguous relationship descriptions
            pass  # Future: classify weak relationships

        elif stage_name == "observe":
            # Nothing to enrich — purely AST-based
            pass

        return changes

    def run_recursive(
        self, ctx: PipelineContext, *, max_depth: int = 3, leaf_threshold: int = 5
    ) -> dict[str, Any]:
        """Run all stages including decompose→synthesize→emit which handle recursion.

        The synthesize stage runs scoped sub-pipelines for each detected system.
        max_depth and leaf_threshold are passed via ctx.config for synthesize to use.
        """
        ctx.config["max_depth"] = max_depth
        ctx.config["leaf_threshold"] = leaf_threshold
        ctx.config["coordinator"] = self  # synthesize needs this for scoped runs

        results = self.run_all(ctx)

        # Write legacy artifacts for backward compatibility
        from .artifacts import write_artifacts
        from .context_gen import write_context

        write_artifacts(ctx)
        write_context(ctx)

        return {
            "results": results,
            "depth": max_depth,
            "subsystems": {},  # now handled by synthesize+emit
            "artifacts_dir": str(ctx.output_dir),
        }
