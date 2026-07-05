# Manifest Ground Truth Upgrade — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade the Reality Manifest from a file inventory (~15% architectural coverage) to a proper multi-resolution ground truth system with class hierarchies, public API exports, decorator detection, symbol-level imports, cohesion metrics, and convert enforcement from silent repair to penalty scoring.

**Architecture:** Extract class/decorator/export data using the same AST already parsed by scanner. Share extraction logic currently duplicated between ContextBuilder (`context_builder.py`) and scanner (`scanner.py`). Convert InterfaceEnforcer to CoverageScorer that produces penalty signals instead of auto-repair. Add cohesion validation.

**Tech Stack:** Python 3.14, ast module, existing architecture_model types, pytest

**Key Files:**
- `src/architecture_model/manifest/scanner.py` — main extraction (178 lines)
- `src/architecture_model/training/oracle_context.py` — manifest generation + context (187 lines)
- `src/architecture_model/training/context_builder.py` — has class/decorator extraction logic (614 lines)
- `src/architecture_model/training/interface_enforcer.py` — to be converted to penalty scorer
- `src/architecture_model/training/oracle_coverage.py` — coverage computation (437 lines)
- `src/architecture_model/training/backward_validator.py` — backward validation (356 lines)
- `src/architecture_model/training/pipeline.py` — orchestration
- `scripts/test_multi_repo.py` — 10-repo validation script

---

## Task 1: Include `__init__.py` in Manifest + Extract Public API

**Files:**
- Modify: `src/architecture_model/training/oracle_context.py:64-68` (remove skip)
- Modify: `src/architecture_model/manifest/scanner.py:29` (remove skip in `_collect_py_files`)
- Modify: `src/architecture_model/manifest/scanner.py:152-178` (add exports extraction)
- Test: `tests/test_training/test_oracle_context.py`

**Step 1: Remove `__init__.py` exclusion in `oracle_context.py:67-68`**

Change:
```python
if py_file.name == "__init__.py":
    continue
```
To: remove these 2 lines entirely.

**Step 2: Remove `__init__.py` exclusion in `scanner.py:29`**

Change:
```python
return sorted(
    p for p in target.rglob("*.py") if "__pycache__" not in str(p) and p.name != "__init__.py"
)
```
To:
```python
return sorted(
    p for p in target.rglob("*.py") if "__pycache__" not in str(p)
)
```

**Step 3: Add `exports` field to `_scan_file()` for `__init__.py` files**

Add a new function to `scanner.py`:
```python
def _extract_exports(tree: ast.Module, filepath: Path) -> list[str]:
    """Extract public API exports from __init__.py.
    
    Looks for __all__ definition, then falls back to re-exported symbols
    from relative imports.
    """
    if filepath.name != "__init__.py":
        return []
    
    # Check for __all__
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        return [
                            ast.literal_eval(elt)
                            for elt in node.value.elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        ]
    
    # Fallback: collect symbols from relative imports
    exports: list[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ImportFrom) and node.level > 0:
            for alias in node.names:
                if not alias.name.startswith("_"):
                    exports.append(alias.name)
    return exports
```

Add to `_scan_file()` return dict:
```python
"exports": _extract_exports(tree, filepath) if tree else [],
```

**Step 4: Run tests**

```bash
python -m pytest tests/ -x -q
```

---

## Task 2: Add Class Extraction to Manifest Scanner

**Files:**
- Modify: `src/architecture_model/manifest/scanner.py` (add `_extract_classes`)
- Test: `tests/test_training/test_oracle_context.py` or `tests/test_manifest/`

**Step 1: Add `_extract_classes()` function to `scanner.py`**

