# Evaluator & Pipeline Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the broken loss signal by implementing semantic entity matching with Ollama embeddings, proper reconstruction fidelity via stub generation, wire the enhanced pipeline into the MPC loop, fill unused context budget, and add DatasetStore.count().

**Architecture:** Replace exact-match entity/relationship comparison with embedding-based semantic matching (nomic-embed-text via Ollama). Add stub-generation round-trip for reconstruction fidelity. Wire ContextBuilder+MultiPass into `_process_repo`. Fill unused slice budget with raw code.

**Tech Stack:** Python, Ollama (nomic-embed-text for embeddings, qwen2.5:7b for generation), aiohttp, pytest, numpy (optional, can use list math)

---

### Task 1: Add Ollama Embedding Client

**Files:**
- Create: `src/architecture_model/training/embeddings.py`
- Test: `tests/test_training/test_embeddings.py`

**Step 1: Write the failing test**

```python
# tests/test_training/test_embeddings.py
"""Tests for Ollama embedding client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from architecture_model.training.embeddings import (
    OllamaEmbedder,
    cosine_similarity,
)


class TestCosineSimilarity:
    def test_identical_vectors(self):
        assert cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_similar_vectors(self):
        sim = cosine_similarity([1.0, 1.0, 0.0], [1.0, 0.9, 0.1])
        assert sim > 0.95

    def test_zero_vector_returns_zero(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


class TestOllamaEmbedder:
    @pytest.mark.asyncio
    async def test_embed_batch(self):
        embedder = OllamaEmbedder()
        embedder._embed_single = AsyncMock(side_effect=[
            [0.1, 0.2], [0.3, 0.4], [0.5, 0.6]
        ])
        result = await embedder.embed(["a", "b", "c"])
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_similarity_matrix(self):
        embedder = OllamaEmbedder()
        embedder._embed_single = AsyncMock(side_effect=[
            [1.0, 0.0], [0.0, 1.0],  # set A
            [0.9, 0.1], [0.1, 0.9],  # set B
        ])
        matrix = await embedder.similarity_matrix(["a", "b"], ["c", "d"])
        assert matrix[0][0] > 0.9  # a vs c
        assert matrix[1][1] > 0.9  # b vs d
        assert matrix[0][1] < 0.3  # a vs d
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_training/test_embeddings.py -v`
Expected: FAIL (module not found)

**Step 3: Write implementation**

```python
# src/architecture_model/training/embeddings.py
"""Ollama embedding client for semantic entity matching."""

from __future__ import annotations

import math
from typing import Optional

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class OllamaEmbedder:
    """Generates embeddings via Ollama's /api/embeddings endpoint."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        host: str = "http://localhost:11434",
    ) -> None:
        self._model = model
        self._host = host

    async def _embed_single(self, text: str) -> list[float]:
        """Embed a single text string."""
        if not HAS_AIOHTTP:
            raise RuntimeError("aiohttp required for embeddings")

        url = f"{self._host}/api/embeddings"
        payload = {"model": self._model, "prompt": text}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["embedding"]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""
        results = []
        for text in texts:
            vec = await self._embed_single(text)
            results.append(vec)
        return results

    async def similarity_matrix(
        self, texts_a: list[str], texts_b: list[str]
    ) -> list[list[float]]:
        """Compute NxM similarity matrix between two text lists."""
        vecs_a = await self.embed(texts_a)
        vecs_b = await self.embed(texts_b)

        matrix = []
        for va in vecs_a:
            row = [cosine_similarity(va, vb) for vb in vecs_b]
            matrix.append(row)
        return matrix
```

**Step 4: Run tests**

Run: `pytest tests/test_training/test_embeddings.py -v`
Expected: PASS

Run: `pytest tests/ -x -q`
Expected: 325+ passed

**Step 5: Commit**

```bash
git add -A && git commit -m "feat(training): add Ollama embedding client for semantic matching"
```

---

### Task 2: Refactor Evaluator — Semantic Entity Matching + Relationship Remapping

**Files:**
- Modify: `src/architecture_model/training/evaluator.py:83-159`
- Modify: `tests/test_training/test_evaluator.py`

**Step 1: Write failing tests**

