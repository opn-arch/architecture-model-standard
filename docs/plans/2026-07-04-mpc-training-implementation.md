# MPC Training Loop — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a full MPC training loop that uses Ollama (surrogate) + litellm (oracle) + HF PEFT (LoRA trainer) to continuously improve architecture model extraction.

**Architecture:** Plugin architecture in `src/architecture_model/training/` subpackage. SQLite dataset store, async extraction pipeline, multi-objective Pareto loss evaluation, with CLI commands under `architecture-model train`.

**Tech Stack:** Python 3.11+, Ollama, litellm, HF transformers + PEFT, SQLite, asyncio, GitHub REST API

**Test command:** `pytest tests/test_training/ --tb=short -q`

**Design doc:** `docs/plans/2026-07-04-mpc-training-loop-design.md`

---

## Prerequisites

Before starting, add training dependencies to `pyproject.toml`:

```toml
[project.optional-dependencies]
training = [
    "torch>=2.0",
    "transformers>=4.40",
    "peft>=0.10",
    "datasets>=2.19",
    "litellm>=1.40",
    "ollama>=0.2",
    "aiohttp>=3.9",
    "numpy>=1.26",
]
```

Create the package directory:
```bash
mkdir -p src/architecture_model/training
mkdir -p tests/test_training
touch src/architecture_model/training/__init__.py
touch tests/test_training/__init__.py
```

---

### Task 1: Dataset Store (`dataset.py`)

The foundation — all other components read/write training examples here.

**Files:**
- Create: `src/architecture_model/training/dataset.py`
- Create: `tests/test_training/test_dataset.py`

**Step 1: Write failing tests**

```python
"""Tests for training dataset store."""
import json
import pytest
from pathlib import Path
from architecture_model.training.dataset import DatasetStore, TrainingExample


@pytest.fixture
def store(tmp_path):
    return DatasetStore(tmp_path / "test.db")


def test_store_creates_db(store):
    """Store creates SQLite database on init."""
    assert store.db_path.exists()


def test_save_and_retrieve_example(store):
    """Can save a training example and retrieve it."""
    example = TrainingExample(
        repo_url="https://github.com/test/repo",
        repo_sha="abc123",
        code_context="def hello(): pass",
        local_output="entities: []",
        oracle_output=None,
        loss_vector=None,
        iteration=1,
        metadata={"stars": 100},
    )
    eid = store.save(example)
    assert eid > 0
    retrieved = store.get(eid)
    assert retrieved.repo_url == "https://github.com/test/repo"
    assert retrieved.code_context == "def hello(): pass"


def test_save_with_oracle_output(store):
    """Can save example with oracle output and loss vector."""
    example = TrainingExample(
        repo_url="https://github.com/test/repo",
        repo_sha="abc123",
        code_context="code",
        local_output="local yaml",
        oracle_output="oracle yaml",
        loss_vector={"L1": 0.8, "L2": 0.9, "L3": 0.7, "L4": 85.0},
        iteration=2,
        metadata={},
    )
    eid = store.save(example)
    retrieved = store.get(eid)
    assert retrieved.oracle_output == "oracle yaml"
    assert retrieved.loss_vector["L1"] == 0.8


def test_update_loss(store):
    """Can update loss vector after initial save."""
    example = TrainingExample(
        repo_url="https://github.com/test/repo",
        repo_sha="abc123",
        code_context="code",
        local_output="yaml",
        oracle_output=None,
        loss_vector=None,
        iteration=1,
        metadata={},
    )
    eid = store.save(example)
    store.update_loss(eid, {"L1": 0.5, "L2": 0.6, "L3": 0.4, "L4": 70.0})
    retrieved = store.get(eid)
    assert retrieved.loss_vector["L1"] == 0.5


def test_query_by_iteration(store):
    """Can query examples by iteration."""
    for i in range(5):
        store.save(TrainingExample(
            repo_url=f"https://github.com/test/repo{i}",
            repo_sha="sha",
            code_context="code",
            local_output="yaml",
            oracle_output="oracle" if i % 2 == 0 else None,
            loss_vector=None,
            iteration=i // 3 + 1,
            metadata={},
        ))
    iter1 = store.query(iteration=1)
    assert len(iter1) == 3


def test_count_new_since_last_train(store):
    """Counts examples added since last training run."""
    for i in range(10):
        store.save(TrainingExample(
            repo_url=f"repo{i}", repo_sha="sha", code_context="code",
            local_output="yaml", oracle_output="oracle",
            loss_vector={"L1": 0.5, "L2": 0.5, "L3": 0.5, "L4": 50.0},
            iteration=1, metadata={},
        ))
    assert store.new_examples_since_last_train() == 10
    store.record_training_run("base_model", "/path/to/lora", 10)
    assert store.new_examples_since_last_train() == 0


def test_export_for_training(store):
    """Exports oracle-validated examples in instruction-tuning format."""
    for i in range(5):
        store.save(TrainingExample(
            repo_url=f"repo{i}", repo_sha="sha",
            code_context=f"code_{i}",
            local_output=f"local_{i}",
            oracle_output=f"oracle_{i}" if i < 3 else None,
            loss_vector={"L1": 0.5, "L2": 0.5, "L3": 0.5, "L4": 50.0},
            iteration=1, metadata={},
        ))
    exported = store.export_for_training()
    # Only oracle-validated examples
    assert len(exported) == 3
    assert all("instruction" in e and "input" in e and "output" in e for e in exported)
```