```python
def _extract_classes(tree: ast.Module) -> list[dict[str, Any]]:
    """Extract class definitions with inheritance and method info.
    
    Returns list of dicts with:
    - name: class name
    - bases: list of base class names
    - methods: list of public method names
    - is_abstract: True if inherits ABC/Protocol or has @abstractmethod
    - decorators: list of class-level decorator names
    """
    classes: list[dict[str, Any]] = []
    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name.startswith("_"):
            continue
            
        # Extract bases
        bases: list[str] = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(base.attr)
            else:
                try:
                    bases.append(ast.unparse(base))
                except Exception:
                    pass
        
        # Extract methods
        methods: list[str] = []
        has_abstractmethod = False
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not item.name.startswith("_") or item.name == "__init__":
                    methods.append(item.name)
                # Check for @abstractmethod
                for dec in item.decorator_list:
                    dec_name = None
                    if isinstance(dec, ast.Name):
                        dec_name = dec.id
                    elif isinstance(dec, ast.Attribute):
                        dec_name = dec.attr
                    if dec_name == "abstractmethod":
                        has_abstractmethod = True
        
        # Determine if abstract
        is_abstract = (
            has_abstractmethod
            or any(b in ("ABC", "Protocol") for b in bases)
            or any(node.name.startswith(p) for p in ("Base", "Abstract", "I")
                   if len(node.name) > len(p))
        )
        
        # Class-level decorators
        decorators: list[str] = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                decorators.append(dec.attr)
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    decorators.append(dec.func.id)
                elif isinstance(dec.func, ast.Attribute):
                    decorators.append(dec.func.attr)
        
        classes.append({
            "name": node.name,
            "bases": bases,
            "methods": methods,
            "is_abstract": is_abstract,
            "decorators": decorators,
        })
    
    return classes
```

**Step 2: Add to `_scan_file()` return dict**

```python
"classes": _extract_classes(tree) if tree else [],
```

**Step 3: Run tests**

```bash
python -m pytest tests/ -x -q
```

---

## Task 3: Add Decorator Detection to Manifest

**Files:**
- Modify: `src/architecture_model/manifest/scanner.py`

**Step 1: Add `_extract_decorated_functions()` to scanner**

```python
def _extract_decorated_functions(tree: ast.Module) -> list[dict[str, Any]]:
    """Extract module-level and class-level decorated functions.
    
    Returns list of dicts with:
    - name: function name
    - decorators: list of decorator names
    - is_method: True if inside a class
    - class_name: parent class name (if method)
    """
    results: list[dict[str, Any]] = []
    
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decs = _get_decorator_names(node)
            if decs:
                results.append({
                    "name": node.name,
                    "decorators": decs,
                    "is_method": False,
                    "class_name": None,
                })
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    decs = _get_decorator_names(item)
                    if decs and item.name != "__init__":
                        results.append({
                            "name": item.name,
                            "decorators": decs,
                            "is_method": True,
                            "class_name": node.name,
                        })
    return results


def _get_decorator_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Extract decorator names from a function node."""
    names: list[str] = []
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name):
            names.append(dec.id)
        elif isinstance(dec, ast.Attribute):
            names.append(dec.attr)
        elif isinstance(dec, ast.Call):
            if isinstance(dec.func, ast.Name):
                names.append(dec.func.id)
            elif isinstance(dec.func, ast.Attribute):
                names.append(dec.func.attr)
    # Filter out trivial decorators that don't signal architecture
    trivial = {"property", "staticmethod", "classmethod", "cached_property", "override"}
    return [n for n in names if n not in trivial]
```

**Step 2: Add to `_scan_file()` return dict**

```python
"decorated_functions": _extract_decorated_functions(tree) if tree else [],
```

**Step 3: Run tests**

---

## Task 4: Add Symbol-Level Import Tracking

**Files:**
- Modify: `src/architecture_model/manifest/scanner.py` (`_extract_imports`)
- Modify: `src/architecture_model/training/oracle_context.py` (`_derive_interfaces` call)

**Step 1: Upgrade `_extract_imports()` to return symbol info**

Add a new function (keep old one for compatibility):
```python
def _extract_imports_detailed(tree: ast.Module) -> list[dict[str, Any]]:
    """Extract imports with symbol-level detail.
    
    Returns list of dicts:
    - module: the imported module name
    - symbols: list of specifically imported symbols (empty for bare imports)
    - is_relative: True if relative import (from . import ...)
    """
    imports: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "module": alias.name,
                    "symbols": [],
                    "is_relative": False,
                })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            symbols = [alias.name for alias in node.names] if node.names else []
            imports.append({
                "module": module,
                "symbols": symbols,
                "is_relative": node.level > 0,
            })
    return imports
```

**Step 2: Add to `_scan_file()` return dict**

```python
"imports_detailed": _extract_imports_detailed(tree) if tree else [],
```

Keep the existing `"imports"` field for backwards compatibility.

**Step 3: Update interface derivation to include symbols**

In `oracle_context.py`, the `_derive_interfaces()` call should pass through symbol info. This may require modifying `manifest/interfaces.py` to accept the detailed import data.

