# Fix Stale Artifacts, Schema Reconciliation, and Auto-Enrichment

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the manifest duplication bug, reconcile schema/dataclass mismatches, add ObservabilityContract and improvement-opportunity validation, build an auto-enrichment script that populates FunctionSignature/Constant/TestContract from manifest data, produce a fully decomposed self-model with function-level detail, and generate 5+ SE documentation PDFs.

**Architecture:** Four phases — (1) fix foundations, (2) extend schema, (3) build enrichment tooling, (4) produce artifacts. Each phase must pass tests before proceeding.

**Tech Stack:** Python 3.11+, YAML, JSON Schema, AST, pandoc + xelatex

---

## Phase 1: Fix Foundations

### Task 1: Fix manifest duplication bug

**Files:**
- Modify: `src/architecture_model/manifest/blocks.py:116`

**Step 1: Fix the bug**

Change line 116 from:
```python
all_files.extend(collect_py_files(root, dir_path))
```
to:
```python
all_files.extend(collect_py_files(root / dir_path))
```

`collect_py_files(directory: Path, recursive: bool = True)` takes a single Path. Currently `dir_path` (a string) is passed as `recursive`, so `root.rglob("*.py")` scans the entire project.

**Step 2: Run tests**

```bash
pytest tests/ -v --ignore=tests/test_config_loader.py --ignore=tests/test_coverage.py -x
```
Expected: 542+ passed

**Step 3: Commit**

```bash
git add src/architecture_model/manifest/blocks.py
git commit -m "fix: manifest duplication bug — collect_py_files called with wrong args"
```

---

### Task 2: Reconcile schema/dataclass mismatches

**Files:**
- Modify: `src/architecture_model/core/types.py`
- Modify: `src/architecture_model/spec/schema.json`
- Modify: `src/architecture_model/core/parser.py` (if parsing logic needs updating)

There are 4 mismatches between `core/types.py` dataclasses and `spec/schema.json`:

**Mismatch 1: FunctionSignature**
- Schema has `complexity` (enum: TRIVIAL, SHORT, COMPLEX) — not in dataclass
- Dataclass has `decorators` (list[str]) — not in schema
- **Fix:** Add `complexity: Optional[str] = None` to dataclass. Add `decorators` to schema.

**Mismatch 2: TestContract**
- Schema has `required_imports` (list[str]) — not in dataclass
- Dataclass has `test_file` (str) — not in schema
- **Fix:** Add `required_imports: list[str] = field(default_factory=list)` to dataclass. Add `test_file` to schema.

**Mismatch 3: Constant**
- Schema has `type` (string) — not in dataclass
- **Fix:** Add `type: Optional[str] = None` to dataclass.

**Mismatch 4: ComponentKind enum**
- Schema has "package", "cli" — not in enum
- **Fix:** Not needed (open enums handle this). But add them to the enum for discoverability.

**Step 1: Write failing tests**

Create `tests/test_schema_reconciliation.py`:
```python
"""Tests for schema/dataclass field parity."""
from architecture_model.core.types import FunctionSignature, TestContract, Constant, ComponentKind

def test_function_signature_has_complexity():
    sig = FunctionSignature(name="foo", params="x: int", returns="int", complexity="TRIVIAL")
    assert sig.complexity == "TRIVIAL"

def test_function_signature_complexity_optional():
    sig = FunctionSignature(name="foo", params="x: int", returns="int")
    assert sig.complexity is None

def test_test_contract_has_required_imports():
    tc = TestContract(test_method="test_foo", assertion="assert x == 1",
                      contract_type="unit", required_imports=["os", "sys"])
    assert tc.required_imports == ["os", "sys"]

def test_test_contract_required_imports_default():
    tc = TestContract(test_method="test_foo", assertion="assert x == 1", contract_type="unit")
    assert tc.required_imports == []

def test_constant_has_type():
    c = Constant(name="FOO", value="42", type="int")
    assert c.type == "int"

def test_constant_type_optional():
    c = Constant(name="FOO", value="42")
    assert c.type is None

def test_component_kind_has_package_cli():
    assert ComponentKind.parse("package") == "package"
    assert ComponentKind.parse("cli") == "cli"
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_schema_reconciliation.py -v
```
Expected: FAIL