**Step 2: Run tests — expect FAIL (module not found)**

```bash
pytest tests/test_training/test_dataset.py -v
```

**Step 3: Implement `dataset.py`**

```python
"""SQLite-backed dataset store for MPC training loop."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class TrainingExample:
    repo_url: str
    repo_sha: str
    code_context: str
    local_output: str
    oracle_output: str | None
    loss_vector: dict[str, float] | None
    iteration: int
    metadata: dict[str, Any]
    id: int | None = None
    created_at: datetime | None = None


class DatasetStore:
    """SQLite-backed store for training examples and run metadata."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS training_examples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_url TEXT NOT NULL,
                repo_sha TEXT NOT NULL,
                code_context TEXT NOT NULL,
                local_output TEXT NOT NULL,
                oracle_output TEXT,
                loss_vector TEXT,
                iteration INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                metadata TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS training_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                base_model TEXT NOT NULL,
                lora_path TEXT NOT NULL,
                examples_used INTEGER NOT NULL,
                final_loss TEXT,
                pareto_front TEXT
            );
        """)
        self._conn.commit()

    def save(self, example: TrainingExample) -> int:
        now = datetime.now(timezone.utc).isoformat()
        cur = self._conn.execute(
            """INSERT INTO training_examples
               (repo_url, repo_sha, code_context, local_output, oracle_output,
                loss_vector, iteration, created_at, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                example.repo_url,
                example.repo_sha,
                example.code_context,
                example.local_output,
                example.oracle_output,
                json.dumps(example.loss_vector) if example.loss_vector else None,
                example.iteration,
                now,
                json.dumps(example.metadata),
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def get(self, example_id: int) -> TrainingExample:
        row = self._conn.execute(
            "SELECT * FROM training_examples WHERE id = ?", (example_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"No example with id={example_id}")
        return self._row_to_example(row)

    def update_loss(self, example_id: int, loss_vector: dict[str, float]) -> None:
        self._conn.execute(
            "UPDATE training_examples SET loss_vector = ? WHERE id = ?",
            (json.dumps(loss_vector), example_id),
        )
        self._conn.commit()

    def query(self, iteration: int | None = None, has_oracle: bool | None = None) -> list[TrainingExample]:
        sql = "SELECT * FROM training_examples WHERE 1=1"
        params: list = []
        if iteration is not None:
            sql += " AND iteration = ?"
            params.append(iteration)
        if has_oracle is True:
            sql += " AND oracle_output IS NOT NULL"
        elif has_oracle is False:
            sql += " AND oracle_output IS NULL"
        rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_example(r) for r in rows]

    def new_examples_since_last_train(self) -> int:
        last_run = self._conn.execute(
            "SELECT MAX(started_at) as last_at FROM training_runs"
        ).fetchone()
        last_at = last_run["last_at"] if last_run else None
        if last_at:
            count = self._conn.execute(
                "SELECT COUNT(*) as cnt FROM training_examples WHERE created_at > ? AND oracle_output IS NOT NULL",
                (last_at,),
            ).fetchone()["cnt"]
        else:
            count = self._conn.execute(
                "SELECT COUNT(*) as cnt FROM training_examples WHERE oracle_output IS NOT NULL"
            ).fetchone()["cnt"]
        return count

    def record_training_run(self, base_model: str, lora_path: str, examples_used: int) -> int:
        now = datetime.now(timezone.utc).isoformat()
        cur = self._conn.execute(
            """INSERT INTO training_runs (started_at, base_model, lora_path, examples_used)
               VALUES (?, ?, ?, ?)""",
            (now, base_model, lora_path, examples_used),
        )
        self._conn.commit()
        return cur.lastrowid

    def export_for_training(self) -> list[dict[str, str]]:
        """Export oracle-validated examples as instruction-tuning format."""
        rows = self._conn.execute(
            "SELECT * FROM training_examples WHERE oracle_output IS NOT NULL"
        ).fetchall()
        results = []
        for row in rows:
            results.append({
                "instruction": (
                    "Extract an architecture model from the following Python codebase. "
                    "Output valid YAML following the UAM schema (7 entity types: actors, "
                    "capabilities, behaviors, interfaces, constraints, layers, components; "
                    "8 relationship types: realizes, uses, constrains, contains, triggers, "
                    "depends_on, implements, exposes)."
                ),
                "input": row["code_context"],
                "output": row["oracle_output"],
            })
        return results

    def _row_to_example(self, row: sqlite3.Row) -> TrainingExample:
        return TrainingExample(
            id=row["id"],
            repo_url=row["repo_url"],
            repo_sha=row["repo_sha"],
            code_context=row["code_context"],
            local_output=row["local_output"],
            oracle_output=row["oracle_output"],
            loss_vector=json.loads(row["loss_vector"]) if row["loss_vector"] else None,
            iteration=row["iteration"],
            created_at=datetime.fromisoformat(row["created_at"]),
            metadata=json.loads(row["metadata"]),
        )

    def close(self) -> None:
        self._conn.close()
```

