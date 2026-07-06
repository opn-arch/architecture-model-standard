# Test-as-Oracle Decomposed Regeneration Loop

**Date:** 2026-07-06  
**Status:** Approved  
**Target:** Get colorama to 50%+ test pass rate through iterative, decomposed, test-aware regen  
**Repos affected:** architecture-model-standard, opencode-arch, arch-agent (future)

## Problem Statement

Extraction scores 98/100 but regeneration scores 0%. The 98 measures internal consistency (IDs link up), not fidelity. A model that can't reconstruct working code hasn't proven it understands the system.

Root causes:
1. **Discovery failure** — auto-init model found only test files, missed flat source modules
2. **Structural ceiling** — schema captures topology (components, relationships) but not behavior (constants, algorithms, contracts)
3. **No iteration** — single-pass regen with no feedback from test failures
4. **No learning** — each attempt starts from zero, no accumulated knowledge

## Design Overview

An integrated system combining:
- **Test-affinity decomposition** — break repos into subsystems by test file mapping
- **Test contract extraction** — derive behavioral specs from test assertions
- **Iterative regen loop** — short extract→regen→test→learn cycles per subsystem
- **Learning store** — repo-specific and general pattern accumulation
- **Smarter validator** — predicts regen readiness from learned heuristics
- **Oracle learning** — prompt evolution based on accumulated outcomes

## Architecture

```
                    ┌─────────────────────────────────┐
                    │         Learning Store           │
                    │  (repo-specific + general)       │
                    │  patterns, outcomes, prompts     │
                    └───────┬───────────┬─────────────┘
                            │           │
                  feeds     │           │ learns from
                  context   │           │ outcomes
                            ▼           │
┌──────────┐    ┌──────────────────┐    │    ┌──────────────┐
│ Test     │───▶│   Oracle (LLM)   │────┼───▶│ Regen Output │
│ Analyzer │    │ (enriched prompt)│    │    │ (source code)│
└──────────┘    └──────────────────┘    │    └──────┬───────┘
      │                   ▲              │           │
      │                   │              │           ▼
      ▼                   │              │    ┌──────────────┐
┌──────────┐    ┌─────────┴────────┐    │    │  Test Runner │
│ Contracts│───▶│ Enriched Model   │    │    │ (per-subsys) │
│ Constants│    │ (structural +    │    │    └──────┬───────┘
│ Sigs     │    │  behavioral)     │    │           │
└──────────┘    └──────────────────┘    │           ▼
                         ▲               │    ┌──────────────┐
                         │               └────│  Gap Analyzer│
                         │                    │  (failures → │
                         └────────────────────│   enrichment)│
                                              └──────────────┘
```

## 1. Schema Extensions (architecture-model-standard)

### New types on Component entity

```python
@dataclass
class Constant:
    name: str           # e.g., "BLACK"
    value: str          # e.g., "30" (string repr, type-agnostic)
    context: str = ""   # e.g., "class attribute of AnsiFore"

@dataclass
class FunctionSignature:
    name: str                    # e.g., "code_to_chars"
    params: list[str]            # e.g., ["code: int"]
    returns: str = ""            # e.g., "str"
    decorators: list[str] = []   # e.g., ["@staticmethod"]
    body_hint: str = ""          # 1-line algorithm description

@dataclass
class TestContract:
    test_file: str              # e.g., "ansi_test.py"
    test_method: str            # e.g., "testForeAttributes"
    assertion: str              # e.g., "Fore.BLACK == '\\033[30m'"
    contract_type: str          # "value_equality" | "type_check" | "raises" | "state_change"
```

Component additions:
```python
constants: list[Constant] = []
signatures: list[FunctionSignature] = []
test_contracts: list[TestContract] = []
```

### YAML representation

```yaml
entities:
  components:
    - id: COMP-ANSI
      name: ANSI Module
      symbols:
        - name: AnsiFore
          kind: class
          supers: [AnsiCodes]
          members: [BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET]
      constants:
        - name: BLACK
          value: "30"
          context: "class attribute of AnsiFore, becomes escape code via code_to_chars"
        - name: RED
          value: "31"
          context: "class attribute of AnsiFore"
      signatures:
        - name: code_to_chars
          params: ["code: int"]
          returns: "str"
          body_hint: "return CSI + str(code) + 'm'"
      test_contracts:
        - test_file: ansi_test.py
          test_method: testForeAttributes
          assertion: "Fore.BLACK == '\\033[30m'"
          contract_type: value_equality
```

## 2. Test-Affinity Decomposer

New decomposition strategy alongside existing F-block complexity clustering.

### Algorithm

