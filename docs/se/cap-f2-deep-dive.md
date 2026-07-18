# CAP-F2: Reality Manifest Generation — Deep Dive

## Modularity Principles

This module — and every module in the architecture-model-standard — should embody the principles the standard prescribes for target systems:

1. **Typed I/O** — every function accepts and returns typed dataclasses, not raw dicts
2. **Success metrics** — every function knows what "success" looks like and logs it (files scanned, parse rate, extraction counts)
3. **Logging** — Python `logging` at every boundary: function entry, significant decisions, errors, completion
4. **Improvement criteria** — each sub-block defines what "better" means (higher parse rate, fewer unclaimed files, richer body hints)
5. **Functional decomposition** — large modules are broken into sub-blocks with clear interfaces between them
6. **Self-reference** — this repo models itself using its own standard (eats its own dogfood)

These principles apply in two directions:
- **Inward** — this repo's own code demonstrates these properties
- **Outward** — projects modeled using this standard inherit these properties

---

## What It Is

The Reality Manifest Generator is the **ground-truth extraction engine** of the architecture-model-standard. It performs AST scanning on Python source code and produces a structured JSON inventory describing everything the project actually contains — functions, classes, imports, constants, interfaces, metrics, and functional blocks.

---

## Module Architecture (`src/architecture_model/manifest/`)

> **COMMENT:** these would be the sub-blocks - this function should have been further decomposed. log each of these for their success

**RESPONSE:** Agreed. Each module below should be a proper sub-block (F2.1 through F2.9) with its own success criteria and telemetry. Proposed decomposition:
- **F2.1** `generator.py` — Orchestration success: manifest produced without errors, all blocks processed
- **F2.2** `scanner.py` — Parse success rate: files parsed / files attempted, functions extracted, classes extracted
- **F2.3** `blocks.py` — Block coverage: files claimed / total files, unclaimed file count
- **F2.4** `interfaces.py` — Interface count, internal vs external import ratio
- **F2.5** `metrics.py` — Metrics computed count, zero-value metric warnings
- **F2.6** `body_hints.py` — Hint coverage: trivial/short/complex distribution, unhintable function count
- **F2.7** `test_analyzer.py` — Contracts extracted count, contract type distribution
- **F2.8** `slicers.py` — Slice generation success per artifact type
- **F2.9** `display.py` — N/A (presentation only)

Currently none of these log success metrics. This is an observability gap that should be addressed.

| Module | Role |
|--------|------|
| `generator.py` | Orchestrator — coordinates all sub-scanners |
| `scanner.py` | AST engine — extracts functions, classes, imports, constants per file |
| `blocks.py` | Maps config-defined F-blocks to scanned file metadata |
| `interfaces.py` | Derives inter-module dependencies from the import graph |
| `metrics.py` | Counts files matching configurable glob patterns |
| `body_hints.py` | Classifies function complexity and produces implementation summaries |
| `test_analyzer.py` | Extracts behavioral contracts from test files |
| `slicers.py` | Produces focused markdown extracts for 10 documentation artifact types |
| `display.py` | Terminal display — prints human-readable manifest summaries |

---

## Data Flow

```
Source Code → [AST Scan] → Per-file metadata → [Block Processor] → F-block groupings
                                              → [Interface Deriver] → Import graph
                                              → [Metrics] → File counts
                                              → JSON manifest (reality-manifest.json)
```

The entry point is `generate_manifest(project_root)` which:

1. Resolves `project_root` to absolute path

2. Loads config from `.architecture-model.yaml` (or auto-generates via `init`)

   > **COMMENT:** whats this relationship - hope not circular

   **RESPONSE:** Not circular. The relationship is one-directional and two-phase:
   - **Phase 1 (one-time):** `architecture-model init` scans directory structure heuristically (no AST) → writes `.architecture-model.yaml`
   - **Phase 2 (repeated):** `generate_manifest()` reads that config as static input → produces manifest
   
   The manifest generator never writes back to the config. `init` and `generate_manifest` are separate commands with no mutual dependency.

