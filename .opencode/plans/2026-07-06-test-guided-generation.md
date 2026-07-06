# Test-Guided Code Generation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generate deployable code from architecture models by using the target repo's test suite as both behavioral specification and verification oracle, with an iterative retry loop that improves pass rate per iteration.

**Architecture:** The system mines behavioral contracts from test files (assertions, parametrize data, fixtures), includes these in the generation prompt alongside the enriched architecture model, generates code, runs the test suite against it, parses failures into structured feedback, and regenerates only the failing components. Each iteration produces training signal (test pass delta → DPO pairs).

**Tech Stack:** Python 3.14, pytest (subprocess), AST parsing, Ollama (qwen2.5:7b), existing TestRunner/TestStructureAnalyzer, existing Surrogate/HierarchicalGenerator

---

## Context & Existing Infrastructure

**Already built (reuse directly):**
- `src/architecture_model/training/test_runner.py` — `TestRunner` class: venv creation, pip install, pytest execution, `TestRunResult` dataclass with pass/fail/error counts
- `src/architecture_model/training/test_analyzer.py` — `TestStructureAnalyzer`: discovers test files, counts tests, extracts imports; `TestCoverageAnalyzer`: module importance, relationships
- `src/architecture_model/training/surrogate.py` — `Surrogate.generate_code(model_yaml)` with `_GENERATE_SYSTEM_PROMPT`
- `src/architecture_model/training/hierarchical_generator.py` — `HierarchicalGenerator` for decomposed generation
- `src/architecture_model/core/decomposer.py` — `auto_assign_f_blocks()`, `decompose_model()`
- `src/architecture_model/core/merger.py` — `enrich_from_manifest()`, `compact_for_generation()`
- `src/architecture_model/training/autoencoder.py` — `RoundTripEvaluator` pattern
- `src/architecture_model/training/code_structure.py` — `StructuralGraph`, `parse_multi_file_code()`

**Key constraints:**
- Run all tests with: `python -m pytest tests/ --ignore=tests/test_config_loader.py -q`
- Current passing: 775 tests (do not regress)
- TestRunner already handles venv isolation — generated code goes into a temp package dir
- Ollama local at `http://localhost:11434` with `qwen2.5:7b`
- Target repos cloned at `/tmp/test-repos/`

**Key insight from user:** "You can look at the test at encoding/generating manifest and coding phases and can retry to try passing tests." The test suite serves THREE roles: specification source, generation context, and verification oracle.

---

## Task Overview

| # | Task | Purpose |
|---|------|---------|
| 1 | Test Contract Miner | Extract behavioral specs from test ASTs |
| 2 | Failure Parser | Structured parsing of pytest failure output |
| 3 | Test-Aware Generation Prompt | Include behavioral contracts in LLM prompt |
| 4 | Code Writer (file materializer) | Write generated code to temp package for testing |
| 5 | Retry Loop Controller | Generate → test → analyze → regenerate cycle |
| 6 | Per-Component Regeneration | Targeted fix of failing modules only |
| 7 | Training Signal Integration | Test pass rate as loss, DPO pairs from iterations |
| 8 | CLI Command | `architecture-model generate --test-guided` |
| 9 | End-to-End Integration Test | Full pipeline on python-dotenv (simplest repo) |
| 10 | Proof-of-Concept Run | Execute on python-dotenv, colorama, arrow, click |

---

### Task 1: Test Contract Miner

**Files:**
- Create: `src/architecture_model/training/test_contract_miner.py`
- Test: `tests/test_training/test_contract_miner.py`

**Purpose:** AST-scan test files to extract behavioral specifications that tell the LLM WHAT each method should do.

**Data structures:**

