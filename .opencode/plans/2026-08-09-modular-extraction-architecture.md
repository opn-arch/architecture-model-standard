# Modular Extraction Architecture

**Date:** 2026-08-09  
**Status:** Design Approved  
**Scope:** architecture-model-standard + opencode-arch (full execution)

---

## Problem Statement

The current extraction pipeline has 15+ entangled stages developed empirically across two repos. Stages are not independently testable, quality is only measured at the end (validate/check), documentation and code overlap between repos, and the pipeline cannot be partially re-run. The result works but is not architected.

## Design Goals

1. **Truth first** — the model must faithfully represent the system as it actually is; economy is a side-effect, not the objective
2. **Domain-universal** — the same 7 modules work for software, electrical, mechanical, and control systems; only the observer (scanner) changes per domain
3. **Clean repo separation** — arch-std owns deterministic truth-seeking; opencode-arch owns fallback escalation (LLM, search, ask user)
4. **Independent modules** — each stage callable alone, with explicit dependencies
5. **Observable** — every stage emits structured quality metrics with confidence scores
6. **Provenance on every claim** — every assertion in the model tracks its evidence source and confidence
7. **Capability-driven** — capabilities drive structure (SE ideal), not import clustering
8. **Systems of systems** — uniform artifacts at every recursion level
9. **Documentation as input** — README, OpenAPI, schematics, datasheets, CI pipelines, git history are evidence for inference
10. **Explicit uncertainty** — modules emit what they know AND what they don't know; unknowns are first-class

---

## Architecture: 7 Independent Modules

### Dependency DAG

```
observe ─────┬──→ infer ──┬──→ allocate ──┬──→ relate ──→ validate
             │            │               │                  ↑
             │            │               ├──→ specify       │
             │            │               │                  │
             │            │               └──→ contract      │
             │            │                                  │
             └────────────┴──────────────────────────────────┘
```

- `specify` and `contract` are independent of `infer` and `relate`
- You can re-enrich specs without re-inferring capabilities
- Validate checks everything against observed ground truth

### Cross-Domain Universality

The 7 modules answer universal systems engineering questions. Only the **observer** (scanner/parser) changes per domain:

| Module | Software | Electrical | Mechanical | Control Systems |
|--------|----------|-----------|------------|-----------------|
| **observe** | AST scan, imports, routes | Schematic netlist, BOM, PCB layout | CAD assembly tree, drawings, material specs | PLC programs, I/O lists, network topology |
| **infer** | Capabilities from routes/tests | Functions from circuit blocks (PSU, signal conditioning, comms) | Functions from assembly purpose (structural, sealing, actuation) | Control loops, safety functions, interlocks |
| **allocate** | Files → components | Nets/parts → functional blocks | Parts → assemblies | I/O → loops → PLCs |
| **relate** | Import edges, call graph | Electrical connections, signal/power flow | Mating interfaces, load paths, thermal paths | Signal flow, interlock chains, cascade deps |
| **specify** | Signatures, body hints, constants | Voltage, current, tolerance, package, derating | Material, dimensions, surface finish, torque specs | Setpoints, tuning params, timing, deadbands |
| **contract** | Test assertions | Acceptance tests (continuity, insulation, functional) | Inspection criteria (dimensional, material cert, pressure) | FAT/SAT, loop checks, safety validation (SIL) |
| **validate** | Model vs code reality | Design vs netlist/BOM | Model vs CAD/drawing reality | Config vs PLC program |

**Key insight:** The pipeline protocol (Stage → StageResult → Uncertainty → Evidence) is domain-agnostic. What changes per domain:

1. **Observer plugins** — different parsers for different input formats:
   - `observe_software` — AST (Python, TS, Kotlin, Java)
   - `observe_electrical` — KiCad/Altium netlist, EAGLE schematic, SPICE
   - `observe_mechanical` — STEP/IGES assembly, FreeCAD, SolidWorks API
   - `observe_controls` — IEC 61131-3 (structured text, ladder), Siemens TIA Portal export

2. **Domain-specific evidence types:**
   ```python
   # Software
   Evidence(source="ast", raw="@router.post('/auth/login')")
   
   # Electrical
   Evidence(source="netlist", raw="U1.VCC connected to R1.1 via NET_3V3")
   Evidence(source="datasheet", raw="MAX output current: 500mA @ 3.3V")
   
   # Mechanical
   Evidence(source="cad", raw="Part-007 mates with Part-012 via M6 bolt pattern")
   Evidence(source="material_spec", raw="316L stainless, yield strength 205 MPa")
   
   # Controls
   Evidence(source="plc_program", raw="FB_PID_Loop_01: PV=AI_001, CV=AO_003")
   Evidence(source="sil_assessment", raw="SIF-003 rated SIL 2, PFDavg = 1.2e-3")
   ```

3. **Domain-specific uncertainty categories:**
   - Electrical: `unspecified_derating`, `missing_thermal_analysis`, `ambiguous_ground_reference`
   - Mechanical: `unspecified_tolerance`, `missing_material_cert`, `ambiguous_fit_type`
   - Controls: `unvalidated_safety_function`, `missing_loop_tuning`, `undocumented_interlock`

4. **Domain-specific quality thresholds:**
   - Software: `parse_success_rate ≥ 90%`
   - Electrical: `net_connectivity_coverage ≥ 95%`, `component_spec_completeness ≥ 80%`
   - Mechanical: `assembly_completeness ≥ 95%`, `tolerance_specification ≥ 90%`
   - Controls: `io_allocation_coverage ≥ 100%`, `safety_function_coverage ≥ 100%`

### Domain Profile Selection