**Step 3: Fix the dataclasses in `core/types.py`**

Add to `FunctionSignature`:
```python
complexity: Optional[str] = None  # TRIVIAL, SHORT, COMPLEX
```

Add to `TestContract`:
```python
required_imports: list[str] = field(default_factory=list)
```

Add to `Constant`:
```python
type: Optional[str] = None
```

Add to `ComponentKind` enum:
```python
PACKAGE = "package"
CLI_TOOL = "cli"
```

**Step 4: Update schema.json**

Add `decorators` (array of strings) to FunctionSignature definition.
Add `test_file` (string) to TestContract definition.

**Step 5: Update parser.py**

Ensure `_parse_component` handles the new fields when parsing from YAML (complexity, required_imports, type on Constant). Also ensure `to_dict()` serialization includes them.

**Step 6: Run all tests**

```bash
pytest tests/test_schema_reconciliation.py -v
pytest tests/ -v --ignore=tests/test_config_loader.py --ignore=tests/test_coverage.py -x
```
Expected: All pass

**Step 7: Commit**

```bash
git add src/architecture_model/core/types.py src/architecture_model/spec/schema.json \
        src/architecture_model/core/parser.py tests/test_schema_reconciliation.py
git commit -m "fix: reconcile 4 schema/dataclass mismatches (complexity, required_imports, type, kinds)"
```

---

## Phase 2: Schema Extensions

### Task 3: Add ObservabilityContract to Component

**Files:**
- Modify: `src/architecture_model/core/types.py`
- Modify: `src/architecture_model/spec/schema.json`
- Modify: `src/architecture_model/core/parser.py`
- Create: `tests/test_observability_contract.py`

**Step 1: Write failing tests**

```python
"""Tests for ObservabilityContract on Component."""
from architecture_model.core.types import ObservabilityContract, Component

def test_observability_contract_creation():
    oc = ObservabilityContract(
        function="validate_model",
        log_level="INFO",
        emits_metric="validation_score",
        on_error="ERROR"
    )
    assert oc.function == "validate_model"
    assert oc.log_level == "INFO"
    assert oc.emits_metric == "validation_score"

def test_observability_contract_defaults():
    oc = ObservabilityContract(function="foo", log_level="DEBUG")
    assert oc.emits_metric is None
    assert oc.on_error == "ERROR"

def test_component_has_observability():
    comp = Component(id="C1", name="test", status="ACTIVE",
                     observability=[ObservabilityContract(function="foo", log_level="INFO")])
    assert len(comp.observability) == 1

def test_component_observability_default_empty():
    comp = Component(id="C1", name="test", status="ACTIVE")
    assert comp.observability == []

def test_observability_roundtrip():
    """Parse and serialize back."""
    from architecture_model.core.parser import _parse_raw
    raw = {
        "meta": {"project": "test", "schema_version": "1.5"},
        "entities": {
            "components": [{
                "id": "C1", "name": "test", "status": "ACTIVE",
                "observability": [{"function": "foo", "log_level": "INFO", "emits_metric": "bar"}]
            }]
        },
        "relationships": []
    }
    model = _parse_raw(raw)
    comp = model.entities["components"][0]
    assert len(comp.observability) == 1
    assert comp.observability[0].emits_metric == "bar"
    # Round-trip
    d = model.to_dict()
    assert d["entities"]["components"][0]["observability"][0]["function"] == "foo"
```

**Step 2: Run tests to verify failure**

```bash
pytest tests/test_observability_contract.py -v
```

**Step 3: Implement**

