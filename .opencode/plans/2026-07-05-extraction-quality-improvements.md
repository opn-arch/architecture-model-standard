# Extraction Quality Improvements Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the 4 highest-impact quality issues identified in the 10-repo validation: prompt precision (edge_precision=0.18), entity F1 ID collision, reconstruction_fidelity anti-correlation, and facade-pattern test mapping (httpcore=0%).

**Architecture:** Each task is independent (no shared state) and can be executed in parallel. Task 1 modifies the extraction prompt and adds few-shot examples. Task 2 removes Pass 1 ID matching from entity F1. Task 3 drops the reconstruction_fidelity objective entirely. Task 4 adds `__init__.py` re-export resolution to the backward validator.

**Tech Stack:** Python 3.14, pytest, AST module, YAML, sqlite3, Ollama (nomic-embed-text for embeddings), copilot-relay for oracle.

---

## Task 1: Fix Extraction Prompt (Precision + Few-Shot)

**Problem:** `edge_precision = 0.18` means 82% of LLM-generated relationships have no import evidence. The prompt gives zero guidance on when to create relationships or how many components to produce.

**Files:**
- Modify: `src/architecture_model/training/oracle_evolution.py:17-50` (the `_BASE_EXTRACTION_PROMPT`)
- Create: `src/architecture_model/training/few_shot_examples.py` (few-shot YAML examples)
- Modify: `src/architecture_model/training/oracle_context.py` (inject few-shot into context)
- Test: `tests/test_training/test_oracle_evolution.py` (verify prompt structure)

**Step 1: Write failing tests for the new prompt constraints**

File: `tests/test_training/test_oracle_evolution.py`

```python
def test_prompt_contains_relationship_precision_guidance():
    """Prompt must instruct LLM to only create evidence-backed relationships."""
    from architecture_model.training.oracle_evolution import _BASE_EXTRACTION_PROMPT
    assert "import" in _BASE_EXTRACTION_PROMPT.lower() or "evidence" in _BASE_EXTRACTION_PROMPT.lower()
    assert "do not invent" in _BASE_EXTRACTION_PROMPT.lower() or "only create" in _BASE_EXTRACTION_PROMPT.lower()


def test_prompt_contains_granularity_guidance():
    """Prompt must provide granularity targets."""
    from architecture_model.training.oracle_evolution import _BASE_EXTRACTION_PROMPT
    # Should mention a component-per-file or module-level decomposition
    assert "module" in _BASE_EXTRACTION_PROMPT.lower() or "file" in _BASE_EXTRACTION_PROMPT.lower()
    assert "granularity" in _BASE_EXTRACTION_PROMPT.lower() or "one component per" in _BASE_EXTRACTION_PROMPT.lower()


def test_prompt_contains_few_shot_reference():
    """Prompt should reference or include an example extraction."""
    from architecture_model.training.oracle_evolution import _BASE_EXTRACTION_PROMPT
    # Either inline example or reference to few-shot
    assert "example" in _BASE_EXTRACTION_PROMPT.lower() or "---" in _BASE_EXTRACTION_PROMPT
```

Run: `pytest tests/test_training/test_oracle_evolution.py -v -k "prompt_contains"`
Expected: FAIL (current prompt lacks these)

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_training/test_oracle_evolution.py -v -k "prompt_contains"`
Expected: 3 FAIL

**Step 3: Create few-shot examples module**

File: `src/architecture_model/training/few_shot_examples.py`

```python
"""Few-shot examples for architecture extraction prompt.

Contains:
1. A manually crafted minimal example (demonstrates restraint)
2. A real extraction excerpt (demonstrates real-world patterns)
"""