```python
@dataclass
class PipelineContext:
    repo_path: Path
    output_dir: Path
    domain: str = "software"              # "software" | "electrical" | "mechanical" | "controls" | "mixed"
    # ...
```

For mixed systems (e.g., an IoT product with firmware + PCB + enclosure + control loops), the coordinator runs domain-appropriate observers in parallel and merges inventories:

```
observe_software(firmware/) ─┐
observe_electrical(pcb/)     ├──→ merged Inventory ──→ infer ──→ ...
observe_mechanical(enclosure/)┘
observe_controls(plc/)       ─┘
```

Cross-domain relationships emerge naturally:
- `firmware.gpio_driver` → `pcb.MCU_PIN_23` (software controls hardware)
- `pcb.TEMP_SENSOR_1` → `controls.AI_001` (electrical feeds control loop)
- `mechanical.ENCLOSURE_VENT` → `electrical.FAN_HEADER_J3` (mechanical enables thermal management)

### Module Summary

| # | Module | Question Answered | Input | Output |
|---|--------|-------------------|-------|--------|
| 1 | **observe** | What physically exists? | repo path | `Inventory` |
| 2 | **infer** | What does the system do? | Inventory | `FunctionalModel` |
| 3 | **allocate** | What code realizes what? | Inventory + FunctionalModel | `StructuralModel` |
| 4 | **relate** | How do parts interact? | all above | `RelationshipModel` |
| 5 | **specify** | What must each function do? | Inventory + StructuralModel | per-component `ComponentSpec` |
| 6 | **contract** | How do you verify it? | Inventory + StructuralModel | per-component `VerificationSpec` |
| 7 | **validate** | Is the model faithful? | all above + Inventory | `ValidationReport` |

---

## Shared Infrastructure

### Uniform Stage Interface

```python
@dataclass
class Diagnostic:
    severity: str          # "error" | "warning" | "info"
    code: str              # e.g. "OBSERVE-001"
    message: str
    context: dict = field(default_factory=dict)

@dataclass
class QualityMetrics:
    score: float                          # 0-100 composite
    sub_scores: dict[str, float]          # Named breakdown
    thresholds: dict[str, float]          # Pass/fail thresholds
    llm_prompt: str = ""                  # Optional LLM assessment prompt
    
    @property
    def passes(self) -> bool:
        return all(self.sub_scores.get(k, 0) >= v for k, v in self.thresholds.items())

@dataclass
class StageResult[T]:
    output: T
    quality: QualityMetrics
    diagnostics: list[Diagnostic]
    input_hash: str                       # Determinism verification
    duration_ms: int
    version: str                          # Module version

class Stage(Protocol[T]):
    name: str
    version: str
    requires: list[str]                   # Other stage names
    
    def run(self, context: PipelineContext) -> StageResult[T]: ...
    def can_run(self, context: PipelineContext) -> bool: ...
    def output_path(self, context: PipelineContext) -> Path: ...

@dataclass
class PipelineContext:
    repo_path: Path
    output_dir: Path                      # .architecture/
    cache: dict[str, StageResult] = field(default_factory=dict)
    scope: str = ""                       # "" = root, "COMP-X" = sub-decomposition
    config: dict = field(default_factory=dict)
```

### Smart Coordinator

```python
class PipelineCoordinator:
    def run_to(self, target: str, ctx: PipelineContext) -> dict[str, StageResult]:
        """Run minimum stages needed to produce target output."""
        ...
    
    def run_stage(self, stage_name: str, ctx: PipelineContext) -> StageResult:
        """Run single stage (checks prerequisites met)."""
        ...
    
    def run_recursive(self, ctx: PipelineContext, max_depth: int = 5):
        """Run full pipeline, then recurse into large components."""
        ...
```

### Provenance & Confidence Model

Every claim in the model tracks how it was discovered and how confident we are:

```python
@dataclass
class Evidence:
    source: str          # "ast" | "documentation" | "llm_analysis" | "user_confirmation" | "git_history" | "config" | "test"
    confidence: float    # 0.0-1.0
    raw: str             # The actual evidence (import line, doc excerpt, LLM reasoning, user quote)
    location: str = ""   # File:line or URL where evidence was found

@dataclass
class Claim[T]:
    """A model assertion with provenance."""
    value: T
    evidence: list[Evidence]
    confidence: float           # Aggregate (weighted by source reliability)
    uncertain: bool = False     # Explicitly flagged as needing resolution
    
    @property
    def confidence(self) -> float:
        if not self.evidence:
            return 0.0
        # Source reliability weights
        weights = {"ast": 1.0, "test": 0.95, "config": 0.9, "documentation": 0.8,
                   "git_history": 0.7, "llm_analysis": 0.6, "user_confirmation": 1.0}
        total = sum(e.confidence * weights.get(e.source, 0.5) for e in self.evidence)
        return min(1.0, total / len(self.evidence))
```

Usage in model entities:

```python
@dataclass
class Capability:
    id: str
    name: Claim[str]                     # Name with provenance
    description: Claim[str]              # Description with provenance
    evidence: list[Evidence]             # All evidence supporting this capability's existence
    children: list["Capability"]
    priority: str

# Example:
Capability(
    id="CAP-AUTH",
    name=Claim(value="Authentication", evidence=[
        Evidence(source="ast", confidence=0.9, raw="@router.post('/auth/login')"),
        Evidence(source="documentation", confidence=0.8, raw="README: 'handles user authentication'"),
        Evidence(source="test", confidence=0.95, raw="test_auth.py exists with 15 test cases"),
    ]),
    ...
)
```

### Uncertainty & MCP Fallback Protocol

Each module emits explicit unknowns alongside its output:

