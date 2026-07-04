# MPC Training Loop Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:writing-plans to create implementation plan from this design.

**Goal:** Build a full Model Predictive Control (MPC) training loop that uses a local LLM (Ollama) as a surrogate model for bulk architecture extraction, a frontier model (litellm) as an oracle for ground truth and hard cases, and LoRA fine-tuning (HF PEFT) to continuously improve the surrogate.

**Architecture:** Plugin architecture — single `training/` subpackage with clear module boundaries. Trainer can run independently on GPU when connected to shared dataset store. Designed for local-first development, separable for distributed execution later.

**Tech Stack:** Ollama (local LLM), litellm (frontier), HF transformers + PEFT (LoRA), SQLite (dataset store), GitHub API (repo discovery), asyncio (parallel extraction)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MPC CONTROLLER                                │
│  (active learning, budget management, convergence detection)         │
└────────┬──────────────────────┬──────────────────────┬──────────────┘
         │                      │                      │
    ┌────▼────┐           ┌─────▼─────┐         ┌─────▼─────┐
    │ REPO    │           │ SURROGATE │         │  ORACLE   │
    │ FETCHER │           │  (Ollama) │         │ (litellm) │
    │         │           │ local LLM │         │ frontier  │
    └────┬────┘           └─────┬─────┘         └─────┬─────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────┐     ┌────────────────┐      ┌────────────────┐
│ Code Repos  │────►│ Local Extract  │      │ Ground Truth   │
│ (GitHub)    │     │ (fast, cheap)  │      │ (expensive)    │
└─────────────┘     └───────┬────────┘      └───────┬────────┘
                            │                        │
                            ▼                        ▼
                    ┌────────────────────────────────────┐
                    │        EVALUATOR                    │
                    │  Multi-objective loss:              │
                    │  L1: structural accuracy (F1)      │
                    │  L2: completeness (coverage)       │
                    │  L3: reconstruction fidelity       │
                    │  L4: validator score (0-100)       │
                    │  → Pareto front computation        │
                    └───────────────┬────────────────────┘
                                    │
                                    ▼
                    ┌────────────────────────────────────┐
                    │        DATASET STORE               │
                    │  SQLite (local-first)              │
                    │  (input, local_output, oracle_out, │
                    │   losses, metadata)                │
                    └───────────────┬────────────────────┘
                                    │
                                    ▼
                    ┌────────────────────────────────────┐
                    │        LoRA TRAINER                 │
                    │  HF PEFT, multi-objective reward   │
                    │  → export to Ollama                │
                    └───────────────┬────────────────────┘
                                    │
                                    ▼
                            [Hot-swap Ollama model]
                            [Next MPC iteration]
```

---

## Module Structure

```
src/architecture_model/training/
├── __init__.py          — public API: train(), evaluate(), fetch_repos()
├── controller.py        — MPC controller (active learning, budget, convergence)
├── surrogate.py         — Ollama client: extract/generate via local LLM
├── oracle.py            — litellm client: frontier model ground-truth generation
├── evaluator.py         — multi-objective loss computation, Pareto front
├── dataset.py           — training example collection, SQLite store, export to HF format
├── trainer.py           — HF PEFT LoRA fine-tuning, Ollama model export
├── repo_fetcher.py      — GitHub API discovery, clone management, quality filtering
└── pipeline.py          — orchestrates the full MPC loop
```

CLI: `architecture-model train [subcommand]`
- `train fetch` — discover and clone repos from GitHub
- `train run` — execute one MPC iteration (extract → evaluate → accumulate)
- `train fit` — run LoRA training on accumulated dataset
- `train swap` — hot-swap Ollama model with newly trained weights
- `train loop` — full autonomous loop (fetch → run → fit → swap → repeat)
- `train status` — show training metrics, Pareto front, convergence

---

## Component Specifications

### 1. MPC Controller (`controller.py`)

Decides per-repo whether to use surrogate only (exploit) or query oracle (explore).

```python
@dataclass
class MPCState:
    iteration: int
    total_repos_processed: int
    oracle_budget_remaining: float  # tokens
    surrogate_accuracy: float       # rolling agreement with oracle
    pareto_front: list[LossVector]
    convergence_history: list[float]
```

**Active Learning Heuristics:**

| Signal | Threshold | Rationale |
|--------|-----------|-----------|
| Validator score | < 70 | Model has structural issues |
| Confidence (entropy) | < 0.6 | Surrogate is uncertain |
| Novel F-block types | new pattern | Never seen this architecture |
| Entity count deviation | > 2σ from mean | Unusual extraction |
| Iteration budget | remaining > 0 | Still have tokens to spend |

**Convergence:** Stop when surrogate-oracle agreement > 95% for 3 consecutive iterations.

### 2. Surrogate (`surrogate.py`)

```python
class Surrogate:
    def __init__(self, model_name: str = "codellama:13b"): ...
    async def extract_model(self, code_context: str) -> ArchitectureModel: ...
    async def generate_code(self, model_slice: str) -> str: ...
    async def confidence(self, result: ArchitectureModel) -> float: ...
    def swap_model(self, new_model_name: str) -> None: ...
```

Prompt: schema spec + few-shot examples + code context → structured YAML output.

### 3. Oracle (`oracle.py`)

```python
class Oracle:
    def __init__(self, model: str = "gpt-4o", budget_tracker: BudgetTracker = None): ...
    async def extract_model(self, code_context: str) -> ArchitectureModel: ...
    async def validate_extraction(self, local_model: ArchitectureModel, code: str) -> ValidationResult: ...
    async def generate_code(self, model_slice: str) -> str: ...