# Manually crafted example showing precise relationship discipline
MANUAL_EXAMPLE = """\
# Example: A small HTTP client library with 5 Python files

Given these source files:
- client.py (imports: connection, auth)
- connection.py (imports: transport)
- transport.py (no internal imports)
- auth.py (imports: transport)
- __init__.py (re-exports from client, connection)

## Correct extraction:

meta:
  schema_version: "1.0"
  project: "http-client"
entities:
  actors:
    - id: A1
      name: API Consumer
      status: ACTIVE
  capabilities:
    - id: CAP1
      name: HTTP Request Handling
      status: ACTIVE
  behaviors:
    - id: B1
      name: Send Request
      status: ACTIVE
  interfaces:
    - id: IF1
      name: Client Public API
      status: ACTIVE
  constraints:
    - id: CON1
      name: Connection Pooling Limit
      status: ACTIVE
  layers:
    - id: L1
      name: Client Layer
      status: ACTIVE
    - id: L2
      name: Transport Layer
      status: ACTIVE
  components:
    - id: C1
      name: Client
      status: ACTIVE
      layer: L1
    - id: C2
      name: Connection Manager
      status: ACTIVE
      layer: L1
    - id: C3
      name: Transport
      status: ACTIVE
      layer: L2
    - id: C4
      name: Auth Handler
      status: ACTIVE
      layer: L2
relationships:
  # ONLY relationships backed by actual import statements:
  - type: depends-on
    from: C1          # client.py imports connection
    to: C2
  - type: depends-on
    from: C1          # client.py imports auth
    to: C4
  - type: depends-on
    from: C2          # connection.py imports transport
    to: C3
  - type: depends-on
    from: C4          # auth.py imports transport
    to: C3
  # Structural relationships (no import backing needed):
  - type: contains
    from: L1
    to: C1
  - type: contains
    from: L1
    to: C2
  - type: contains
    from: L2
    to: C3
  - type: contains
    from: L2
    to: C4
  - type: realizes
    from: C1
    to: CAP1
  - type: exposes
    from: C1
    to: IF1

## Key decisions explained:
# - 4 components for 5 files (excluding __init__.py which is a re-export facade)
# - Only 4 depends-on relationships because only 4 cross-file import edges exist
# - contains/realizes/exposes don't need import backing (structural)
# - NO relationship between Transport and Connection Manager in reverse direction
#   even though they're related conceptually — no import evidence for it
"""

# Real-world extraction excerpt (trimmed from python-dotenv oracle output)
# This will be populated during implementation by running oracle on python-dotenv
# and selecting the model that scored highest on CoverageScorer
REAL_EXAMPLE_HEADER = """\
# Example: python-dotenv (real extraction from a .env file loading library)
# Source structure: main.py, cli.py, parser.py, variables.py, ipython.py, __init__.py
"""

# Placeholder — populated in Step 5
REAL_EXAMPLE = ""
```

**Step 4: Rewrite `_BASE_EXTRACTION_PROMPT` with precision guidance**

File: `src/architecture_model/training/oracle_evolution.py` (replace lines 17-50)

```python
_BASE_EXTRACTION_PROMPT = """\
You are an architecture extraction engine. Given source code, extract a \
UAM (Universal Architecture Model) in YAML format.

## Entity Types (7)
- actors: external agents (human, system, external-service)
- capabilities: functional blocks the system provides
- behaviors: use cases, workflows, operational sequences
- interfaces: APIs, protocols, data exchanges
- constraints: non-functional requirements, design rules
- layers: architectural tiers (group components by abstraction level)
- components: deployable units — typically ONE component per Python module/file

## Relationship Types (8)
- realizes: component realizes a capability
- contains: layer contains a component (structural grouping)
- depends-on: component A depends on component B (A imports from B)
- exposes: component exposes an interface
- consumes: component consumes an interface
- traces-to: entity traces to a requirement
- allocated-to: component allocated to a layer
- constrained-by: entity constrained by a constraint

## CRITICAL: Relationship Precision Rules
1. ONLY create `depends-on` relationships where you can see an actual import statement \
(e.g., `from module_b import X` in module_a means A depends-on B)
2. `contains` and `allocated-to` are structural — use them to group components into layers
3. `realizes` and `exposes` connect components to capabilities/interfaces — \
use sparingly, only for primary responsibilities
4. Do NOT invent relationships based on conceptual similarity — every dependency \
MUST have import evidence in the source code
5. When in doubt, OMIT the relationship. Fewer precise relationships are better \
than many speculative ones.

## Granularity Guidelines
- Create one component per significant Python module (file with >20 LOC)
- Small utility files (<20 LOC) can be merged into their parent component
- `__init__.py` files are re-export facades, not separate components
- Aim for 5-15 components for small libraries, 10-30 for medium ones
- Every component MUST map to at least one source file

## Output Format
Output ONLY valid YAML matching this structure:
meta:
  schema_version: "1.0"
  project: "<project name>"
entities:
  actors: [...]
  capabilities: [...]
  behaviors: [...]
  interfaces: [...]
  constraints: [...]
  layers: [...]
  components: [...]
relationships: [...]

Each entity: id, name, status (ACTIVE/PLANNED/DORMANT/DEPRECATED).
Each relationship: type, from, to.

Output raw YAML only — no markdown fences, no explanation."""
```

**Step 5: Generate real few-shot example from python-dotenv**

This is a manual step during implementation:
1. Run oracle extraction on python-dotenv once
2. Score it with CoverageScorer
3. If overall > 0.6, use it as the real example
4. Trim to essential structure (remove verbose descriptions)
5. Save to `few_shot_examples.py` as `REAL_EXAMPLE`

Run: `python3 -c "..." # one-off extraction script (see implementation notes below)`