```python
@dataclass
class Uncertainty:
    """Something the module couldn't determine deterministically."""
    category: str        # "ambiguous_purpose" | "orphan_file" | "implicit_relationship" | "missing_entry_point" | ...
    description: str     # Human-readable description of what's unknown
    context: dict        # Relevant data for resolving (file paths, partial evidence)
    suggested_fallback: str  # "llm_analysis" | "search_git" | "ask_user" | "search_docs"
    priority: str        # "blocking" (must resolve) | "enriching" (would improve) | "informational"

@dataclass
class StageResult[T]:
    output: T
    quality: QualityMetrics
    diagnostics: list[Diagnostic]
    uncertainties: list[Uncertainty]      # NEW: explicit unknowns
    input_hash: str
    duration_ms: int
    version: str
```

The MCP layer (opencode-arch) resolves uncertainties:

```python
# In opencode-arch/agent/resolution.py

class UncertaintyResolver:
    """Resolves uncertainties emitted by arch-std modules using MCP fallbacks."""
    
    async def resolve(self, uncertainty: Uncertainty, ctx: PipelineContext) -> Evidence | None:
        match uncertainty.suggested_fallback:
            case "llm_analysis":
                # Feed context to frontier model, get architectural judgment
                return await self._llm_analyze(uncertainty)
            case "search_git":
                # Search commit messages, blame, PRs for intent
                return await self._search_git(uncertainty)
            case "ask_user":
                # Present question to user with context
                return await self._ask_user(uncertainty)
            case "search_docs":
                # Search documentation, wiki, issue tracker
                return await self._search_docs(uncertainty)
    
    async def resolve_all(self, result: StageResult, ctx: PipelineContext) -> StageResult:
        """Resolve all blocking uncertainties, optionally enriching ones."""
        for u in result.uncertainties:
            if u.priority == "blocking":
                evidence = await self.resolve(u, ctx)
                if evidence:
                    self._incorporate(result, u, evidence)
        return result
```

### Per-Module Uncertainty Examples

| Module | Uncertainty Category | Example | Fallback |
|--------|---------------------|---------|----------|
| **observe** | `undiscovered_entry_point` | WebSocket handlers not caught by route scanner | LLM reads source for connection patterns |
| **observe** | `dynamic_import` | `importlib.import_module(name)` | Search git for all values of `name` |
| **infer** | `ambiguous_purpose` | Module with generic name (`utils.py`, `helpers.py`) | Ask user or LLM to classify |
| **infer** | `missing_capability` | Code exists but no routes/tests point to it | LLM analyzes module docstrings + README |
| **allocate** | `multi_capability_file` | File serves authentication AND authorization | LLM judges primary purpose; or ask user |
| **allocate** | `orphan_file` | File with no imports to/from other modules | Search git blame for context |
| **relate** | `implicit_coupling` | Event bus pattern (publish/subscribe, no direct import) | LLM identifies event patterns |
| **relate** | `runtime_dependency` | Config-driven wiring (DI container) | Search config files for bindings |
| **specify** | `complex_algorithm` | Function with 50+ lines, no docstring | LLM summarizes intent |
| **specify** | `magic_constants` | Unexplained numeric literals | Search git for commit that introduced them |
| **contract** | `untested_function` | Public function with no test coverage | LLM infers expected behavior from usage |
| **contract** | `integration_boundary` | Test spans multiple components | Ask user for acceptance criteria |
| **validate** | `low_coherence` | Component boundary score < 40% | LLM proposes alternative boundaries; ask user |

### The Truth-Seeking Pipeline

The complete flow with fallbacks:

```
┌─────────────────────────────────────────────────────────────────┐
│ architecture-model-standard (deterministic truth-seeking)        │
│                                                                 │
│  observe ──→ infer ──→ allocate ──→ relate ──→ specify/contract │
│     │           │          │          │            │            │
│     ▼           ▼          ▼          ▼            ▼            │
│  [uncertainties emitted at each stage]                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ opencode-arch (MCP fallback layer)                              │
│                                                                 │
│  For each uncertainty:                                          │
│    1. LLM analysis (ask frontier model to reason)               │
│    2. Search (git blame, docs, issues, web)                     │
│    3. Ask user (present context + question)                     │
│                                                                 │
│  Feed resolved evidence back → re-run affected stage            │
│  Repeat until: all blocking uncertainties resolved              │
│              OR: user accepts remaining uncertainty              │
└─────────────────────────────────────────────────────────────────┘
```

This ensures the model pursues **truth** for any system — not just well-structured Python repos. Messy codebases with event buses, dynamic dispatch, runtime wiring, or poor documentation still get faithful models because the MCP layer fills gaps that deterministic analysis cannot.

---

## Module 1: `observe` — Ground Truth Inventory

**Purpose:** Measure what exists. Zero inference. Pure AST + file parsing.

### Output Type

```python
@dataclass
class Inventory:
    modules: list[ModuleRecord]
    edges: list[ImportEdge]
    routes: list[RouteRecord]
    constraints: list[ConstraintRecord]
    test_files: list[TestFileRecord]
    docs: list[DocRecord]                # README, docs/*.md
    configs: list[ConfigRecord]          # pyproject.toml, docker-compose
    api_specs: list[APISpecRecord]       # OpenAPI, GraphQL schemas

@dataclass
class ModuleRecord:
    path: Path
    language: str
    functions: list[FunctionRecord]      # name, signature, body_hint, calls, decorators
    classes: list[ClassRecord]           # name, bases, methods, attributes
    constants: list[ConstantRecord]      # name, value, type
    imports: list[str]
    line_count: int
    docstring: str | None
```

### Quality Metrics