Add to `tests/test_training/test_evaluator.py`:

```python
class TestEntityMatchMap:
    def test_exact_id_match(self):
        from architecture_model.training.evaluator import compute_entity_match_map
        local = _make_model(components=[
            Component(id="C01", name="Client", layer="L1", status=Status.ACTIVE),
        ])
        oracle = _make_model(components=[
            Component(id="C01", name="Client", layer="L1", status=Status.ACTIVE),
        ])
        m = compute_entity_match_map(local, oracle)
        assert m == {"C01": "C01"}

    def test_name_match_different_ids(self):
        from architecture_model.training.evaluator import compute_entity_match_map
        local = _make_model(components=[
            Component(id="C01", name="HTTP Client", layer="L1", status=Status.ACTIVE),
        ])
        oracle = _make_model(components=[
            Component(id="C05", name="HTTP Client", layer="L1", status=Status.ACTIVE),
        ])
        m = compute_entity_match_map(local, oracle)
        assert m == {"C01": "C05"}

    def test_fuzzy_name_match(self):
        from architecture_model.training.evaluator import compute_entity_match_map
        local = _make_model(components=[
            Component(id="C01", name="http transport", layer="L1", status=Status.ACTIVE),
        ])
        oracle = _make_model(components=[
            Component(id="C03", name="transport http layer", layer="L1", status=Status.ACTIVE),
        ])
        m = compute_entity_match_map(local, oracle)
        # "http transport" vs "transport http layer" — Jaccard({http,transport}, {transport,http,layer}) = 2/3 > 0.4
        assert "C01" in m and m["C01"] == "C03"


class TestRelationshipRemapping:
    def test_remapped_relationships_match(self):
        local = _make_model(
            components=[
                Component(id="C01", name="Client", layer="L1", status=Status.ACTIVE),
                Component(id="C02", name="Server", layer="L1", status=Status.ACTIVE),
            ],
            relationships=[
                Relationship(type=RelationType.DEPENDS_ON, from_id="C01", to_id="C02"),
            ],
        )
        oracle = _make_model(
            components=[
                Component(id="C10", name="Client", layer="L1", status=Status.ACTIVE),
                Component(id="C20", name="Server", layer="L1", status=Status.ACTIVE),
            ],
            relationships=[
                Relationship(type=RelationType.DEPENDS_ON, from_id="C10", to_id="C20"),
            ],
        )
        f1 = compute_relationship_f1(local, oracle)
        assert f1 == 1.0  # should match after remapping
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_training/test_evaluator.py::TestEntityMatchMap -v`
Expected: FAIL (compute_entity_match_map not found)

**Step 3: Implement**

Add `compute_entity_match_map()` to evaluator.py. Modify `compute_relationship_f1()` to accept optional `id_map` and remap local IDs. Modify `Evaluator.compute_loss()` to build the map and pass it through.

Key implementation:

```python
def compute_entity_match_map(
    local_model: ArchitectureModel,
    oracle_model: ArchitectureModel,
) -> dict[str, str]:
    """Build local_id → oracle_id mapping using 3-pass matching."""
    local_entities = _collect_typed_entities(local_model)
    oracle_entities = _collect_typed_entities(oracle_model)
    
    id_map: dict[str, str] = {}
    oracle_matched: set[int] = set()
    matched_local: set[int] = set()
    
    # Pass 1: exact type+ID
    for li, (l_type, l_id, l_name) in enumerate(local_entities):
        for oi, (o_type, o_id, o_name) in enumerate(oracle_entities):
            if oi in oracle_matched:
                continue
            if l_type == o_type and l_id == o_id:
                id_map[l_id] = o_id
                oracle_matched.add(oi)
                matched_local.add(li)
                break
    
    # Pass 2: exact type+name (lowercase already)
    for li, (l_type, l_id, l_name) in enumerate(local_entities):
        if li in matched_local:
            continue
        for oi, (o_type, o_id, o_name) in enumerate(oracle_entities):
            if oi in oracle_matched:
                continue
            if l_type == o_type and l_name == o_name:
                id_map[l_id] = o_id
                matched_local.add(li)
                oracle_matched.add(oi)
                break
    
    # Pass 3: fuzzy name (word Jaccard >= 0.4)
    for li, (l_type, l_id, l_name) in enumerate(local_entities):
        if li in matched_local:
            continue
        l_words = set(l_name.replace("-", " ").replace("_", " ").split())
        best_oi = None
        best_sim = 0.0
        for oi, (o_type, o_id, o_name) in enumerate(oracle_entities):
            if oi in oracle_matched or l_type != o_type:
                continue
            o_words = set(o_name.replace("-", " ").replace("_", " ").split())
            if not l_words or not o_words:
                continue
            jaccard = len(l_words & o_words) / len(l_words | o_words)
            if jaccard > best_sim:
                best_sim = jaccard
                best_oi = oi
        if best_oi is not None and best_sim >= 0.4:
            id_map[l_id] = oracle_entities[best_oi][1]
            matched_local.add(li)
            oracle_matched.add(best_oi)
    
    return id_map


def compute_relationship_f1(
    local_model: ArchitectureModel,
    oracle_model: ArchitectureModel,
    id_map: dict[str, str] | None = None,
) -> float:
    """Match relationships using remapped entity IDs."""
    if id_map is None:
        id_map = compute_entity_match_map(local_model, oracle_model)
    
    def remap(eid: str) -> str:
        return id_map.get(eid, eid)
    
    local_rels = {(r.type, remap(r.from_id), remap(r.to_id)) for r in local_model.relationships}
    oracle_rels = {(r.type, r.from_id, r.to_id) for r in oracle_model.relationships}
    
    if not local_rels and not oracle_rels:
        return 1.0
    if not local_rels or not oracle_rels:
        return 0.0
    
    true_positives = len(local_rels & oracle_rels)
    precision = true_positives / len(local_rels)
    recall = true_positives / len(oracle_rels)
    
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)
```

Also update `Evaluator.compute_loss()` (line ~215) to pass the map:
```python
id_map = compute_entity_match_map(local_model, oracle_model)
entity_f1 = compute_entity_f1(local_model, oracle_model)
rel_f1 = compute_relationship_f1(local_model, oracle_model, id_map=id_map)
```

Also update **completeness** to be weighted: `0.7 * entity_recall + 0.3 * relationship_recall`:
```python
def _compute_completeness(local_model, oracle_model, id_map=None):
    entity_recall = _compute_entity_recall(local_model, oracle_model)
    rel_recall = _compute_relationship_recall(local_model, oracle_model, id_map=id_map)
    return 0.7 * entity_recall + 0.3 * rel_recall

def _compute_relationship_recall(local_model, oracle_model, id_map=None):
    """Recall of oracle relationships found (after ID remapping)."""
    if id_map is None:
        id_map = compute_entity_match_map(local_model, oracle_model)
    def remap(eid): return id_map.get(eid, eid)
    local_rels = {(r.type, remap(r.from_id), remap(r.to_id)) for r in local_model.relationships}
    oracle_rels = {(r.type, r.from_id, r.to_id) for r in oracle_model.relationships}
    if not oracle_rels:
        return 1.0
    if not local_rels:
        return 0.0
    return len(local_rels & oracle_rels) / len(oracle_rels)
```

**Step 4: Add async embedding pass (Pass 4) — optional enhancement**

Add `compute_entity_match_map_async()` that adds a 4th pass using `OllamaEmbedder` for remaining unmatched entities (cosine > 0.7 threshold). This is called from an async evaluator path.

**Step 5: Run tests, commit**

Run: `pytest tests/test_training/test_evaluator.py -v`
Expected: All pass (existing + new)

Run: `pytest tests/ -x -q`
Expected: 325+ passed

```bash
git add -A && git commit -m "feat(training): semantic entity matching + relationship remapping in evaluator"
```

---

### Task 3: Implement Reconstruction Fidelity via Stub Generation

**Files:**
- Modify: `src/architecture_model/training/evaluator.py`
- Modify: `src/architecture_model/training/surrogate.py:75-78` (prompt)
- Test: `tests/test_training/test_evaluator.py`

**Step 1: Write failing test**