**Step 6: Integrate few-shot into oracle context**

File: `src/architecture_model/training/oracle_context.py`

Add to the `build()` method, prepending the few-shot example to the context string:

```python
from architecture_model.training.few_shot_examples import MANUAL_EXAMPLE, REAL_EXAMPLE

# In build() method, after assembling the manifest context:
few_shot_section = f"\n\n## Few-Shot Example\n{MANUAL_EXAMPLE}"
if REAL_EXAMPLE:
    few_shot_section += f"\n\n## Real-World Example\n{REAL_EXAMPLE}"
context = few_shot_section + "\n\n## Your Task: Extract architecture for the following code\n\n" + context
```

**Step 7: Run tests to verify they pass**

Run: `pytest tests/test_training/test_oracle_evolution.py -v -k "prompt_contains"`
Expected: 3 PASS

**Step 8: Run full test suite**

Run: `pytest tests/ -x -q --tb=short`
Expected: 435+ passed

**Step 9: Commit**

```bash
git add src/architecture_model/training/oracle_evolution.py \
        src/architecture_model/training/few_shot_examples.py \
        src/architecture_model/training/oracle_context.py \
        tests/test_training/test_oracle_evolution.py
git commit -m "feat(training): add precision guidance + few-shot examples to extraction prompt

edge_precision=0.18 means 82% of relationships lack import evidence.
New prompt adds: relationship precision rules (only create depends-on
with import evidence), granularity guidelines (one component per module),
and few-shot examples showing restraint."
```

---

## Task 2: Fix Entity F1 ID Collision

**Problem:** LLMs generate sequential IDs (C1, C2, C3...). When comparing two models, Pass 1 matches by `type + ID`, causing position-based matching (C1=C1, C2=C2) regardless of semantic content. Two completely different architectures with same IDs get inflated F1.

**Fix:** Remove Pass 1 (exact ID matching) from `compute_entity_f1`. Keep name-based matching (Pass 2) and fuzzy matching (Pass 3) in `compute_entity_match_map`. The entity F1 function should use name-based matching only.

**Files:**
- Modify: `src/architecture_model/training/evaluator.py:96-126` (`compute_entity_f1`)
- Modify: `src/architecture_model/training/evaluator.py:129-175` (`compute_entity_match_map`)
- Modify: `tests/test_training/test_evaluator.py` (update tests)

**Step 1: Write a failing test demonstrating the ID collision bug**

File: `tests/test_training/test_evaluator.py` (add to `TestEntityF1` class)

```python
def test_entity_f1_rejects_id_only_match(self):
    """Two models with same IDs but different names should NOT match by ID."""
    from architecture_model.training.evaluator import compute_entity_f1

    # Model A: C1=Parser, C2=Lexer
    model_a = self._make_model(components=[
        {"id": "C1", "name": "Parser"},
        {"id": "C2", "name": "Lexer"},
    ])
    # Model B: C1=HTTPClient, C2=ConnectionPool (completely different semantics)
    model_b = self._make_model(components=[
        {"id": "C1", "name": "HTTP Client"},
        {"id": "C2", "name": "Connection Pool"},
    ])

    f1 = compute_entity_f1(model_a, model_b)
    # These should NOT match — names are completely different
    assert f1 < 0.5, f"ID collision: F1={f1}, expected <0.5 since names differ"


def test_entity_f1_matches_by_name_across_ids(self):
    """Same names with different IDs should still match."""
    from architecture_model.training.evaluator import compute_entity_f1

    # Model A: C1=Parser, C2=Lexer
    model_a = self._make_model(components=[
        {"id": "C1", "name": "Parser"},
        {"id": "C2", "name": "Lexer"},
    ])
    # Model B: COMP_A=Parser, COMP_B=Lexer (different IDs, same names)
    model_b = self._make_model(components=[
        {"id": "COMP_A", "name": "Parser"},
        {"id": "COMP_B", "name": "Lexer"},
    ])

    f1 = compute_entity_f1(model_a, model_b)
    assert f1 == 1.0, f"Name match failed: F1={f1}, expected 1.0"
```

