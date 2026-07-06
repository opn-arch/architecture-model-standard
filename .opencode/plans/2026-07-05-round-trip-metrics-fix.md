# Round-Trip Metrics Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the autoencoder round-trip metrics to compare generated code against REAL source files (not DB metadata), with NaN-aware scoring and new module-level metrics.

**Architecture:** Replace ground truth source (DB `code_context` → real cloned repo files), fix empty-set Jaccard to return NaN instead of 1.0, add module name overlap and fuzzy class matching metrics, use adaptive composite weighting that excludes N/A metrics.

**Tech Stack:** Python, AST parsing (code_structure.py), Ollama (qwen2.5:7b surrogate + nomic-embed-text embeddings), copilot-relay (frontier oracle), aiohttp, sqlite3

---

## Task 1: Rewrite `scripts/test_round_trip.py` with all fixes

**Files:**
- Modify: `scripts/test_round_trip.py` (complete rewrite)

### Changes Required

**1. Fix `jaccard()` (line 117-125)**

Replace:
```python
def jaccard(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 1.0
    ...
```

With:
```python
def jaccard(set_a: set, set_b: set) -> float:
    """Returns NaN if original (set_a) is empty. Returns 0.0 if generated empty."""
    if not set_a:
        return float("nan")  # Original has nothing — metric N/A
    if not set_b:
        return 0.0
    a = {s.lower() for s in set_a}
    b = {s.lower() for s in set_b}
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union > 0 else 0.0
```

**2. Add `fuzzy_class_match()` — new metric**

```python
def fuzzy_class_match(orig_classes: set, gen_classes: set) -> float:
    """Substring/containment matching. NaN if original empty."""
    if not orig_classes:
        return float("nan")
    if not gen_classes:
        return 0.0
    orig_lower = {s.lower() for s in orig_classes}
    gen_lower = {s.lower() for s in gen_classes}
    matched = 0
    for orig in orig_lower:
        for gen in gen_lower:
            if orig == gen or (len(orig) >= 4 and orig in gen) or (len(gen) >= 4 and gen in orig):
                matched += 1
                break
    return matched / len(orig_lower)
```

**3. Add `module_name_overlap()` — new metric**

```python
def module_name_overlap(orig_modules: list, gen_modules: list) -> float:
    """Fraction of original modules found in generated (suffix matching). NaN if original empty."""
    if not orig_modules:
        return float("nan")
    if not gen_modules:
        return 0.0
    def normalize(mod):
        parts = mod.lower().strip().split(".")
        names = {mod.lower().strip()}
        if parts: names.add(parts[-1])
        if len(parts) >= 2: names.add(".".join(parts[-2:]))
        return names
    gen_names = set()
    for g in gen_modules:
        gen_names.update(normalize(g))
    matched = sum(1 for orig in orig_modules if normalize(orig) & gen_names)
    return matched / len(orig_modules)
```

**4. Fix `import_overlap()` — NaN for empty original**

Replace `if not orig_imports: return 1.0` with `return float("nan")`

**5. Fix `module_ratio()` — NaN for empty original**

Replace `if a == 0 and b == 0: return 1.0` with `if a == 0: return float("nan")`

**6. Add `load_repo_source()` — read from /tmp/test-repos/**

```python
REPO_SUBDIRS = {
    "click": "src/click", "typer": "typer", "httpcore": "httpcore",
    "anyio": "src/anyio", "python-dotenv": "src/dotenv",
    "colorama": "colorama", "tqdm": "tqdm", "attrs": "src",
    "structlog": "src/structlog", "pydantic": "pydantic",
    "fastapi": "fastapi", "rich": "rich", "httpx": "httpx",
    "black": "src/black", "marshmallow": "src/marshmallow",
    "flask": "src/flask", "jinja": "src/jinja2",
    "starlette": "starlette", "arrow": "arrow",
}

def load_repo_source(repo_name: str) -> StructuralGraph:
    subdir = REPO_SUBDIRS.get(repo_name, repo_name)
    repo_path = Path(f"/tmp/test-repos/{repo_name}/{subdir}")
    if not repo_path.exists():
        repo_path = Path(f"/tmp/test-repos/{repo_name}")
    parts = []
    for f in sorted(repo_path.rglob("*.py"))[:100]:
        try:
            content = f.read_text(errors="ignore")
            parts.append(f"# {f.relative_to(repo_path.parent)}\n{content}")
        except: continue
    return parse_multi_file_code("\n\n".join(parts)) if parts else StructuralGraph()
```

**7. Fix `compute_round_trip_score()` — adaptive composite**

New weights (total=1.0):
```python
weights = {
    "class_overlap": 0.10,
    "fuzzy_class": 0.10,
    "method_overlap": 0.10,
    "function_overlap": 0.05,
    "import_recall": 0.15,
    "module_name_overlap": 0.20,
    "module_count_ratio": 0.10,
    "semantic_class_match": 0.10,
    "intent_coverage": 0.10,
}
```

Composite: only sum non-NaN metrics, divide by their weight total.

**8. Replace ground truth loading in `process_repo_round_trip()`**

Replace:
```python
original_graph = parse_multi_file_code(example["code_context"])
```
With:
```python
original_graph = load_repo_source(name)
```

**9. Update table headers and formatting**

Add columns for fuzzy_class, module_name_overlap, module_count_ratio.
Use `fmt()` helper that shows "N/A" for NaN values.

### Step: Run to verify

```bash
python scripts/test_round_trip.py 2>&1
```

Expected: ~16-18 repos processed, overall scores in 0.15-0.50 range (meaningful, not inflated), module_name_overlap should be highest metric (~0.4-0.7).

### Step: Commit

```bash
git add scripts/test_round_trip.py
git commit -m "fix(metrics): rewrite round-trip test with real source ground truth and NaN-aware scoring"
```

---

## Expected Results After Fix

Based on the analysis:

| Metric | Before (broken) | After (expected) | Why |
|--------|-----------------|------------------|-----|
| class_overlap | 0.12 surr | 0.03-0.08 | Honest: module→class naming mismatch |
| fuzzy_class | N/A | 0.15-0.30 | New: substring matching helps |
| method_overlap | 0.22 (inflated) | 0.02-0.05 | Honest: method names rarely match |
| function_overlap | 0.78 (inflated) | 0.05-0.15 | Was mostly both-empty=1.0 |
| import_recall | 0.47 | 0.15-0.30 | Real repos have 40-100 imports |
| module_name_overlap | N/A | 0.40-0.70 | New: this is what model captures |
| module_count_ratio | 0.15 | 0.30-0.60 | Model generates ~right module count |
| semantic_match | 0.19 | 0.30-0.50 | With real classes, embeddings match better |
| intent_coverage | 0.13 | 0.20-0.40 | More original classes to match against |
| **OVERALL** | 0.25 (meaningless) | **0.20-0.35** (honest) | Lower but informative |

The key insight from the corrected metrics will be:
- **Module-level reconstruction works** (0.4-0.7) — the model captures decomposition
- **Class-level reconstruction is poor** (0.03-0.08 hard, 0.15-0.30 fuzzy) — model doesn't preserve class names
- **Method-level is very poor** (0.02-0.05) — model loses method-level detail
- This tells us exactly where to improve: the model needs class-level detail, not just module-level

---

## Verification

After running:
1. Module name overlap should be the highest metric (validates model captures decomposition)
2. No metric should be 1.0 for any repo (inflation eliminated)
3. Repos with more components in the model should score higher (correlation check)
4. Copilot should outperform surrogate on most metrics (better code generation)