```python
class TestReconstructionFidelity:
    def test_identical_code_scores_one(self):
        from architecture_model.training.evaluator import compute_reconstruction_fidelity
        code = "class Foo:\n    def bar(self): pass\n    def baz(self): pass\n"
        assert compute_reconstruction_fidelity(code, code) == 1.0

    def test_partial_overlap(self):
        from architecture_model.training.evaluator import compute_reconstruction_fidelity
        original = "class Foo:\n    def bar(self): pass\n    def baz(self): pass\n"
        stubs = "class Foo:\n    def bar(self): ...\n    def qux(self): ...\n"
        score = compute_reconstruction_fidelity(original, stubs)
        # Foo and bar match, baz vs qux don't
        assert 0.3 < score < 0.9

    def test_no_overlap_scores_zero(self):
        from architecture_model.training.evaluator import compute_reconstruction_fidelity
        original = "class Foo:\n    def bar(self): pass\n"
        stubs = "class Baz:\n    def qux(self): ...\n"
        assert compute_reconstruction_fidelity(original, stubs) == 0.0

    def test_invalid_syntax_falls_back_to_regex(self):
        from architecture_model.training.evaluator import compute_reconstruction_fidelity
        original = "class Foo:\n    def bar(self): pass\n"
        stubs = "class Foo:\n    def bar(self  # invalid syntax\n"
        score = compute_reconstruction_fidelity(original, stubs)
        # Should still find "class Foo" via regex fallback
        assert score > 0.0
```

**Step 2: Implement `compute_reconstruction_fidelity()` — ENSEMBLE approach**

Add to evaluator.py — two-component ensemble:
1. **AST Jaccard (0.5 weight):** Extract `ClassName.method_name` signatures from both code strings via AST (with regex fallback), compute set Jaccard.
2. **Embedding cosine (0.5 weight):** Embed both code strings with OllamaEmbedder, compute cosine similarity.

```python
def compute_reconstruction_fidelity(
    original_code: str,
    reconstructed_code: str,
    embedding_score: float | None = None,
) -> float:
    """Ensemble: 0.5 * AST signature Jaccard + 0.5 * embedding cosine.
    
    If embedding_score is None (embeddings unavailable), falls back to AST-only.
    """
    ast_score = _compute_ast_signature_jaccard(original_code, reconstructed_code)
    if embedding_score is not None:
        return 0.5 * ast_score + 0.5 * embedding_score
    return ast_score
```

The async path in `Evaluator.compute_loss_async()` will call embeddings and pass `embedding_score`. The sync path falls back to AST-only.

**Step 3: Update `_GENERATE_SYSTEM_PROMPT`** in surrogate.py to produce stubs:

```python
_GENERATE_SYSTEM_PROMPT = """\
You are a code stub generation engine. Given an architecture model YAML, \
generate Python stub code implementing the described architecture. \
Output class definitions with method signatures and brief docstrings. \
Do NOT implement method bodies — use 'pass' or '...' for all bodies. \
Output only Python code — no explanations, no markdown fences."""
```

**Step 4: Run tests, commit**

```bash
pytest tests/test_training/test_evaluator.py -v
pytest tests/ -x -q
git add -A && git commit -m "feat(training): implement reconstruction fidelity via AST+embedding ensemble"
```

---

### Task 4: Wire Enhanced Pipeline into MPC _process_repo

**Files:**
- Modify: `src/architecture_model/training/pipeline.py:108-166`
- Test: Add integration test or modify existing pipeline tests

**Step 1: Write test verifying enhanced pipeline is used**

```python
@pytest.mark.asyncio
async def test_process_repo_uses_enhanced_extract(self):
    """_process_repo should call enhanced_extract, not raw extract_model."""
    from unittest.mock import patch, AsyncMock, MagicMock
    # Setup pipeline with mocks
    # Patch enhanced_extract to return a model
    # Verify it was called (not surrogate.extract_model directly)
```

**Step 2: Modify `_process_repo`**

Replace:
```python
code_context = self._read_code_context(clone_path)
local_model = await self.surrogate.extract_model(code_context)
```

With:
```python
local_model, confidence = await self.enhanced_extract(clone_path)
code_context = self._read_code_context(clone_path)  # for oracle
```

**Step 3: Run tests, commit**

