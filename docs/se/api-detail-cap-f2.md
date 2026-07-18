# API Detail — CAP-F2: Reality Manifest Generation

## IF-MANIFEST-API — `architecture_model.manifest.generator`

### `generate_manifest(project_root: Path, config: Optional[Any] = None) -> dict[str, Any]`

The primary entry point for reality manifest generation. Performs a full AST scan of the project and returns a JSON-serializable inventory of the codebase.

**Algorithm:**

1. Resolve `project_root` to absolute path
2. Load config from `.architecture-model.yaml` if not provided
3. Compute project-level metrics (file counts, LOC, function counts)
4. For each functional block defined in config:
   - Collect all `.py` files in the block's directory
   - AST-parse each file for functions, classes, imports, constants
   - Group results as sub-functions within the block
5. Scan additional directories from config layers (web, services, data) for uncovered files
6. Build full module list by AST-parsing each scanned file
7. Derive interfaces from collected module data (public APIs, exported symbols)
8. Assemble and return the manifest dict

**Return structure:**

| Key | Type | Description |
|-----|------|-------------|
| `generated_at` | `str` | ISO timestamp of generation |
| `project_root` | `str` | Absolute path to scanned project |
| `metrics` | `dict` | Aggregate code metrics (file_count, function_count, LOC) |
| `functional_blocks` | `dict[str, dict]` | Keyed by block ID; each contains `name`, `sub_functions` (files with AST metadata) |
| `modules` | `list[dict]` | Per-file metadata (see scanner output below) |
| `interfaces` | `list[dict]` | Derived public interfaces |

---

### `load_or_generate_manifest(project_root: Path, output_dir: Path | None = None) -> dict[str, Any]`

Cached wrapper around `generate_manifest`. Checks for a fresh manifest on disk (< 1 hour old) and returns it if available; otherwise regenerates.

**Behavior:**

1. Resolve manifest path from config output paths (or `output_dir / reality-manifest.json`)
2. If manifest file exists and is < 3600 seconds old, load and return it
3. Otherwise call `generate_manifest()`, write result to disk as JSON, return it

Used by the MCP server to avoid redundant scans on repeated calls.

---

## Supporting Modules

### Scanner — `architecture_model.manifest.scanner`

The AST engine behind manifest generation. `_scan_file(root, filepath)` returns per-file metadata:

| Field | Type | Description |
|-------|------|-------------|
| `file` | `str` | Relative path from project root |
| `name` | `str` | Human-readable name (from docstring or filename) |
| `docstring` | `str | None` | Module-level docstring |
| `functions` | `list[str]` | Public function signatures (formatted strings) |
| `imports` | `list[str]` | Imported module names |
| `line_count` | `int` | Total lines in file |
| `status` | `str` | `"active"` (>50 LOC), `"dormant"` (<=50), or `"missing"` |
| `classes` | `list[dict]` | Class definitions with `name`, `bases`, `methods`, `is_abstract`, `decorators`, `attributes` |
| `exports` | `list[str]` | Public API symbols (from `__all__` or relative imports in `__init__.py`) |
| `decorated_functions` | `list[dict]` | Functions with non-trivial decorators (name, decorators, is_method, class_name) |
| `imports_detailed` | `list[dict]` | Imports with symbol-level detail (module, symbols, is_relative) |
| `module_constants` | `dict[str, str]` | `UPPER_CASE` module-level constants mapped to `repr(value)` |
| `module_assignments` | `dict[str, str]` | Non-constant module-level assignments (e.g., `Fore = AnsiFore()`) mapped to `ast.unparse(value)` |

### Key Scanner Functions

| Function | Purpose |
|----------|---------|
| `_collect_py_files(root, dir)` | Recursively find all `.py` files, excluding `__pycache__` |
| `_parse_file_ast(filepath)` | Parse a Python file into AST; returns `None` on failure |
| `_extract_public_functions(tree)` | Extract public function signatures (skips `_`-prefixed) |
| `_extract_classes(tree)` | Extract classes with bases, methods, abstract status, attributes |
| `_extract_module_constants(tree)` | Find `UPPER_CASE = literal` assignments |
| `_extract_module_assignments(tree)` | Find non-constant `name = expr` assignments |
| `_extract_imports_detailed(tree)` | Imports with symbol lists and relative flag |
| `_extract_exports(tree, filepath)` | Public exports from `__init__.py` (`__all__` or re-exports) |
| `_extract_class_attributes(cls_node)` | Class-level `name = literal` assignments |
| `_build_signature(node)` | Format `func(arg: type, ...) -> ret` string |

### Metrics — `architecture_model.manifest.metrics`

`_compute_metrics(root, config)` produces aggregate project metrics used in the manifest's `metrics` field.

### Blocks — `architecture_model.manifest.blocks`

`_process_block(root, block_id, block_def, sub_block_configs)` processes a single functional block:
- Collects files for the block
- AST-scans each file
- Groups into sub-functions (one per file)
- Returns block-level metadata

### Interfaces — `architecture_model.manifest.interfaces`

`_derive_interfaces(all_modules, root)` analyzes the module list to identify public interfaces (exported functions, classes) that form the project's API surface.

---

## BEH-MANIFEST: Manifest Generation (Behavioral View)

**Trigger:** `architecture-model manifest <path> [-o output]`

**Preconditions:**
- Target path must be a valid directory
- A `.architecture-model.yaml` config must exist or be auto-discoverable

**Steps:**

1. Resolve path and verify it is a directory
2. Load configuration via `get_config(root)`
3. Compute project-level metrics
4. For each functional block in configuration:
   - AST-scan all files in the block
   - Extract functions, classes, and imports
5. Scan additional directories from config layers for uncovered files
6. Build full module list by AST-parsing each scanned file for metadata
7. Derive interfaces from collected module data
8. Assemble manifest: `{generated_at, project_root, metrics, functional_blocks, modules, interfaces}`
9. Write manifest as JSON to the output path
10. Print summary (module count, interface count, F-block count, metrics)

**Postconditions:**
- `reality-manifest.json` exists on disk
- Manifest contains full AST-derived inventory
- No source code is modified

---

## What Makes the Manifest Valuable

The manifest is the **ground-truth bridge** between code and architecture. It answers: "what actually exists in the codebase right now?" The architecture model says what things *mean*; the manifest says what things *are*.

Key data extracted that enables downstream use:
- **`module_constants`** — exact values of `CSI`, `OSC`, `BEL` etc. (enables code regeneration)
- **`class attributes`** — `BLACK=30, RED=31` (enables faithful recreation)
- **`module_assignments`** — `Fore = AnsiFore()` (module-level instances)
- **`function signatures`** — full param/return type info
- **Body hints** (via separate `body_hints` module) — trivial implementations like `return CSI + str(code) + 'm'`
- **Test contracts** (via `test_analyzer`) — expected behaviors from test assertions