Note: The `TestEntityF1` class may need a `_make_model` helper. Check if one exists; if not, add:

```python
@staticmethod
def _make_model(components=None, **kwargs):
    """Helper to build minimal ArchitectureModel for testing."""
    from architecture_model.core.types import (
        ArchitectureModel, Entities, Component, Meta,
    )
    comps = [Component(id=c["id"], name=c["name"], status="ACTIVE") for c in (components or [])]
    return ArchitectureModel(
        meta=Meta(schema_version="1.0", project="test"),
        entities=Entities(components=comps),
        relationships=[],
    )
```

**Step 2: Run the new tests to confirm they fail**

Run: `pytest tests/test_training/test_evaluator.py -v -k "rejects_id_only_match or matches_by_name_across_ids"`
Expected: `test_entity_f1_rejects_id_only_match` FAILS (current code matches C1=C1 by ID)

**Step 3: Fix `compute_entity_f1` — remove Pass 1 (ID matching)**

File: `src/architecture_model/training/evaluator.py`

Replace the current `compute_entity_f1` function (approximately lines 96-126):

```python
def compute_entity_f1(local_model: ArchitectureModel, oracle_model: ArchitectureModel) -> float:
    """
    Match entities by type + name (case-insensitive), with fuzzy fallback.
    Compute precision, recall, and F1.

    NOTE: Does NOT match by ID because LLMs generate sequential IDs (C1, C2)
    that collide across different extractions, causing spurious position-based matches.
    """
    local_entities = _collect_typed_entities(local_model)
    oracle_entities = _collect_typed_entities(oracle_model)

    if not local_entities and not oracle_entities:
        return 1.0  # vacuously true

    if not local_entities or not oracle_entities:
        return 0.0

    oracle_matched: set[int] = set()
    local_matched: set[int] = set()

    # Pass 1: match by type + name (exact, case-insensitive)
    for li, (l_type, l_id, l_name) in enumerate(local_entities):
        for oi, (o_type, o_id, o_name) in enumerate(oracle_entities):
            if oi in oracle_matched:
                continue
            if l_type == o_type and l_name == o_name:
                local_matched.add(li)
                oracle_matched.add(oi)
                break

    # Pass 2: fuzzy match unmatched by type + word Jaccard >= 0.4
    for li, (l_type, l_id, l_name) in enumerate(local_entities):
        if li in local_matched:
            continue
        best_score = 0.0
        best_oi = -1
        for oi, (o_type, o_id, o_name) in enumerate(oracle_entities):
            if oi in oracle_matched:
                continue
            if l_type != o_type:
                continue
            l_words = set(l_name.split())
            o_words = set(o_name.split())
            if not l_words or not o_words:
                continue
            jaccard = len(l_words & o_words) / len(l_words | o_words)
            if jaccard >= 0.4 and jaccard > best_score:
                best_score = jaccard
                best_oi = oi
        if best_oi >= 0:
            local_matched.add(li)
            oracle_matched.add(best_oi)

    true_positives = len(local_matched)
    precision = true_positives / len(local_entities) if local_entities else 0.0
    recall = true_positives / len(oracle_entities) if oracle_entities else 0.0

    if precision + recall == 0:
        return 0.0

    return 2 * (precision * recall) / (precision + recall)
```

Also update `compute_entity_match_map` — remove its Pass 1 (exact ID match), renumber Pass 2→1, Pass 3→2:

```python
def compute_entity_match_map(
    local_model: ArchitectureModel, oracle_model: ArchitectureModel
) -> dict[str, str]:
    """Build a mapping from local entity IDs to oracle entity IDs.

    Pass 1: exact type + name (lowercase) match
    Pass 2: fuzzy name match via word Jaccard >= 0.4

    NOTE: No ID-based matching — LLMs generate sequential IDs that collide.
    """
    local_entities = _collect_typed_entities(local_model)
    oracle_entities = _collect_typed_entities(oracle_model)

    id_map: dict[str, str] = {}
    oracle_matched: set[int] = set()
    local_matched: set[int] = set()

    # Pass 1: exact type + name (lowercase)
    for li, (l_type, l_id, l_name) in enumerate(local_entities):
        for oi, (o_type, o_id, o_name) in enumerate(oracle_entities):
            if oi in oracle_matched:
                continue
            if l_type == o_type and l_name == o_name:
                id_map[l_id] = o_id
                local_matched.add(li)
                oracle_matched.add(oi)
                break

    # Pass 2: fuzzy name match via word Jaccard >= 0.4
    for li, (l_type, l_id, l_name) in enumerate(local_entities):
        if li in local_matched:
            continue
        best_score = 0.0
        best_oi = -1
        for oi, (o_type, o_id, o_name) in enumerate(oracle_entities):
            if oi in oracle_matched:
                continue
            if l_type != o_type:
                continue
            l_words = set(l_name.split())
            o_words = set(o_name.split())
            if not l_words or not o_words:
                continue
            jaccard = len(l_words & o_words) / len(l_words | o_words)
            if jaccard >= 0.4 and jaccard > best_score:
                best_score = jaccard
                best_oi = oi
        if best_oi >= 0:
            o_id = oracle_entities[best_oi][1]
            id_map[l_id] = o_id
            local_matched.add(li)
            oracle_matched.add(best_oi)

    return id_map
```

**Step 4: Update existing tests that relied on ID matching**

The test `test_entity_f1_perfect_match` passes identical models — still works (names match).
The test `test_entity_f1_name_fallback` tests name matching with different IDs — still works.

Check `test_exact_id_match` in `TestEntityMatchMap` — this test needs updating. The test likely matches entities that have the same ID AND same name. If so, it still passes (name match). If it relies on ID-only matching (same ID, different name), rename and rewrite it.

Look at the actual test carefully during implementation and decide whether to:
- Remove the test if it tested ID-only matching
- Keep it if it coincidentally also matches by name

**Step 5: Run tests**

Run: `pytest tests/test_training/test_evaluator.py -v`
Expected: All pass (including new collision tests)

**Step 6: Run full suite**

Run: `pytest tests/ -x -q --tb=short`
Expected: 435+ passed

**Step 7: Commit**

```bash
git add src/architecture_model/training/evaluator.py tests/test_training/test_evaluator.py
git commit -m "fix(evaluator): remove ID-based entity matching to prevent sequential ID collision

LLMs generate C1, C2, C3... IDs that collide across extractions.
Pass 1 (type+ID match) caused position-based matching regardless of
semantic content. Now uses name-only matching: exact name (Pass 1)
then word-Jaccard fuzzy (Pass 2, threshold 0.4)."
```

---

## Task 3: Drop Reconstruction Fidelity from LossVector

**Problem:** `reconstruction_fidelity` anti-correlates with quality (rewards copying code names verbatim, penalizes architectural abstraction). It's also operationally inert — the pipeline never supplies the `original_code`/`reconstructed_code` args, so it's always 0.0 in production.

**Fix:** Remove `reconstruction_fidelity` from `LossVector`, `compute_loss`, Pareto dominance, and all references. Reduces loss to 3 objectives: structural_accuracy, completeness, validator_score.

**Files:**
- Modify: `src/architecture_model/training/evaluator.py` (LossVector, compute_loss, remove helper functions)
- Modify: `src/architecture_model/training/pipeline.py:223` (loss_vector serialization)
- Modify: `scripts/test_multi_repo.py:319-344` (loss result recording)
- Modify: `tests/test_training/test_evaluator.py` (remove reconstruction tests, update assertions)
- Modify: `tests/test_training/test_controller.py` (update LossVector construction)
- Modify: `tests/test_training/test_pipeline.py:65` (update loss dict)
- Modify: `tests/test_training/test_dataset.py` (update loss examples)
- Modify: `scripts/test_httpx.py`, `scripts/test_sentry.py`, `scripts/test_integration.py` (remove field)

**Step 1: Write test asserting LossVector has exactly 3 fields**

File: `tests/test_training/test_evaluator.py`

```python
def test_loss_vector_has_three_objectives():
    """LossVector should have exactly 3 objectives (no reconstruction_fidelity)."""
    from architecture_model.training.evaluator import LossVector
    lv = LossVector(structural_accuracy=0.5, completeness=0.7, validator_score=90.0)
    assert hasattr(lv, 'structural_accuracy')
    assert hasattr(lv, 'completeness')
    assert hasattr(lv, 'validator_score')
    assert not hasattr(lv, 'reconstruction_fidelity')
```