```
test_affinity_decompose(repo_path: Path) -> list[Subsystem]:
    1. Discover all test files (*_test.py, test_*.py, tests/test_*)
    2. For each test file:
       - AST-parse imports → identify source modules being tested
       - Parse test class/method names → behavioral surface area
       - Map: test_file → [source_modules]
    3. Group source modules by their primary test file
       - Module with no dedicated test → assign to closest neighbor by import graph
       - Module tested by multiple test files → assign to test with most assertions
    4. Each group = one Subsystem
    5. Return list[Subsystem(name, source_files, test_files, dependencies)]
```

### Subsystem dataclass

```python
@dataclass
class Subsystem:
    name: str                    # e.g., "ansi"
    source_files: list[Path]     # modules in this subsystem
    test_files: list[Path]       # tests that validate this subsystem
    dependencies: list[str]      # other subsystem names this depends on
    complexity: float            # from existing complexity scorer
```

### For colorama

| Subsystem | Source | Test | Dependencies |
|-----------|--------|------|--------------|
| ansi | `ansi.py` | `ansi_test.py` | none |
| initialise | `initialise.py` | `initialise_test.py` | ansi, ansitowin32 |
| ansitowin32 | `ansitowin32.py` | `ansitowin32_test.py` | ansi, win32 |
| winterm | `win32.py`, `winterm.py` | `winterm_test.py` | none |
| root | `__init__.py` | — | all above |

## 3. Test Contract Analyzer

New module: `architecture_model/manifest/test_analyzer.py`

### Algorithm

```
analyze_test_contracts(test_file: Path) -> list[TestContract]:
    1. AST-parse the test file
    2. For each test method (methods starting with "test"):
       - Walk AST for assert* calls:
         - assertEqual(a, b) → value_equality contract
         - assertTrue(expr) → truth contract
         - assertRaises(ExcType) → raises contract
         - assertIsInstance(obj, Type) → type_check contract
       - Resolve LHS expressions to component symbols where possible
       - Extract literal values from RHS
    3. For each import:
       - Map to required API surface (what source modules/symbols must exist)
    4. Return structured contracts with source traceability
```

### Constant extraction from tests

```
extract_constants_from_tests(test_file: Path, source_module: str) -> list[Constant]:
    For each assertEqual(Obj.ATTR, literal_value):
      → Constant(name=ATTR, value=literal_value, context=f"attribute of {Obj}")
    For each assertEqual(func(args), literal_value):
      → Constant(name=f"{func}({args})", value=literal_value, context="function output")
```

## 4. Iterative Regen Loop (Orchestrator)

### CLI command

```
opencode-arch regen-loop \
    --repo /tmp/test-repos/colorama \
    --max-iterations 5 \
    --target-pass-rate 0.5 \
    --subsystem ansi            # optional: focus on one subsystem
```

### Loop algorithm

```
regen_loop(repo_path, max_iterations=5, target=0.5):
    subsystems = test_affinity_decompose(repo_path)
    
    # Sort by dependency order (leaves first)
    subsystems = topological_sort(subsystems)
    
    for subsystem in subsystems:
        model = extract_subsystem_model(subsystem)
        contracts = analyze_test_contracts(subsystem.test_files)
        model = enrich_with_contracts(model, contracts)
        
        for iteration in range(max_iterations):
            # Validate: predict readiness
            readiness = validate_regen_readiness(model, contracts)
            
            # Regen: call oracle with enriched context
            prompt = build_regen_prompt(model, contracts, subsystem, iteration)
            regen_result = oracle_call(prompt, subsystem.source_files)
            
            # Test: run ONLY this subsystem's tests
            test_result = run_tests(subsystem.test_files, repo_path)
            
            # Learn: log outcome
            log_outcome(subsystem, model, test_result, iteration)
            
            if test_result.pass_rate >= target:
                break
            
            # Gap analysis: what's missing?
            gaps = analyze_gaps(test_result.failures, model)
            model = enrich_with_gaps(model, gaps)
    
    # Integration: run full test suite
    full_result = run_full_tests(repo_path)
    log_final_outcome(repo_path, full_result)
```

### Per-iteration prompt structure

```markdown
## Regenerate {{subsystem.name}} (iteration {{n}})

### Source files to produce:
{{subsystem.source_files}}

### Architecture Model
{{compressed structural model for this subsystem}}

### Constants (must be exact)
{{constants list with values}}

### Function Signatures
{{signatures with body_hints}}

### Test Contracts (assertions that MUST pass)
{{test_contracts formatted as spec}}

### Dependency Context
{{public APIs of subsystems this depends on}}

### Previous Attempt Feedback (iteration > 0)
{{test failures from last iteration with analysis}}

### Learned Patterns
{{relevant patterns from learning store}}
```