3. Computes project-level metrics via glob patterns

4. For each F-block defined in config:

   > **COMMENT:** from .architecture-model.yaml?

   **RESPONSE:** Yes, F-block definitions come exclusively from `.architecture-model.yaml`. The config's `functional_blocks` section lists block IDs, names, and their associated directories/files. See the "Functional Block Discovery" section below for the full explanation of why this is config-driven rather than AST-discovered.

   - Collects all `.py` files in the block's directory

     > **COMMENT:** create a catalog?

     **RESPONSE:** The manifest effectively IS a catalog — every scanned file appears in the `modules` list with full metadata. However, there's no explicit "file catalog" artifact that lists all project files with their claim status (which block owns them, or unclaimed). Adding a catalog view showing file → block mapping and orphan files would be useful for completeness auditing.

   - AST-parses each file for functions, classes, imports, constants

     > **COMMENT:** look for unused files, missed files / someother format, we want to resolve all files

     **RESPONSE:** Current gaps:
     1. **Non-Python files** are completely ignored — `.yaml`, `.json`, `.sql`, `.toml`, `.md`, `.html`, etc. are invisible to the manifest
     2. **Unused Python files** (files that exist but are never imported by anything) are not flagged
     3. **Missing files** (referenced in imports but not found) are not reported
     
     The manifest should resolve ALL files in the project tree, not just `.py` files. Non-Python files could at minimum be cataloged by type/location even without AST parsing. Unused file detection would require cross-referencing the import graph with the file list.

   - Derives inputs/outputs from function signatures via regex

     > **COMMENT:** how does this improve success criteria LOG

     **RESPONSE:** Currently it doesn't log or measure anything. The derived inputs/outputs are used downstream by the context formatter to summarize function behavior, but there's no feedback loop measuring:
     - How many functions had parseable signatures vs unparseable
     - Whether derived I/O actually matched runtime behavior
     - Coverage rate (functions with I/O derived / total functions)
     
     This should emit metrics to the telemetry layer.

5. Scans additional directories from config layers for uncovered files

   > **COMMENT:** how?

   **RESPONSE:** The config's `layers` section can list directories not already covered by F-blocks (e.g., `scripts/`, `migrations/`, `tests/`). The generator iterates these, calls `_collect_py_files()` on each directory (same recursive `.py` glob used for F-blocks), then runs `_scan_file()` on each. The results go into the `modules` list but are NOT grouped into any F-block — they're just additional scanned files. Same scanner, no special logic, just broader coverage.

6. Derives interfaces from the internal import graph

   > **COMMENT:** python compatible only?

   **RESPONSE:** **Yes, Python only.** The interface detection relies on Python's `ast` module to parse imports, and maps them to Python module paths. Zero support for:
   - JavaScript/TypeScript (`import`/`require`)
   - Go (`import`)
   - Rust (`use`)
   - Java (`import`)
   - Any non-Python dependency graph
   
   Supporting other languages would require either tree-sitter (multi-language AST parser) or language-specific import resolvers. This is a hard architectural constraint that should be logged as CONSTRAINT in the model.

7. Returns the manifest dict: `{metrics, functional_blocks, modules, interfaces}`

   > **COMMENT:** seems unnecessary to have one manifest - sub-systems should have their own; this way a lot of context can be saved, opportunities to make code more modular with clear interfaces will arise

   **RESPONSE:** Strong point. A single monolithic manifest has several problems:
   - **Context waste:** loading the full manifest when you only need one subsystem
   - **No interface pressure:** subsystems don't need to declare clean boundaries
   - **Scaling:** large projects produce massive manifests that are expensive to parse/transmit
   
   Per-subsystem manifests would:
   - Force each F-block to define its own inputs/outputs/interfaces explicitly
   - Enable incremental regeneration (only re-scan changed subsystems)
   - Save LLM context (load only the relevant subsystem manifest)
   - Naturally produce the modular architecture you're describing
   
   The `slice_by_fblock` slicer partially addresses this at the model level, but not at the manifest level. A proper implementation would produce `reality-manifest-F1.json`, `reality-manifest-F2.json`, etc., each self-contained with their own interfaces section showing cross-block dependencies.

