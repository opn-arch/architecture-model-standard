"""Tests for DecomposedRoundTripEvaluator (per-system fidelity)."""

from __future__ import annotations

import pytest

from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
    Symbol,
    SymbolKind,
    System,
)
from architecture_model.core.decomposer import DecompositionResult
from architecture_model.training.decomposed_evaluator import (
    DecomposedRoundTripEvaluator,
    DecomposedRoundTripScore,
    _build_reference_graph_for_system,
    _compute_system_score,
    _jaccard,
)
from architecture_model.training.code_structure import (
    StructuralGraph,
    ClassInfo,
    FunctionInfo,
    ImportEdge,
    parse_code_structure,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_decomposition() -> DecompositionResult:
    """Build a DecompositionResult with 2 systems for testing."""
    # Sub-model for auth system
    auth_sub = ArchitectureModel(
        meta=ModelMeta(schema_version="1.3", project="test", system="Auth"),
        entities=Entities(
            components=[
                Component(
                    id="comp-auth-service", name="auth_service", status=Status.ACTIVE,
                    symbols=[
                        Symbol(name="AuthService", kind=SymbolKind.CLASS, members=["login", "logout"]),
                    ],
                    functions=["validate_token"],
                ),
                Component(
                    id="comp-auth-repo", name="auth_repo", status=Status.ACTIVE,
                    symbols=[
                        Symbol(name="AuthRepo", kind=SymbolKind.CLASS, members=["find_user", "save_user"]),
                    ],
                ),
            ],
        ),
        relationships=[
            Relationship(type=RelationType.DEPENDS_ON, from_id="comp-auth-service", to_id="comp-auth-repo"),
        ],
    )

    # Sub-model for data system
    data_sub = ArchitectureModel(
        meta=ModelMeta(schema_version="1.3", project="test", system="Data"),
        entities=Entities(
            components=[
                Component(
                    id="comp-database", name="database", status=Status.ACTIVE,
                    symbols=[
                        Symbol(name="Database", kind=SymbolKind.CLASS, members=["connect", "query"]),
                    ],
                    functions=["create_pool"],
                ),
            ],
        ),
        relationships=[],
    )

    # Top-level model with systems
    top_level = ArchitectureModel(
        meta=ModelMeta(schema_version="1.3", project="test"),
        entities=Entities(
            systems=[
                System(
                    id="sys-auth", name="Auth", status=Status.ACTIVE,
                    f_block="F1", complexity_score=15.0,
                    sub_model_ref="systems/auth.yaml",
                    component_ids=["comp-auth-service", "comp-auth-repo"],
                ),
                System(
                    id="sys-data", name="Data", status=Status.ACTIVE,
                    f_block="F2", complexity_score=10.0,
                    sub_model_ref="systems/data.yaml",
                    component_ids=["comp-database"],
                ),
            ],
            components=[],
        ),
        relationships=[
            Relationship(type=RelationType.DEPENDS_ON, from_id="sys-auth", to_id="sys-data"),
        ],
    )

    return DecompositionResult(
        top_level=top_level,
        sub_models={"sys-auth": auth_sub, "sys-data": data_sub},
    )


def _make_manifest() -> dict:
    """Build a manifest with module entries matching the systems."""
    return {
        "modules": [
            {
                "path": "src/auth_service/service.py",
                "classes": [
                    {"name": "AuthService", "methods": ["login", "logout"], "bases": []},
                ],
                "functions": [{"name": "validate_token", "args": ["token"]}],
                "imports": ["os", "hashlib"],
            },
            {
                "path": "src/auth_repo/repository.py",
                "classes": [
                    {"name": "AuthRepo", "methods": ["find_user", "save_user"], "bases": []},
                ],
                "functions": [],
                "imports": ["sqlalchemy"],
            },
            {
                "path": "src/database/pool.py",
                "classes": [
                    {"name": "Database", "methods": ["connect", "query"], "bases": []},
                ],
                "functions": [{"name": "create_pool", "args": ["url"]}],
                "imports": ["asyncpg"],
            },
            {
                "path": "src/utils/helpers.py",
                "classes": [],
                "functions": [{"name": "format_output", "args": ["data"]}],
                "imports": [],
            },
        ],
    }


# ---------------------------------------------------------------------------
# Tests: _jaccard helper
# ---------------------------------------------------------------------------


class TestJaccardHelper:
    def test_identical_sets(self):
        assert _jaccard({"A", "B"}, {"A", "B"}) == 1.0

    def test_disjoint_sets(self):
        assert _jaccard({"A"}, {"B"}) == 0.0

    def test_empty_both(self):
        assert _jaccard(set(), set()) == 1.0

    def test_empty_one(self):
        assert _jaccard({"A"}, set()) == 0.0

    def test_case_insensitive(self):
        assert _jaccard({"AuthService"}, {"authservice"}) == 1.0


# ---------------------------------------------------------------------------
# Tests: _compute_system_score
# ---------------------------------------------------------------------------


class TestComputeSystemScore:
    def test_perfect_overlap(self):
        """Identical graphs → overall 1.0."""
        graph = StructuralGraph(
            classes=[ClassInfo(name="Foo", methods=["bar"], bases=[], module="m")],
            functions=[FunctionInfo(name="baz", args=[], module="m")],
            imports=[ImportEdge(from_module="m", to_module="os")],
            modules=["m"],
        )
        result = _compute_system_score(graph, graph)
        assert result["class_overlap"] == 1.0
        assert result["method_overlap"] == 1.0
        assert result["function_overlap"] == 1.0
        assert result["import_similarity"] == 1.0
        assert result["overall"] == 1.0

    def test_no_overlap(self):
        """Completely different graphs → overall 0.0."""
        ref = StructuralGraph(
            classes=[ClassInfo(name="Alpha", methods=["run"], bases=[], module="m")],
            functions=[FunctionInfo(name="start", args=[], module="m")],
            imports=[ImportEdge(from_module="m", to_module="os")],
            modules=["m"],
        )
        gen = StructuralGraph(
            classes=[ClassInfo(name="Beta", methods=["stop"], bases=[], module="g")],
            functions=[FunctionInfo(name="finish", args=[], module="g")],
            imports=[ImportEdge(from_module="g", to_module="sys")],
            modules=["g"],
        )
        result = _compute_system_score(ref, gen)
        assert result["class_overlap"] == 0.0
        assert result["method_overlap"] == 0.0
        assert result["function_overlap"] == 0.0
        assert result["import_similarity"] == 0.0
        assert result["overall"] == pytest.approx(0.1)  # only module_ratio contributes (1.0 * 0.10)

    def test_partial_overlap(self):
        """Some matching, some not → medium score."""
        ref = StructuralGraph(
            classes=[
                ClassInfo(name="AuthService", methods=["login"], bases=[], module="m"),
                ClassInfo(name="UserRepo", methods=["find"], bases=[], module="m"),
            ],
            functions=[],
            imports=[],
            modules=["m"],
        )
        gen = StructuralGraph(
            classes=[
                ClassInfo(name="AuthService", methods=["login", "register"], bases=[], module="g"),
            ],
            functions=[],
            imports=[],
            modules=["g"],
        )
        result = _compute_system_score(ref, gen)
        # class: {authservice} & {authservice} / {authservice, userrepo} = 1/2 = 0.5
        assert result["class_overlap"] == pytest.approx(0.5)
        assert 0.0 < result["overall"] < 1.0


# ---------------------------------------------------------------------------
# Tests: _build_reference_graph_for_system
# ---------------------------------------------------------------------------


class TestBuildReferenceGraph:
    def test_builds_graph_from_manifest(self):
        """Correctly filters manifest modules for auth system."""
        decomposition = _make_decomposition()
        manifest = _make_manifest()

        graph = _build_reference_graph_for_system("sys-auth", decomposition, manifest)

        # Should include AuthService and AuthRepo (from auth_service and auth_repo modules)
        class_names = {c.name for c in graph.classes}
        assert "AuthService" in class_names
        assert "AuthRepo" in class_names
        # Should NOT include Database (from database module)
        assert "Database" not in class_names

        # Should include validate_token function
        func_names = {f.name for f in graph.functions}
        assert "validate_token" in func_names

        # Should have modules
        assert len(graph.modules) == 2

    def test_builds_graph_for_data_system(self):
        """Correctly filters manifest modules for data system."""
        decomposition = _make_decomposition()
        manifest = _make_manifest()

        graph = _build_reference_graph_for_system("sys-data", decomposition, manifest)

        class_names = {c.name for c in graph.classes}
        assert "Database" in class_names
        assert "AuthService" not in class_names

        func_names = {f.name for f in graph.functions}
        assert "create_pool" in func_names

    def test_unknown_system_returns_empty(self):
        """Non-existent system ID → empty graph."""
        decomposition = _make_decomposition()
        manifest = _make_manifest()

        graph = _build_reference_graph_for_system("sys-unknown", decomposition, manifest)
        assert graph.classes == []
        assert graph.functions == []

    def test_empty_manifest_returns_empty(self):
        """No modules in manifest → empty graph."""
        decomposition = _make_decomposition()

        graph = _build_reference_graph_for_system("sys-auth", decomposition, {"modules": []})
        assert graph.classes == []
        assert graph.functions == []


# ---------------------------------------------------------------------------
# Tests: DecomposedRoundTripEvaluator.evaluate
# ---------------------------------------------------------------------------


class TestDecomposedRoundTripEvaluator:
    def test_evaluate_with_matching_code(self):
        """Per-system code matching reference → high scores."""
        decomposition = _make_decomposition()
        manifest = _make_manifest()

        # Generated code that closely matches the auth system
        auth_code = """\
import os
import hashlib

class AuthService:
    def __init__(self, repo):
        self.repo = repo

    def login(self, user, password):
        pass

    def logout(self):
        pass

class AuthRepo:
    def find_user(self, uid):
        pass

    def save_user(self, user):
        pass

def validate_token(token):
    pass
"""
        # Generated code that matches the data system
        data_code = """\
import asyncpg

class Database:
    def connect(self):
        pass

    def query(self, sql):
        pass

def create_pool(url):
    pass
"""
        per_system_code = {
            "sys-auth": auth_code,
            "sys-data": data_code,
        }
        original_graph = StructuralGraph()  # Not used directly when manifest has data

        evaluator = DecomposedRoundTripEvaluator()
        score = evaluator.evaluate(decomposition, per_system_code, original_graph, manifest)

        assert isinstance(score, DecomposedRoundTripScore)
        assert score.n_systems == 2
        assert "sys-auth" in score.system_scores
        assert "sys-data" in score.system_scores

        # Both systems should score well
        assert score.system_scores["sys-auth"] > 0.5
        assert score.system_scores["sys-data"] > 0.5
        assert score.overall > 0.5

    def test_evaluate_with_missing_code(self):
        """Missing code for a system → 0 score for that system."""
        decomposition = _make_decomposition()
        manifest = _make_manifest()

        per_system_code = {
            "sys-auth": "class AuthService:\n    def login(self): pass\n",
            # sys-data missing
        }
        original_graph = StructuralGraph()

        evaluator = DecomposedRoundTripEvaluator()
        score = evaluator.evaluate(decomposition, per_system_code, original_graph, manifest)

        assert score.n_systems == 2
        assert score.system_scores["sys-data"] == 0.0
        assert score.system_details["sys-data"]["overall"] == 0.0
        # Auth should still have some score
        assert score.system_scores["sys-auth"] > 0.0

    def test_evaluate_with_wrong_code(self):
        """Unrelated code for a system → low score."""
        decomposition = _make_decomposition()
        manifest = _make_manifest()

        # Completely wrong code for auth system
        per_system_code = {
            "sys-auth": "class CacheManager:\n    def get(self, key): pass\n",
            "sys-data": "class QueueProcessor:\n    def enqueue(self, msg): pass\n",
        }
        original_graph = StructuralGraph()

        evaluator = DecomposedRoundTripEvaluator()
        score = evaluator.evaluate(decomposition, per_system_code, original_graph, manifest)

        assert score.system_scores["sys-auth"] < 0.3
        assert score.system_scores["sys-data"] < 0.3
        assert score.overall < 0.3

    def test_weighted_overall_by_complexity(self):
        """Overall is weighted by complexity_score."""
        decomposition = _make_decomposition()
        manifest = _make_manifest()

        # Auth system (complexity 15.0) gets high score
        auth_code = """\
class AuthService:
    def login(self, user, password): pass
    def logout(self): pass

class AuthRepo:
    def find_user(self, uid): pass
    def save_user(self, user): pass

def validate_token(token): pass
"""
        # Data system (complexity 10.0) gets 0 score (missing)
        per_system_code = {
            "sys-auth": auth_code,
            # sys-data missing → 0 score
        }
        original_graph = StructuralGraph()

        evaluator = DecomposedRoundTripEvaluator()
        score = evaluator.evaluate(decomposition, per_system_code, original_graph, manifest)

        # Overall should be weighted: (auth_score * 15 + 0 * 10) / 25
        auth_score = score.system_scores["sys-auth"]
        expected_overall = (auth_score * 15.0 + 0.0 * 10.0) / 25.0
        assert score.overall == pytest.approx(expected_overall)

    def test_evaluate_empty_per_system_code(self):
        """All systems missing code → overall 0."""
        decomposition = _make_decomposition()
        manifest = _make_manifest()

        per_system_code: dict[str, str] = {}
        original_graph = StructuralGraph()

        evaluator = DecomposedRoundTripEvaluator()
        score = evaluator.evaluate(decomposition, per_system_code, original_graph, manifest)

        assert score.n_systems == 2
        assert score.overall == 0.0

    def test_system_details_has_all_metrics(self):
        """Each system's details dict has the expected keys."""
        decomposition = _make_decomposition()
        manifest = _make_manifest()

        per_system_code = {
            "sys-auth": "class AuthService:\n    pass\n",
            "sys-data": "class Database:\n    pass\n",
        }
        original_graph = StructuralGraph()

        evaluator = DecomposedRoundTripEvaluator()
        score = evaluator.evaluate(decomposition, per_system_code, original_graph, manifest)

        expected_keys = {"class_overlap", "method_overlap", "function_overlap",
                         "import_similarity", "module_ratio", "overall"}
        for sys_id in ["sys-auth", "sys-data"]:
            assert set(score.system_details[sys_id].keys()) == expected_keys


# ---------------------------------------------------------------------------
# Tests: Fallback reference (when manifest has no matching modules)
# ---------------------------------------------------------------------------


class TestFallbackReference:
    def test_fallback_uses_component_symbols(self):
        """When manifest has no matching modules, fallback uses component symbols."""
        decomposition = _make_decomposition()
        empty_manifest: dict = {"modules": []}

        # Build original graph with the expected classes
        original_graph = StructuralGraph(
            classes=[
                ClassInfo(name="AuthService", methods=["login", "logout"], bases=[], module="m"),
                ClassInfo(name="AuthRepo", methods=["find_user"], bases=[], module="m"),
                ClassInfo(name="Unrelated", methods=["foo"], bases=[], module="m"),
            ],
            functions=[
                FunctionInfo(name="validate_token", args=["token"], module="m"),
                FunctionInfo(name="unrelated_func", args=[], module="m"),
            ],
            imports=[],
            modules=["m"],
        )

        # Evaluate with empty manifest — should fall back
        per_system_code = {
            "sys-auth": "class AuthService:\n    def login(self): pass\n    def logout(self): pass\n",
            "sys-data": "class Database:\n    def connect(self): pass\n",
        }

        evaluator = DecomposedRoundTripEvaluator()
        score = evaluator.evaluate(decomposition, per_system_code, original_graph, empty_manifest)

        # Auth system should score something (fallback uses symbols from sub-model)
        assert score.system_scores["sys-auth"] > 0.0
        assert score.n_systems == 2


# ---------------------------------------------------------------------------
# Tests: Pipeline integration method
# ---------------------------------------------------------------------------


class TestPipelineDecomposedFidelity:
    def test_compute_decomposed_fidelity_returns_dict(self):
        """_compute_decomposed_fidelity returns expected dict structure."""
        from unittest.mock import MagicMock, AsyncMock

        from architecture_model.training.pipeline import TrainingPipeline

        # Build minimal pipeline (mock all dependencies)
        pipeline = TrainingPipeline(
            surrogate=MagicMock(),
            oracle=MagicMock(),
            store=MagicMock(),
            evaluator=MagicMock(),
            controller=MagicMock(),
            trainer=MagicMock(),
            repo_fetcher=MagicMock(),
        )

        decomposition = _make_decomposition()
        manifest = _make_manifest()

        auth_code = "class AuthService:\n    def login(self): pass\n"
        data_code = "class Database:\n    def connect(self): pass\n"

        original_code = "# src/auth_service/service.py\nclass AuthService:\n    def login(self): pass\n"

        result = pipeline._compute_decomposed_fidelity(
            decomposition=decomposition,
            per_system_code={"sys-auth": auth_code, "sys-data": data_code},
            original_code=original_code,
            manifest=manifest,
        )

        assert result is not None
        assert "system_fidelity" in result
        assert "overall_decomposed_score" in result
        assert isinstance(result["system_fidelity"], dict)
        assert "sys-auth" in result["system_fidelity"]
        assert "sys-data" in result["system_fidelity"]
        assert isinstance(result["overall_decomposed_score"], float)

    def test_compute_decomposed_fidelity_graceful_failure(self):
        """On error, returns None without raising."""
        from unittest.mock import MagicMock, patch

        from architecture_model.training.pipeline import TrainingPipeline

        pipeline = TrainingPipeline(
            surrogate=MagicMock(),
            oracle=MagicMock(),
            store=MagicMock(),
            evaluator=MagicMock(),
            controller=MagicMock(),
            trainer=MagicMock(),
            repo_fetcher=MagicMock(),
        )

        # Pass invalid decomposition that will cause an error
        with patch(
            "architecture_model.training.pipeline.DecomposedRoundTripEvaluator.evaluate",
            side_effect=RuntimeError("boom"),
        ):
            result = pipeline._compute_decomposed_fidelity(
                decomposition=_make_decomposition(),
                per_system_code={},
                original_code="",
                manifest={},
            )

        assert result is None