```python
@dataclass
class MethodContract:
    """Behavioral contract for a single method/function, derived from tests."""
    component: str          # Source module name (e.g., "core", "parser")
    target: str             # Class.method or function name being tested
    test_source: str        # Test file:function that defines this contract
    assertions: list[str]   # Simplified assertion descriptions
    inputs: list[str]       # Example inputs from parametrize or test body
    expected: list[str]     # Expected outputs/behaviors
    raises: list[str]       # Expected exceptions
    fixtures: list[str]     # Required setup (fixture names)

@dataclass
class TestContracts:
    """All behavioral contracts extracted from a test suite."""
    contracts: list[MethodContract]
    public_api: list[str]           # Symbols imported by tests (= public API)
    fixture_definitions: dict[str, str]  # fixture_name → 1-line description
    total_tests: int
    total_assertions: int

    def for_component(self, component_name: str) -> list[MethodContract]:
        """Filter contracts relevant to a specific component."""
        ...

    def summary_for_prompt(self, component_name: str, max_tokens: int = 500) -> str:
        """Format contracts as text for inclusion in generation prompt."""
        ...
```

**Extraction algorithm:**

```python
class TestContractMiner:
    def mine(self, repo_path: Path, package_name: str) -> TestContracts:
        """Mine behavioral contracts from test suite.
        
        1. Discover test files (reuse TestStructureAnalyzer._discover_test_files)
        2. For each test file:
           a. Parse AST
           b. Extract imports → map to source components
           c. For each test function:
              - Find method calls on imported objects → target identification
              - Extract assert statements → behavioral expectations
              - Extract pytest.raises blocks → error contracts  
              - Extract @parametrize data → input/output examples
              - Extract fixture usage → setup requirements
        3. Group contracts by component
        4. Deduplicate and summarize
        """

    def _extract_assertions(self, func_node: ast.FunctionDef) -> list[str]:
        """Extract simplified assertion descriptions from a test function body."""
        # assert result.output == "foo" → "output equals 'foo'"
        # assert not result.exception → "no exception raised"
        # assert "text" in result.output → "output contains 'text'"
        
    def _extract_parametrize(self, func_node: ast.FunctionDef) -> list[dict]:
        """Extract @pytest.mark.parametrize decorator data."""
        # @parametrize("input,expected", [(1, "one"), (2, "two")])
        # → [{"input": "1", "expected": "one"}, ...]

    def _identify_target(self, func_node: ast.FunctionDef, imports: dict) -> str | None:
        """Identify which source method/class a test is exercising."""
        # Look at: first method call on an imported object, fixture type hints,
        # test function name (test_invoke → targets "invoke")
```

**Tests to write:**

```python
class TestContractMiner:
    def test_extracts_public_api_from_imports(self, tmp_path):
        """Test files that import 'from click import Command' → public_api includes 'Command'."""
        
    def test_extracts_assertion_equals(self, tmp_path):
        """'assert result == 42' → contract with expected=['equals 42']."""
        
    def test_extracts_assertion_contains(self, tmp_path):
        """'assert "foo" in output' → contract with expected=['contains foo']."""
        
    def test_extracts_raises_contract(self, tmp_path):
        """'with pytest.raises(ValueError)' → contract with raises=['ValueError']."""
        
    def test_extracts_parametrize_cases(self, tmp_path):
        """@parametrize → contract with inputs/expected from test data."""
        
    def test_identifies_target_from_method_call(self, tmp_path):
        """'runner.invoke(cli, args)' → target='invoke'."""
        
    def test_identifies_target_from_test_name(self, tmp_path):
        """'def test_basic_functionality' → target='basic_functionality' (fallback)."""
        
    def test_groups_by_component(self, tmp_path):
        """Contracts grouped by which module the test imports from."""
        
    def test_summary_for_prompt_respects_max_tokens(self, tmp_path):
        """summary_for_prompt truncates at token limit."""
        
    def test_mines_real_click_tests(self):
        """Integration: mine /tmp/test-repos/click/tests → non-empty contracts."""
```

Commit: `feat: add TestContractMiner for behavioral spec extraction from tests`

---

### Task 2: Failure Parser

**Files:**
- Create: `src/architecture_model/training/failure_parser.py`
- Test: `tests/test_training/test_failure_parser.py`

**Purpose:** Parse pytest failure output into structured feedback that tells the LLM exactly what went wrong and where.

