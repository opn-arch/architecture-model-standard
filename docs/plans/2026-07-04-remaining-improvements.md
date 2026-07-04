# Remaining Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close validation score gaps, improve large-repo handling, benchmark all models, and run the MPC training loop end-to-end.

**Architecture:** Extend `_add_semantic_relationships()` to generate behavior→capability `realizes` and behavior→component `allocated-to` relationships. Improve ContextBuilder file selection for 100+ file repos. Benchmark all 3 registry models. Run full pipeline.

**Tech Stack:** Python, pytest, Ollama (qwen2.5:7b, gemma2:9b, llama3.1:8b), copilot-relay (SSE)

---

### Task 1: Fix Orphan Behaviors + Unrealized Capabilities

**Problem:** Validator issues WARNING for capabilities with no `realizes` relationship, and INFO for behaviors with no relationships. Current `_add_semantic_relationships` only generates component→capability `realizes` (picking best match). Missing: behavior→capability and behavior→component links.

**Files:**
- Modify: `src/architecture_model/training/multi_pass.py:530-648` (`_add_semantic_relationships`)
- Test: `tests/test_training/test_multi_pass.py`

**Step 1: Write failing test**

```python
def test_semantic_relationships_behavior_realizes_capability(self):
    """Behaviors get allocated-to their best-matching component."""
    merged = {
        "entities": {
            "capabilities": [
                {"id": "CAP01", "name": "Console Rendering", "description": "Render to terminal"},
            ],
            "behaviors": [
                {"id": "B01", "name": "Render Console Output", "description": "Display formatted text"},
            ],
            "components": [
                {"id": "C01", "name": "Console", "description": "Terminal output driver"},
            ],
            "interfaces": [],
            "constraints": [],
        },
        "relationships": [],
    }
    rels = []
    existing_set = set()
    MultiPassExtractor._add_semantic_relationships(merged, rels, existing_set)
    
    # Behavior should be linked to something (not orphaned)
    behavior_rels = [r for r in rels if r["from"] == "B01" or r["to"] == "B01"]
    assert len(behavior_rels) >= 1, f"Behavior B01 is orphaned, got: {rels}"
```

**Step 2: Implement — add behavior→capability realizes + behavior→component allocated-to**

In `_add_semantic_relationships`, after the existing component→capability section, add:

```python
# 'realizes' (behavior → capability): behavior realizes a capability if keywords overlap
behaviors = [b for b in entities.get("behaviors", []) if isinstance(b, dict)]
beh_kws = [(b, _keywords(b)) for b in behaviors]

for cap in capabilities:
    cap_id = cap.get("id", "")
    cap_kws = _keywords(cap)
    if not cap_id or len(cap_kws) < 2:
        continue
    # Check if any behavior realizes this capability
    for beh, kws in beh_kws:
        beh_id = beh.get("id", "")
        overlap = len(cap_kws & kws)
        if overlap >= 2:
            key = ("realizes", beh_id, cap_id)
            if key not in existing_set:
                existing_rels.append({"type": "realizes", "from": beh_id, "to": cap_id})
                existing_set.add(key)

# 'allocated-to' (behavior → component): link each behavior to best-matching component
for beh, kws in beh_kws:
    beh_id = beh.get("id", "")
    if not beh_id or len(kws) < 2:
        continue
    # Skip if behavior already has relationships
    has_rel = any(k for k in existing_set if beh_id in k[1:])
    if has_rel:
        continue
    best_comp = None
    best_score = 0
    for comp, comp_kw in comp_kws:
        overlap = len(kws & comp_kw)
        if overlap > best_score:
            best_score = overlap
            best_comp = comp
    if best_comp and best_score >= 1:
        key = ("allocated-to", beh_id, best_comp["id"])
        if key not in existing_set:
            existing_rels.append({"type": "allocated-to", "from": beh_id, "to": best_comp["id"]})
            existing_set.add(key)
```

**Step 3: Run tests**

```bash
pytest tests/test_training/test_multi_pass.py -v
pytest tests/ -x -q
```

**Step 4: Commit**

```bash
git add -A && git commit -m "Add behavior→capability and behavior→component semantic relationships

Generates 'realizes' between behaviors and capabilities when keywords
overlap, and 'allocated-to' for orphan behaviors to their best-matching
component. Closes UNREALIZED_CAPABILITY warnings and ORPHAN_BEHAVIOR info."
```

---

### Task 2: Improve Context Builder for Large Repos

**Problem:** For repos with 100+ files (like rich), the current `_iter_py_files(max_files=100)` just takes the first 100 sorted alphabetically. Files deeper in subdirectories or with less obvious names get missed. Also the `max_chars=15000` total budget (3000 per slice) is tight for large repos.

**Files:**
- Modify: `src/architecture_model/training/context_builder.py`
- Test: `tests/test_training/test_context_builder.py`

**Changes:**
1. Increase `max_chars` default from 15000 to 24000 (fits in qwen2.5's 32k context)
2. Smarter `_iter_py_files`: prioritize files by architectural significance (entry points, __init__.py, large files with many classes, then alphabetical)
3. Add `_rank_files()` method that scores files by:
   - Has `__init__.py` in same dir (+2)
   - File size > 1KB (+1)
   - Name matches common patterns like "base", "core", "main", "app" (+3)
   - Depth <= 2 from repo root (+1)

**Step 1: Write failing test**

```python
def test_large_repo_prioritizes_significant_files(self, tmp_path):
    """Context builder should prioritize architecturally significant files."""
    # Create a repo with 150 files, some significant
    (tmp_path / "__init__.py").write_text("from .core import *")
    (tmp_path / "core.py").write_text("class CoreEngine:\n    def run(self): pass\n" * 20)
    (tmp_path / "base.py").write_text("class BaseHandler:\n    pass\n" * 10)
    # Create 148 filler files in subdir
    sub = tmp_path / "plugins"
    sub.mkdir()
    (sub / "__init__.py").write_text("")
    for i in range(147):
        (sub / f"plugin_{i:03d}.py").write_text(f"# plugin {i}\nclass P{i}: pass\n")
    
    cb = ContextBuilder(tmp_path)
    slices = cb.build()
    combined = slices.combined()
    
    # Core/base files should appear in context even with 150 files
    assert "CoreEngine" in combined or "core.py" in combined
    assert "BaseHandler" in combined or "base.py" in combined
```

**Step 2-4:** Implement, test, commit

---

### Task 3: Pull llama3.1:8b

```bash
ollama pull llama3.1:8b
```

---

### Task 4: Run Model Swap Benchmark

Run `scripts/test_model_swap.py` across all 3 models on httpx.
Also create a rich variant or extend the script for both repos.

---

### Task 5: Run MPC Training Loop End-to-End

1. Clone 3-5 repos (httpx, rich, fastapi, typer, textual)
2. Run enhanced extraction on each with qwen2.5:7b
3. Query copilot-relay oracle for each
4. Store examples in training.db
5. Compare surrogate vs oracle scores
6. (Optional) Attempt LoRA fine-tune if HF dependencies are available

This is the capstone integration test.
