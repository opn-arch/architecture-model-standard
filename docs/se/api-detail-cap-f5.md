# API Detail — CAP-F5: Configuration & Schema

## Overview

CAP-F5 provides the self-bootstrapping configuration system and the formal JSON Schema that defines what a valid architecture model looks like. Realized by two components:

- **COMP-CONFIG** (`config/loader.py`, `config/schema.py`) — loads, discovers, and writes project configuration
- **COMP-SPEC** (`spec/schema.json`) — JSON Schema v1.4 definition (Draft 2020-12)

---

## Configuration API — `architecture_model.config.loader`

### `get_config(root: Path) -> ProjectConfig`

**The recommended entry point.** Always returns a valid config — loads from file if `.architecture-model.yaml` exists, otherwise auto-discovers.

Additionally: for blocks loaded from YAML that don't define `sub_blocks`, auto-discovers sub-blocks from their directory structure.

---

### `load_config(root: Path) -> ProjectConfig`

Loads configuration strictly from `.architecture-model.yaml`.

**Raises:** `FileNotFoundError` if no config file exists.

**Parsing:** YAML → dict → `ProjectConfig.from_dict(data, root=root)`

---

### `discover_config(root: Path) -> ProjectConfig`

Auto-discovers project configuration by scanning the filesystem. No config file needed.

**Algorithm:**

1. Infer project name from directory name
2. **Discover layers** — scan for common directory patterns:
   - `web-layer`: `app/routers`, `app/views`, `app/api`, `src/api`
   - `services-layer`: `app/services`, `src/services`
   - `data-layer`: `app/models`, `src/models`, `alembic`
   - `pipeline-layer`: `scripts`, `pipeline`
   - `scheduling-layer`: `app/tasks`, `tasks/`
3. **Discover metrics** — look for countable directories (routers, models, migrations, templates)
4. **Discover functional blocks** — each subpackage becomes an F-block:
   - Find source root (src-layout → flat-layout → lib-layout)
   - Each immediate subdirectory with `.py` files → one F-block
   - Names from directory name; descriptions from `__init__.py` docstrings
   - Recursively discover sub-blocks (up to 3 levels deep)
5. If no layers found heuristically, derive from F-block directories

---

### `write_config(config: ProjectConfig, root: Path | None = None) -> Path`

Serializes `ProjectConfig` to `.architecture-model.yaml` with an auto-generation header comment.

---

## Source Root Discovery — `_find_source_root(root: Path) -> Path | None`

Checks three common Python package layouts:

| Layout | Pattern | Example |
|--------|---------|---------|
| src-layout | `src/<package>/__init__.py` with subdirectories | `src/architecture_model/` |
| flat-layout | `<package>/__init__.py` at root (excluding tests, docs, etc.) | `mypackage/` |
| lib-layout | `lib/<package>/__init__.py` | `lib/mylib/` |

Returns the deepest package directory that has code subdirectories, or `None` if no clear structure.

---

## Configuration Schema — `architecture_model.config.schema`

### `ProjectConfig` (root dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Project name |
| `system` | `str` | System identifier |
| `output` | `OutputConfig` | Output path templates |
| `layers` | `list[LayerConfig]` | Architecture layers with directories |
| `functional_blocks` | `list[FunctionalBlockConfig]` | F-blocks with files/dirs |
| `metrics` | `list[MetricConfig]` | Countable metrics |
| `root` | `Path` | Project root (runtime, not serialized) |

**Computed properties:**
- `layer_dir_map` — `{layer_id: [dirs]}` for merger
- `fblock_dir_map` — `{dir_or_file_prefix: f_block_id}` for merger heuristics
- `fblock_dict` — legacy dict format for backward compatibility
- `metrics_paths` — `{label: resolved_path}`
- `resolved_output()` — resolves `{project}` template in output paths

**Serialization:** `from_dict(data, root)` / `to_dict()` for YAML round-tripping.

---

### `OutputConfig`

| Field | Default | Description |
|-------|---------|-------------|
| `model` | `output/{project}/architecture-model.yaml` | Where to write generated models |
| `manifest` | `output/{project}/reality-manifest.json` | Where to write manifests |
| `artifacts` | `output/{project}/artifacts/stage2` | Where to write SE artifacts |

