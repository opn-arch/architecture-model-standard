"""Pipeline coordinator with DAG resolution and recursive decomposition."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from architecture_model.pipeline.global_learning import GlobalLearningStore
from architecture_model.pipeline.learning import LearningStore
from architecture_model.pipeline.llm_refine import refine_with_llm, _LLM_REFINABLE_STAGES
from architecture_model.pipeline.protocol import (
    EnrichmentRecord,
    PipelineContext,
    QualityGateError,
    Stage,
    StageResult,
    StageQualityReview,
)


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
        return self._run_recorded(order, ctx, record_quality=False)

    def _execute_order(
        self, order: list[str], ctx: PipelineContext, stage_history: list[Any]
    ) -> dict[str, StageResult]:
        results: dict[str, StageResult] = {}
        for name in order:
            if ctx.has(name):
                results[name] = ctx.cache[name]
                continue
            stage = self._stages[name]
            started = datetime.now(timezone.utc)
            timer = perf_counter()
            try:
                result = stage.run(ctx)
                result = self._maybe_refine(name, result, ctx)
                ctx.cache[name] = result
                results[name] = result
                self._evaluate_gates(name, result, ctx)
            except Exception:
                stage_history.append(self._stage_record(
                    name, stage, ctx, started, perf_counter() - timer, None, "failed"
                ))
                raise
            stage_history.append(self._stage_record(
                name, stage, ctx, started, perf_counter() - timer, result, "completed"
            ))
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
        return self._run_recorded(order, ctx, record_quality=True)

    def _run_recorded(
        self, order: list[str], ctx: PipelineContext, *, record_quality: bool
    ) -> dict[str, StageResult]:
        from .history import append_pipeline_history

        ctx.run_id = str(uuid4())
        started = datetime.now(timezone.utc)
        timer = perf_counter()
        stage_history: list[Any] = []
        try:
            results = self._execute_order(order, ctx, stage_history)
            if record_quality:
                self._record_quality(results)
        except Exception as exc:
            record = self._build_run_record(
                ctx, started, perf_counter() - timer, stage_history, "failed", str(exc)
            )
            try:
                append_pipeline_history(ctx.repo_path, record)
            except Exception:
                pass
            raise
        try:
            append_pipeline_history(
                ctx.repo_path,
                self._build_run_record(ctx, started, perf_counter() - timer, stage_history, "completed"),
            )
        except Exception as exc:
            ctx.history_warnings.append(f"Pipeline history persistence failed: {exc}")
        return results

    @staticmethod
    def _stage_record(name, stage, ctx, started, elapsed, result, status):
        from .history import StageHistoryRecord

        output = getattr(result, "output", None)
        output_summary = PipelineCoordinator._result_summary(output)
        input_summary = {
            dep: PipelineCoordinator._result_summary(ctx.cache[dep].output)
            for dep in getattr(stage, "requires", []) if dep in ctx.cache
        }
        return StageHistoryRecord(
            name=name,
            started_at=started.isoformat().replace("+00:00", "Z"),
            completed_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            duration_ms=max(0, int(elapsed * 1000)),
            score=getattr(getattr(result, "quality", None), "score", None),
            status=status,
            invoked_by="pipeline-coordinator",
            dependencies=list(getattr(stage, "requires", [])),
            input_summary=input_summary,
            output_summary=output_summary,
            artifacts=[str(path) for path in getattr(output, "written_paths", [])],
        )

    @staticmethod
    def _result_summary(output) -> dict[str, Any]:
        if output is None:
            return {}
        counts: dict[str, int] = {}
        for attr in (
            "modules", "edges", "routes", "constraints", "test_files", "docs",
            "capabilities", "actors", "behaviors", "components", "unallocated",
            "relationships", "layers", "interfaces", "requirements", "contracts",
            "systems", "system_models", "written_paths", "issues",
        ):
            value = getattr(output, attr, None)
            if isinstance(value, (list, tuple, dict, set)):
                counts[attr] = len(value)
        return {"type": type(output).__name__, "counts": counts, **counts}

    @staticmethod
    def _build_run_record(ctx, started, elapsed, stages, status, error=""):
        from .history import ComponentHistoryRecord, ModuleHistoryRecord, PipelineRunRecord

        observe = ctx.get("observe")
        allocate = ctx.get("allocate")
        inventory = getattr(observe, "output", None)
        allocation = getattr(allocate, "output", None)
        modules = list(getattr(inventory, "modules", []) or [])
        routes = list(getattr(inventory, "routes", []) or [])
        components = list(getattr(allocation, "components", []) or [])
        file_to_component = {
            str(path): comp.id for comp in components for path in getattr(comp, "files", [])
        }
        timestamp = started.isoformat().replace("+00:00", "Z")
        stage_names = [stage.name for stage in stages]
        infer_output = getattr(ctx.get("infer"), "output", None)
        specify_output = getattr(ctx.get("specify"), "output", None)
        contract_output = getattr(ctx.get("contract"), "output", None)
        relate_output = getattr(ctx.get("relate"), "output", None)
        capabilities = list(getattr(infer_output, "capabilities", []) or [])
        behaviors = list(getattr(infer_output, "behaviors", []) or [])
        actors = list(getattr(infer_output, "actors", []) or [])
        interfaces = list(getattr(specify_output, "interfaces", []) or [])
        requirements = list(getattr(specify_output, "requirements", []) or [])
        contracts = list(getattr(contract_output, "contracts", []) or [])
        relationships = list(getattr(relate_output, "relationships", []) or [])
        comp_entities: dict[str, set[str]] = {comp.id: set() for comp in components}
        cap_to_components: dict[str, set[str]] = {}
        for comp in components:
            if getattr(comp, "capability_id", ""):
                cap_to_components.setdefault(comp.capability_id, set()).add(comp.id)
        for rel in relationships:
            if rel.rel_type == "realizes" and rel.from_id in comp_entities:
                cap_to_components.setdefault(rel.to_id, set()).add(rel.from_id)
        for cap in capabilities:
            owner_ids = set(cap_to_components.get(cap.id, set()))
            if cap.evidence_source == "routes":
                owner_ids.update(
                    file_to_component.get(str(route.file), "") for route in routes
                )
                owner_ids.discard("")
            elif cap.evidence_source:
                owner_ids.update(
                    comp_id for path, comp_id in file_to_component.items()
                    if path in cap.evidence_source
                )
            cap_to_components[cap.id] = owner_ids
            for comp_id in owner_ids:
                comp_entities[comp_id].add(cap.id)
        for behavior in behaviors:
            for comp_id in cap_to_components.get(behavior.capability_id, set()):
                comp_entities[comp_id].add(behavior.id)
                if behavior.actor_id:
                    comp_entities[comp_id].add(behavior.actor_id)
        actor_ids = {actor.id for actor in actors}
        for comp_id in comp_entities:
            comp_entities[comp_id].intersection_update(
                {cap.id for cap in capabilities} | {item.id for item in behaviors} | actor_ids
            )
        for interface in interfaces:
            if interface.component_id in comp_entities:
                comp_entities[interface.component_id].add(interface.id)
        for requirement in requirements:
            comp_id = file_to_component.get(str(requirement.source_file), "")
            if comp_id:
                comp_entities[comp_id].add(requirement.id)
        comp_artifacts = PipelineCoordinator._existing_artifacts(ctx, components)
        component_records = []
        for comp in components:
            files = [str(path) for path in getattr(comp, "files", [])]
            entity_ids = sorted(comp_entities[comp.id])
            counts = {
                "files": len(files), "modules": len(files),
                "capabilities": sum(item.startswith("CAP-") for item in entity_ids),
                "behaviors": sum(item.startswith("BEH-") for item in entity_ids),
                "actors": sum(item.startswith("ACT-") for item in entity_ids),
                "interfaces": sum(item.startswith("IF-") for item in entity_ids),
                "requirements": sum(item.startswith("REQ-") for item in entity_ids),
                "contracts": sum(item.target_component == comp.id for item in contracts),
                "relationships": sum(
                    item.from_id == comp.id or item.to_id == comp.id
                    or item.from_id in entity_ids or item.to_id in entity_ids
                    for item in relationships
                ),
            }
            component_records.append(ComponentHistoryRecord(
                component_id=comp.id,
                name=comp.name,
                files=files,
                modules=files,
                stages=stage_names,
                timestamp=timestamp,
                invoked_by=ctx.invocation or ctx.invocation_source,
                source=ctx.invocation_source,
                scope=ctx.scope,
                parent_run_id=ctx.parent_run_id,
                produced_entity_ids=entity_ids,
                artifacts=comp_artifacts.get(comp.id, []),
                counts=counts,
            ))
        module_records = []
        for module in modules:
            path = str(module.path)
            module_routes = [route for route in routes if str(getattr(route, "file", "")) == path]
            module_entity_ids = {
                item.id for item in requirements if str(item.source_file) == path
            }
            for cap in capabilities:
                if path and (path in str(cap.evidence_source) or (
                    cap.evidence_source == "routes" and any(str(route.file) == path for route in module_routes)
                )):
                    module_entity_ids.add(cap.id)
            for behavior in behaviors:
                if behavior.capability_id in module_entity_ids:
                    module_entity_ids.add(behavior.id)
                    if behavior.actor_id:
                        module_entity_ids.add(behavior.actor_id)
            comp_id = file_to_component.get(path, "")
            module_entity_ids.update(
                interface.id for interface in interfaces if interface.component_id == comp_id
                and any(method in {item.name for item in module.functions} for method in interface.methods)
            )
            module_artifacts = []
            inventory_path = ctx.output_dir / "inventory.json"
            if inventory_path.is_file():
                from .history import serialize_artifact_path

                module_artifacts.append(serialize_artifact_path(inventory_path, ctx.repo_path))
            module_records.append(ModuleHistoryRecord(
                path=path,
                module=Path(path).stem,
                component_id=comp_id,
                timestamp=timestamp,
                invoked_by=ctx.invocation or ctx.invocation_source,
                source=ctx.invocation_source,
                scope=ctx.scope,
                parent_run_id=ctx.parent_run_id,
                produced_functions=[item.name for item in module.functions],
                produced_classes=[item.name for item in module.classes],
                produced_routes=[f"{item.method} {item.path}" for item in module_routes],
                produced_constants=[item.name for item in module.constants],
                produced_entity_ids=sorted(module_entity_ids),
                artifacts=module_artifacts,
                counts={
                    "functions": len(module.functions), "classes": len(module.classes),
                    "routes": len(module_routes), "constants": len(module.constants),
                    "entities": len(module_entity_ids),
                },
            ))
        artifacts = [artifact for stage in stages for artifact in stage.artifacts]
        return PipelineRunRecord(
            run_id=ctx.run_id,
            started_at=timestamp,
            completed_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            duration_ms=max(0, int(elapsed * 1000)),
            source=ctx.invocation_source,
            invocation=ctx.invocation,
            scope=ctx.scope,
            parent_run_id=ctx.parent_run_id,
            status=status,
            stages=stages,
            components=component_records,
            modules=module_records,
            produced_artifacts=artifacts,
            error=error,
        )

    @staticmethod
    def _existing_artifacts(ctx, components) -> dict[str, list[str]]:
        from .history import serialize_artifact_path

        result: dict[str, list[str]] = {comp.id: [] for comp in components}
        shared = [
            ctx.output_dir / name for name in
            ("functional.yaml", "structure.yaml", "relationships.yaml", "validation.json")
        ]
        for comp in components:
            candidates = [*shared]
            safe_name = comp.id.lower().replace(" ", "-")
            candidates.extend([
                ctx.output_dir / "specs" / f"{safe_name}.yaml",
                ctx.output_dir / "contracts" / f"{safe_name}.yaml",
            ])
            result[comp.id] = [
                serialize_artifact_path(path, ctx.repo_path) for path in candidates if path.is_file()
            ]
        return result

    def _record_quality(self, results: dict[str, StageResult]) -> None:
        """Record stage quality scores to learning store."""
        if not self._learning:
            return
        scores = {name: float(r.quality.score) for name, r in results.items()}
        self._learning.record_run(datetime.now().isoformat()[:10], scores)

    def _maybe_refine(self, stage_name: str, result: StageResult, ctx: PipelineContext) -> StageResult:
        """Run LLM refinement on heuristic output if applicable."""
        if ctx.llm_callback is None or stage_name not in _LLM_REFINABLE_STAGES:
            return result

        inputs = self._build_refinement_inputs(stage_name, ctx)
        coro = refine_with_llm(ctx, stage_name, inputs, result)

        try:
            loop = asyncio.get_running_loop()
            # Already in async context — run in thread to avoid nested loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                refined_result, log = pool.submit(asyncio.run, coro).result()
        except RuntimeError:
            refined_result, log = asyncio.run(coro)

        if log is not None:
            ctx.refinement_logs.append(log)

        return refined_result

    def _build_refinement_inputs(self, stage_name: str, ctx: PipelineContext) -> dict:
        """Build inputs dict for refine_with_llm from cached stage results."""
        inputs: dict[str, Any] = {}

        observe_result = ctx.get("observe")
        infer_result = ctx.get("infer")
        allocate_result = ctx.get("allocate")

        if observe_result is not None:
            modules = getattr(observe_result.output, "modules", [])
            inputs["modules"] = [
                {"path": str(getattr(m, "path", "")), "functions": [f.name for f in getattr(m, "functions", [])]}
                for m in modules
            ]
            imports = []
            for m in modules:
                for imp in getattr(m, "imports", []):
                    imports.append({"source": str(getattr(m, "path", "")), "target": str(imp)})
            inputs["imports"] = imports

        if infer_result is not None:
            caps = getattr(infer_result.output, "capabilities", [])
            inputs["capabilities"] = [
                {"id": getattr(c, "id", ""), "name": getattr(c, "name", "")}
                for c in caps
            ]

        if allocate_result is not None:
            comps = getattr(allocate_result.output, "components", [])
            inputs["components"] = [
                {"id": getattr(c, "id", ""), "name": getattr(c, "name", ""),
                 "layer": getattr(c, "layer", ""), "files": [str(f) for f in getattr(c, "files", [])]}
                for c in comps
            ]

        return inputs

    def _evaluate_gates(self, stage_name: str, result: StageResult, ctx: PipelineContext) -> None:
        """Evaluate quality gates and optionally run LLM review with auto-corrections."""
        from .gates import get_gates_for_stage

        gates = get_gates_for_stage(stage_name)
        gate_results = [g.evaluate(result.quality) for g in gates]

        # Enhanced LLM review if callback available (skip for refined stages — redundant)
        llm_review = ""
        suggestions: list[str] = []
        component_reviews: dict[str, str] = {}
        if ctx.llm_callback is not None and stage_name not in _LLM_REFINABLE_STAGES:
            try:
                from .stage_review import build_semantic_review_prompt, parse_correction_response
                import asyncio

                components = self._extract_component_data(result, ctx)
                modules = self._extract_module_data(result, ctx)

                prompt = build_semantic_review_prompt(
                    stage_name, result.quality, gate_results,
                    components, modules, summary=result.summary,
                )

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    pass
                else:
                    response = loop.run_until_complete(
                        ctx.llm_enrich(stage_name, prompt, {"purpose": "semantic_review"})
                    )
                    if response:
                        parsed = parse_correction_response(response)
                        llm_review = response
                        suggestions = parsed.suggestions
            except Exception:
                pass

        review = StageQualityReview(
            stage=stage_name,
            quality=result.quality,
            gate_results=gate_results,
            llm_review=llm_review,
            suggestions=suggestions,
            component_reviews=component_reviews,
        )
        ctx.review_log.append(review)

        blockers = [gr for gr in gate_results if gr.blocks]
        if blockers:
            raise QualityGateError(
                f"Stage '{stage_name}' blocked: " + "; ".join(gr.message for gr in blockers),
                gate_results=blockers,
            )

    def _extract_component_data(self, result: StageResult, ctx: PipelineContext) -> list[dict]:
        """Extract component info from stage result for review prompt."""
        components = []
        for comp_id, comp_q in result.quality.component_scores.items():
            components.append({
                "id": comp_id, "name": comp_id, "intent": "",
                "file_count": 0, "quality": comp_q.score,
            })
        return components

    def _extract_module_data(self, result: StageResult, ctx: PipelineContext) -> list[dict]:
        """Extract module info from stage result for review prompt."""
        modules = []
        if hasattr(result.output, '__iter__') and not isinstance(result.output, (str, dict)):
            try:
                for item in result.output:
                    if hasattr(item, 'path') and hasattr(item, 'quality_score'):
                        modules.append({
                            "path": str(item.path),
                            "functions": len(getattr(item, 'functions', [])),
                            "quality": item.quality_score,
                        })
            except TypeError:
                pass
        return modules

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
                        import time as _time

                        ctx.enrichment_log.append(
                            EnrichmentRecord(
                                entity_id=cap.id,
                                entity_type="capability",
                                stage="infer",
                                old_value=old,
                                new_value=cap.name,
                                prompt=prompt,
                                response=new_name.strip(),
                                timestamp=_time.strftime("%Y-%m-%dT%H:%M:%S"),
                            )
                        )

            # Deduplicate capability names
            seen_cap_names: dict[str, int] = {}
            for cap in output.capabilities:
                if cap.name in seen_cap_names:
                    seen_cap_names[cap.name] += 1
                    old = cap.name
                    cap.name = f"{cap.name} ({seen_cap_names[cap.name]})"
                    changes.append(f"DEDUP CAP {cap.id}: '{old}' → '{cap.name}'")
                else:
                    seen_cap_names[cap.name] = 1

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
                        import time as _time

                        ctx.enrichment_log.append(
                            EnrichmentRecord(
                                entity_id=comp.id,
                                entity_type="component",
                                stage="allocate",
                                old_value=old,
                                new_value=comp.name,
                                prompt=prompt,
                                response=new_name.strip(),
                                timestamp=_time.strftime("%Y-%m-%dT%H:%M:%S"),
                            )
                        )

            # Deduplicate component names
            seen_comp_names: dict[str, int] = {}
            for comp in output.components:
                if comp.name in seen_comp_names:
                    seen_comp_names[comp.name] += 1
                    old = comp.name
                    comp.name = f"{comp.name} ({seen_comp_names[comp.name]})"
                    changes.append(f"DEDUP COMP {comp.id}: '{old}' → '{comp.name}'")
                else:
                    seen_comp_names[comp.name] = 1

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
        from .history import finalize_pipeline_history, serialize_artifact_path

        artifacts = [
            serialize_artifact_path(path, ctx.repo_path)
            for path in ctx.output_dir.rglob("*")
            if path.is_file()
            and path != ctx.repo_path / ".architecture" / "pipeline-history.jsonl"
        ]
        try:
            emit = results.get("emit")
            emitted = emit.output if emit and hasattr(emit.output, "final_model_score") else None
            final_validation = None
            if emitted:
                final_validation = {
                    "extraction_score": emitted.extraction_score,
                    "final_model_score": emitted.final_model_score,
                    "final_model_path": serialize_artifact_path(
                        emitted.final_model_path, ctx.repo_path
                    ) if emitted.final_model_path else "",
                    "promoted": emitted.promoted,
                    "issues": emitted.final_validation_issues,
                }
            finalize_pipeline_history(
                ctx.repo_path, ctx.run_id, artifacts, final_validation=final_validation
            )
        except Exception as exc:
            ctx.history_warnings.append(f"Pipeline history finalization failed: {exc}")

        return {
            "results": results,
            "depth": max_depth,
            "subsystems": {},  # now handled by synthesize+emit
            "artifacts_dir": str(ctx.output_dir),
        }