| Metric | Threshold | Meaning |
|--------|-----------|---------|
| `parse_success_rate` | ≥90% | Files successfully parsed |
| `symbol_density` | ≥3.0 | Avg extractable symbols per file |
| `edge_completeness` | ≥80% | Resolved imports / total imports |

### LLM Assessment Prompt

> "Given this inventory of {n} modules with {m} functions and {e} import edges, are there obvious gaps? (e.g., test files not discovered, config files missed, documentation not found)"

### Merges From Current Code

- `manifest/generator.py` → core scanning logic
- `manifest/multi_scanner.py` → multi-language support
- `manifest/body_hints.py` → body hint extraction (observation, not enrichment)
- `opencode-arch/extract/route_detector.py` → route detection (moves to arch-std)
- `opencode-arch/extract/constraint_detector.py` → constraint detection (moves to arch-std)

### Key Design Decision

Body hints are **observed facts** about function implementations, not enrichment applied later. They belong in the inventory alongside signatures. This eliminates the current confusion where body hints are extracted in `manifest/body_hints.py` but consumed in `orchestration/enrich.py`.

---

## Module 2: `infer` — Capability Discovery

**Purpose:** From evidence, determine what the system does (capabilities) and who uses it (actors). Capability-driven: capabilities are inferred FIRST and drive all subsequent structure.

### Output Type

```python
@dataclass
class FunctionalModel:
    capabilities: list[Capability]       # Hierarchical tree
    actors: list[Actor]
    use_cases: list[UseCase]
    constraints: list[Constraint]

@dataclass
class Capability:
    id: str
    name: str
    description: str
    evidence: list[str]                  # File paths, routes, test names
    children: list[Capability]           # Sub-capabilities
    priority: str                        # must | should | could

@dataclass
class UseCase:
    id: str
    name: str
    actor: str
    trigger: str
    steps: list[str]
    capabilities_exercised: list[str]
```

### Inference Algorithm (Capability-Driven)

1. **Cluster by purpose:**
   - Route groups by URL prefix → capability per prefix (`/auth/*` → "Authentication")
   - Test file clusters → confirms capabilities (`test_auth*` validates "Authentication")
   - Service modules with shared domain models → capability per entity
   - Documentation mentions → evidence for capabilities not visible in code

2. **Build hierarchy from specificity:**
   - `/users` → "User Management"
   - `/users/auth` → "User Management > Authentication"
   - Max depth 3 levels

3. **Infer actors from evidence:**
   - Authenticated routes → "Authenticated User"
   - Admin decorators → "Administrator"
   - Webhook handlers → "External System"
   - Scheduled tasks → "System (Timer)"
   - Database connections → "Database" (external actor)

4. **Infer use cases from trigger chains:**
   - Call-graph BFS from entry points
   - Linear chains of length ≥2 → use case
   - Actor from entry point authentication pattern

### Quality Metrics

| Metric | Threshold | Meaning |
|--------|-----------|---------|
| `capability_coverage` | ≥70% | Functions traceable to a capability |
| `actor_completeness` | ≥80% | Entry point types with actors |
| `hierarchy_depth` | ≥2 | Capabilities properly decomposed |

### LLM Assessment Prompt

> "Given routes: {routes}, test files: {test_files}, service functions: {services}, I inferred these capabilities: {capabilities}. Are there capabilities the code provides that are missing? Are any too granular or too broad?"

### Merges From Current Code

- `orchestration/capability_inference.py`
- `orchestration/use_case_inference.py`
- `orchestration/trigger_detection.py` (trigger chain → use case)
- Parts of `extract/from_code.py` (actor/capability derivation)

---

## Module 3: `allocate` — Structure Assignment

**Purpose:** Assign code to components that realize capabilities. Capabilities drive the structure; import affinity is a tiebreaker.

### Output Type

```python
@dataclass
class StructuralModel:
    components: list[Component]
    layers: list[Layer]
    allocations: list[Allocation]

@dataclass
class Component:
    id: str
    name: str
    files: list[Path]
    layer: str | None
    realizes: list[str]                  # Capability IDs
    kind: str                            # service | library | entry-point | data | shared

@dataclass
class Allocation:
    component_id: str
    capability_id: str
    evidence: list[str]
```

### Allocation Algorithm

1. **Seed from capabilities:** For each capability, collect files that directly evidence it (route handlers, test targets, service functions in use-case steps).

2. **Assign remaining files:** For unclaimed files, assign to the component whose existing files import them most (import affinity as tiebreaker).

3. **Split oversized components:** If a component has >N files and realizes multiple capabilities → split along capability lines.

4. **Merge undersized:** If ≤2 files and shares all imports with neighbor → merge.

5. **Layer assignment:** From dependency direction (components depended-on-by-many = lower layer).

### Quality Metrics

| Metric | Threshold | Meaning |
|--------|-----------|---------|
| `file_coverage` | ≥95% | Files allocated to components |
| `boundary_coherence` | ≥60% | Internal edge ratio |
| `capability_alignment` | ≥70% | Components realize 1-3 capabilities |

### Merges From Current Code

- `manifest/grouping.py` (group_modules — reframed as capability-driven)
- `core/decomposer.py` (detect_systems — becomes recursive decomposition trigger)
- Parts of `orchestration/full_extraction.py` (component creation)

---

## Module 4: `relate` — Relationship Extraction

**Purpose:** Derive all typed relationships between entities.

### Output Type

```python
@dataclass
class RelationshipModel:
    relationships: list[Relationship]

@dataclass
class Relationship:
    type: str          # realizes | depends-on | triggers | contains | exposes | consumes | constrained-by
    from_id: str
    to_id: str
    evidence: str      # Import path, call chain, or structural reason
    strength: float    # 0-1
```

