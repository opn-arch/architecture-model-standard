"""
Pipeline Orchestrator: MPC training loop coordination.

Ties together all components (surrogate, oracle, dataset store, evaluator,
controller, trainer, repo_fetcher) into the Model Predictive Control loop
for iterative fine-tuning of the local surrogate model.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from architecture_model.training.surrogate import Surrogate
from architecture_model.training.oracle import Oracle
from architecture_model.training.dataset import DatasetStore, TrainingExample
from architecture_model.training.evaluator import Evaluator
from architecture_model.training.controller import MPCController, MPCState
from architecture_model.training.trainer import LoRATrainer
from architecture_model.training.repo_fetcher import RepoFetcher, RepoInfo
from architecture_model.training.oracle_coverage import ManifestCoverageComputer
from architecture_model.training.oracle_performance import OraclePerformanceStore, OracleResult
from architecture_model.training.oracle_context import OracleContextBuilder
from architecture_model.training.oracle_critique import SelfCritiqueRefiner
from architecture_model.training.oracle_evolution import PromptEvolver
from architecture_model.training.coverage_scorer import CoverageScorer
from architecture_model.training.best_of_n import BestOfNGenerator
from architecture_model.training.autoencoder import RoundTripEvaluator, RoundTripScore
from architecture_model.core.validator import validate_model
from architecture_model.core.merger import enrich_from_manifest

logger = logging.getLogger(__name__)

# Training threshold: how many new oracle-validated examples before triggering LoRA fine-tune
_TRAINING_THRESHOLD = 50


class TrainingPipeline:
    """Orchestrates the MPC training loop.

    Coordinates repo discovery, surrogate extraction, oracle verification,
    loss evaluation, dataset storage, and periodic LoRA fine-tuning.
    """

    def __init__(
        self,
        surrogate: Surrogate,
        oracle: Oracle,
        store: DatasetStore,
        evaluator: Evaluator,
        controller: MPCController,
        trainer: LoRATrainer,
        repo_fetcher: RepoFetcher,
        training_targets: list | None = None,
        oracle_learning_enabled: bool = False,
        round_trip_evaluator: Optional[RoundTripEvaluator] = None,
    ) -> None:
        self.surrogate = surrogate
        self.oracle = oracle
        self.store = store
        self.evaluator = evaluator
        self.controller = controller
        self.trainer = trainer
        self.repo_fetcher = repo_fetcher
        self.training_targets = training_targets

        # Round-trip (autoencoder) evaluator: self-supervised quality signal
        self._round_trip_evaluator = round_trip_evaluator

        # Oracle self-learning subsystem (optional)
        self._oracle_learning_enabled = oracle_learning_enabled
        self._coverage_computer = ManifestCoverageComputer()
        self._oracle_perf_store: Optional[OraclePerformanceStore] = None
        self._critique_refiner: Optional[SelfCritiqueRefiner] = None
        self._prompt_evolver: Optional[PromptEvolver] = None
        self._oracle_context_builder_class = OracleContextBuilder

        # Best-of-N DPO preference pair generator
        self._best_of_n: Optional[BestOfNGenerator] = BestOfNGenerator(
            surrogate=self.surrogate,
            evaluator=self.evaluator,
            n=4,
            temperature=0.8,
        )

        if oracle_learning_enabled:
            db_path = str(Path("./data/oracle_performance.db"))
            self._oracle_perf_store = OraclePerformanceStore(db_path)
            self._critique_refiner = SelfCritiqueRefiner(
                self.oracle, self._coverage_computer
            )
            self._prompt_evolver = PromptEvolver(self._oracle_perf_store)

    async def run_iteration(self, n_repos: int = 50) -> MPCState:
        """Run a single MPC iteration.

        1. Discover repos via repo_fetcher
        2. For each repo: extract with surrogate, optionally verify with oracle
        3. Save training examples to store
        4. Trigger training if threshold reached
        5. Advance controller state

        Returns:
            Updated MPCState after this iteration.
        """
        # Step 1: Discover repos
        repos = await self.repo_fetcher.discover(n_repos)

        # Step 2: Process each repo
        for repo in repos:
            await self._process_repo(repo)

        # Step 3: Check training threshold
        new_examples = self.store.new_examples_since_last_train()
        if new_examples >= _TRAINING_THRESHOLD:
            self._trigger_training()

        # Step 4: Advance iteration
        self.controller.next_iteration()

        return self.controller.state

    async def run_loop(self, max_iterations: int = 100) -> MPCState:
        """Run the full MPC loop until convergence, budget exhaustion, or max iterations.

        Args:
            max_iterations: Maximum number of iterations to run.

        Returns:
            Final MPCState.
        """
        for _ in range(max_iterations):
            await self.run_iteration()

            # Check termination conditions
            if self.controller.is_converged():
                logger.info("Convergence detected, stopping loop.")
                break

            if self.controller.state.oracle_budget_remaining <= 0:
                logger.info("Oracle budget exhausted, stopping loop.")
                break

        return self.controller.state

    async def _process_repo(self, repo: RepoInfo) -> None:
        """Process a single repo: extract, evaluate, store.

        Uses enhanced extraction (ContextBuilder + MultiPass + Refiner).
        Records loss in Pareto front. Saves DPO preferences when quality is low.

        Args:
            repo: Repository metadata from discovery.
        """
        # Clone and get paths
        clone_path = self.repo_fetcher.clone(repo)

        # Use enhanced extraction pipeline
        local_model, confidence = await self.enhanced_extract(clone_path)
        if local_model is None:
            return

        # Still need code context for oracle comparison
        code_context = self._read_code_context(clone_path)

        # Round-trip evaluation: self-supervised quality signal
        round_trip_score: Optional[RoundTripScore] = None
        if self._round_trip_evaluator is not None and code_context:
            try:
                round_trip_score = await self._round_trip_evaluator.evaluate(
                    original_code=code_context,
                    model=local_model,
                )
                logger.info(
                    "Round-trip score: class=%.2f method=%.2f func=%.2f "
                    "import=%.2f module=%.2f semantic=%.2f intent=%.2f overall=%.3f",
                    round_trip_score.class_overlap,
                    round_trip_score.method_overlap,
                    round_trip_score.function_overlap,
                    round_trip_score.import_similarity,
                    round_trip_score.module_ratio,
                    round_trip_score.semantic_class_match,
                    round_trip_score.intent_coverage,
                    round_trip_score.overall,
                )
                # Modulate confidence: low round-trip → lower confidence → more oracle queries
                confidence = 0.6 * confidence + 0.4 * round_trip_score.overall
            except Exception as e:
                logger.warning("Round-trip evaluation failed: %s", e)

        # Compute validator score
        validation_result = validate_model(local_model)
        validator_score = float(validation_result.score)

        # Decide whether to query oracle
        should_query = self.controller.should_query_oracle(
            validator_score=validator_score,
            confidence=confidence,
            is_novel=True,
        )

        oracle_output = None
        loss_vector = None
        cov_score = None

        if should_query:
            # Build oracle context (manifest-enriched if learning enabled)
            if self._oracle_learning_enabled:
                oracle_ctx_builder = self._oracle_context_builder_class(clone_path)
                oracle_context = oracle_ctx_builder.build()
            else:
                oracle_context = code_context

            # Query oracle for ground truth
            oracle_model = await self.oracle.extract_model(oracle_context)
            self.controller.record_oracle_query()

            if oracle_model is not None:
                # Self-critique refinement (if enabled)
                if self._critique_refiner is not None:
                    manifest = oracle_ctx_builder._generate_manifest() if self._oracle_learning_enabled else {}
                    oracle_model = await self._critique_refiner.refine(
                        oracle_model, manifest, oracle_context
                    )

                # Coverage scoring: measure quality as penalty signal (no model modification)
                if self._oracle_learning_enabled:
                    manifest = oracle_ctx_builder._generate_manifest() if 'manifest' not in dir() else manifest
                    cov_score = CoverageScorer().score(oracle_model, manifest)
                    logger.info(
                        "Coverage score: edge=%.2f prec=%.2f coh=%.2f dir=%.2f overall=%.2f",
                        cov_score.edge_coverage, cov_score.edge_precision,
                        cov_score.cohesion, cov_score.directionality, cov_score.overall,
                    )

                # Record performance (if enabled)
                if self._oracle_perf_store is not None:
                    manifest = oracle_ctx_builder._generate_manifest() if self._oracle_learning_enabled else {}
                    coverage = self._coverage_computer.compute(manifest, oracle_model)
                    validation_result_oracle = validate_model(oracle_model)
                    self._oracle_perf_store.record(OracleResult(
                        repo_url=repo.url,
                        prompt_variant=f"v{self._prompt_evolver.version}" if self._prompt_evolver else "v1",
                        coverage_score=coverage.overall,
                        validator_score=float(validation_result_oracle.score),
                        iteration=self.controller.state.iteration,
                        uncovered_modules=str(coverage.uncovered_modules) if coverage.uncovered_modules else None,
                        uncovered_interfaces=str(coverage.uncovered_interfaces) if coverage.uncovered_interfaces else None,
                    ))

                    # Check prompt evolution trigger
                    if self._prompt_evolver and self._prompt_evolver.should_evolve(self.controller.state.iteration):
                        new_prompt = await self._prompt_evolver.evolve(self.oracle)
                        self.oracle.set_system_prompt(new_prompt)

                # Compute loss between surrogate and oracle
                loss = self.evaluator.compute_loss(
                    local_model=local_model,
                    oracle_model=oracle_model,
                    coverage_score=cov_score if self._oracle_learning_enabled else None,
                )
                loss_vector = {
                    "structural_accuracy": loss.structural_accuracy,
                    "completeness": loss.completeness,
                    "validator_score": loss.validator_score,
                }

                # Enrich local model from manifest and compute naming_accuracy
                naming_accuracy = self._compute_naming_accuracy(local_model, clone_path)
                if naming_accuracy is not None:
                    loss_vector["naming_accuracy"] = naming_accuracy

                oracle_output = oracle_model.to_yaml()

                # Record loss for Pareto-based convergence tracking
                self.controller.record_loss(loss)

                # Generate Best-of-N DPO preference pairs
                if loss.structural_accuracy < 0.8 and self._best_of_n is not None:
                    pair = await self._best_of_n.generate(code_context, oracle_model)
                    if pair is not None:
                        best, worst = pair
                        margin = best.loss.structural_accuracy - worst.loss.structural_accuracy
                        self.store.save_preference(
                            prompt=code_context,
                            chosen=best.yaml_output,
                            rejected=worst.yaml_output,
                            margin=margin,
                            iteration=self.controller.state.iteration,
                        )

        # Save training example
        metadata: dict = {}
        if round_trip_score is not None:
            metadata["round_trip"] = {
                "class_overlap": round_trip_score.class_overlap,
                "method_overlap": round_trip_score.method_overlap,
                "function_overlap": round_trip_score.function_overlap,
                "import_similarity": round_trip_score.import_similarity,
                "module_ratio": round_trip_score.module_ratio,
                "semantic_class_match": round_trip_score.semantic_class_match,
                "intent_coverage": round_trip_score.intent_coverage,
                "overall": round_trip_score.overall,
            }

        example = TrainingExample(
            repo_url=repo.url,
            repo_sha=repo.default_branch,
            code_context=code_context,
            local_output=local_model.to_yaml(),
            oracle_output=oracle_output,
            loss_vector=loss_vector,
            iteration=self.controller.state.iteration,
            metadata=metadata,
        )
        self.store.save(example)

    _DPO_THRESHOLD = 10  # Minimum preference pairs before DPO training

    def _trigger_training(self) -> None:
        """Prepare dataset and run LoRA fine-tuning + DPO if enough data."""
        logger.info("Training threshold reached, starting fine-tuning.")
        dataset = self.trainer.prepare_dataset(self.store)

        if self.training_targets:
            # Multi-adapter training
            output_base = Path("./adapters")
            self.trainer.train_all(dataset, self.training_targets, output_base=output_base)
        else:
            # Single model training (backward compat)
            output_dir = Path("./adapters/default")
            self.trainer.train(dataset, output_dir=output_dir)

        # DPO training: trigger when enough preference pairs accumulated
        pref_count = self.store.count_preferences()
        if pref_count >= self._DPO_THRESHOLD:
            logger.info(
                "DPO threshold reached (%d preferences), starting DPO fine-tuning.",
                pref_count,
            )
            try:
                from .trainer_dpo import DPOLoRATrainer

                prefs = self.store.export_preferences()
                try:
                    from datasets import Dataset as HFDataset
                except ImportError:
                    logger.warning("datasets not installed, skipping DPO training.")
                    return
                pref_dataset = HFDataset.from_list(prefs)
                dpo_trainer = DPOLoRATrainer(
                    base_model=self.trainer._config.hf_name
                    if hasattr(self.trainer, "_config")
                    else "Qwen/Qwen2.5-7B-Instruct",
                )
                dpo_output = Path("./adapters/dpo")
                dpo_trainer.train(pref_dataset, output_dir=dpo_output, epochs=1)
                logger.info("DPO training complete, adapter saved to %s", dpo_output)
            except Exception as e:
                logger.warning("DPO training failed: %s", e)

    def _read_code_context(self, clone_path: Path) -> str:
        """Read code from a cloned repo to produce context for extraction.

        Simple implementation: concatenates Python files found in the repo.
        """
        code_parts: list[str] = []
        path = Path(clone_path)

        if path.is_dir():
            for py_file in sorted(path.rglob("*.py")):
                try:
                    content = py_file.read_text(errors="ignore")
                    code_parts.append(f"# {py_file.relative_to(path)}\n{content}")
                except (OSError, ValueError):
                    continue

        return "\n\n".join(code_parts) if code_parts else ""

    def _compute_naming_accuracy(
        self, local_model, clone_path: Path
    ) -> Optional[float]:
        """Compute naming_accuracy by enriching local model from repo manifest.

        Scans the cloned repo with AST to build a manifest, then calls
        enrich_from_manifest() which compares the model's predicted symbols
        against ground-truth class/function names.

        Returns:
            naming_accuracy float (0.0-1.0), or None if enrichment not possible.
        """
        try:
            from architecture_model.manifest.scanner import _scan_file

            path = Path(clone_path)
            if not path.is_dir():
                return None

            # Build lightweight manifest from Python files
            modules: list[dict] = []
            py_files = sorted(path.rglob("*.py"))[:100]
            for f in py_files:
                try:
                    meta = _scan_file(path, f)
                    modules.append(meta)
                except Exception:
                    continue

            if not modules:
                return None

            manifest = {"modules": modules, "interfaces": []}
            result = enrich_from_manifest(local_model, manifest)
            return result.naming_accuracy

        except Exception as e:
            logger.warning("Naming accuracy computation failed: %s", e)
            return None

    async def enhanced_extract(self, repo_path: Path) -> tuple:
        """Enhanced extraction: context_builder → multi_pass → refiner.

        Uses AST-guided context selection, 5-pass hierarchical extraction,
        and iterative validator-feedback refinement for higher quality results.

        Args:
            repo_path: Path to the cloned repository source code.

        Returns:
            Tuple of (ArchitectureModel | None, confidence: float).
        """
        from .context_builder import ContextBuilder
        from .multi_pass import MultiPassExtractor
        from .refiner import ModelRefiner

        # Build smart context
        cb = ContextBuilder(repo_path)
        slices = cb.build()

        # Multi-pass extraction
        extractor = MultiPassExtractor(
            self.surrogate, slices, project_name=repo_path.name
        )
        model = await extractor.extract()
        if model is None:
            return None, 0.0

        # Refine with validator feedback
        refiner = ModelRefiner(self.surrogate, max_rounds=2)
        model = await refiner.refine(model, slices.combined())

        confidence = self.surrogate.confidence(model)
        return model, confidence
