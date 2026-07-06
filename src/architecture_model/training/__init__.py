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
from architecture_model.training.trainer_dpo import DPOLoRATrainer
from architecture_model.training.repo_fetcher import RepoFetcher, RepoInfo
from architecture_model.training.context_builder import ContextBuilder, ContextSlices
from architecture_model.training.multi_pass import MultiPassExtractor, PassResult
from architecture_model.training.refiner import ModelRefiner
from architecture_model.training.model_config import (
    ModelConfig, MODEL_REGISTRY, get_model_config, resolve_config,
    resolve_training_targets,
)
from architecture_model.training.embeddings import OllamaEmbedder, cosine_similarity
from architecture_model.training.oracle_coverage import ManifestCoverageComputer, CoverageResult
from architecture_model.training.oracle_performance import OraclePerformanceStore, OracleResult
from architecture_model.training.oracle_context import OracleContextBuilder
from architecture_model.training.oracle_few_shot import FewShotRetriever
from architecture_model.training.oracle_critique import SelfCritiqueRefiner
from architecture_model.training.oracle_evolution import PromptEvolver
from architecture_model.training.interface_enforcer import InterfaceEnforcer, EnforcementResult
from architecture_model.training.backward_validator import BackwardValidator, BackwardResult
from architecture_model.training.model_comparison import compare_models
from architecture_model.training.coverage_scorer import CoverageScorer, CoverageScore
from architecture_model.training.test_runner import TestRunner, TestRunResult
from architecture_model.training.test_analyzer import (
    TestStructureAnalyzer, TestStructure,
    TestCoverageAnalyzer, TestCoverage,
)
from architecture_model.training.code_structure import (
    parse_code_structure, parse_multi_file_code,
    StructuralGraph, ClassInfo, FunctionInfo, ImportEdge,
)
from architecture_model.training.decomposed_evaluator import (
    DecomposedRoundTripEvaluator, DecomposedRoundTripScore,
)
from architecture_model.training.semantic_matcher import SemanticMatcher, SemanticMatch
from architecture_model.training.failure_parser import FailureParser, FailureReport, TestFailure
from architecture_model.training.test_guided_generator import (
    TestGuidedGenerator, TestGuidedResult, GenerationAttempt,
)

__all__ = [
    "TrainingPipeline", "DatasetStore", "TrainingExample",
    "Evaluator", "LossVector", "Surrogate", "Oracle", "BudgetTracker",
    "MPCController", "MPCState", "LoRATrainer", "DPOLoRATrainer",
    "RepoFetcher", "RepoInfo",
    "ContextBuilder", "ContextSlices", "MultiPassExtractor", "PassResult",
    "ModelRefiner",
    "ModelConfig", "MODEL_REGISTRY", "get_model_config", "resolve_config",
    "resolve_training_targets",
    "OllamaEmbedder", "cosine_similarity",
    "ManifestCoverageComputer", "CoverageResult",
    "OraclePerformanceStore", "OracleResult",
    "OracleContextBuilder",
    "FewShotRetriever",
    "SelfCritiqueRefiner", "PromptEvolver",
    "InterfaceEnforcer", "EnforcementResult",
    "BackwardValidator", "BackwardResult",
    "compare_models",
    "CoverageScorer", "CoverageScore",
    "TestRunner", "TestRunResult",
    "TestStructureAnalyzer", "TestStructure",
    "TestCoverageAnalyzer", "TestCoverage",
    "parse_code_structure", "parse_multi_file_code",
    "StructuralGraph", "ClassInfo", "FunctionInfo", "ImportEdge",
    "DecomposedRoundTripEvaluator", "DecomposedRoundTripScore",
    "SemanticMatcher", "SemanticMatch",
    "FailureParser", "FailureReport", "TestFailure",
    "TestGuidedGenerator", "TestGuidedResult", "GenerationAttempt",
]
