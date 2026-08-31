# Interface Specification Document

## 1. Interface Inventory

| Interface ID | Name | Type | Protocol | Provider | Consumer(s) |
|---|---|---|---|---|---|
| IF-1 | main CLI | CLI | stdin/stdout | COMP-8 | End User |
| IF-2 | runner CLI | CLI | stdin/stdout | COMP-8 | CI/CD, Scripts |
| IF-3 | Documentation Library API | Library | Python import | COMP-4 | COMP-8, COMP-5 |
| IF-4 | Scanners Library API | Library | Python import | COMP-3.1 | COMP-2.2, COMP-6 |
| IF-5 | Core Doc Generators API | Library | Python import | COMP-4.1 | COMP-8, COMP-4.2 |
| IF-6 | SE Document Suite API | Library | Python import | COMP-4.2 | COMP-8 |
| IF-7–IF-16 | Various Doc APIs | Library | Python import | COMP-4.x | COMP-8, COMP-5 |
| IF-auto-COMP-1 | Core API | Library | Python import | COMP-1 | All components |
| IF-auto-COMP-2 | Pipeline API | Library | Python import | COMP-2 | COMP-8, COMP-5 |
| IF-auto-COMP-5 | Orchestration API | Library | Python import | COMP-5 | COMP-8 |
| IF-auto-COMP-6 | Extract API | Library | Python import | COMP-6 | COMP-2, COMP-5 |
| IF-auto-COMP-7 | Authoring API | Library | Python import | COMP-7 | COMP-8 |
| IF-auto-COMP-9 | Configuration API | Library | Python import | COMP-9 | All components |
| IF-auto-COMP-10 | Export API | Library | Python import | COMP-10 | COMP-8 |
| IF-auto-COMP-11 | Pipeline Learning API | Library | Python import | COMP-11 | COMP-2 |
| IF-auto-COMP-12 | Utilities API | Library | Python import | COMP-12 | All components |

---

## 2. API Interfaces

This system does not expose HTTP/REST APIs. All interfaces are Python library APIs invoked via import.

### IF-auto-COMP-1: Core API

**Provider:** `src/architecture_model/core/__init__.py`

```python
# Type System (COMP-1.1)
@dataclass
class Component:
    id: str
    name: str
    layer: str
    description: str
    files: List[str]
    children: List[str]

@dataclass
class Interface:
    id: str
    name: str
    protocol: str
    provider: str
    consumer: str

@dataclass
class Relationship:
    source: str
    target: str
    relation_type: RelationType

class RelationType(Enum):
    EXPOSES = "exposes"
    CONSUMES = "consumes"
    DEPENDS_ON = "depends_on"
    CONTAINS = "contains"

# Parser & Persistence (COMP-1.3)
def parse_model(path: Path) -> ArchitectureModel: ...
def serialize_model(model: ArchitectureModel, path: Path) -> None: ...

# Validation (COMP-1.2)
def validate_model(model: ArchitectureModel) -> List[ValidationError]: ...

# Model Operations (COMP-1.4)
def slice_model(model: ArchitectureModel, component_ids: List[str]) -> ArchitectureModel: ...
def diff_models(old: ArchitectureModel, new: ArchitectureModel) -> ModelDiff: ...
def compute_coverage(model: ArchitectureModel, source_root: Path) -> CoverageReport: ...

# Quality Metrics (COMP-1.5)
def compute_confidence(model: ArchitectureModel) -> ConfidenceReport: ...
def check_regen_readiness(model: ArchitectureModel) -> RegenReadiness: ...
```

**Data Format:** Python dataclasses; persistence as YAML files.  
**Error Handling:** Raises `ValidationError`, `ParseError`, `ModelError`.

---

### IF-auto-COMP-2: Pipeline API

**Provider:** `src/architecture_model/pipeline/__init__.py`

```python
# Coordination (COMP-2.1)
class PipelineCoordinator:
    def run(self, config: PipelineConfig, source_root: Path) -> ArchitectureModel: ...
    def run_stage(self, stage: str, context: PipelineContext) -> StageResult: ...

@dataclass
class PipelineConfig:
    stages: List[str]  # ["observe","infer","allocate","relate","specify","contract","validate","decompose","synthesize","emit"]
    cache_dir: Optional[Path]
    profile: Optional[str]

@dataclass
class PipelineContext:
    source_root: Path
    model: ArchitectureModel
    artifacts: Dict[str, Any]
    cache: Optional[PipelineCache]

# Stage Protocol
class Stage(Protocol):
    name: str
    def execute(self, context: PipelineContext) -> StageResult: ...

@dataclass
class StageResult:
    model: ArchitectureModel
    artifacts: Dict[str, Any]
    errors: List[str]
    duration_ms: float
```

**Error Handling:** Stages return errors in `StageResult.errors`; coordinator may halt or continue based on config.

---

### IF-auto-COMP-5: Orchestration API

```python
# Enrichment (COMP-5.1)
def enrich_model(model: ArchitectureModel, source_root: Path) -> ArchitectureModel: ...
def auto_enrich(model: ArchitectureModel, source_root: Path, profile: str = "default") -> ArchitectureModel: ...

# Decomposition (COMP-5.2)
def decompose_model(model: ArchitectureModel, max_depth: int = 2) -> ArchitectureModel: ...
def extract_behavior_flows(model: ArchitectureModel, source_root: Path) -> List[BehaviorFlow]: ...
```

---

### IF-auto-COMP-6: Extract API

```python
def extract_from_code(source_root: Path, config: Optional[ExtractConfig] = None) -> ArchitectureModel: ...
def extract_from_artifacts(artifact_dir: Path) -> ArchitectureModel: ...
def detect_routes(source_root: Path) -> List[Route]: ...
def detect_constraints(source_root: Path) -> List[Constraint]: ...
```