Run: `pytest tests/test_training/test_evaluator.py::test_loss_vector_has_three_objectives -v`
Expected: FAIL (reconstruction_fidelity still exists)

**Step 2: Remove from LossVector dataclass**

File: `src/architecture_model/training/evaluator.py`

```python
@dataclass
class LossVector:
    """Multi-objective loss vector with 3 objectives."""

    structural_accuracy: float  # entity/relationship F1 vs oracle (0-1)
    completeness: float  # recall of oracle entities (0-1)
    validator_score: float  # existing 0-100 validator score

    def dominates(self, other: LossVector) -> bool:
        """Pareto dominance: better or equal on ALL, strictly better on at least one."""
        self_vals = (
            self.structural_accuracy,
            self.completeness,
            self.validator_score,
        )
        other_vals = (
            other.structural_accuracy,
            other.completeness,
            other.validator_score,
        )

        at_least_one_strictly_better = False
        for s, o in zip(self_vals, other_vals):
            if s < o:
                return False
            if s > o:
                at_least_one_strictly_better = True

        return at_least_one_strictly_better
```

**Step 3: Remove from `compute_loss`**

Remove parameters `original_code` and `reconstructed_code` from the method signature.
Remove the L3 computation section. Update the return:

```python
return LossVector(
    structural_accuracy=structural_accuracy,
    completeness=completeness,
    validator_score=validator_score,
)
```

**Step 4: Remove `_compute_line_jaccard` and `compute_reconstruction_fidelity` functions**

Delete both functions entirely (lines ~181-269). They are no longer called.

**Step 5: Update all test files**

For each test that constructs `LossVector(...)`, remove the `reconstruction_fidelity` field:

```python
# Before:
LossVector(structural_accuracy=0.8, completeness=0.9, reconstruction_fidelity=0.7, validator_score=95.0)
# After:
LossVector(structural_accuracy=0.8, completeness=0.9, validator_score=95.0)
```

Remove the entire `TestReconstructionFidelity` class (6 tests) from `test_evaluator.py`.

Update `test_evaluator_compute_loss` tests to not pass `original_code`/`reconstructed_code` and not assert on `reconstruction_fidelity`.

Files to update (grep for `reconstruction_fidelity`):
- `tests/test_training/test_evaluator.py` — multiple classes
- `tests/test_training/test_controller.py` — LossVector constructor calls
- `tests/test_training/test_pipeline.py` — loss dict reference
- `tests/test_training/test_dataset.py` — stored loss examples

**Step 6: Update scripts and pipeline**

In `pipeline.py` (line ~220-225):
```python
loss_vector = {
    "structural_accuracy": loss.structural_accuracy,
    "completeness": loss.completeness,
    "validator_score": loss.validator_score,
}
```

In `scripts/test_multi_repo.py` (loss recording sections):
```python
result["loss"] = {
    "structural_accuracy": loss.structural_accuracy,
    "completeness": loss.completeness,
    "validator_score": loss.validator_score,
}
# And the worst-case section:
result["loss"] = {
    "structural_accuracy": 0.0,
    "completeness": 0.0,
    "validator_score": 0.0,
}
```

Update `scripts/test_httpx.py`, `scripts/test_sentry.py`, `scripts/test_integration.py` similarly.

**Step 7: Run full test suite**

Run: `pytest tests/ -x -q --tb=short`
Expected: 429+ passed (6 reconstruction tests removed, others updated)

**Step 8: Commit**

```bash
git add -A
git commit -m "refactor(evaluator): drop reconstruction_fidelity from LossVector

Anti-correlates with quality (rewards verbatim code-name copying, penalizes
architectural abstraction). Was operationally inert (pipeline never supplied
code args, always 0.0). Pareto dominance now uses 3 objectives:
structural_accuracy, completeness, validator_score."
```

---

## Task 4: Fix Test Mapping for Facade-Pattern Repos

**Problem:** httpcore gets 0% test mapping because ALL its tests do `import httpcore` (bare package import). This resolves to `__init__.py` which maps to no component. The manifest now includes `exports` and `imports_detailed` data in `__init__.py`, but the backward validator doesn't use it.