```bash
pytest tests/ -x -q
git add -A && git commit -m "feat(training): wire enhanced pipeline into MPC _process_repo"
```

---

### Task 5: Fill Unused Context Budget with Raw Code

**Files:**
- Modify: `src/architecture_model/training/context_builder.py`
- Modify: `tests/test_training/test_context_builder.py`

**Step 1: Write failing test**

```python
def test_fill_budget_adds_raw_code_when_under_budget(self, tmp_path):
    """When a slice uses <70% budget, raw code is appended."""
    (tmp_path / "__init__.py").write_text("from .core import Engine")
    (tmp_path / "core.py").write_text(
        "class Engine:\n"
        "    '''The core processing engine.'''\n"
        "    def process(self, data):\n"
        "        '''Process incoming data through the pipeline.'''\n"
        "        return self._transform(data)\n"
        "    def _transform(self, data):\n"
        "        return data.upper()\n"
    )
    # Small budget so AST summary fills <70%
    cb = ContextBuilder(tmp_path, max_chars=50000)  # 10k per slice
    slices = cb.build()
    combined = slices.combined()
    # With budget fill, raw code should appear
    assert "Process incoming data" in combined or "transform" in combined
```

**Step 2: Add `_fill_budget()` method and apply to each slice builder**

```python
def _fill_budget(self, slice_text: str, relevant_files: list[Path]) -> str:
    """If slice uses <70% of budget, append raw code from relevant files."""
    budget_target = int(self._per_slice * 0.7)
    budget_remaining = budget_target - len(slice_text)
    if budget_remaining < 200:
        return slice_text
    
    parts = [slice_text, "\n\n# --- RAW CODE (remaining budget) ---"]
    for f in relevant_files:
        if budget_remaining <= 0:
            break
        try:
            content = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        chunk = f"\n# {f.relative_to(self.repo_path)}\n{content[:budget_remaining]}"
        parts.append(chunk)
        budget_remaining -= len(chunk)
    
    return self._truncate("\n".join(parts))
```

Apply at end of each `_build_*_slice` before return, passing appropriate files:
- `_build_structure_slice` → top-ranked files by `_rank_files`
- `_build_boundaries_slice` → API/interface files
- `_build_behavior_slice` → handler/task files
- `_build_relationships_slice` → most-imported files
- `_build_constraints_slice` → config/type files

**Step 3: Run tests, commit**

```bash
pytest tests/test_training/test_context_builder.py -v
pytest tests/ -x -q
git add -A && git commit -m "feat(training): fill unused context budget with raw code"
```

---

### Task 6: Add DatasetStore.count()

**Files:**
- Modify: `src/architecture_model/training/dataset.py`
- Modify: `tests/test_training/test_dataset.py`

**Step 1: Write failing test**

```python
def test_count_returns_total(self, tmp_path):
    store = DatasetStore(str(tmp_path / "test.db"))
    assert store.count() == 0
    store.save(TrainingExample(
        repo_url="https://github.com/test/test",
        repo_sha="abc123",
        code_context="# code",
        local_output="# model",
        iteration=1,
    ))
    assert store.count() == 1
```

**Step 2: Implement**

Add to `DatasetStore` class:
```python
def count(self) -> int:
    """Return total number of training examples."""
    row = self._conn.execute("SELECT COUNT(*) FROM training_examples").fetchone()
    return row[0]
```

**Step 3: Run tests, commit**

```bash
pytest tests/test_training/test_dataset.py -v
pytest tests/ -x -q
git add -A && git commit -m "feat(training): add DatasetStore.count() convenience method"
```

---

### Task 7: Integration Verification

**Step 1:** Run full test suite: `pytest tests/ -v` — all should pass

**Step 2:** Run MPC loop and verify improved metrics:
```python
# Expected: structural_accuracy 0.3-0.7 (was 0.01-0.08)
# Expected: reconstruction_fidelity > 0 (was 0.0)
```

**Step 3:** Commit any remaining fixes

---

### Task 8: Loss-Weighted SFT Training

**Files:**
- Modify: `src/architecture_model/training/dataset.py`
- Modify: `src/architecture_model/training/trainer.py`
- Test: `tests/test_training/test_trainer.py`, `tests/test_training/test_dataset.py`