**Data structures:**

```python
@dataclass
class TestFailure:
    """Structured representation of a single test failure."""
    test_name: str              # e.g., "test_basic_functionality"
    test_file: str              # e.g., "tests/test_basic.py"
    error_type: str             # "AssertionError", "ImportError", "AttributeError", etc.
    error_message: str          # The actual error text
    failed_assertion: str | None  # The assert line that failed (if AssertionError)
    expected: str | None        # Expected value (from assert == comparisons)
    actual: str | None          # Actual value
    relevant_component: str | None  # Which source module is implicated
    traceback_hint: str         # 1-2 line traceback showing where in source it failed

@dataclass
class FailureReport:
    """Aggregated failure analysis from a test run."""
    failures: list[TestFailure]
    total_passed: int
    total_failed: int
    total_collected: int
    pass_rate: float
    
    # Grouped analysis
    by_component: dict[str, list[TestFailure]]  # component → failures
    by_error_type: dict[str, int]               # error_type → count
    
    def format_for_retry_prompt(self, component: str | None = None, max_failures: int = 10) -> str:
        """Format failures as LLM-friendly text for retry generation."""
```

**Implementation:**

```python
class FailureParser:
    def parse(self, pytest_output: str, package_name: str) -> FailureReport:
        """Parse pytest verbose output into structured failures.
        
        Expects output from: pytest --tb=short -v
        
        Parsing strategy:
        1. Find FAILED lines → test_name, test_file
        2. Find traceback blocks → error_type, error_message
        3. For AssertionError: extract the assert expression and values
        4. Map failures to components via import chain in traceback
        """
    
    def _parse_traceback_block(self, block: str) -> tuple[str, str, str | None]:
        """Parse a single traceback block → (error_type, message, assertion_line)."""
        
    def _extract_expected_actual(self, assertion_line: str, error_msg: str) -> tuple[str | None, str | None]:
        """From 'assert x == y' and 'AssertionError: assert 1 == 2' → ('2', '1')."""
        
    def _map_to_component(self, traceback: str, package_name: str) -> str | None:
        """Find which source module the failure originated from.
        
        Look for lines like 'File "src/click/core.py", line 42, in invoke'
        → component = 'core'
        """
```

Commit: `feat: add FailureParser for structured test failure analysis`

---

### Task 3: Test-Aware Generation Prompt

**Files:**
- Modify: `src/architecture_model/training/surrogate.py` (add `_GENERATE_WITH_CONTRACTS_PROMPT`)
- Create: `src/architecture_model/training/prompt_builder.py`
- Test: `tests/test_training/test_prompt_builder.py`

**Purpose:** Build generation prompts that include behavioral contracts so the LLM generates implementations (not just stubs).

**Key change:** The current `_GENERATE_SYSTEM_PROMPT` says "Do NOT implement method/function bodies — use 'pass'". The new prompt says "IMPLEMENT method bodies to satisfy these behavioral contracts."

**New prompt template:**

```python
_GENERATE_WITH_TESTS_PROMPT = """\
You are an architecture-to-code compiler. Given a UAM architecture model YAML \
with code-level detail AND behavioral contracts extracted from the test suite, \
generate Python source code that:
1. Matches the structural specification exactly (class names, method signatures, imports)
2. IMPLEMENTS method bodies to satisfy the behavioral contracts
3. Passes the described test assertions

Rules:
1. Each component → one .py module (filename = component name)
2. 'symbols' → exact class names with correct inheritance
3. 'members' → methods with correct signatures and WORKING implementations  
4. 'functions' → top-level functions with WORKING implementations
5. depends-on with 'imports' → from .{target} import {symbols}
6. Use type hints throughout
7. IMPLEMENT all method bodies (not stubs). Use the behavioral contracts to determine correct behavior.
8. If a contract says "raises X when Y" → implement that error handling
9. If a contract says "returns Z" → ensure the method returns that

{contracts_section}

Output format:
- Separate modules with '# component_name.py' comment headers
- Import statements at top (stdlib first, then relative)
- Output ONLY Python code — no markdown fences, no explanations."""
```