---

## AST Scanning Techniques

Uses **only Python's built-in `ast` module** — no third-party dependencies. Per file, `_scan_file` extracts:

> **COMMENT:** what about other languages, 0 support? LOG, success criteria

**RESPONSE:** Correct — zero support for non-Python languages. The entire scanning pipeline is Python-`ast`-specific. This means:
- **TypeScript/JS projects:** cannot be scanned at all
- **Polyglot projects:** only the Python portions are visible
- **Success criteria that should be logged:**
  - Total files in project vs files scannable (Python) vs files actually scanned
  - Parse failure rate (syntax errors, encoding issues)
  - Coverage ratio: scanned LOC / total project LOC
- **To support other languages**, the scanner would need a pluggable backend (e.g., tree-sitter for universal AST, or language-specific parsers registered by file extension)

### Functions (`_extract_public_functions`)

- Iterates top-level `FunctionDef` / `AsyncFunctionDef` nodes
- Skips private functions (names starting with `_`)
- Builds full signature strings including parameter annotations and return types via `_build_signature`

  > **COMMENT:** why signatures

  **RESPONSE:** Signatures serve three critical downstream purposes:
  1. **Code regeneration:** the signature is the function's contract — name, parameter types, return type. Without it, an LLM regenerating code wouldn't know the function's API surface
  2. **Input/output derivation:** the block processor extracts inputs (parameter names/types) and outputs (return type) from the signature string to summarize what each function consumes and produces
  3. **Interface documentation:** signatures appear in the `functional-architecture` and `icd` slices, giving readers the API at a glance without reading source
  
  The signature is the minimum viable representation of "what this function does structurally." Body hints add "how," but the signature is the "what."

### Classes (`_extract_classes`)

- Extracts: name, base classes, public methods (+ `__init__`), decorators, class-level attributes
- Detects abstract classes via `@abstractmethod`, `ABC`/`Protocol` bases, or `Base`/`Abstract`/`I` name prefixes

### Imports (two levels)

- `_extract_imports` — simple list of imported module names
- `_extract_imports_detailed` — full detail: module, symbols, `is_relative` flag

### Constants and Assignments

- `_extract_module_constants` — `UPPER_CASE` names assigned to literals (`str`/`int`/`float`/`bool`/`bytes`)
- `_extract_module_assignments` — non-constant, non-private module-level assignments (instance creation, calls)
- `_extract_class_attributes` — class-level literal assignments (e.g., `BLACK = 30`)

### Exports

- From `__init__.py`: parses `__all__` list, or falls back to relative import symbols

### Decorated Functions

- Extracts non-trivial decorators (excludes `@property`, `@staticmethod`, etc.) from both module-level and class methods

---

## Body Hints — The Key to Lossless Representation

This is the critical enrichment that enables blind code regeneration at 100% fidelity:

| Complexity | Criteria | Output |
|-----------|----------|--------|
| TRIVIAL | 1 statement after docstring | Exact `ast.unparse()` of the single statement |
| SHORT | 2–5 statements | Semicolon-joined `ast.unparse()` of all statements |
| COMPLEX | 6+ statements | Structural summary: loops, conditionals, assignments |

> **COMMENT:** what does it mean? this looks like the place where we want to dig deeper; like the recursive method, where we generate its own manifest?

**RESPONSE:** For COMPLEX functions (6+ statements), the body hint is a lossy structural skeleton. Example for a 20-line function:

```
for item in items: ...; if item.valid: ...; result = process(item); return result
```

This tells you the shape (loop → conditional → process → return) but not the actual logic. You're right that this is the weak point — COMPLEX functions are where regeneration fidelity drops.

The recursive manifest idea is compelling: treat a COMPLEX function like a subsystem. Decompose it into:
- Its own "sub-manifest" with internal variables as "components"
- Control flow as "behaviors"
- Called functions as "interfaces"