**Step 1: Write failing tests**

```python
# tests/test_training/test_dataset.py — add to existing
class TestExportWeighted:
    def test_export_weighted_includes_sample_weight(self, tmp_path):
        store = DatasetStore(str(tmp_path / "test.db"))
        store.save(TrainingExample(
            repo_url="https://github.com/test/a",
            repo_sha="abc",
            code_context="# code",
            local_output="# model",
            oracle_output="# oracle",
            loss_vector={"structural_accuracy": 0.3, "completeness": 0.5,
                         "reconstruction_fidelity": 0.0, "validator_score": 80},
            iteration=1,
        ))
        examples = store.export_weighted()
        assert "sample_weight" in examples[0]
        # structural_accuracy=0.3 → weight = 1.0 + (1-0.3)*2 = 2.4
        assert examples[0]["sample_weight"] == pytest.approx(2.4, abs=0.1)

    def test_export_weighted_high_accuracy_low_weight(self, tmp_path):
        store = DatasetStore(str(tmp_path / "test.db"))
        store.save(TrainingExample(
            repo_url="https://github.com/test/b",
            repo_sha="def",
            code_context="# code",
            local_output="# model",
            oracle_output="# oracle",
            loss_vector={"structural_accuracy": 0.9, "completeness": 0.9,
                         "reconstruction_fidelity": 0.5, "validator_score": 95},
            iteration=1,
        ))
        examples = store.export_weighted()
        # structural_accuracy=0.9 → weight = 1.0 + (1-0.9)*2 = 1.2
        assert examples[0]["sample_weight"] == pytest.approx(1.2, abs=0.1)
```

```python
# tests/test_training/test_trainer.py — add
class TestWeightedTrainer:
    def test_weighted_trainer_accepts_weights(self):
        """WeightedCETrainer should be importable and accept sample_weight."""
        from architecture_model.training.trainer import WeightedCETrainer
        assert WeightedCETrainer is not None
```

**Step 2: Implement**

Add to `dataset.py`:
```python
def export_weighted(self) -> list[dict]:
    """Export training examples with sample_weight based on inverse loss."""
    examples = self.export_for_training()
    for ex in examples:
        loss = ex.get("loss_vector") or {}
        acc = loss.get("structural_accuracy", 0.5)
        ex["sample_weight"] = 1.0 + (1.0 - acc) * 2.0
    return examples
```

Add to `trainer.py`:
```python
class WeightedCETrainer(Trainer):
    """HF Trainer subclass that applies per-sample loss weights."""

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        weights = inputs.pop("sample_weight", None)
        outputs = model(**inputs)
        loss = outputs.loss
        if weights is not None:
            loss = (loss * weights).mean()
        return (loss, outputs) if return_outputs else loss
```

**Step 3: Run tests, commit**

```bash
pytest tests/test_training/test_dataset.py tests/test_training/test_trainer.py -v
pytest tests/ -x -q
git add -A && git commit -m "feat(training): add loss-weighted SFT training with sample weights"
```

---

### Task 9: DPO Preference Training

**Files:**
- Modify: `src/architecture_model/training/dataset.py` (preferences table)
- Create: `src/architecture_model/training/trainer_dpo.py`
- Test: `tests/test_training/test_dataset.py`, `tests/test_training/test_trainer_dpo.py`

**Step 1: Write failing tests**

```python
# tests/test_training/test_dataset.py — add
class TestPreferences:
    def test_save_and_export_preference(self, tmp_path):
        store = DatasetStore(str(tmp_path / "test.db"))
        store.save_preference(
            prompt="# code context",
            chosen="entities:\n  components:\n    - id: C01",
            rejected="entities:\n  components: []",
            margin=0.7,
            iteration=1,
        )
        prefs = store.export_preferences()
        assert len(prefs) == 1
        assert prefs[0]["prompt"] == "# code context"
        assert prefs[0]["chosen"].startswith("entities:")
        assert prefs[0]["rejected"].startswith("entities:")

    def test_preference_count(self, tmp_path):
        store = DatasetStore(str(tmp_path / "test.db"))
        store.save_preference("a", "b", "c", 0.5, 1)
        store.save_preference("d", "e", "f", 0.3, 2)
        assert store.count_preferences() == 2
```

