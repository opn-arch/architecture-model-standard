"""MPC Training Loop for Architecture Model extraction.

Install with: pip install architecture-model-standard[training]
"""
from architecture_model.training.pipeline import TrainingPipeline
from architecture_model.training.dataset import DatasetStore, TrainingExample
from architecture_model.training.evaluator import Evaluator, LossVector
from architecture_model.training.surrogate import Surrogate
from architecture_model.training.oracle import Oracle, BudgetTracker
from architecture_model.training.controller import MPCController, MPCState
from architecture_model.training.trainer import LoRATrainer
from architecture_model.training.repo_fetcher import RepoFetcher, RepoInfo
from architecture_model.training.context_builder import ContextBuilder, ContextSlices
from architecture_model.training.multi_pass import MultiPassExtractor, PassResult
from architecture_model.training.refiner import ModelRefiner
from architecture_model.training.model_config import (
    ModelConfig, MODEL_REGISTRY, get_model_config, resolve_config,
    resolve_training_targets,
)

__all__ = [
    "TrainingPipeline", "DatasetStore", "TrainingExample",
    "Evaluator", "LossVector", "Surrogate", "Oracle", "BudgetTracker",
    "MPCController", "MPCState", "LoRATrainer", "RepoFetcher", "RepoInfo",
    "ContextBuilder", "ContextSlices", "MultiPassExtractor", "PassResult",
    "ModelRefiner",
    "ModelConfig", "MODEL_REGISTRY", "get_model_config", "resolve_config",
    "resolve_training_targets",
]