**Step 4: Run tests — all pass**

```bash
pytest tests/test_training/test_dataset.py -v
```

**Step 5: Commit**

```bash
git add src/architecture_model/training/ tests/test_training/
git commit -m "feat(training): add SQLite dataset store for training examples"
```

---

### Task 2: Evaluator (`evaluator.py`)

Multi-objective loss computation and Pareto front.

**Files:**
- Create: `src/architecture_model/training/evaluator.py`
- Create: `tests/test_training/test_evaluator.py`

**Step 1: Write failing tests**

```python
"""Tests for multi-objective evaluator."""
import pytest
from architecture_model.training.evaluator import (
    LossVector,
    Evaluator,
    compute_entity_f1,
    compute_relationship_f1,
)
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Actor, ActorType,
    Capability, Behavior, Interface, InterfaceType,
    Constraint, Layer, Component, Relationship, RelationType,
    Status, Priority, Strength,
)


def _make_model(actors=None, capabilities=None, behaviors=None, relationships=None):
    """Helper to build a minimal ArchitectureModel."""
    return ArchitectureModel(
        meta=ModelMeta(system="test", schema_version="1.0.0"),
        entities=Entities(
            actors=actors or [],
            capabilities=capabilities or [],
            behaviors=behaviors or [],
            interfaces=[],
            constraints=[],
            layers=[],
            components=[],
        ),
        relationships=relationships or [],
    )


def test_loss_vector_dominates():
    """A dominates B if better or equal on all objectives and strictly better on at least one."""
    a = LossVector(structural_accuracy=0.9, completeness=0.9, reconstruction_fidelity=0.8, validator_score=95)
    b = LossVector(structural_accuracy=0.8, completeness=0.8, reconstruction_fidelity=0.7, validator_score=90)
    assert a.dominates(b)
    assert not b.dominates(a)


def test_loss_vector_no_dominance():
    """Neither dominates when trade-offs exist."""
    a = LossVector(structural_accuracy=0.9, completeness=0.7, reconstruction_fidelity=0.8, validator_score=90)
    b = LossVector(structural_accuracy=0.7, completeness=0.9, reconstruction_fidelity=0.8, validator_score=90)
    assert not a.dominates(b)
    assert not b.dominates(a)


def test_entity_f1_perfect_match():
    """Perfect entity match gives F1=1.0."""
    local = _make_model(actors=[
        Actor(id="ACT-1", name="User", status=Status.ACTIVE, type=ActorType.HUMAN)
    ])
    oracle = _make_model(actors=[
        Actor(id="ACT-1", name="User", status=Status.ACTIVE, type=ActorType.HUMAN)
    ])
    assert compute_entity_f1(local, oracle) == pytest.approx(1.0)


def test_entity_f1_partial_match():
    """Partial match gives F1 < 1.0."""
    local = _make_model(actors=[
        Actor(id="ACT-1", name="User", status=Status.ACTIVE, type=ActorType.HUMAN),
    ])
    oracle = _make_model(actors=[
        Actor(id="ACT-1", name="User", status=Status.ACTIVE, type=ActorType.HUMAN),
        Actor(id="ACT-2", name="Admin", status=Status.ACTIVE, type=ActorType.HUMAN),
    ])
    f1 = compute_entity_f1(local, oracle)
    assert 0.5 < f1 < 1.0  # Found 1 of 2


def test_evaluator_compute_loss():
    """Evaluator produces a LossVector from models."""
    local = _make_model(
        actors=[Actor(id="ACT-1", name="User", status=Status.ACTIVE, type=ActorType.HUMAN)],
        capabilities=[Capability(id="CAP-1", name="Auth", status=Status.ACTIVE, f_block="F1")],
    )
    oracle = _make_model(
        actors=[Actor(id="ACT-1", name="User", status=Status.ACTIVE, type=ActorType.HUMAN)],
        capabilities=[
            Capability(id="CAP-1", name="Auth", status=Status.ACTIVE, f_block="F1"),
            Capability(id="CAP-2", name="API", status=Status.ACTIVE, f_block="F2"),
        ],
    )
    evaluator = Evaluator()
    loss = evaluator.compute_loss(local_model=local, oracle_model=oracle)
    assert 0 <= loss.structural_accuracy <= 1.0
    assert 0 <= loss.completeness <= 1.0
    assert 0 <= loss.validator_score <= 100


def test_pareto_front_update():
    """Pareto front keeps only non-dominated points."""
    evaluator = Evaluator()
    points = [
        LossVector(0.9, 0.7, 0.8, 90),  # good accuracy, weak completeness
        LossVector(0.7, 0.9, 0.8, 90),  # weak accuracy, good completeness
        LossVector(0.6, 0.6, 0.5, 70),  # dominated by both above
    ]
    front = evaluator.compute_pareto_front(points)
    assert len(front) == 2  # third point is dominated
```