Add to `core/types.py`:
```python
@dataclass
class ObservabilityContract:
    function: str
    log_level: str  # DEBUG, INFO, WARNING, ERROR
    emits_metric: Optional[str] = None
    on_error: str = "ERROR"
    on_success: Optional[str] = None
```

Add to `Component`:
```python
observability: list[ObservabilityContract] = field(default_factory=list)
```

Update `_parse_component` in `parser.py` to parse `observability` list.
Update `Component.to_dict()` / `dump_model` to serialize it.
Add to `schema.json` under component properties.

Bump schema version to `1.5` in schema.json.

**Step 4: Run all tests**

```bash
pytest tests/ -v --ignore=tests/test_config_loader.py --ignore=tests/test_coverage.py -x
```

**Step 5: Commit**

```bash
git add src/architecture_model/core/types.py src/architecture_model/spec/schema.json \
        src/architecture_model/core/parser.py tests/test_observability_contract.py
git commit -m "feat: add ObservabilityContract to Component (schema v1.5)"
```

---

### Task 4: Add improvement-opportunity validator checks

**Files:**
- Modify: `src/architecture_model/core/validator.py`
- Create: `tests/test_improvement_checks.py`

**Step 1: Write failing tests**

```python
"""Tests for improvement opportunity validation checks."""
from architecture_model.core.types import (
    ArchitectureModel, Component, FunctionSignature, TestContract,
    ObservabilityContract, ModelMeta
)
from architecture_model.core.validator import validate_model

def _model_with_component(comp):
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.5"),
        entities={"components": [comp]},
        relationships=[]
    )

def test_flags_no_signatures():
    comp = Component(id="C1", name="test", status="ACTIVE", signatures=[])
    result = validate_model(_model_with_component(comp))
    msgs = [i.message for i in result.issues]
    assert any("signature" in m.lower() or "IMPROVEMENT" in m for m in msgs)

def test_flags_no_test_contracts():
    comp = Component(id="C1", name="test", status="ACTIVE",
                     signatures=[FunctionSignature(name="foo", params="", returns="int")])
    result = validate_model(_model_with_component(comp))
    msgs = [i.message for i in result.issues]
    assert any("test" in m.lower() and "contract" in m.lower() for m in msgs)

def test_flags_no_observability():
    comp = Component(id="C1", name="test", status="ACTIVE",
                     signatures=[FunctionSignature(name="foo", params="", returns="int")],
                     test_contracts=[TestContract(test_method="test_foo", assertion="assert True", contract_type="unit")])
    result = validate_model(_model_with_component(comp))
    msgs = [i.message for i in result.issues]
    assert any("observability" in m.lower() for m in msgs)

def test_no_flags_when_fully_specified():
    comp = Component(id="C1", name="test", status="ACTIVE",
                     signatures=[FunctionSignature(name="foo", params="", returns="int")],
                     test_contracts=[TestContract(test_method="test_foo", assertion="assert True", contract_type="unit")],
                     observability=[ObservabilityContract(function="foo", log_level="INFO")])
    result = validate_model(_model_with_component(comp))
    improvement_msgs = [i for i in result.issues if "IMPROVEMENT" in i.code or "improvement" in i.message.lower()]
    assert len(improvement_msgs) == 0
```

**Step 2: Run to verify failure**

**Step 3: Implement checks in `validator.py`**