**Prompt builder:**

```python
class PromptBuilder:
    def build_generation_prompt(
        self,
        model_yaml: str,
        contracts: TestContracts | None = None,
        failure_context: FailureReport | None = None,
        component_filter: str | None = None,
    ) -> tuple[str, str]:  # (system_prompt, user_content)
        """Build a generation prompt with optional behavioral contracts and failure context."""
        
    def build_retry_prompt(
        self,
        model_yaml: str,
        previous_code: str,
        failures: FailureReport,
        component: str,
    ) -> tuple[str, str]:
        """Build a targeted retry prompt for a specific failing component."""
```

Commit: `feat: add test-aware PromptBuilder for behavioral generation`

---

### Task 4: Code Writer (File Materializer)

**Files:**
- Create: `src/architecture_model/training/code_writer.py`
- Test: `tests/test_training/test_code_writer.py`

**Purpose:** Take generated code (multi-module string) and write it to a temp package directory that can be tested with pytest.

```python
@dataclass
class MaterializedPackage:
    """A generated package written to disk, ready for testing."""
    package_dir: Path           # Root dir containing the package
    package_name: str           # Package name (e.g., "click")
    modules: list[str]          # Module files written
    init_written: bool          # Whether __init__.py was generated
    
class CodeWriter:
    def materialize(
        self,
        generated_code: str,
        package_name: str,
        output_dir: Path,
    ) -> MaterializedPackage:
        """Write generated multi-module code to a package directory.
        
        1. Parse generated code on '# module_name.py' separators
        2. Create output_dir/package_name/ directory
        3. Write each module as a .py file
        4. Generate __init__.py with public exports if not present
        5. Return MaterializedPackage with paths
        """
    
    def patch_for_testing(
        self,
        package: MaterializedPackage,
        original_repo: Path,
    ) -> None:
        """Copy test infrastructure from original repo into the materialized package.
        
        - Copy conftest.py, fixtures
        - Copy pyproject.toml / setup.py (for pip install -e)
        - Ensure test imports resolve to our generated package
        """
```

Commit: `feat: add CodeWriter to materialize generated code for testing`

---

### Task 5: Retry Loop Controller

**Files:**
- Create: `src/architecture_model/training/test_guided_generator.py`
- Test: `tests/test_training/test_guided_generator.py`

**Purpose:** Core orchestrator: generate → test → analyze → regenerate cycle.

```python
@dataclass
class GenerationAttempt:
    """Record of one generation attempt in the retry loop."""
    iteration: int
    code: str
    pass_rate: float
    failures: FailureReport
    time_seconds: float
    components_regenerated: list[str]

@dataclass  
class TestGuidedResult:
    """Final result of the test-guided generation process."""
    final_code: str
    final_pass_rate: float
    iterations: int
    attempts: list[GenerationAttempt]
    converged: bool
    structural_score: float | None

class TestGuidedGenerator:
    """Generates code that passes tests via iterative refinement."""
    
    def __init__(
        self,
        surrogate: Surrogate,
        test_runner: TestRunner,
        contract_miner: TestContractMiner,
        prompt_builder: PromptBuilder,
        code_writer: CodeWriter,
        failure_parser: FailureParser,
        max_retries: int = 10,
        convergence_threshold: int = 3,
    ): ...
    
    async def generate(
        self,
        model: ArchitectureModel,
        manifest: dict,
        repo_path: Path,
        package_name: str,
    ) -> TestGuidedResult:
        """Full test-guided generation pipeline."""
        
    async def _initial_generation(self, model, manifest, contracts) -> str:
        """Generate initial code using enriched model + contracts."""
        
    async def _retry_component(self, component, model_yaml, previous_code, failures, contracts) -> str:
        """Regenerate a single failing component with failure context."""
        
    def _check_convergence(self, attempts: list[GenerationAttempt]) -> bool:
        """True if last N attempts show no pass_rate improvement."""
```