**Step 2: Run tests — expect FAIL**

**Step 3: Implement `evaluator.py`**

Core logic: entity matching via ID/type, relationship matching via type + endpoints, Pareto dominance filtering. No external dependencies beyond numpy for optional vectorization.

**Step 4: Run tests — all pass**

**Step 5: Commit**

```bash
git add src/architecture_model/training/evaluator.py tests/test_training/test_evaluator.py
git commit -m "feat(training): add multi-objective evaluator with Pareto front"
```

---

### Task 3: Surrogate Client (`surrogate.py`)

Ollama client for local LLM extraction and generation.

**Files:**
- Create: `src/architecture_model/training/surrogate.py`
- Create: `tests/test_training/test_surrogate.py`

**Step 1: Write failing tests**

Tests should mock the Ollama client (don't require running Ollama for unit tests):

```python
"""Tests for Ollama surrogate client."""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from architecture_model.training.surrogate import Surrogate


@pytest.fixture
def surrogate():
    return Surrogate(model_name="codellama:13b")


def test_surrogate_init(surrogate):
    assert surrogate.model_name == "codellama:13b"


@pytest.mark.asyncio
async def test_extract_model_formats_prompt(surrogate):
    """extract_model sends correctly formatted prompt to Ollama."""
    mock_response = {"message": {"content": "meta:\\n  system: test\\nentities:\\n  actors: []"}}
    with patch.object(surrogate, "_chat", new_callable=AsyncMock, return_value=mock_response):
        result = await surrogate.extract_model("def hello(): pass")
        surrogate._chat.assert_called_once()
        call_args = surrogate._chat.call_args
        messages = call_args[0][0] if call_args[0] else call_args[1]["messages"]
        # Should have system + user messages
        assert any("UAM schema" in m["content"] or "architecture" in m["content"] for m in messages)


@pytest.mark.asyncio
async def test_extract_model_parses_yaml(surrogate):
    """extract_model parses YAML response into ArchitectureModel."""
    yaml_response = """meta:
  system: test-app
  schema_version: "1.0.0"
entities:
  actors:
    - id: ACT-1
      name: User
      status: active
      type: human
  capabilities: []
  behaviors: []
  interfaces: []
  constraints: []
  layers: []
  components: []
relationships: []"""
    mock_response = {"message": {"content": yaml_response}}
    with patch.object(surrogate, "_chat", new_callable=AsyncMock, return_value=mock_response):
        model = await surrogate.extract_model("some code")
        assert model is not None
        assert model.meta.system == "test-app"


@pytest.mark.asyncio
async def test_confidence_low_for_empty_model(surrogate):
    """Confidence should be low for models with few entities."""
    yaml_response = """meta:
  system: test
  schema_version: "1.0.0"
entities:
  actors: []
  capabilities: []
  behaviors: []
  interfaces: []
  constraints: []
  layers: []
  components: []
relationships: []"""
    mock_response = {"message": {"content": yaml_response}}
    with patch.object(surrogate, "_chat", new_callable=AsyncMock, return_value=mock_response):
        model = await surrogate.extract_model("big complex code")
        confidence = surrogate.confidence(model)
        assert confidence < 0.5  # Empty model = low confidence


def test_swap_model(surrogate):
    """swap_model updates the model name."""
    surrogate.swap_model("arch-model-v2")
    assert surrogate.model_name == "arch-model-v2"
```

**Step 2: Run tests — expect FAIL**

**Step 3: Implement `surrogate.py`**

Wraps Ollama Python client. Formats prompts with schema spec, parses YAML responses, provides confidence estimation based on entity density.

**Step 4: Run tests — all pass**

**Step 5: Commit**

```bash
git add src/architecture_model/training/surrogate.py tests/test_training/test_surrogate.py
git commit -m "feat(training): add Ollama surrogate client for local LLM extraction"
```

---

### Task 4: Oracle Client (`oracle.py`)

litellm-based frontier model client.

**Files:**
- Create: `src/architecture_model/training/oracle.py`
- Create: `tests/test_training/test_oracle.py`

**Step 1: Write failing tests**

Similar structure to surrogate tests but using litellm mock. Test budget tracking, structured output parsing, and fallback behavior.

**Step 2: Run tests — expect FAIL**

**Step 3: Implement `oracle.py`**

Wraps litellm for provider-agnostic frontier calls. Includes BudgetTracker that tracks token usage and refuses calls when budget exhausted.

```python
class BudgetTracker:
    def __init__(self, max_tokens: int): ...
    def can_afford(self, estimated_tokens: int) -> bool: ...
    def record_usage(self, tokens_used: int) -> None: ...
    @property
    def remaining(self) -> int: ...

class Oracle:
    def __init__(self, model: str = "gpt-4o", budget: BudgetTracker | None = None): ...
    async def extract_model(self, code_context: str) -> ArchitectureModel: ...
    async def validate_extraction(self, model: ArchitectureModel, code: str) -> dict: ...
```

**Step 4: Run tests — all pass**

**Step 5: Commit**

```bash
git add src/architecture_model/training/oracle.py tests/test_training/test_oracle.py
git commit -m "feat(training): add litellm oracle client with budget tracking"
```

---

### Task 5: Repo Fetcher (`repo_fetcher.py`)

GitHub API discovery and clone management.

**Files:**
- Create: `src/architecture_model/training/repo_fetcher.py`
- Create: `tests/test_training/test_repo_fetcher.py`

**Step 1: Write failing tests**

Test: repo discovery query building, quality filtering, clone path management. Mock GitHub API responses.

**Step 2: Implement**

```python
@dataclass
class RepoInfo:
    url: str
    full_name: str
    stars: int
    language: str
    default_branch: str
    has_ci: bool
    size_kb: int

class RepoFetcher:
    def __init__(self, clone_dir: Path, github_token: str | None = None): ...
    async def discover(self, n: int, language: str = "python", min_stars: int = 100) -> list[RepoInfo]: ...
    def clone(self, repo: RepoInfo) -> Path: ...
    def quality_filter(self, repos: list[RepoInfo]) -> list[RepoInfo]: ...
```

Quality filters: Python 3.8+, has CI/tests, >100 stars, <100k LOC.

**Step 3: Run tests — all pass**

**Step 4: Commit**

```bash
git add src/architecture_model/training/repo_fetcher.py tests/test_training/test_repo_fetcher.py
git commit -m "feat(training): add GitHub API repo discovery and clone management"
```

---

### Task 6: MPC Controller (`controller.py`)

Active learning decisions, budget management, convergence detection.

**Files:**
- Create: `src/architecture_model/training/controller.py`
- Create: `tests/test_training/test_controller.py`

**Step 1: Write failing tests**

Test: should_query_oracle() logic, convergence detection, budget enforcement, state persistence.

**Step 2: Implement**

```python
@dataclass
class MPCState:
    iteration: int = 0
    total_repos_processed: int = 0
    oracle_budget_remaining: float = 100_000
    surrogate_accuracy: float = 0.0
    convergence_history: list[float] = field(default_factory=list)

class MPCController:
    def __init__(self, state: MPCState, oracle_budget: float = 100_000): ...
    def should_query_oracle(self, validator_score: float, confidence: float, is_novel: bool) -> bool: ...
    def record_agreement(self, agreed: bool) -> None: ...
    def is_converged(self) -> bool: ...
    def next_iteration(self) -> None: ...
```

**Step 3: Run tests — all pass**

**Step 4: Commit**

```bash
git add src/architecture_model/training/controller.py tests/test_training/test_controller.py
git commit -m "feat(training): add MPC controller with active learning heuristics"
```

---

### Task 7: LoRA Trainer (`trainer.py`)

HF PEFT integration, dataset preparation, Ollama export.

**Files:**
- Create: `src/architecture_model/training/trainer.py`
- Create: `tests/test_training/test_trainer.py`

**Step 1: Write failing tests**

Test: dataset formatting (instruction tuning format), LoRA config validation, export command generation. Training itself is integration-tested (mock the actual training loop).

**Step 2: Implement**

```python
class LoRATrainer:
    def __init__(self, base_model: str = "codellama/CodeLlama-13b-hf", lora_r: int = 16, lora_alpha: int = 32): ...
    def prepare_dataset(self, store: DatasetStore) -> "Dataset": ...
    def train(self, dataset: "Dataset", output_dir: Path, epochs: int = 3) -> Path: ...
    def export_to_ollama(self, adapter_path: Path, model_name: str) -> None: ...
```

The `export_to_ollama` method creates a Modelfile and runs `ollama create`.

**Step 3: Run tests — all pass**

**Step 4: Commit**

```bash
git add src/architecture_model/training/trainer.py tests/test_training/test_trainer.py
git commit -m "feat(training): add LoRA trainer with HF PEFT and Ollama export"
```

---

### Task 8: Pipeline Orchestrator (`pipeline.py`)

Ties everything together into the MPC loop.

**Files:**
- Create: `src/architecture_model/training/pipeline.py`
- Create: `tests/test_training/test_pipeline.py`

**Step 1: Write failing tests**

Test: single iteration (mock surrogate/oracle), convergence exit, budget exhaustion, training trigger at threshold.

**Step 2: Implement**

```python
class TrainingPipeline:
    def __init__(
        self,
        surrogate: Surrogate,
        oracle: Oracle,
        store: DatasetStore,
        evaluator: Evaluator,
        controller: MPCController,
        trainer: LoRATrainer,
        repo_fetcher: RepoFetcher,
    ): ...

    async def run_iteration(self, n_repos: int = 50) -> MPCState: ...
    async def run_loop(self, max_iterations: int = 100) -> MPCState: ...
```

**Step 3: Run tests — all pass**

**Step 4: Commit**

```bash
git add src/architecture_model/training/pipeline.py tests/test_training/test_pipeline.py
git commit -m "feat(training): add MPC pipeline orchestrator"
```

---

### Task 9: CLI Commands (`cli/train.py`)

Wire training pipeline into the CLI.

**Files:**
- Create: `src/architecture_model/cli/train.py`
- Modify: `src/architecture_model/cli/main.py` (add `train` subcommand group)

**Step 1: Write tests**

Test: CLI argument parsing, help text, dry-run mode.

**Step 2: Implement CLI commands**

```
architecture-model train fetch [--n 50] [--min-stars 100] [--clone-dir ./repos]
architecture-model train run [--n-repos 50] [--db training.db]
architecture-model train fit [--db training.db] [--base-model codellama:13b] [--epochs 3]
architecture-model train swap [--model-name arch-model-v1]
architecture-model train loop [--max-iterations 100] [--budget 100000]
architecture-model train status [--db training.db]
```

**Step 3: Run tests — all pass**

**Step 4: Commit**

```bash
git add src/architecture_model/cli/train.py src/architecture_model/cli/main.py
git commit -m "feat(training): add 'architecture-model train' CLI commands"
```

---

### Task 10: Package Integration

**Files:**
- Modify: `pyproject.toml` (add `[training]` optional deps)
- Modify: `src/architecture_model/training/__init__.py` (public API)

**Step 1: Update pyproject.toml**

**Step 2: Write `__init__.py` public API**

```python
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

__all__ = [
    "TrainingPipeline", "DatasetStore", "TrainingExample",
    "Evaluator", "LossVector", "Surrogate", "Oracle", "BudgetTracker",
    "MPCController", "MPCState", "LoRATrainer", "RepoFetcher", "RepoInfo",
]
```

**Step 3: Run full test suite**

```bash
pytest --tb=short -q
```

**Step 4: Commit**

```bash
git add pyproject.toml src/architecture_model/training/__init__.py
git commit -m "feat(training): wire up package with optional dependencies and public API"
```

---

## Implementation Order Rationale

```
Task 1: Dataset Store      ← foundation, everything writes here
Task 2: Evaluator          ← loss computation, independent of LLM clients
Task 3: Surrogate          ← local LLM client
Task 4: Oracle             ← frontier LLM client
Task 5: Repo Fetcher       ← data sourcing
Task 6: Controller         ← decision logic (uses evaluator outputs)
Task 7: Trainer            ← LoRA training (reads from dataset store)
Task 8: Pipeline           ← orchestrates all above
Task 9: CLI                ← user interface
Task 10: Package           ← final integration
```

Each task is independently testable. Tasks 1-5 have zero interdependencies. Tasks 6-8 build on earlier components. Tasks 9-10 are integration.