### Derivation Rules

| Type | How Derived |
|------|-------------|
| `realizes` | From allocation (component → capability) |
| `depends-on` | Cross-component import edges from inventory |
| `triggers` | Call-graph traversal between behavior entry points |
| `contains` | Capability hierarchy + layer containment |
| `exposes` | Public functions imported by other components |
| `consumes` | Actor → interface patterns from routes |
| `constrained-by` | Constraint → component from config evidence |

### Quality Metrics

| Metric | Threshold | Meaning |
|--------|-----------|---------|
| `relationship_accuracy` | ≥80% | Edges backed by real imports |
| `orphan_rate_max` | ≤10% | Entities with 0 relationships |
| `trigger_completeness` | ≥60% | Behavioral flows fully traced |

### Merges From Current Code

- `orchestration/trigger_detection.py`
- `orchestration/behavior_decompose.py`
- Parts of `extract/from_code.py` (relationship derivation)
- Parts of `orchestration/auto_enrich.py` (interface extraction)

---

## Module 5: `specify` — Implementation Detail

**Purpose:** Attach enough detail to each component for deterministic reimplementation.

**Dependencies:** `observe` + `allocate` only. Independent of infer/relate.

### Output Type (per component)

```python
@dataclass
class ComponentSpec:
    component_id: str
    signatures: list[FunctionSignature]  # name, params, returns, decorators, body_hint
    constants: list[Constant]            # name, value, type, context
    symbols: list[Symbol]                # classes, protocols, enums with members
    patterns: list[str]                  # Detected design patterns
    interfaces: ComponentInterfaces      # provides/requires with symbol lists
```

### Quality Metrics

| Metric | Threshold | Meaning |
|--------|-----------|---------|
| `signature_coverage` | ≥80% | Functions with full signatures |
| `body_hint_coverage` | ≥60% | Functions with implementation hints |
| `constant_coverage` | ≥50% | Known constants extracted |

### Merges From Current Code

- `orchestration/enrich.py` (enrich_model)
- `orchestration/auto_enrich.py` (enrich_from_manifest, pattern detection, symbol extraction)
- Consumes body hints already present in inventory (from observe)

---

## Module 6: `contract` — Verification Extraction

**Purpose:** Extract what "correct" means for each component.

**Dependencies:** `observe` + `allocate` only. Independent of infer/relate/specify.

### Output Type (per component)

```python
@dataclass
class VerificationSpec:
    component_id: str
    contracts: list[TestContract]        # assertion, contract_type, test_method
    acceptance_criteria: list[str]       # From use-case postconditions
    required_imports: list[str]          # What tests need
    constant_derivations: list[Constant] # Constants discovered in tests
```

### Quality Metrics

| Metric | Threshold | Meaning |
|--------|-----------|---------|
| `contract_count_min` | ≥3.0 | Avg contracts per component |
| `function_coverage` | ≥50% | Functions with ≥1 contract |
| `constant_extraction` | ≥70% | Test-referenced constants found |

### Merges From Current Code

- `manifest/test_analyzer.py` (analyze_test_file)
- Parts of `orchestration/enrich.py` (_enrich_test_contracts)

---

## Module 7: `validate` — Faithfulness Check

**Purpose:** Verify the model is faithful to code reality AND internally consistent.

**Dependencies:** All other stages (compares everything against observe ground truth).

### Output Type

```python
@dataclass
class ValidationReport:
    structural_score: float              # YAML well-formedness (0-100)
    file_coverage: float                 # % files in model
    relationship_accuracy: float         # % edges backed by imports
    boundary_coherence: float            # Grouping quality
    capability_realization: float        # % capabilities with components
    overall: float                       # Weighted composite
    gaps: list[Diagnostic]
```

### Merges From Current Code

- `core/validator.py` (11 structural checks)
- `opencode-arch/mcp/tools/check.py` (representativeness: FC/RA/BC algorithm → moves to arch-std)

---

## Systems of Systems: Uniform Artifacts at Every Level

### Recursive Decomposition Rule

Any component with >N files (configurable, default 5) is itself decomposed by running modules 1-7 within that component's scope. This produces the same artifact set at every level.

### Output File Structure

```
.architecture/
├── inventory.json            ← observe output
├── functional.yaml           ← infer output (capabilities, actors, use cases)
├── structure.yaml            ← allocate output (components, layers)
├── relationships.yaml        ← relate output (typed edges)
├── validation.json           ← validate output (scores, gaps)
├── context.md                ← LLM-readable summary (auto-generated)
│
├── specs/
│   ├── {component-id}.yaml   ← specify output per component
│   └── ...
│
├── contracts/
│   ├── {component-id}.yaml   ← contract output per component
│   └── ...
│
└── subsystems/
    └── {component-id}/
        └── .architecture/    ← same structure, recursively
```

### What Varies by Level

| Artifact | Top Level | Sub-System | Leaf |
|----------|-----------|------------|------|
| functional.yaml | System capabilities | Sub-capabilities | Micro-capabilities |
| structure.yaml | Major components (6-12) | Sub-components (3-8) | Modules (1-5 files) |
| specs/ | Key signatures only | All public functions | Every function + body hint |
| contracts/ | Integration contracts | Unit contracts | Assertion-level |
| context.md | Architecture overview | Component deep-dive | Implementation guide |

### The `context.md` Contract

Each level auto-generates an LLM-readable summary:

```markdown
# {System Name}

## Purpose
{One sentence from capability descriptions}

## Capabilities
{Bulleted list with descriptions}

## Components
{Table: name, files, realizes, depends-on}

## Key Interfaces
{Provides/requires with signatures}

## Constraints
{Non-functional requirements with evidence}
```