Commit: `feat: add TestGuidedGenerator retry loop controller`

---

### Task 6: Per-Component Regeneration

**Files:**
- Modify: `src/architecture_model/training/test_guided_generator.py`
- Test: `tests/test_training/test_guided_generator.py` (additional tests)

**Purpose:** When tests fail, only regenerate the module(s) responsible.

```python
async def _targeted_retry(self, package, failures, model, contracts, current_code) -> str:
    """Regenerate only the failing component(s)."""

def _extract_component_code(self, full_code: str, component: str) -> str:
    """Extract a single component's code from multi-module output."""

def _splice_component(self, full_code: str, component: str, new_code: str) -> str:
    """Replace a component's section with new implementation."""
```

Commit: `feat: add per-component targeted regeneration`

---

### Task 7: Training Signal Integration

**Files:**
- Modify: `src/architecture_model/training/pipeline.py`
- Test: `tests/test_training/test_pipeline_test_signal.py`

**Purpose:** Use test pass rate as primary training signal and generate DPO pairs from retry iterations.

```python
# In loss_vector:
loss_vector["test_pass_rate"] = test_guided_result.final_pass_rate
loss_vector["test_iterations"] = test_guided_result.iterations

# DPO pairs from improvement iterations:
for i in range(1, len(attempts)):
    if attempts[i].pass_rate > attempts[i-1].pass_rate:
        store.save_preference(
            prompt=model_yaml,
            chosen=attempts[i].code,
            rejected=attempts[i-1].code,
            margin=attempts[i].pass_rate - attempts[i-1].pass_rate,
        )
```

Commit: `feat: integrate test pass rate as training signal`

---

### Task 8: CLI Command

**Files:**
- Create or modify: `src/architecture_model/cli/generate.py`
- Test: `tests/test_cli/test_generate_command.py`

```bash
architecture-model generate --test-guided /path/to/repo --max-retries 10 --model qwen2.5:7b
```

Commit: `feat: add 'generate --test-guided' CLI command`

---

### Task 9: End-to-End Integration Test

**Files:**
- Create: `tests/test_integration/test_guided_generation_e2e.py`
- Create: `scripts/test_guided_round_trip.py`

Mocked integration test + real execution script.

Commit: `feat: add end-to-end integration test for test-guided generation`

---

### Task 10: Proof-of-Concept Run

Execute on real repos, record results. No code changes.

```bash
python scripts/test_guided_round_trip.py --repo python-dotenv --max-retries 10
python scripts/test_guided_round_trip.py --repo colorama --max-retries 10
python scripts/test_guided_round_trip.py --repo arrow --max-retries 10
python scripts/test_guided_round_trip.py --repo click --max-retries 15
```

**Success criteria:**
- python-dotenv: >50% test pass rate
- colorama: >40% test pass rate  
- arrow: >30% test pass rate
- click: >15% test pass rate

---

## Dependency Graph

```
Task 1 (Contract Miner) ─┐
Task 2 (Failure Parser)  ─┤
Task 3 (Prompt Builder)  ─┼─→ Task 5 (Retry Loop) ─→ Task 7 (Training Signal)
Task 4 (Code Writer)     ─┘         │              ─→ Task 8 (CLI)
                                     │              ─→ Task 9 (Integration)
                              Task 6 (Per-Comp) ────→ Task 10 (PoC Run)
```

Tasks 1-4 are INDEPENDENT and can be parallelized.

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Generated code doesn't import correctly | CodeWriter generates `__init__.py` with `__all__` from symbols |
| Tests need specific fixtures/conftest | CodeWriter.patch_for_testing copies test infra from original |
| Retry loop diverges (gets worse) | Convergence detection stops after 3 non-improving iterations |
| Token limit exceeded (contracts too large) | PromptBuilder.summary_for_prompt has max_tokens cap |
| 7B model can't implement complex logic | Start with simple repos; plan for 13B upgrade path |
| Test failures from env issues | Filter collection errors, mark infra failures non-actionable |