This would be a form of **hierarchical body hints** — if a function is too complex for a flat hint, recursively decompose it until each piece is TRIVIAL or SHORT. This directly parallels the sub-block decomposition idea at the function level.

Currently this is NOT implemented. The 6-statement threshold is a hard cutoff, and everything above it gets the same lossy treatment regardless of whether it's 7 lines or 200 lines.

`extract_file_hints(filepath)` scans an entire file and produces `FunctionSignature` objects (from `core.types`) containing: name, params, returns, decorators, and `body_hint`.

---

## Test Contract Analysis

Extracts behavioral specifications from test files:

> **COMMENT:** LOG, success criteria / metrics

**RESPONSE:** Currently no logging or metrics on contract extraction. Should track:
- **Contracts extracted per file** — are test files yielding useful contracts or being missed?
- **Contract type distribution** — is the analyzer finding mostly `value_equality` and missing `raises`? Pattern coverage matters
- **Unparseable assertions** — how many test assertions couldn't be classified into any contract type? This is the "dark matter" of test analysis
- **Contract-to-function ratio** — are the extracted contracts actually covering the functions in the manifest? Low ratio = the test analyzer is missing important behavioral specs
- **Success criteria:** >80% of test assertions should map to a known contract type; <5% unparseable rate

| Contract Type | Source Pattern |
|---------------|---------------|
| `value_equality` | `assertEqual(a, b)` or `assert a == b` |
| `state_change` | `assertTrue(expr)` / `assertFalse(expr)` |
| `type_check` | `assertIsInstance(obj, Type)` / `assert isinstance(...)` |
| `raises` | `assertRaises(E)` / `pytest.raises(E)` (inline and context-manager) |

**Constant derivation:** Parses `value_equality` contracts for patterns like `Fore.BLACK == '\033[30m'` and derives `Constant(name="BLACK", value="30", context="...")`.

---

## Metrics Collection

> **COMMENT:** what? why?

**RESPONSE:** Metrics exist to provide a quick quantitative snapshot of the project without reading the full manifest. They answer: "how big is this project and what does it contain?" Examples: `total_python_files: 150`, `router_count: 30`, `model_count: 12`.

**Why they matter:**
- **Sanity check:** if `total_python_files` drops between runs, something was deleted or the scan broke
- **Progress tracking:** metrics in the `readme` and `requirements-analysis` slices give stakeholders a dashboard
- **Validation input:** the validator can check claims like "this system has 30 API endpoints" against `router_count`

**Why they're debatable:** they're just glob counts — trivial to compute on the fly. Having a dedicated module for this may be over-engineering. They could arguably be a function inside the generator rather than a separate module.

Driven by `.architecture-model.yaml` config. Each metric specifies:

- `path` — directory to scan
- `pattern` — glob pattern
- `recursive` — whether to rglob
- `exclude` — filenames to skip
- `label` — output key name

Always appends `total_python_files` (excludes `__pycache__`, `venv`, `.venv`, `node_modules`).

---

## Functional Block Discovery

F-blocks are **not** auto-discovered from code — they come from the `.architecture-model.yaml` config (or from `architecture-model init` which generates that config). Processing:

> **COMMENT:** i thought they are discovered from ast scan

**RESPONSE:** Two-phase process, easy to confuse:
1. **Discovery (one-time, `init` command):** scans directory structure heuristically — each top-level package becomes an F-block. This is structural discovery (directory names), NOT AST-based. No function/class analysis happens here.
2. **Population (repeated, `generate_manifest`):** takes the already-defined F-blocks from config and fills them with AST-scanned content (functions, classes, imports).

So F-blocks are discovered from directory structure (not AST), then populated via AST. The `init` command could theoretically use AST to make smarter grouping decisions (e.g., cluster files by import affinity), but currently it doesn't.