## 5. Learning Store

### Schema

**Repo-specific** — `{repo}/.arch-learning.json`:
```json
{
  "repo": "colorama",
  "sessions": [
    {
      "timestamp": "2026-07-06T...",
      "subsystems": {
        "ansi": {
          "iterations": [
            {
              "model_features": {
                "constants": 12, "signatures": 3,
                "contracts": 8, "symbols": 4
              },
              "test_result": {"passed": 2, "failed": 6, "total": 8},
              "gaps_identified": ["missing code_to_chars body", "RESET_ALL constant"],
              "prompt_hash": "abc123"
            }
          ],
          "converged_iteration": 3,
          "final_pass_rate": 0.75
        }
      }
    }
  ],
  "effective_patterns": [
    "Include CSI constant definition in body_hint for escape code generators",
    "AnsiCodes.__init__ converts int attributes to escape strings via code_to_chars"
  ]
}
```

**General** — `~/.opencode-arch/learning.db` (extending existing telemetry SQLite):
```sql
CREATE TABLE regen_outcomes (
    id INTEGER PRIMARY KEY,
    repo TEXT NOT NULL,
    subsystem TEXT NOT NULL,
    iteration INTEGER NOT NULL,
    constant_count INTEGER,
    signature_count INTEGER,
    contract_count INTEGER,
    symbol_count INTEGER,
    pass_rate REAL,
    time_seconds REAL,
    prompt_hash TEXT,
    timestamp TEXT
);

CREATE TABLE oracle_patterns (
    id INTEGER PRIMARY KEY,
    pattern_type TEXT,         -- "extraction" | "regen" | "enrichment" | "decomposition"
    repo_category TEXT,        -- "flat-layout" | "src-layout" | "monorepo"
    pattern TEXT,              -- successful prompt fragment or structural insight
    effectiveness REAL,        -- avg pass rate when pattern was applied
    sample_count INTEGER,
    last_updated TEXT
);

CREATE TABLE prompt_templates (
    id INTEGER PRIMARY KEY,
    template_name TEXT,        -- "regen_v1", "regen_v2"
    template_body TEXT,
    avg_pass_rate REAL,
    usage_count INTEGER,
    last_used TEXT
);
```

## 6. Smarter Validator (Phase 1)

### New validation rule: REGEN_READINESS

Added as rule 8 alongside existing 7 rules:

```python
def _check_regen_readiness(self, model: ArchitectureModel) -> list[ValidationIssue]:
    issues = []
    for comp in model.entities.get("components", []):
        if not comp.test_contracts:
            continue  # Only check components with test contracts
        
        # How many contracts reference constants we don't have?
        referenced_constants = extract_constant_refs(comp.test_contracts)
        defined_constants = {c.name for c in comp.constants}
        missing = referenced_constants - defined_constants
        
        if missing:
            coverage = len(defined_constants) / max(len(referenced_constants), 1)
            if coverage < 0.3:
                issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    code="REGEN_UNREADY",
                    message=f"{comp.id}: {len(missing)} constants referenced in tests but undefined"
                ))
            elif coverage < 0.7:
                issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    code="REGEN_PARTIAL",
                    message=f"{comp.id}: {coverage:.0%} constant coverage, regen may fail"
                ))
        
        # Signature coverage
        called_functions = extract_function_calls(comp.test_contracts)
        defined_sigs = {s.name for s in comp.signatures}
        sig_coverage = len(defined_sigs & called_functions) / max(len(called_functions), 1)
        
        if sig_coverage < 0.5:
            issues.append(ValidationIssue(
                severity=Severity.WARNING,
                code="REGEN_LOW_SIG_COVERAGE",
                message=f"{comp.id}: only {sig_coverage:.0%} of tested functions have signatures"
            ))
    
    return issues
```

### Scoring impact

```python
# Updated scoring with regen readiness weight
score = max(0, 100 
    - (error_count * 10) 
    - (warning_count * 2)
    - (regen_unready_count * 5)   # NEW: penalizes regen-unready components
)
```

### Future: learned thresholds

Once the learning store has 50+ outcomes, thresholds adapt:
```python
def _adaptive_threshold(self, feature: str, repo_category: str) -> float:
    """Query learning store for effective threshold."""
    outcomes = self.learning_store.query(
        f"SELECT {feature}, pass_rate FROM regen_outcomes WHERE repo_category = ?",
        (repo_category,)
    )
    # Find threshold where pass_rate > 0.5 starts
    return compute_elbow_threshold(outcomes)
```

