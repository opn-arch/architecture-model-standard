"""
Pipeline Orchestrator: MPC training loop coordination.

Ties together all components (surrogate, oracle, dataset store, evaluator,
controller, trainer, repo_fetcher) into the Model Predictive Control loop
for iterative fine-tuning of the local surrogate model.
"""

from __future__ import annotations

import logging
from pathlib import Path

from architecture_model.training.surrogate import Surrogate
from architecture_model.training.oracle import Oracle
from architecture_model.training.dataset import DatasetStore, TrainingExample
from architecture_model.training.evaluator import Evaluator
from architecture_model.training.controller import MPCController, MPCState
from architecture_model.training.trainer import LoRATrainer
from architecture_model.training.repo_fetcher import RepoFetcher, RepoInfo
from architecture_model.core.validator import validate_model

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
    ) -> None:
        self.surrogate = surrogate
        self.oracle = oracle
        self.store = store
        self.evaluator = evaluator
        self.controller = controller
        self.trainer = trainer
        self.repo_fetcher = repo_fetcher
        self.training_targets = training_targets

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

        if should_query:
            # Query oracle for ground truth
            oracle_model = await self.oracle.extract_model(code_context)

            if oracle_model is not None:
                # Compute loss between surrogate and oracle
                loss = self.evaluator.compute_loss(
                    local_model=local_model,
                    oracle_model=oracle_model,
                )
                loss_vector = {
                    "structural_accuracy": loss.structural_accuracy,
                    "completeness": loss.completeness,
                    "reconstruction_fidelity": loss.reconstruction_fidelity,
                    "validator_score": loss.validator_score,
                }
                oracle_output = str(oracle_model)

                # Record loss for Pareto-based convergence tracking
                self.controller.record_loss(loss)

                # Save DPO preference when quality is low
                if loss.structural_accuracy < 0.6:
                    self.store.save_preference(
                        prompt=code_context,
                        chosen=str(oracle_model),
                        rejected=str(local_model),
                        margin=1.0 - loss.structural_accuracy,
                        iteration=self.controller.state.iteration,
                    )

        # Save training example
        example = TrainingExample(
            repo_url=repo.url,
            repo_sha=repo.default_branch,
            code_context=code_context,
            local_output=str(local_model),
            oracle_output=oracle_output,
            loss_vector=loss_vector,
            iteration=self.controller.state.iteration,
        )
        self.store.save(example)

    def _trigger_training(self) -> None:
        """Prepare dataset and run LoRA fine-tuning for all target models."""
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