### Completeness Invariants

1. **Capability decomposition is complete:** Every leaf capability maps to ≥1 component.
2. **File allocation is exhaustive:** Union of all leaf component files = all source files.
3. **Relationship closure:** All edges at level N are internal or boundary (referencing sibling by ID).
4. **Spec coverage increases with depth:** Leaf specs have every function; top-level has summaries.

---

## Documentation as Input

The `observe` module ingests non-code artifacts as evidence:

| Source | Evidence For |
|--------|-------------|
| README.md | Capability names, system purpose, actor descriptions |
| docs/*.md | Detailed capability descriptions, architectural decisions |
| OpenAPI/GraphQL schemas | Interface definitions, validates route detection |
| docker-compose.yaml | External actors (databases, queues, caches) |
| CI pipelines | Deployment constraints, environment separation |
| pyproject.toml | Technology constraints, dependency declarations |

The `infer` module uses this documentation alongside code evidence. Documentation can reveal capabilities invisible to AST scanning (e.g., "real-time notifications" mentioned in README but implemented via WebSockets that the route scanner missed).

---

## Repo Separation

### architecture-model-standard (this repo)

**Role:** Deterministic truth-seeking. Emits what it knows with confidence, and explicitly flags what it doesn't know.

All 7 modules + coordinator + types + CLI:

```
src/architecture_model/
├── pipeline/
│   ├── protocol.py       ← Stage, StageResult, QualityMetrics, Evidence, Claim, Uncertainty
│   ├── coordinator.py    ← PipelineCoordinator
│   ├── observe.py        ← Module 1
│   ├── infer.py          ← Module 2
│   ├── allocate.py       ← Module 3
│   ├── relate.py         ← Module 4
│   ├── specify.py        ← Module 5
│   ├── contract.py       ← Module 6
│   └── validate.py       ← Module 7
├── extract/
│   ├── route_detector.py   ← moved from opencode-arch
│   ├── constraint_detector.py ← moved from opencode-arch
│   ├── from_artifacts.py   ← moved from opencode-arch
│   └── table_parser.py    ← moved from opencode-arch
├── core/
│   ├── check.py            ← representativeness algorithm (moved from opencode-arch)
│   └── ...existing...
└── ...existing (types, config, manifest scanners)...
```

### opencode-arch

**Role:** Resolve uncertainties. Bridge between deterministic analysis and truth via LLM reasoning, search, and user interaction.

```
src/opencode_arch/
├── mcp/tools/
│   ├── observe.py     ← calls arch-std observe, resolves uncertainties, formats for MCP
│   ├── infer.py       ← calls arch-std infer, LLM validates capabilities
│   ├── allocate.py    ← calls arch-std allocate, resolves orphans
│   ├── relate.py      ← calls arch-std relate, discovers implicit coupling
│   ├── specify.py     ← calls arch-std specify, LLM explains complex algorithms
│   ├── contract.py    ← calls arch-std contract, infers missing contracts
│   ├── validate.py    ← calls arch-std validate, proposes fixes
│   └── pipeline.py    ← calls coordinator + resolution loop
├── agent/
│   ├── resolution.py  ← UncertaintyResolver (LLM/search/ask user)
│   ├── iteration.py   ← retry/escalate logic
│   └── assessment.py  ← LLM quality assessment
├── telemetry/         ← unchanged
└── learning/          ← unchanged
```
src/architecture_model/
├── pipeline/
│   ├── protocol.py       ← Stage, StageResult, QualityMetrics, PipelineContext
│   ├── coordinator.py    ← PipelineCoordinator
│   ├── observe.py        ← Module 1
│   ├── infer.py          ← Module 2
│   ├── allocate.py       ← Module 3
│   ├── relate.py         ← Module 4
│   ├── specify.py        ← Module 5
│   ├── contract.py       ← Module 6
│   └── validate.py       ← Module 7
├── extract/
│   ├── route_detector.py   ← moved from opencode-arch
│   ├── constraint_detector.py ← moved from opencode-arch
│   ├── from_artifacts.py   ← moved from opencode-arch
│   └── table_parser.py    ← moved from opencode-arch
├── core/
│   ├── check.py            ← representativeness algorithm (moved from opencode-arch)
│   └── ...existing...
└── ...existing (types, config, manifest scanners)...
```

### opencode-arch

Thin MCP wrappers + agent concerns:

```
src/opencode_arch/
├── mcp/tools/
│   ├── observe.py     ← calls arch-std observe, formats for MCP
│   ├── infer.py       ← calls arch-std infer
│   ├── allocate.py    ← calls arch-std allocate
│   ├── relate.py      ← calls arch-std relate
│   ├── specify.py     ← calls arch-std specify
│   ├── contract.py    ← calls arch-std contract
│   ├── validate.py    ← calls arch-std validate
│   └── pipeline.py    ← calls coordinator.run_to/run_recursive
├── agent/
│   ├── iteration.py   ← retry/escalate logic
│   └── assessment.py  ← LLM quality assessment (uses llm_prompt from metrics)
├── telemetry/         ← unchanged
└── learning/          ← unchanged
```

### Deleted (redundancy resolved)

- `opencode-arch/extract/from_code.py` — duplicate of arch-std version
- `opencode-arch/context/formatter.py` — budget logic absorbed into arch-std slicer/context.md generation

---

## Migration Path

### Phase 1: Infrastructure
1. Create `pipeline/protocol.py` with shared types
2. Create `pipeline/coordinator.py` with DAG resolution

### Phase 2: Move files from opencode-arch
1. `route_detector.py` → `extract/`
2. `constraint_detector.py` → `extract/`
3. `from_artifacts.py` → `extract/`
4. `table_parser.py` → `extract/`
5. Check algorithm from `mcp/tools/check.py` → `core/check.py`

### Phase 3: Implement modules (one at a time)
1. `observe` — wraps existing manifest + scanners + moved detectors
2. `allocate` — refactors grouping.py with capability-driven logic
3. `infer` — refactors capability_inference + use_case_inference
4. `relate` — refactors trigger_detection + relationship derivation
5. `specify` — refactors enrich.py
6. `contract` — refactors test_analyzer
7. `validate` — merges validator + check

### Phase 4: Recursive + artifacts
1. Implement recursive decomposition in coordinator
2. Implement `context.md` generation
3. Implement uniform artifact output structure

### Phase 5: opencode-arch cleanup
1. Replace MCP tools with thin wrappers
2. Delete duplicated code
3. Update imports

---

## Quality Contract Summary

| Module | Key Metric | Threshold | LLM Assessment |
|--------|-----------|-----------|----------------|
| observe | parse_success_rate | ≥90% | "Are there obvious gaps in the inventory?" |
| infer | capability_coverage | ≥70% | "Are capabilities at the right granularity?" |
| allocate | file_coverage | ≥95% | "Do boundaries reflect logical concerns?" |
| relate | relationship_accuracy | ≥80% | "Are key interactions captured?" |
| specify | signature_coverage | ≥80% | "Is this enough to reimplement?" |
| contract | function_coverage | ≥50% | "Do contracts capture key behaviors?" |
| validate | overall | ≥80% | N/A (deterministic sufficient) |

---

## Success Criteria

1. Each module independently callable with `architecture-model {module} {repo_path}`
2. Each module produces deterministic output (same input → same output)
3. Each module emits explicit uncertainties (what it doesn't know) alongside its output
4. Every claim in the model has provenance (evidence source + confidence)
5. Recursive decomposition produces valid artifacts at each level (same structure)
6. An LLM can implement any leaf component from `spec.yaml` + `contracts.yaml` + parent `context.md`
7. opencode-arch resolves uncertainties via LLM analysis, search, and user interaction
8. The system produces faithful models for ANY codebase — not just well-structured Python repos
9. The pipeline can be partially re-run (change spec without re-inferring capabilities)
10. Uncertainty resolution is auditable (every resolved unknown shows the evidence that resolved it)

---

## Learning & Improvement

### Three Learning Loops

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Loop 1: IMMEDIATE (within a single extraction session)                   │
│                                                                         │
│ Module emits uncertainty → MCP resolves → evidence fed back → re-run   │
│ Module emits low score → coordinator escalates → richer input → re-run │
│                                                                         │
│ Learning: nothing persists. This is reactive adaptation.                │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ Loop 2: CROSS-SESSION (same project, over time)                          │
│                                                                         │
│ User corrects model → correction stored with provenance                 │
│ Next extraction run → corrections consumed as prior evidence            │
│ Quality scores compared to previous run → trend detection               │
│                                                                         │
│ Learning: project-specific calibration persists in .architecture/       │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ Loop 3: CROSS-PROJECT (universal improvement)                            │
│                                                                         │
│ Telemetry from many projects → pattern classification                   │
│ Which heuristics fail most? Which domains? Which project shapes?        │
│ Lessons extracted → default thresholds updated → all projects benefit   │
│                                                                         │
│ Learning: universal heuristic improvement persists in the package       │
└─────────────────────────────────────────────────────────────────────────┘
```

### What Can Improve Per Module

| Module | What Learns | From What Signal |
|--------|------------|-----------------|
| **observe** | File patterns to scan/exclude, language detection | Parse failures, user corrections ("that's generated code") |
| **infer** | Capability clustering, hierarchy depth, actor patterns | User corrections ("merge these"), LLM assessments |
| **allocate** | Grouping thresholds, capability-alignment weights | Boundary coherence over time, user re-assignments |
| **relate** | Relationship inference rules, trigger patterns | Accuracy scores, removed false-positive edges |
| **specify** | Body hint classification, pattern catalog | Blind regen success rates |
| **contract** | Test discovery patterns, assertion extraction | Contract count vs regen success correlation |
| **validate** | Scoring weights, threshold calibration | User overrides ("this is correct despite score 70") |

### Loop 1: Immediate (Session Feedback)

Resolution outcomes within a session inform the next uncertainty:

```python
@dataclass
class ResolutionOutcome:
    """What happened when an uncertainty was resolved."""
    uncertainty: Uncertainty
    resolution: Evidence              # What resolved it
    method: str                       # "llm" | "search" | "user" | "escalation"
    attempts: int                     # How many fallbacks tried before success
    duration_ms: int
```

If the same uncertainty type recurs in the session, skip to the method that worked.

### Loop 2: Cross-Session (Project Memory)

Stored in `.architecture/learning/`:

```
.architecture/
├── learning/
│   ├── corrections.yaml        ← user corrections with provenance
│   ├── resolutions.yaml        ← resolved uncertainties (what worked)
│   ├── calibration.yaml        ← project-specific threshold overrides
│   └── history/
│       ├── 2026-08-09.json     ← quality scores per run
│       ├── 2026-08-10.json
│       └── ...
```

#### Corrections as Prior Evidence

User corrections become high-confidence evidence for next run:

```python
@dataclass
class Correction:
    timestamp: str
    module: str                   # Which module's output was corrected
    entity_id: str
    correction_type: str          # "rename" | "split" | "merge" | "remove" | "add" | "reclassify" | "reassign"
    before: dict
    after: dict
    reason: str                   # User's explanation

# On next run, loaded as:
Evidence(
    source="user_correction",
    confidence=1.0,
    raw="User split COMP-UTILS into COMP-LOGGING and COMP-HELPERS (2026-08-09)"
)
```

#### Calibration

Project-specific threshold overrides when defaults don't fit:

```yaml
# .architecture/learning/calibration.yaml
allocate:
  boundary_coherence_threshold: 50.0   # lowered from 60.0
  reason: "User confirmed cross-cutting design is intentional"
  date: 2026-08-09
infer:
  hierarchy_depth_threshold: 1         # flat microservice, no sub-capabilities
  reason: "Single-layer service by design"
```

#### Trend Detection

```python
@dataclass
class QualityTrend:
    module: str
    metric: str
    values: list[tuple[str, float]]    # (date, score)
    direction: str                      # "improving" | "degrading" | "stable"
    alert: str | None                   # "coherence dropped 15% since last refactor"
```

The coordinator warns before running:
> "allocate: boundary_coherence degraded from 72% to 58% over 3 runs. Recent additions may not be well-allocated."

### Loop 3: Cross-Project (Universal Learning)

Lives in opencode-arch telemetry + learning systems:

#### Pattern Classification

```python
@dataclass
class FailurePattern:
    pattern_id: str
    module: str                        # Which module failed
    category: str                      # "CROSS_DEP" | "MISSING_IMPL" | "EVENT_BUS_INVISIBLE" | etc.
    frequency: int                     # How often seen across projects
    domain: str                        # "software" | "electrical" | "controls" | "all"
    project_shape: str                 # "monolith" | "microservices" | "library" | "embedded" | "mixed"
    successful_resolution: str         # "expand_context" | "add_pattern_detector" | "ask_user"
    resolution_confidence: float
```

#### Heuristic Evolution

```python
@dataclass
class HeuristicUpdate:
    module: str
    parameter: str                     # e.g. "allocate.split_threshold"
    old_value: Any
    new_value: Any
    evidence: str                      # "72% of projects with >20 files/component show coherence <50%"
    projects_affected: int
    improvement_expected: float
```

Example learnings over time:

| Observation | Update |
|-------------|--------|
| Event-driven projects get low `relationship_accuracy` | Add event-bus detector to `relate` |
| Monorepos >100 files need depth ≥3 | Adjust `max_depth` default by file count |
| Electrical mixed-signal → always `ambiguous_ground_reference` | Pre-seed ground net detection |
| Control systems without SIL docs → always `unvalidated_safety_function` | Escalate to `ask_user` immediately |

#### Report Cards

```python
@dataclass
class ReportCard:
    project: str
    run_date: str
    domain: str
    grade: str                         # A-F
    module_scores: dict[str, QualityMetrics]
    overall_confidence: float          # avg evidence confidence across all claims
    uncertainty_resolution_rate: float # resolved / total uncertainties
    correction_rate: float             # user corrections / total claims (lower = better)
    vs_previous: dict[str, float]      # delta per metric
    improvements: list[str]            # actionable suggestions
    lessons: list[str]                 # insights for cross-project learning
```

### The Improvement Flywheel

```
New project analyzed
    → modules emit uncertainties + quality scores
    → MCP resolves uncertainties (records what worked)
    → user corrects remaining errors (records corrections)
    → telemetry captures everything
    → pattern classifier identifies systemic issues
    → heuristic optimizer proposes default changes
    → next run on SAME project: corrections as prior evidence, calibrated thresholds
    → next run on NEW project: improved defaults from cross-project learning
    → over time: fewer uncertainties, higher first-run scores, faster resolution
```

### Learning Architecture Diagram

```
┌─ architecture-model-standard ─────────────────────────────────────┐
│                                                                    │
│  Modules 1-7 (deterministic)                                      │
│       ├── emit: StageResult (output + quality + uncertainties)    │
│       ├── consume: prior corrections as Evidence                  │
│       └── consume: calibration overrides for thresholds           │
│                                                                    │
│  .architecture/learning/ (project-local persistence)              │
│       ├── corrections.yaml → prior evidence                      │
│       ├── resolutions.yaml → skip to working fallback            │
│       ├── calibration.yaml → adjusted thresholds                 │
│       └── history/ → trend detection                             │
│                                                                    │
└───────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─ opencode-arch ──────────────────────────────────────────────────┐
│                                                                   │
│  Resolution Layer                                                 │
│       ├── resolve uncertainties (LLM, search, ask user)          │
│       └── record resolution outcomes                             │
│                                                                   │
│  Telemetry                                                       │
│       ├── collect StageResults from all projects                 │
│       ├── aggregate per-module, per-metric, per-domain           │
│       └── store in telemetry DB                                  │
│                                                                   │
│  Learning Engine                                                  │
│       ├── pattern classifier (what fails, where, why)            │
│       ├── heuristic optimizer (which defaults should change)     │
│       ├── lesson extractor (insights from corrections/outcomes)  │
│       └── report card generator (grades + trends + actions)      │
│                                                                   │
│  Feedback to arch-std                                            │
│       └── PRs updating module defaults based on cross-project    │
│           evidence ("add event-bus detector", "raise threshold") │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### What's New vs Current Learning System

| Current (opencode-arch) | New (structured) |
|--------------------|-----------------|
| Classifies regen failures only | Classifies failures across all 7 modules |
| Grades regen runs only | Report cards grade entire pipeline runs |
| Adapts prompts for regen | Heuristic optimizer adjusts module parameters |
| Feedback stored as untyped JSONL | Corrections as typed YAML, consumed as prior evidence |
| Session-level telemetry | Per-module, per-metric, per-domain telemetry |
| No project-local learning | `.architecture/learning/` persists across runs |
| Regen-focused lessons | Lessons cover observe→validate across all domains |