```python
# tests/test_training/test_trainer_dpo.py
"""Tests for DPO preference trainer."""
import pytest
from unittest.mock import patch, MagicMock

from architecture_model.training.trainer_dpo import DPOLoRATrainer


class TestDPOLoRATrainer:
    def test_init_default_config(self):
        trainer = DPOLoRATrainer()
        assert trainer.base_model == "Qwen/Qwen2.5-7B-Instruct"

    def test_requires_trl(self):
        trainer = DPOLoRATrainer()
        with patch("architecture_model.training.trainer_dpo.HAS_TRL", False):
            with pytest.raises(RuntimeError, match="trl"):
                trainer.train(MagicMock(), Path("/tmp/out"))
```

**Step 2: Implement**

Add preferences table + methods to `dataset.py`:
```python
# In DatasetStore.__init__, add table creation:
self._conn.execute("""
    CREATE TABLE IF NOT EXISTS preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prompt TEXT NOT NULL,
        chosen TEXT NOT NULL,
        rejected TEXT NOT NULL,
        margin REAL NOT NULL,
        iteration INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

def save_preference(self, prompt: str, chosen: str, rejected: str, margin: float, iteration: int) -> None:
    self._conn.execute(
        "INSERT INTO preferences (prompt, chosen, rejected, margin, iteration) VALUES (?, ?, ?, ?, ?)",
        (prompt, chosen, rejected, margin, iteration),
    )
    self._conn.commit()

def export_preferences(self) -> list[dict]:
    rows = self._conn.execute("SELECT prompt, chosen, rejected FROM preferences").fetchall()
    return [{"prompt": r[0], "chosen": r[1], "rejected": r[2]} for r in rows]

def count_preferences(self) -> int:
    row = self._conn.execute("SELECT COUNT(*) FROM preferences").fetchone()
    return row[0]
```

Create `trainer_dpo.py`:
```python
"""DPO Preference Trainer using trl.DPOTrainer."""
from __future__ import annotations
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from architecture_model.training.model_config import ModelConfig, get_model_config

if TYPE_CHECKING:
    from datasets import Dataset

try:
    from trl import DPOTrainer, DPOConfig
    HAS_TRL = True
except ImportError:
    HAS_TRL = False

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

class DPOLoRATrainer:
    """DPO fine-tuning using trl for preference learning."""

    def __init__(self, base_model: str = "Qwen/Qwen2.5-7B-Instruct",
                 model_config: Optional[ModelConfig] = None, beta: float = 0.1) -> None:
        if model_config:
            self.base_model = model_config.hf_model_id
            self._config = model_config
        else:
            self.base_model = base_model
            self._config = None
        self.beta = beta

    def train(self, preference_dataset: "Dataset", output_dir: Path, epochs: int = 1) -> Path:
        if not HAS_TRL:
            raise RuntimeError("trl is required for DPO training. Install with: pip install trl")
        if not HAS_TRANSFORMERS:
            raise RuntimeError("transformers + peft required. Install with: pip install transformers peft")

        model = AutoModelForCausalLM.from_pretrained(self.base_model)
        tokenizer = AutoTokenizer.from_pretrained(self.base_model)

        lora_config = LoraConfig(
            r=16, lora_alpha=32,
            target_modules=self._config.lora_target_modules if self._config else ["q_proj", "v_proj"],
            task_type="CAUSAL_LM",
        )

        output_dir = Path(output_dir)
        dpo_config = DPOConfig(
            output_dir=str(output_dir),
            num_train_epochs=epochs,
            beta=self.beta,
            per_device_train_batch_size=2,
        )

        trainer = DPOTrainer(
            model=model,
            args=dpo_config,
            train_dataset=preference_dataset,
            tokenizer=tokenizer,
            peft_config=lora_config,
        )
        trainer.train()
        trainer.save_model(str(output_dir))
        return output_dir
```

**Step 3: Run tests, commit**

```bash
pytest tests/test_training/test_dataset.py tests/test_training/test_trainer_dpo.py -v
pytest tests/ -x -q
git add -A && git commit -m "feat(training): add DPO preference training with trl"
```