## 7. Oracle Learning (Prompt Evolution)

### Context injection via architect_slice

New focus mode for the slice tool:
```python
architect_slice(repo_path, focus="regen:ansi", budget=4000)
```

In `focus="regen:{subsystem}"` mode, budget allocation:
- 30% — Structural model (compressed as today)
- 30% — Test contracts and constants (behavioral specs)
- 20% — Learned patterns from learning store
- 20% — Previous iteration feedback / dependency APIs

### Prompt template evolution

Templates stored in `opencode-arch/src/opencode_arch/prompts/`:
```
prompts/
├── extract.md          — base extraction prompt
├── regen.md            — base regeneration prompt
├── regen_iteration.md  — iteration prompt (includes failure analysis)
├── enrich.md           — enrichment-from-failure prompt
└── compose.md          — subsystem composition prompt
```

Each has `{{slots}}` filled from:
1. Model data (structural + behavioral)
2. Learning store (patterns, prior outcomes)
3. Graph context (dependencies, isolation status)
4. Iteration context (what failed, what to fix)

### Graph awareness in prompts

Dependency graphs inform oracle about module isolation:
```
Subsystem "ansi": NO dependencies → can regen in complete isolation
Subsystem "initialise": depends on [ansi, ansitowin32] → regen assumes those APIs exist

Prompt includes:
  "You may import from ansi: AnsiFore, AnsiBack, AnsiStyle, Fore, Back, Style"
  "You may import from ansitowin32: AnsiToWin32, StreamWrapper"
```

## 8. Implementation Plan (First Deliverable)

Target: colorama 50%+ test pass rate.

### Phase 1: Schema + Test Analyzer (architecture-model-standard)
1. Add `Constant`, `FunctionSignature`, `TestContract` to types.py
2. Update parser/serializer to handle new fields
3. Implement `test_analyzer.py` — extract contracts from test files
4. Add test-affinity decomposition strategy to decomposer
5. Add REGEN_READINESS validation rule
6. Tests for all new code

### Phase 2: Loop Orchestrator (opencode-arch)
1. New CLI command: `regen-loop`
2. New MCP tool: `architect_regen_subsystem`
3. Learning store schema (extend telemetry SQLite)
4. Prompt templates with slot system
5. Gap analyzer (parse test failures → enrichment actions)
6. Integration with existing `architect_slice` (new focus mode)

### Phase 3: Colorama Proof
1. Run test-affinity decomposition on colorama
2. Extract enriched model (with constants + contracts from tests)
3. Run regen loop per subsystem
4. Target: ansi subsystem passes first (simplest: pure constants)
5. Then initialise (state management)
6. Then composition (full test suite)
7. Record learning data

### Phase 4: Generalize + Learn
1. Run on python-dotenv, structlog
2. Accumulate learning store data
3. Tune validator thresholds from outcomes
4. Evolve prompt templates based on what works

## Success Criteria

| Metric | Target |
|--------|--------|
| Colorama ansi subsystem | 100% test pass rate |
| Colorama full suite | 50%+ test pass rate |
| Iterations to converge (ansi) | <= 3 |
| Validator predicts regen failure | accuracy > 70% |
| Learning store has actionable patterns | >= 5 cross-repo patterns |

## Dependencies

- architecture-model-standard schema must be extended BEFORE opencode-arch loop
- Test analyzer needs to handle unittest (colorama) AND pytest (most repos) patterns
- `opencode run` MCP integration must remain stable (fixed this session)
- `python-dotenv` must be wheel-installed in venv (not editable)

## Future: arch-agent Integration

Once learning store has 100+ (model_features → pass_rate) tuples:
1. Export training data from SQLite
2. Train surrogate model (small classifier) to predict regen readiness
3. Replace heuristic validator rule 8 with surrogate predictions
4. Surrogate also predicts "what enrichment would help most?" (active learning)

## Fixes for Current Test Failures

The immediate colorama 0/5 failure root causes and fixes:

1. **Auto-init model only discovered test files** — Fix: test-affinity decomposer discovers source modules by parsing test imports, not directory structure
2. **No constants in model** — Fix: test contract analyzer extracts `assertEqual(Fore.BLACK, '\033[30m')` → Constant(BLACK, 30)
3. **No function signatures** — Fix: AST scan + test analysis provides full signatures
4. **No iteration** — Fix: regen loop with gap analysis from test failures
5. **Package not installed in temp dir** — Fix: `pip install -e .` before running tests (already patched in benchmark script)
6. **Single 10-minute timeout** — Fix: per-subsystem loops with shorter, focused prompts
