# API Detail — CAP-F4: CLI Operations

## IF-CLI — `architecture_model.cli.main`

Entry point: `architecture-model` (installed via `console_scripts`). Built with `argparse`, dispatches to handler functions.

---

### `architecture-model init [path] [--force]`

**Handler:** `_cmd_init(args)`

Auto-generates `.architecture-model.yaml` for a project by scanning its directory structure.

**Steps:**

1. Resolve path to absolute directory
2. Check if `.architecture-model.yaml` already exists (abort unless `--force`)
3. Call `discover_config(root)` to scan and infer project structure
4. Print summary: project name, system, layers, functional blocks (with file counts), metrics
5. Call `write_config(config, root)` to serialize and save

**Exit codes:** 0 = success, 1 = already exists or path invalid

---

### `architecture-model validate <model.yaml> [--strict]`

**Handler:** `_cmd_validate(args)`

Validates an architecture model against schema and structural invariants.

**Steps:**

1. `load_model(path)` — parse YAML into `ArchitectureModel`
2. `validate_model(model, strict=args.strict)` — run 8 validation checks
3. Print `result.summary()` (score, error/warning counts)
4. Print each issue with severity, code, message, entity_id

**Exit codes:** 0 = valid (0 errors), 1 = invalid (has errors)

---

### `architecture-model slice <model.yaml> --fblock|--layer|--artifact|--status [-o output]`

**Handler:** `_cmd_slice(args)`

Extracts a model subset based on the chosen dimension.

**Options (mutually exclusive):**

| Flag | Slicer Called | Example |
|------|-------------|---------|
| `--fblock F3` | `slice_by_fblock(model, "F3")` | All entities in F-block F3 |
| `--layer web-layer` | `slice_by_layer(model, "web-layer")` | Layer + its components |
| `--artifact use-cases` | `slice_for_artifact(model, "use-cases")` | Entities needed for that doc |
| `--status PLANNED` | `slice_by_status(model, Status.PLANNED)` | Only planned entities |

**Output:** Prints entity/relationship count. If `-o` specified, writes sliced model as YAML.

---

### `architecture-model diff <old.yaml> <new.yaml>`

**Handler:** `_cmd_diff(args)`

Compares two model versions and prints a structured diff report.

**Steps:**

1. Load both models
2. `diff_models(old, new)` → `ModelDiff`
3. Print `diff.format_report()` — markdown with grouped entity/relationship changes
4. Print affected artifacts that should be regenerated

---

### `architecture-model stats <model.yaml>`

**Handler:** `_cmd_stats(args)`

Displays comprehensive model statistics.

**Output includes:**

- Project name, system, schema version, generation timestamp, source artifacts, manifest hash
- Total entity count + breakdown by type (actors, capabilities, behaviors, interfaces, constraints, layers, components)
- Total relationship count + breakdown by type (realizes, depends_on, contains, etc.)
- Status breakdown (ACTIVE, PLANNED, DEPRECATED counts)
- Inline validation score

---

### `architecture-model impact <model.yaml> <entity_id> [--depth N]`

**Handler:** `_cmd_impact(args)`

Traces impact through the relationship graph using BFS.

**Algorithm:**

1. Verify entity_id exists in model
2. Build undirected adjacency map from all relationships (both directions)
3. BFS from entity_id to `--depth` (default 2)
4. Print all reachable entities grouped by distance

**Example output:**
```
Impact analysis: CAP-F1 (depth=2)
Affected entities: 5
  [depth 1] COMP-CORE
  [depth 1] IF-PARSE-API
  [depth 2] COMP-CLI
  [depth 2] COMP-CONFIG
```

---

### `architecture-model manifest [path] [-o output]`

**Handler:** `_cmd_manifest(args)`

Generates `reality-manifest.json` via full AST scan of the project.

**Steps:**

1. Resolve path and verify directory
2. Call `generate_manifest(root)` (full AST scan)
3. Determine output path (from `-o` flag or config's `resolved_output().manifest`)
4. Write manifest as JSON
5. Print summary: module count, interface count, F-block count, metrics

---

## Behavioral Views

### BEH-INIT: Project Initialization

**Trigger:** `architecture-model init <path>`  
**Actor:** Developer (via CLI)

**Preconditions:**
- Target path is a valid directory
- `.architecture-model.yaml` must not exist (unless `--force`)

**Postconditions:**
- `.architecture-model.yaml` exists at project root with layers, F-blocks, metrics
- No source code modified

### BEH-VALIDATE: Model Validation

See [api-detail-cap-f1.md](api-detail-cap-f1.md) for the full behavioral flow.

---

## CLI Architecture

```
main(argv) → argparse → dispatch table → handler function
                                              │
                                              ├── imports from core.parser
                                              ├── imports from core.validator
                                              ├── imports from core.slicer
                                              ├── imports from core.differ
                                              ├── imports from config.loader
                                              └── imports from manifest.generator
```

All imports are lazy (inside handler functions) to keep CLI startup fast. The CLI is a thin dispatch layer — all logic lives in the core/manifest/config modules.