---

### Task 10: Pareto-Based Agreement + Convergence Wiring

**Files:**
- Modify: `src/architecture_model/training/controller.py`
- Modify: `src/architecture_model/training/pipeline.py`
- Test: `tests/test_training/test_controller.py`, `tests/test_training/test_pipeline.py`

**Step 1: Write failing tests**

```python
# tests/test_training/test_controller.py — add
class TestParetoAgreement:
    def test_first_loss_always_agrees(self):
        state = MPCState()
        ctrl = MPCController(state)
        loss = LossVector(structural_accuracy=0.5, completeness=0.6,
                          reconstruction_fidelity=0.3, validator_score=80)
        agreed = ctrl.record_loss(loss)
        assert agreed is True

    def test_dominated_loss_disagrees(self):
        state = MPCState()
        ctrl = MPCController(state)
        # First: good
        ctrl.record_loss(LossVector(0.8, 0.9, 0.7, 95))
        # Second: strictly worse on all dimensions
        agreed = ctrl.record_loss(LossVector(0.3, 0.4, 0.2, 50))
        assert agreed is False

    def test_non_dominated_loss_agrees(self):
        state = MPCState()
        ctrl = MPCController(state)
        ctrl.record_loss(LossVector(0.8, 0.5, 0.7, 90))
        # Better on completeness, worse on accuracy — not dominated
        agreed = ctrl.record_loss(LossVector(0.6, 0.9, 0.5, 85))
        assert agreed is True

    def test_convergence_when_all_agree(self):
        state = MPCState()
        ctrl = MPCController(state)
        ctrl._CONVERGENCE_WINDOW = 3
        # 3 non-dominated (all equally good, different tradeoffs)
        ctrl.record_loss(LossVector(0.9, 0.5, 0.7, 90))
        ctrl.record_loss(LossVector(0.5, 0.9, 0.7, 90))
        ctrl.record_loss(LossVector(0.7, 0.7, 0.9, 90))
        assert ctrl.is_converged() is True
```

**Step 2: Implement**

Modify `controller.py`:
```python
from architecture_model.training.evaluator import LossVector

class MPCController:
    def __init__(self, state, oracle_budget=None):
        # ... existing ...
        self._pareto_front: list[LossVector] = []

    def record_loss(self, loss: LossVector) -> bool:
        """Check if loss is competitive with Pareto front. Returns True if non-dominated."""
        dominated = any(f.dominates(loss) for f in self._pareto_front)
        agreed = not dominated

        # Update Pareto front (add then prune dominated)
        candidates = self._pareto_front + [loss]
        self._pareto_front = [
            c for c in candidates
            if not any(o.dominates(c) for o in candidates if o is not c)
        ]

        self.state.convergence_history.append(1.0 if agreed else 0.0)
        return agreed

    def is_converged(self) -> bool:
        """Converged when 80%+ of recent outputs are non-dominated."""
        history = self.state.convergence_history
        if len(history) < self._CONVERGENCE_WINDOW:
            return False
        recent = history[-self._CONVERGENCE_WINDOW:]
        return sum(recent) / len(recent) >= 0.8
```

Modify `_process_repo` in pipeline.py to:
1. Call `self.controller.record_loss(loss)` after computing loss
2. Save DPO preference when `loss.structural_accuracy < 0.6`

**Step 3: Run tests, commit**

```bash
pytest tests/test_training/test_controller.py -v
pytest tests/ -x -q
git add -A && git commit -m "feat(training): Pareto-based agreement tracking and convergence detection"
```

---

## Execution Order (Recommended)

```
6 (trivial: count) → 1 (embeddings) → 2 (evaluator + weighted completeness) → 3 (reconstruction ensemble) → 5 (context fill) → 8 (loss-weighted SFT) → 9 (DPO pairs) → 10 (Pareto agreement) → 4 (pipeline wiring) → 7 (verify)
```

Tasks 1→2 are sequential (2 depends on 1). Tasks 3, 5, 6 are independent. Tasks 8, 9, 10 depend on proper metrics (Tasks 2, 3). Task 4 wires everything together. Task 7 validates the full system.