Add 3 INFO-level checks (don't affect score):
- `IMPROVEMENT_NO_SIGNATURES` — ACTIVE component with 0 signatures
- `IMPROVEMENT_NO_TEST_CONTRACTS` — ACTIVE component with signatures but 0 test contracts
- `IMPROVEMENT_NO_OBSERVABILITY` — ACTIVE component with 0 observability contracts

Use a new code prefix `IMPROVEMENT_*` with severity `INFO`.

**Step 4: Run all tests**

**Step 5: Commit**

```bash
git add src/architecture_model/core/validator.py tests/test_improvement_checks.py
git commit -m "feat: add improvement-opportunity validation checks (INFO-level)"
```

---

## Phase 3: Auto-Enrichment Tooling

### Task 5: Build enrichment script as CLI command

**Files:**
- Create: `src/architecture_model/cli/enrich.py` (or add to `main.py`)
- Create: `tests/test_enrich.py`

This is the key deliverable. The `architecture-model enrich` command:
1. Loads the architecture model from `.architecture-model.yaml`
2. Runs `generate_manifest()` to get AST data
3. For each Component, finds its module(s) in the manifest by matching `component.files` or `component.name` to manifest module paths
4. Populates `signatures` from manifest function data + `body_hints.extract_file_hints()`
5. Populates `constants` from manifest `module_constants`
6. Discovers test files by convention (`tests/test_{module_name}.py`, `tests/test_{package}/test_{module}.py`)
7. Populates `test_contracts` by scanning test files for assert statements
8. Writes the enriched model back to `.architecture-model.yaml`

**Step 1: Write failing tests**

```python
"""Tests for auto-enrichment CLI command."""
import pytest
from pathlib import Path
from architecture_model.core.types import ArchitectureModel, Component, ModelMeta
from architecture_model.core.parser import load_model

# Test the enrichment logic, not the CLI wrapper
from architecture_model.enrich import enrich_model  # or wherever it lives

def test_enrich_populates_signatures(tmp_path):
    """Given a component pointing at a Python file, enrich should extract function signatures."""
    # Create a source file
    src = tmp_path / "src" / "mymod.py"
    src.parent.mkdir(parents=True)
    src.write_text('''
def greet(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}"

MAX_RETRIES = 3
''')
    # Create a minimal model
    comp = Component(id="C1", name="mymod", status="ACTIVE", files=["src/mymod.py"])
    model = ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.5"),
        entities={"components": [comp]},
        relationships=[]
    )
    enriched = enrich_model(model, tmp_path)
    c = enriched.entities["components"][0]
    assert len(c.signatures) >= 1
    assert c.signatures[0].name == "greet"
    assert "str" in c.signatures[0].returns
    assert len(c.constants) >= 1
    assert c.constants[0].name == "MAX_RETRIES"

def test_enrich_finds_test_contracts(tmp_path):
    """Enrich should discover test files and extract contracts."""
    src = tmp_path / "src" / "mymod.py"
    src.parent.mkdir(parents=True)
    src.write_text("def add(a, b): return a + b\n")
    test_file = tmp_path / "tests" / "test_mymod.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text('''
def test_add():
    assert add(1, 2) == 3
''')
    comp = Component(id="C1", name="mymod", status="ACTIVE", files=["src/mymod.py"])
    model = ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.5"),
        entities={"components": [comp]},
        relationships=[]
    )
    enriched = enrich_model(model, tmp_path)
    c = enriched.entities["components"][0]
    assert len(c.test_contracts) >= 1
    assert c.test_contracts[0].test_method == "test_add"

def test_enrich_preserves_existing_fields(tmp_path):
    """Enrichment should not overwrite manually-authored signatures."""
    src = tmp_path / "src" / "mymod.py"
    src.parent.mkdir(parents=True)
    src.write_text("def foo(): pass\n")
    from architecture_model.core.types import FunctionSignature
    existing_sig = FunctionSignature(name="manual", params="x: int", returns="int", body_hint="return x * 2")
    comp = Component(id="C1", name="mymod", status="ACTIVE", files=["src/mymod.py"],
                     signatures=[existing_sig])
    model = ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.5"),
        entities={"components": [comp]},
        relationships=[]
    )
    enriched = enrich_model(model, tmp_path)
    c = enriched.entities["components"][0]
    sig_names = [s.name for s in c.signatures]
    assert "manual" in sig_names  # preserved
    assert "foo" in sig_names     # added
```

**Step 2: Design the enrichment module**

The `enrich_model(model, project_root) -> ArchitectureModel` function:

```python
def enrich_model(model: ArchitectureModel, project_root: Path) -> ArchitectureModel:
    """Auto-populate signatures, constants, test_contracts on components from AST data."""
    manifest = generate_manifest(project_root)

    for comp in model.entities.get("components", []):
        # 1. Find source files for this component
        source_files = _resolve_component_files(comp, project_root)

        # 2. Extract signatures (preserve existing, add new)
        existing_names = {s.name for s in comp.signatures}
        for fpath in source_files:
            hints = extract_file_hints(fpath)  # from body_hints module
            for sig in hints:
                if sig.name not in existing_names and not sig.name.startswith("_"):
                    comp.signatures.append(sig)
                    existing_names.add(sig.name)

        # 3. Extract constants
        existing_const_names = {c.name for c in comp.constants}
        for fpath in source_files:
            module_info = _find_module_in_manifest(manifest, fpath)
            if module_info:
                for name, value in module_info.module_constants.items():
                    if name not in existing_const_names:
                        comp.constants.append(Constant(name=name, value=str(value)))
                        existing_const_names.add(name)

        # 4. Find and extract test contracts
        existing_test_methods = {t.test_method for t in comp.test_contracts}
        test_files = _discover_test_files(comp, project_root)
        for tpath in test_files:
            contracts = _extract_test_contracts(tpath)
            for tc in contracts:
                if tc.test_method not in existing_test_methods:
                    comp.test_contracts.append(tc)
                    existing_test_methods.add(tc.test_method)

    return model
```

Key helper functions:
- `_resolve_component_files(comp, root)` — uses `comp.files` if set, else searches by `comp.name` in src tree
- `_discover_test_files(comp, root)` — looks for `tests/test_{name}.py`, `tests/test_{package}/test_{name}.py`, etc.
- `_extract_test_contracts(test_path)` — AST-scans test file for `def test_*` functions, extracts assert statements

**Step 3: Implement, run tests, commit**

```bash
git add src/architecture_model/enrich.py tests/test_enrich.py \
        src/architecture_model/cli/main.py
git commit -m "feat: add 'architecture-model enrich' CLI command for auto-enrichment"
```

---

## Phase 4: Self-Model & Artifacts

### Task 6: Update self-model with full decomposition

**Files:**
- Modify: `.architecture-model.yaml`

Add 4 top-level components (COMP-EXTRACT, COMP-PROFILES, COMP-UTILS, COMP-INTEGRATIONS).
Decompose COMP-CORE into 7 sub-components.
Decompose COMP-MANIFEST into 8 sub-components.
Fix IF-MANIFEST-API (`-> Manifest`), COMP-CLI command count (8).
Add capabilities, interfaces, and all relationships.

Target: ~24 components, ~60+ relationships, score 100/100.

See Task 2 from previous plan version for full entity listings.

**Step 1: Write the YAML**

**Step 2: Validate**

```bash
python -c "
from architecture_model.core.parser import load_model
from architecture_model.core.validator import validate_model
model = load_model('.architecture-model.yaml')
result = validate_model(model)
print(f'Score: {result.score}/100, Components: {len(model.entities.get(\"components\", []))}, Rels: {len(model.relationships)}')
for i in result.issues: print(f'  {i.severity}: {i.message}')
"
```

**Step 3: Commit**

```bash
git add .architecture-model.yaml
git commit -m "feat: full sub-component decomposition of CORE (7) and MANIFEST (8)"
```

---

### Task 7: Run enrichment on self-model

**Files:**
- Modify: `.architecture-model.yaml` (enriched with signatures, constants, test contracts)

**Step 1: Run the enrichment command**

```bash
architecture-model enrich .architecture-model.yaml
```

This should auto-populate:
- `signatures` on each of the 24 sub-components from AST scanning
- `constants` from module-level assignments
- `test_contracts` from matching test files

**Step 2: Review and validate**

```bash
python -c "
from architecture_model.core.parser import load_model
from architecture_model.core.validator import validate_model
model = load_model('.architecture-model.yaml')
result = validate_model(model)
print(f'Score: {result.score}/100')
total_sigs = sum(len(c.signatures) for c in model.entities.get('components', []))
total_tests = sum(len(c.test_contracts) for c in model.entities.get('components', []))
total_consts = sum(len(c.constants) for c in model.entities.get('components', []))
print(f'Signatures: {total_sigs}, TestContracts: {total_tests}, Constants: {total_consts}')
# Check improvement opportunities are resolved
improvements = [i for i in result.issues if 'IMPROVEMENT' in i.code]
print(f'Remaining improvements: {len(improvements)}')
"
```

**Step 3: Commit**

```bash
git add .architecture-model.yaml
git commit -m "chore: auto-enrich self-model with signatures, constants, test contracts"
```

---

### Task 8: Regenerate reality manifest + per-F-block slices

**Files:**
- Modify: `output/reality-manifest.json`
- Create: `output/manifests/*.json`

**Step 1: Generate full manifest (bug is fixed from Task 1)**

```bash
mkdir -p output/manifests
python -c "
import json
from pathlib import Path
from architecture_model.manifest.generator import generate_manifest
manifest = generate_manifest(Path('.'))
with open('output/reality-manifest.json', 'w') as f:
    json.dump(manifest.to_dict(), f, indent=2, default=str)
print(f'Blocks: {len(manifest.functional_blocks)}')
for b in manifest.functional_blocks:
    print(f'  {b.block_id}: {len(b.sub_functions)} files')
"
```

**Step 2: Generate per-F-block slices**

```bash
python -c "
import json
from pathlib import Path
from architecture_model.manifest.generator import generate_manifest
from architecture_model.manifest.slicers import get_manifest_slice
manifest = generate_manifest(Path('.'))
md = manifest.to_dict()
for block in manifest.functional_blocks:
    name = block.block_id.lower().replace('f-', '')
    try:
        s = get_manifest_slice(md, name)
        Path(f'output/manifests/{name}.json').write_text(s)
        print(f'Wrote output/manifests/{name}.json')
    except Exception as e:
        print(f'Skipped {name}: {e}')
"
```

**Step 3: Commit**

```bash
git add output/reality-manifest.json output/manifests/
git commit -m "chore: regenerate reality manifest and per-F-block slices"
```

---

## Phase 5: Documentation & PDFs

### Task 9: Rewrite functional-architecture.md

**Files:**
- Modify: `docs/se/functional-architecture.md`

Full rewrite reflecting 24 components (9 top-level + 15 sub-components), typed APIs, domain profiles. Include:
- Top-level F-block table
- COMP-CORE internal decomposition with dependency diagram
- COMP-MANIFEST internal decomposition with data flow diagram
- All key API signatures with typed returns
- Cross-cutting concerns (profiles, utils, observability)

Remove `generator: opencode-arch-docs` frontmatter.

**Commit after writing.**

---

### Task 10: Rewrite layer-architecture.md

**Files:**
- Modify: `docs/se/layer-architecture.md`

Full rewrite with:
- 9 top-level components in Application Layer
- COMP-CORE internal dependency graph (7 sub-components)
- COMP-MANIFEST internal dependency graph (8 sub-components)
- Cross-component dependency edges
- Interface exposure mapping
- Component catalog table (24 rows)

**Commit after writing.**

---

### Task 11: Rewrite behavior-flows.md

**Files:**
- Modify: `docs/se/behavior-flows.md`

Remove LLM residue. Include 8 behavior flows with sub-component tracing:
1. Project Initialization (CLI → CONFIG)
2. Model Validation (CLI → PARSER → VALIDATOR → PROFILES)
3. Manifest Generation (CLI → GENERATOR → SCANNER → BLOCKS → METRICS → INTERFACES)
4. Model Slicing (SLICER)
5. LLM Context Formatting (INTEGRATIONS → CORE)
6. Domain Profile Loading (PROFILES → TYPES)
7. Model Diffing (DIFFER)
8. Model Enrichment (ENRICH CLI → MANIFEST → BODY_HINTS → TEST_ANALYZER) ← NEW

**Commit after writing.**

---

### Task 12: Quick-fix system-overview.md and component-catalog.md

**Files:**
- Modify: `docs/se/system-overview.md`
- Modify: `docs/se/component-catalog.md`

Patch factual errors only: component counts, API signatures, missing components. Don't full-rewrite.

**Commit after fixing.**

---

### Task 13: Generate 5+ PDFs

**Files:**
- Output: `output/pdfs/{functional-architecture,layer-architecture,behavior-flows,system-overview,component-catalog}.pdf`

```bash
for doc in functional-architecture layer-architecture behavior-flows system-overview component-catalog; do
  pandoc "docs/se/${doc}.md" -o "output/pdfs/${doc}.pdf" \
    --pdf-engine=xelatex \
    -V mainfont="Helvetica" \
    -V monofont="Menlo" \
    -V geometry:margin=1in \
    --resource-path=docs/se
done
ls -la output/pdfs/*.pdf
```

**Commit after generating.**

---

## Phase 6: Final Verification

### Task 14: Full verification

**Step 1: Test suite**
```bash
pytest tests/ -v --ignore=tests/test_config_loader.py --ignore=tests/test_coverage.py
```
Expected: 550+ passed (new tests added)

**Step 2: Self-model validation**
```bash
python -c "
from architecture_model.core.parser import load_model
from architecture_model.core.validator import validate_model
model = load_model('.architecture-model.yaml')
result = validate_model(model)
assert result.score == 100, f'Score: {result.score}, Issues: {result.issues}'
print(f'Score: {result.score}/100')
comps = model.entities.get('components', [])
print(f'Components: {len(comps)}')
total_sigs = sum(len(c.signatures) for c in comps)
total_tests = sum(len(c.test_contracts) for c in comps)
total_consts = sum(len(c.constants) for c in comps)
total_obs = sum(len(c.observability) for c in comps)
print(f'Signatures: {total_sigs}, Constants: {total_consts}, TestContracts: {total_tests}, Observability: {total_obs}')
improvements = [i for i in result.issues if 'IMPROVEMENT' in getattr(i, 'code', '')]
print(f'Improvement opportunities: {len(improvements)}')
"
```

**Step 3: Manifest spot-check**
```bash
python -c "
import json
with open('output/reality-manifest.json') as f:
    m = json.load(f)
for b in m['functional_blocks']:
    print(f\"{b['block_id']}: {len(b['sub_functions'])} files\")
assert all(len(b['sub_functions']) < 20 for b in m['functional_blocks'])
"
```

**Step 4: PDF existence**
```bash
ls -la output/pdfs/*.pdf | wc -l
# Expected: >= 5
```

---

## Summary

| Phase | Tasks | Key Deliverable |
|-------|-------|----------------|
| 1: Foundations | 1-2 | Bug fix + schema reconciliation |
| 2: Schema Extensions | 3-4 | ObservabilityContract + improvement checks |
| 3: Enrichment Tooling | 5 | `architecture-model enrich` CLI command |
| 4: Self-Model | 6-8 | Decomposed + enriched self-model, manifest + slices |
| 5: Documentation | 9-13 | 3 rewritten docs + 2 patched docs + 5 PDFs |
| 6: Verification | 14 | All green: tests, validation, manifests, PDFs |

**Parallelism:**
- Tasks 1 + 2 are independent (run in parallel)
- Task 3 depends on Task 2 (needs reconciled types)
- Task 4 depends on Task 3 (needs ObservabilityContract)
- Task 5 depends on Tasks 1-4 (needs all schema changes)
- Tasks 6-8 depend on Task 5
- Tasks 9-12 can run in parallel after Task 6
- Task 13 depends on 9-12
- Task 14 depends on all