1. For each block: collect files from its `dirs` and explicit `files` lists
2. Scan each file with `_scan_file`
3. Derive inputs (first 3 params per function) and outputs (return types) via regex on signatures

   > **COMMENT:** LOG

   **RESPONSE:** Agreed — this derivation is silent. Should log: how many functions had extractable I/O, how many had no type annotations (unparseable returns), and the coverage rate per block.

4. If config provides `sub_block_configs`, build a hierarchical manifest with `_build_sub_block_manifest` — files are claimed by matching filename or directory prefix
5. Unclaimed files go into an "Ungrouped" sub-block

> **COMMENT:** looking at the docs/se we are not doing proper functional decomposition. its such an important truth anchor, catalog, context saver, and extremely important architecturally

**RESPONSE:** This is a key observation. Looking at the current `docs/se/` structure, CAP-F2 is treated as a single capability with no sub-decomposition. But the manifest generator has 9 distinct modules doing very different things. Proper functional decomposition would:
- Make each sub-block independently testable and measurable
- Serve as a truth anchor (does each sub-block's output match expectations?)
- Save context (an agent working on scanner bugs only needs F2.2, not all of F2)
- Reveal architectural issues (are sub-blocks properly decoupled? does `blocks.py` depend on `scanner.py` internals?)

This applies recursively to the entire project — every capability in `docs/se/capability-map.md` should be decomposed to this level.

---

## Interface Detection

Import-graph analysis:

> **COMMENT:** where? ast? LOG

**RESPONSE:** Yes, via AST. The `_extract_imports_detailed()` function in `scanner.py` uses `ast.Import` and `ast.ImportFrom` nodes to collect all import statements per file. Then `_derive_interfaces()` in `interfaces.py` cross-references these against the scanned module list to find internal dependencies. No logging currently — should log: total imports found, internal vs external ratio, unresolved imports.

1. Map each scanned file path to a Python module name (`app/routers/logs.py` → `app.routers.logs`)

   > **COMMENT:** LOG, good diagram opportunity. the idea of minimal (not redundant) representation of info in manifest — architectural

   **RESPONSE:** The file-to-module mapping is a natural place to generate a dependency diagram. Each node = a module, each edge = an import. This would be the minimal, non-redundant representation of the project's structure — far more useful than listing every function in every file. Could be output as a Mermaid or DOT graph alongside the manifest.

2. For each file's imports, check if the import target matches another internal module (exact or prefix match)

3. Produce deduplicated `{source, target, import_path}` triples

   > **COMMENT:** explain

   **RESPONSE:** A triple `{source: "a/b.py", target: "c/d.py", import_path: "c.d"}` means:
   - **source:** the file that contains the import statement
   - **target:** the file that provides the imported module
   - **import_path:** the Python dotted path used in the `import` statement (e.g., `from c.d import something`)
   
   Deduplicated means: if `a/b.py` imports `c.d` in three different places, only one triple is produced. This gives a clean dependency graph without noise from repeated imports.

---

## External Tool Interfaces

### 1. CLI — `architecture-model manifest`

Direct invocation via the CLI command in `cli/main.py`:

```bash
architecture-model manifest [--output path]
```

Calls `generate_manifest(root)` and writes JSON. Also used by `_cmd_coverage` which generates a manifest on-the-fly for model-vs-reality comparison.

### 2. MCP Server (opencode-arch) — `architect_scan` tool

The `opencode-arch` MCP server wraps this as the `architect_scan` tool:

```python
# In opencode-arch MCP server
manifest = generate_manifest(project_root)
return manifest  # returned to the LLM agent
```

The LLM agent invokes `architect_scan` to get raw reality data before producing an architecture model.

### 3. MCP Server — `architect_slice` tool

Uses `get_manifest_slice(manifest, artifact_name)` to produce focused markdown extracts. Supports 10 artifact types:

| Artifact | Content |
|----------|---------|
| `functional-architecture` | F-blocks + metrics with hierarchical sub-block trees |
| `logical-architecture` | Modules grouped by layer |
| `data-dictionary` | Model files + schemas |
| `icd` | Routers, external services, cross-layer imports, pipeline stages, DB models |
| `readme` | Summary metrics + block overview |
| `testing` | Test files + F-block coverage mapping |
| `deployment-guide` | Migration count + infrastructure file existence checks |
| `operations-manual` | CLI commands + router endpoints |
| `use-cases` | F-blocks + API/CLI capabilities + scheduled jobs |
| `requirements-analysis` | Full metrics + capability inventory + test coverage |

### 4. Caching — `load_or_generate_manifest`

> **COMMENT:** must be some smarter way

**RESPONSE:** The 1-hour TTL is crude. Smarter alternatives:
- **Git-based:** regenerate only if `git rev-parse HEAD` changed since last manifest
- **File-hash-based:** hash all `.py` file mtimes; regenerate only if hash changed
- **Per-file incremental:** track mtime per file, only re-scan changed files, merge into existing manifest
- **Event-driven:** use filesystem watchers (fswatch/inotify) to trigger re-scan on save

Git-based is the simplest improvement — one `git` call vs re-scanning the entire project.

Checks if `reality-manifest.json` exists and is < 1 hour old. Fresh → load from disk. Stale → regenerate. Prevents redundant AST scans during repeated MCP calls.

> **COMMENT:** LOG

**RESPONSE:** Should log: cache hit/miss, manifest age, regeneration time, file count delta from previous manifest.

### 5. Validation Engine

> **COMMENT:** different F, CAP-F1?

**RESPONSE:** Correct — validation is **CAP-F1** (Model Validation), not part of CAP-F2. The manifest is an *input* to CAP-F1. The relationship is: CAP-F2 produces the ground truth (manifest), CAP-F1 checks architectural claims (model) against that ground truth. This cross-reference should be explicit in both capability documents.

The manifest serves as ground truth that `validate_model()` checks architectural claims against — e.g., "does component COMP-1 actually exist in the scanned code?"

### 6. Context Formatter

> **COMMENT:** LOG. whats the exact interface

**RESPONSE:** The exact interface:

```python
# From architecture_model.integrations.llm_context
def format_model_context(
    model: ArchitectureModel,
    max_tokens: int = 4000,
    detail_level: str = "standard"  # "minimal" | "standard" | "full"
) -> str

def format_fblock_context(
    model: ArchitectureModel,
    f_block: str,          # e.g., "F1"
    max_tokens: int = 4000
) -> str
```

Note: these take `ArchitectureModel` (the parsed model), not the raw manifest dict. The manifest feeds into model creation upstream. The context formatter compresses the model into a token-efficient string for LLM prompts.

Should log: input token count, output token count, compression ratio, detail level used, truncation warnings.

`format_model_context()` achieves 2.8x–86x compression ratios depending on repo size and subsystem connectivity.

---

## Output Schema

```json
{
  "generated_at": "2026-07-17T12:00:00",
  "project_root": "/absolute/path",
  "metrics": {
    "router_count": 30,
    "total_python_files": 150
  },
  "functional_blocks": {
    "F1": {
      "name": "Block Name",
      "status": "active",
      "description_source": "...",
      "sub_functions": [
        {
          "id": "F1.1",
          "name": "...",
          "file": "...",
          "functions": ["..."],
          "inputs": ["..."],
          "outputs": ["..."],
          "status": "active",
          "line_count": 200
        }
      ],
      "sub_blocks": []
    }
  },
  "modules": [
    {
      "file": "...",
      "name": "...",
      "docstring": "...",
      "functions": ["..."],
      "imports": ["..."],
      "line_count": 100,
      "status": "active",
      "classes": [],
      "exports": [],
      "decorated_functions": [],
      "imports_detailed": [],
      "module_constants": {},
      "module_assignments": {}
    }
  ],
  "interfaces": [
    {
      "source": "a/b.py",
      "target": "c/d.py",
      "import_path": "c.d"
    }
  ]
}
```

The manifest is the foundation of the entire pipeline — without accurate reality data, no validation, compression, or regeneration is possible.