---

### `LayerConfig`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Layer identifier (e.g., `web-layer`) |
| `dirs` | `list[str]` | Source directories belonging to this layer |
| `description` | `str` | Optional human description |

---

### `FunctionalBlockConfig`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Block ID (e.g., `F1`, `F2`) |
| `name` | `str` | Human name (e.g., "Core") |
| `dirs` | `list[str]` | Directories containing this block's code |
| `files` | `list[str]` | Specific files in this block |
| `description_source` | `str` | Where the description came from (docstring or auto) |
| `sub_blocks` | `list[SubBlockConfig]` | Nested sub-blocks (recursive) |

---

### `SubBlockConfig` (recursive)

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Sub-block ID (e.g., `F1.A`, `F1.B`, `F1.A.1`) |
| `name` | `str` | Name (from directory or `__init__.py` docstring) |
| `dirs` | `list[str]` | Directories |
| `files` | `list[str]` | Files |
| `description` | `str` | Description |
| `sub_blocks` | `list[SubBlockConfig]` | Deeper nesting |

ID scheme: `F{n}.{A-Z}` at depth 0, `F{n}.{A}.{1-N}` at depth 1+.

---

### `MetricConfig`

| Field | Type | Description |
|-------|------|-------------|
| `label` | `str` | Metric name (e.g., "router", "model", "migration") |
| `path` | `str` | Directory to count in |
| `pattern` | `str` | Glob pattern (default `*.py`) |
| `exclude` | `list[str]` | Filenames to exclude |
| `recursive` | `bool` | Whether to count recursively |

---

## JSON Schema — `spec/schema.json`

**Version:** 1.4.0  
**Standard:** JSON Schema Draft 2020-12  
**URI:** `https://architecture-model-standard.dev/schema/v1.4.0/model.json`

### Required Top-Level Keys

```json
{
  "meta": { ... },         // required
  "entities": { ... },     // required
  "relationships": [ ... ] // required
}
```

### Meta (required fields)

| Field | Type | Constraint |
|-------|------|------------|
| `schema_version` | string | Pattern: `^\d+\.\d+\.\d+$` |
| `project` | string | Non-empty |
| `generated_at` | string | ISO 8601 date-time format |

### Entity Types (8)

| Type | Key in `entities` | Description |
|------|-------------------|-------------|
| Actor | `actors` | External agents interacting with the system |
| Capability | `capabilities` | Functional blocks the system provides |
| Behavior | `behaviors` | Use cases, workflows, operational sequences |
| Interface | `interfaces` | APIs, protocols, data exchanges |
| Constraint | `constraints` | Non-functional requirements, design rules |
| Layer | `layers` | Architectural tiers |
| Component | `components` | Deployable units, modules, packages |
| System | `systems` | Complex F-block groups promoted to subsystems |

### Relationship Types (8+)

`realizes`, `uses`, `constrains`, `contains`, `triggers`, `depends_on`, `implements`, `exposes`

Plus extended types: `consumes`, `allocated_to`, `constrained_by`, `traces_to`

### v1.4 Additions (on Component)

| Field | Type | Purpose |
|-------|------|---------|
| `constants` | `[{name, value, context}]` | Module/class constants with values |
| `signatures` | `[{name, params, returns, decorators, body_hint}]` | Function signatures with implementation hints |
| `test_contracts` | `[{test_file, test_method, assertion, contract_type}]` | Test-derived behavioral contracts |

These three fields enable **blind code regeneration** — enough detail in the model to recreate source code that passes all tests without reading the original source.

---

## How Config Enables the Pipeline

```
architecture-model init
        │
        ▼
discover_config(root)
        │
        ├── _find_source_root() → src/mypackage/
        ├── _get_code_subdirectories() → [core/, manifest/, cli/, config/, spec/]
        ├── _discover_functional_blocks() → [F1, F2, F3, F4, F5]
        ├── _discover_layers() → [web-layer, services-layer, ...]
        └── _discover_metrics() → [router: 5, model: 12, ...]
        │
        ▼
write_config() → .architecture-model.yaml
        │
        ▼
get_config() → ProjectConfig (used by manifest, merger, CLI)
```

Zero manual setup required. Point `architecture-model init` at any Python project and it produces a working config.