---

### IF-auto-COMP-3.1: Scanners API

```python
class ScanResult:
    modules: List[ModuleInfo]
    imports: List[ImportInfo]
    classes: List[ClassInfo]
    functions: List[FunctionInfo]

def scan_python(path: Path) -> ScanResult: ...
def scan_typescript(path: Path) -> ScanResult: ...
def scan_kotlin(path: Path) -> ScanResult: ...
def multi_scan(root: Path, languages: List[str] = None) -> ScanResult: ...
```

---

## 3. CLI Interfaces

### IF-1: Main CLI

**Entry point:** `python -m architecture_model` / `src/architecture_model/cli/main.py`

| Command | Arguments | Options | Output |
|---|---|---|---|
| `extract` | `<source_root>` | `--output PATH`, `--profile NAME`, `--format yaml\|json` | YAML model file |
| `validate` | `<model_path>` | `--strict`, `--schema PATH` | Validation report (stdout) |
| `enrich` | `<model_path>` | `--source PATH`, `--profile NAME`, `--output PATH` | Enriched YAML model |
| `pipeline` | `<source_root>` | `--stages LIST`, `--cache-dir PATH`, `--config PATH` | Final model + report |
| `docs` | `<model_path>` | `--output-dir PATH`, `--format md\|html`, `--suite se\|core\|all` | Documentation directory |
| `export` | `<model_path>` | `--format flat\|reference`, `--output PATH` | Exported files |
| `diff` | `<old_model> <new_model>` | `--format md\|json` | Diff report |
| `slice` | `<model_path>` | `--components IDS`, `--output PATH` | Sliced model |
| `visualize` | `<model_path>` | `--type diagram\|matrix`, `--output PATH` | Diagram file |
| `author` | `<requirements_path>` | `--output PATH` | Authored model |
| `gate` | `<model_path>` | `--criteria PATH` | Pass/fail + report |

**Output format:** Markdown to stdout by default; YAML/JSON for model files.  
**Exit codes:** 0 = success, 1 = validation failure, 2 = runtime error.

### IF-2: Runner CLI

Subset of main CLI optimized for CI/CD pipelines. Same commands with `--ci` flag for machine-readable JSON output.

---

## 4. Internal Interfaces

### COMP-9 → All Components: Configuration Contract

```python
@dataclass
class AppConfig:
    source_root: Path
    output_dir: Path
    profile: str
    stages: List[str]
    cache_enabled: bool
    llm_config: Optional[Dict[str, Any]]

def load_config(path: Optional[Path] = None) -> AppConfig: ...
```

### COMP-12 → All Components: Utilities Contract

```python
# Discovery
def discover_files(root: Path, extensions: List[str]) -> List[Path]: ...

# Monitoring
def log_stage(stage: str, duration_ms: float, status: str) -> None: ...
```

### COMP-2.1 → COMP-2.2–2.5: Stage Protocol

All stages implement the `Stage` protocol. Coordinator calls `execute(context)` sequentially, passing accumulated `PipelineContext`.

### COMP-3.2 → COMP-2.3: Graph Data Contract

```python
@dataclass
class CallGraph:
    nodes: List[str]  # fully-qualified function names
    edges: List[Tuple[str, str]]  # (caller, callee)

@dataclass
class ImportGraph:
    modules: List[str]
    imports: List[Tuple[str, str]]  # (importer, imported)
```

---

## 5. Data Formats

### Architecture Model (YAML)

```yaml
version: "1.0"
metadata:
  name: string
  description: string
  generated_at: ISO-8601 datetime
components:
  - id: string          # e.g. "COMP-1"
    name: string
    layer: string       # foundation | domain | application | interface | infrastructure
    description: string
    files: [string]
    children: [string]  # child component IDs
interfaces:
  - id: string
    name: string
    protocol: string
    provider: string    # component ID
    consumer: string    # component ID
relationships:
  - source: string      # component ID
    target: string      # component ID
    type: string        # exposes | consumes | depends_on | contains
behaviors:
  - id: string
    name: string
    trigger: string
    steps: [string]
```

### Validation Report (JSON)

```json
{
  "valid": false,
  "errors": [
    {"rule": "referential_integrity", "message": "...", "location": "..."}
  ],
  "warnings": [...]
}
```

### Pipeline Report (JSON)

```json
{
  "stages_executed": ["observe", "infer", ...],
  "total_duration_ms": 12345,
  "stage_results": [
    {"stage": "observe", "duration_ms": 200, "errors": [], "artifacts_produced": [...]}
  ],
  "final_model_path": "output/model.yaml"
}
```

### Scan Result (internal)

```json
{
  "modules": [{"path": "...", "language": "python", "loc": 150}],
  "classes": [{"name": "...", "module": "...", "methods": [...]}],
  "functions": [{"name": "...", "module": "...", "signature": "..."}],
  "imports": [{"source": "...", "target": "...", "kind": "absolute|relative"}]
}
```

---

## 6. Interface Dependencies

| Interface | External Dependency | Nature |
|---|---|---|
| IF-auto-COMP-9 | File system | YAML config files read from disk |
| IF-auto-COMP-1.3 | File system | Model YAML persistence |
| IF-auto-COMP-3.1 | File system | Source code files for scanning |
| IF-auto-COMP-6 | File system | Source code and artifact files |
| IF-1, IF-2 | stdin/stdout/stderr | OS process I/O |
| IF-auto-COMP-11 | File system | Learning store (JSON/YAML on disk) |
| COMP-4.1, COMP-4.2 | File system | Generated documentation output |

**No external network dependencies** are documented. All interfaces operate locally against the file system and in-process Python calls.

---

*Document generated from architecture model interface definitions. All signatures are representative of the public API contracts between identified components.*