---

## Task 5: Convert InterfaceEnforcer → CoverageScorer (Penalty Signal)

**Files:**
- Create: `src/architecture_model/training/coverage_scorer.py`
- Modify: `src/architecture_model/training/pipeline.py` (replace enforcer with scorer)
- Modify: `src/architecture_model/training/__init__.py` (update exports)
- Deprecate: `src/architecture_model/training/interface_enforcer.py` (keep for reference)
- Test: `tests/test_training/test_coverage_scorer.py`

**Step 1: Create CoverageScorer**

```python
@dataclass
class CoverageScore:
    """Multi-dimensional coverage score (all 0-1, higher is better)."""
    edge_coverage: float      # fraction of manifest import edges backed by model relationships
    edge_precision: float     # fraction of model relationships backed by manifest import edges
    cohesion: float           # mean internal edges / possible internal edges per component
    directionality: float     # fraction of relationships with correct import direction
    overall: float            # weighted average
    
    # Detail
    missing_edges: list[tuple[str, str]]     # (comp_A, comp_B) pairs with imports but no rel
    spurious_rels: list[tuple[str, str]]     # (comp_A, comp_B) with rel but no imports
    low_cohesion_components: list[str]       # component names with cohesion < 0.1


class CoverageScorer:
    """Scores how well an architecture model's relationships match manifest import reality.
    
    Unlike InterfaceEnforcer, this DOES NOT modify the model.
    It only produces a score + detail about what's missing/wrong.
    """
    
    def score(self, model: ArchitectureModel, manifest: dict) -> CoverageScore:
        ...
```

**Step 2: Implement scoring logic**

- `edge_coverage`: For each manifest import edge A→B, check if covering components have a relationship
- `edge_precision`: For each model relationship, check if backing import edges exist  
- `cohesion`: For each component, compute internal_edges / possible_internal_edges
- `directionality`: For each relationship where we can determine direction, check it matches

**Step 3: Wire into pipeline (replace InterfaceEnforcer)**

---

## Task 6: Add Cohesion/Modularity Validation

**Files:**
- Part of `coverage_scorer.py` (Task 5)

**What:** The cohesion computation uses the manifest import graph + model component-file mapping:
- `internal_edges(C)` = edges where both source and target are in component C
- `external_edges(C)` = edges where exactly one endpoint is in component C
- `cohesion(C)` = internal_edges / (|files_in_C| * (|files_in_C| - 1)) 
- Components with 0 internal edges and >0 external edges are "suspect"

---

## Task 7: Fix Remaining Metric Bugs

**Files:**
- Modify: `src/architecture_model/training/backward_validator.py` (changelog filter)
- Modify: `src/architecture_model/training/oracle_coverage.py` (interface normalization)

**Step 1: Filter changelogs from doc coverage**

In `_extract_documented_features()`, skip files named `changelog*`, `CHANGELOG*`, `CHANGES*`, `HISTORY*`. Also filter headings matching version patterns like `[x.y.z]`, `vX.Y`, `X.Y.Z - date`.

**Step 2: Normalize interface coverage for flat repos**

Instead of requiring a direct relationship for every import edge, use "reachable within 2 hops" for repos with high module/component ratio (e.g., rich: 76 modules / 6 components = ratio > 10).

---

## Task 8: Pipeline Integration + Hard Gate

**Files:**
- Modify: `src/architecture_model/training/pipeline.py`
- Modify: `scripts/test_multi_repo.py`

**What:**
- Replace `InterfaceEnforcer.enforce()` call with `CoverageScorer.score()`
- Add rejection gate: if `coverage_score.overall < 0.4`, log warning + mark as low-quality
- Store coverage_score in training examples as structured data
- Include cohesion metrics in backward validation

---

## Task 9: Update Tests + Full Validation Run

**Steps:**
1. Run `python -m pytest tests/ -v` — fix any broken tests
2. Run `python scripts/test_multi_repo.py --skip-clone` — full 10-repo validation
3. Compare results against previous run
4. Commit all changes

**Expected outcomes:**
- httpcore/httpx test mapping: 0% → 50%+ (via `__init__.py` inclusion)
- python-dotenv doc coverage: 13% → 50%+ (changelog filtered)
- Training signal: coverage + cohesion + precision (not just existence)
- InterfaceEnforcer no longer masks LLM failure