**Root cause chain:**
1. Test file does `import httpcore`
2. `_build_import_to_file_map` maps `"httpcore"` → `"__init__.py"`
3. `_build_module_component_map` returns `""` for `__init__.py` (no component match)
4. Result: tested_component_ids remains empty → 0%

**Fix:** When an import resolves to `__init__.py` and `module_map` returns no component, follow the re-exports in `__init__.py` (available as `imports_detailed` with `is_relative: True` in the manifest) to find the actual submodule files, then map THOSE to components.

**Files:**
- Modify: `src/architecture_model/training/backward_validator.py:101-154` (`_check_test_mapping`)
- Test: `tests/test_training/test_backward_validator.py`

**Step 1: Write failing test for facade-pattern resolution**

File: `tests/test_training/test_backward_validator.py`

```python
class TestFacadePatternTestMapping:
    """Test that package-level imports (import httpcore) resolve to submodule components."""

    def test_bare_package_import_resolves_to_submodule_components(self, tmp_path):
        """import httpcore -> __init__.py -> re-exports from _api.py -> maps to component."""
        from architecture_model.training.backward_validator import BackwardValidator
        from architecture_model.core.types import (
            ArchitectureModel, Entities, Component, Meta,
        )

        # Setup: repo with facade pattern
        pkg = tmp_path / "httpcore"
        pkg.mkdir()

        # __init__.py re-exports from _api
        (pkg / "__init__.py").write_text(
            "from httpcore._api import request, stream\n"
            "from httpcore._async import AsyncConnectionPool\n"
        )
        (pkg / "_api.py").write_text(
            "def request(method, url): pass\ndef stream(method, url): pass\n"
        )
        (pkg / "_async.py").write_text(
            "class AsyncConnectionPool: pass\n"
        )

        # Test file that only imports the package
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_api.py").write_text(
            "import httpcore\ndef test_request(): httpcore.request('GET', 'http://x')\n"
        )

        # Model with components matching submodules
        model = ArchitectureModel(
            meta=Meta(schema_version="1.0", project="httpcore"),
            entities=Entities(components=[
                Component(id="C1", name="API Handler", status="ACTIVE"),
                Component(id="C2", name="Async Connection Pool", status="ACTIVE"),
            ]),
            relationships=[],
        )

        # Manifest with __init__.py exports and imports_detailed
        manifest = {
            "modules": [
                {
                    "file": "__init__.py",
                    "imports": ["httpcore._api", "httpcore._async"],
                    "imports_detailed": [
                        {"module": "httpcore._api", "names": ["request", "stream"], "is_relative": True},
                        {"module": "httpcore._async", "names": ["AsyncConnectionPool"], "is_relative": True},
                    ],
                    "exports": ["request", "stream", "AsyncConnectionPool"],
                },
                {
                    "file": "_api.py",
                    "imports": [],
                    "functions": ["request", "stream"],
                },
                {
                    "file": "_async.py",
                    "imports": [],
                    "classes": [{"name": "AsyncConnectionPool", "bases": [], "methods": []}],
                },
            ],
            "interfaces": [],
            "functional_blocks": {"httpcore": {"files": ["__init__.py", "_api.py", "_async.py"]}},
        }

        validator = BackwardValidator()
        score, tested, untested = validator._check_test_mapping(
            model=model, manifest=manifest, repo_path=tmp_path, source_dir=pkg,
        )

        # Should resolve: import httpcore -> __init__.py -> re-exports _api.py, _async.py
        # -> _api.py maps to "API Handler", _async.py maps to "Async Connection Pool"
        assert score > 0.0, f"Facade pattern not resolved: tested={tested}, untested={untested}"
        assert len(tested) >= 1, f"Expected at least 1 tested component, got {tested}"
```

**Step 2: Run test to confirm it fails**

Run: `pytest tests/test_training/test_backward_validator.py::TestFacadePatternTestMapping -v`
Expected: FAIL (score == 0.0)

**Step 3: Implement facade resolution in `_check_test_mapping`**

File: `src/architecture_model/training/backward_validator.py`

Add a helper method `_resolve_facade_imports` to the `BackwardValidator` class:

```python
def _resolve_facade_imports(
    self, init_file: str, manifest: dict, import_to_file: dict[str, str]
) -> list[str]:
    """Resolve __init__.py re-exports to actual submodule file paths.

    When a test imports the package (e.g., `import httpcore`), and __init__.py
    re-exports from submodules, return those submodule file paths.

    Args:
        init_file: The __init__.py file path as it appears in manifest modules.
        manifest: Full manifest dict with modules containing imports_detailed.
        import_to_file: Current import->file resolution map.

    Returns:
        List of file paths that __init__.py re-exports from.
    """
    # Find the __init__.py module entry in manifest
    init_module = None
    for mod in manifest.get("modules", []):
        mod_file = mod.get("file", "")
        if mod_file == init_file or mod_file.endswith("__init__.py"):
            if mod_file == init_file:
                init_module = mod
                break
    
    # Fallback: find any __init__.py
    if init_module is None:
        for mod in manifest.get("modules", []):
            if mod.get("file", "").endswith("__init__.py"):
                init_module = mod
                break

    if init_module is None:
        return []

    # Use imports_detailed if available (has is_relative flag)
    detailed = init_module.get("imports_detailed", [])
    if detailed:
        target_files = []
        for imp in detailed:
            if imp.get("is_relative", False):
                # Relative import: resolve module name to file
                module_name = imp.get("module", "")
                if module_name in import_to_file:
                    target_files.append(import_to_file[module_name])
                else:
                    # Try the last segment as filename
                    parts = module_name.rsplit(".", 1)
                    if len(parts) == 2:
                        candidate = parts[1] + ".py"
                        # Also try with underscore prefix
                        candidates = [candidate, "_" + candidate]
                        for mod in manifest.get("modules", []):
                            if mod.get("file", "") in candidates or mod.get("file", "").endswith("/" + candidate):
                                target_files.append(mod["file"])
                                break
        return target_files

    # Fallback: use plain imports list
    target_files = []
    for imp_name in init_module.get("imports", []):
        if imp_name in import_to_file:
            target_files.append(import_to_file[imp_name])
    return target_files
```

Then modify `_check_test_mapping` — in the loop where imports are resolved to components (look for the section that does `module_map.get(file_path, "")`), add facade resolution:

```python
# After resolving file_path from import_to_file and getting comp_id from module_map:
comp_id = module_map.get(file_path, "")

# If import resolves to __init__.py with no component, follow re-exports
if not comp_id and file_path and ("__init__.py" in file_path):
    reexport_files = self._resolve_facade_imports(
        file_path, manifest, import_to_file
    )
    for re_file in reexport_files:
        re_comp = module_map.get(re_file, "")
        if re_comp:
            tested_comp_ids.add(re_comp)
    continue  # Skip adding empty comp_id

if comp_id:
    tested_comp_ids.add(comp_id)
```

**Step 4: Run test to confirm it passes**

Run: `pytest tests/test_training/test_backward_validator.py::TestFacadePatternTestMapping -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `pytest tests/ -x -q --tb=short`
Expected: 436+ passed (1 new test added)

**Step 6: Commit**

```bash
git add src/architecture_model/training/backward_validator.py \
        tests/test_training/test_backward_validator.py
git commit -m "fix(backward): resolve facade-pattern imports through __init__.py re-exports

httpcore gets 0% test mapping because tests only do 'import httpcore'
which resolves to __init__.py (no component match). Now follows
imports_detailed re-exports from __init__.py to actual submodule files,
then maps those to components."
```

---

## Execution Order

Tasks are independent — they can run in parallel via subagent-driven-development. Recommended priority if sequential:

1. **Task 4** (Facade test mapping) — quickest fix, immediate metric improvement, fewest files
2. **Task 2** (Entity F1 ID collision) — correctness fix, contained to evaluator.py
3. **Task 3** (Drop reconstruction_fidelity) — cleanup, many files but trivial changes
4. **Task 1** (Prompt fix) — highest impact but requires oracle call for real example

## Validation

After all 4 tasks, run:
```bash
pytest tests/ -x -q --tb=short  # Expect 430+ passed (6 removed, 5+ added)
python scripts/test_multi_repo.py --skip-clone --repos 3  # Quick 3-repo check
```

Expected improvements:
- `edge_precision` should rise from 0.18 to >0.4 (Task 1)
- httpcore `test_mapping` should rise from 0% to >30% (Task 4)
- Entity F1 more meaningful when comparing surrogate vs oracle (Task 2)
- LossVector cleaner, 3 objectives (Task 3)
