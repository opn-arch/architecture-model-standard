# CLI Reference

> **Note:** This reference is derived from the architecture model's component structure. Specific argument defaults and option flags are inferred from the system's documented capabilities.

---

## Global Usage

```bash
architecture-model [OPTIONS] COMMAND [ARGS...]
```

### Global Options

| Option | Description |
|--------|-------------|
| `--config PATH` | Path to configuration file |
| `--profile NAME` | Domain profile to use |
| `--output DIR` | Output directory |
| `--format FORMAT` | Output format (yaml, json, markdown) |
| `--verbose` / `-v` | Enable verbose output |
| `--quiet` / `-q` | Suppress non-essential output |

---

## Pipeline Commands

### `pipeline run`

Run the full 10-stage extraction pipeline against a codebase.

```bash
architecture-model pipeline run [OPTIONS] PATH
```

| Option | Description |
|--------|-------------|
| `--stages STAGES` | Comma-separated stages to run (observe,infer,allocate,relate,specify,contract,validate,decompose,synthesize,emit) |
| `--cache / --no-cache` | Enable/disable pipeline caching |
| `--report` | Generate pipeline report |
| `PATH` | Root path of the codebase to analyze |

**Examples:**

```bash
architecture-model pipeline run ./my-project
architecture-model pipeline run --stages observe,infer,allocate ./src
architecture-model pipeline run --no-cache --report ./my-project
```

---

## Scan Commands

### `scan`

Scan source files and produce a manifest of modules, classes, and functions.

```bash
architecture-model scan [OPTIONS] PATH
```

| Option | Description |
|--------|-------------|
| `--language LANG` | Language filter (python, typescript, kotlin) |
| `--recursive / --no-recursive` | Recursive directory scanning |
| `--include-tests` | Include test files in scan |
| `--cache / --no-cache` | Use scan cache |

**Examples:**

```bash
architecture-model scan ./src
architecture-model scan --language typescript --recursive ./frontend
```

---

## Model Commands

### `validate`

Validate an architecture model file.

```bash
architecture-model validate [OPTIONS] MODEL_PATH
```

| Option | Description |
|--------|-------------|
| `--strict` | Enable strict validation (referential integrity, cycles) |
| `--schema PATH` | Custom JSON schema path |

**Examples:**

```bash
architecture-model validate architecture.yaml
architecture-model validate --strict ./models/system.yaml
```

### `diff`

Compare two model versions.

```bash
architecture-model diff [OPTIONS] MODEL_A MODEL_B
```

**Examples:**

```bash
architecture-model diff v1/architecture.yaml v2/architecture.yaml
```

### `slice`

Extract a subset of the model.

```bash
architecture-model slice [OPTIONS] MODEL_PATH
```

| Option | Description |
|--------|-------------|
| `--component NAME` | Slice by component |
| `--layer NAME` | Slice by layer |
| `--interface NAME` | Slice by interface |

**Examples:**

```bash
architecture-model slice --component "COMP-1" architecture.yaml
architecture-model slice --layer domain architecture.yaml
```

### `coverage`

Compute source-to-model coverage metrics.

```bash
architecture-model coverage [OPTIONS] MODEL_PATH PATH
```

**Examples:**

```bash
architecture-model coverage architecture.yaml ./src
```

---

## Documentation Commands

### `docs generate`

Generate architecture documentation suite.

```bash
architecture-model docs generate [OPTIONS] MODEL_PATH
```

| Option | Description |
|--------|-------------|
| `--type TYPE` | Document type (component-spec, icd, dependency-matrix, health, drift, diagrams, index, all) |
| `--output DIR` | Output directory |

**Examples:**

```bash
architecture-model docs generate --type all architecture.yaml
architecture-model docs generate --type icd --output ./docs architecture.yaml
```

### `docs se`

Generate systems engineering document suite.

```bash
architecture-model docs se [OPTIONS] MODEL_PATH
```

| Option | Description |
|--------|-------------|
| `--doc TYPE` | SE document type (conops, functional-analysis, logical-architecture, requirements, use-cases, verification, all) |
| `--output DIR` | Output directory |

**Examples:**

```bash
architecture-model docs se --doc all architecture.yaml
architecture-model docs se --doc conops --output ./se-docs architecture.yaml
```

---

## Enrichment Commands

### `enrich`

Auto-enrich a model with signatures, test contracts, and capabilities.

```bash
architecture-model enrich [OPTIONS] MODEL_PATH PATH
```

| Option | Description |
|--------|-------------|
| `--signatures` | Enrich with function signatures |
| `--contracts` | Enrich with test contracts |
| `--capabilities` | Infer capabilities |
| `--all` | Apply all enrichments |

**Examples:**

```bash
architecture-model enrich --all architecture.yaml ./src
architecture-model enrich --signatures --contracts architecture.yaml ./src
```

---

## Decomposition Commands

### `decompose`

Decompose a model into finer-grained components.

```bash
architecture-model decompose [OPTIONS] MODEL_PATH
```

| Option | Description |
|--------|-------------|
| `--depth INT` | Decomposition depth (default: 1) |
| `--component NAME` | Target specific component |

**Examples:**

```bash
architecture-model decompose --depth 2 architecture.yaml
architecture-model decompose --component "COMP-1" architecture.yaml
```

---

## Extract Commands

### `extract`

Extract architecture model from code artifacts.

```bash
architecture-model extract [OPTIONS] PATH
```

| Option | Description |
|--------|-------------|
| `--from-code` | Extract from source code |
| `--from-artifacts` | Extract from existing artifacts (README, configs) |
| `--routes` | Detect API routes |
| `--constraints` | Detect constraints |

**Examples:**

```bash
architecture-model extract --from-code ./src
architecture-model extract --from-artifacts --routes ./my-project
```

---

## Authoring Commands

### `author`

Forward-author a model from requirements.

```bash
architecture-model author [OPTIONS] REQUIREMENTS_PATH
```

**Examples:**

```bash
architecture-model author requirements.md
```

### `gate`

Check development gate readiness.

```bash
architecture-model gate [OPTIONS] MODEL_PATH
```

**Examples:**

```bash
architecture-model gate architecture.yaml
```

---

## Export Commands

### `export`

Export model in flat-file format for AI consumption.

```bash
architecture-model export [OPTIONS] MODEL_PATH
```

| Option | Description |
|--------|-------------|
| `--format FORMAT` | Export format (flatfiles, reference) |
| `--output DIR` | Output directory |

**Examples:**

```bash
architecture-model export --format flatfiles --output ./export architecture.yaml
architecture-model export --format reference architecture.yaml
```

---

## Visualize Commands

### `visualize`

Generate visual diagrams from the model.

```bash
architecture-model visualize [OPTIONS] MODEL_PATH
```

| Option | Description |
|--------|-------------|
| `--type TYPE` | Diagram type (component, dependency, layer, flow) |
| `--output PATH` | Output file path |

**Examples:**

```bash
architecture-model visualize --type component architecture.yaml
architecture-model visualize --type dependency --output deps.md architecture.yaml
```

---

## Configuration Commands

### `config init`

Initialize a configuration file.

```bash
architecture-model config init [OPTIONS]
```

**Examples:**

```bash
architecture-model config init
architecture-model config init --profile microservices
```

### `config show`

Display current configuration.

```bash
architecture-model config show
```

---

## Learning Commands

### `learning show`

Display pipeline learning store and heuristics.

```bash
architecture-model learning show [OPTIONS]
```

### `learning reset`

Reset the global learning store.

```bash
architecture-model learning reset
```