```

### 4. Evaluator (`evaluator.py`)

```python
@dataclass
class LossVector:
    structural_accuracy: float   # L1: entity/relationship F1 vs oracle
    completeness: float          # L2: recall of oracle entities
    reconstruction_fidelity: float  # L3: code→model→code AST similarity
    validator_score: float       # L4: existing 0-100 score
    
    def dominates(self, other: "LossVector") -> bool: ...

class Evaluator:
    def compute_loss(self, local_model, oracle_model, original_code, reconstructed_code) -> LossVector: ...
    def update_pareto_front(self, new_point: LossVector) -> list[LossVector]: ...
```

**Loss computation details:**

- **L1 (Structural Accuracy):** Entity matching by type + name similarity → F1. Relationship matching by type + endpoint matching → F1. Average of both.
- **L2 (Completeness):** Recall — fraction of oracle entities/relationships found by surrogate.
- **L3 (Reconstruction Fidelity):** code→model→code AST tree-edit-distance on normalized structure (function/class names, import graph, control flow). NOT byte-for-byte.
- **L4 (Validator Score):** Existing internal consistency score (0-100). Free — no oracle needed.

### 5. Dataset Store (`dataset.py`)

SQLite schema:

```sql
CREATE TABLE training_examples (
    id INTEGER PRIMARY KEY,
    repo_url TEXT,
    repo_sha TEXT,
    code_context TEXT,
    local_output TEXT,
    oracle_output TEXT,
    loss_vector JSON,
    iteration INTEGER,
    created_at TIMESTAMP,
    metadata JSON
);

CREATE TABLE training_runs (
    id INTEGER PRIMARY KEY,
    started_at TIMESTAMP,
    base_model TEXT,
    lora_path TEXT,
    examples_used INTEGER,
    final_loss JSON,
    pareto_front JSON
);
```

Export to HF `datasets` format for LoRA training.

### 6. Trainer (`trainer.py`)

```python
class LoRATrainer:
    def __init__(self, base_model: str, lora_config: dict): ...
    def prepare_dataset(self, store: DatasetStore) -> Dataset: ...
    def train(self, dataset: Dataset, epochs: int = 3) -> str: ...
    def export_to_ollama(self, adapter_path: str, model_name: str) -> None: ...
```

Training format (instruction tuning):
```
System: You are an architecture model extractor...
User: <code context>
Assistant: <architecture YAML>
```

Only oracle-validated examples used for training. Curriculum learning: hardest examples (highest loss) first.

### 7. Repo Fetcher (`repo_fetcher.py`)

```python
class RepoFetcher:
    def discover(self, n: int, language: str, min_stars: int) -> list[RepoInfo]: ...
    def clone(self, repo: RepoInfo, target_dir: Path) -> Path: ...
    def quality_filter(self, repos: list[RepoInfo]) -> list[RepoInfo]: ...
```

Quality signals: has CI, has tests, >100 stars, Python 3.8+, <100k LOC (manageable context).

---

## MPC Loop Algorithm

```
INITIALIZE:
  surrogate ← Ollama(base_model="codellama:13b")
  oracle ← litellm(model="gpt-4o")
  store ← SQLite("training.db")
  state ← MPCState(iteration=0, budget=100k_tokens)

LOOP (until convergence or budget exhausted):
  1. FETCH: repos ← discover_repos(n=50, language="python", min_stars=100)
  
  2. EXTRACT (parallel, async):
     for repo in repos:
       code_ctx ← format_code_context(repo)
       local_model ← surrogate.extract(code_ctx)
       score ← validator.score(local_model)
       confidence ← surrogate.confidence(local_model)
       
       if score < 70 OR confidence < 0.6 OR is_novel_pattern(local_model):
         oracle_model ← oracle.extract(code_ctx)
         state.budget -= token_cost
       else:
         oracle_model ← None
       
       store.save(repo, code_ctx, local_model, oracle_model)
  
  3. EVALUATE:
     for example in store.current_iteration():
       loss ← evaluator.compute_loss(...)
       store.update_loss(example.id, loss)
     pareto_front ← evaluator.update_pareto_front(store.all_losses())
  
  4. TRAIN (when enough new examples):
     if store.new_examples_since_last_train() >= 200:
       dataset ← trainer.prepare_dataset(store)
       adapter ← trainer.train(dataset, epochs=3)
       trainer.export_to_ollama(adapter, f"arch-model-v{state.iteration}")
       surrogate.swap_model(f"arch-model-v{state.iteration}")
  
  5. CHECK CONVERGENCE:
     agreement ← measure_surrogate_oracle_agreement(store.recent(100))
     if agreement > 0.95 for last 3 iterations: BREAK
     state.iteration += 1
```

---

## Dependencies

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

Install: `pip install architecture-model-standard[training]`

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Local LLM serving | Ollama | Easy setup, Metal support, model management |
| Frontier access | litellm (configurable) | Provider-agnostic, swap models freely |
| Training framework | HF PEFT | Standard, broad model support |
| Dataset store | SQLite | Zero-config, local-first, upgradeable to Postgres |
| Loss function | Multi-objective Pareto (4 losses) | Avoids arbitrary weighting |
| Active learning | Uncertainty + validator score | Minimize oracle calls |
| Architecture | Plugin (single package) | Simple local dev, separable later |
| Repo sourcing | GitHub API auto-discovery | Scale without manual curation |
| Convergence | Surrogate-oracle agreement > 95% | Clear stopping criterion |
