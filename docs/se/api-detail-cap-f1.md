# API Detail — CAP-F1: Model Parsing & Validation

## IF-PARSE-API — `architecture_model.core.parser`

### `load_model(path: str | Path) -> ArchitectureModel`

The primary entry point. Reads a YAML file from disk, parses it into the typed `ArchitectureModel` dataclass tree.

Internally:
1. Opens the file with `yaml.safe_load()`
2. Raises `ValueError` if the file is empty
3. Delegates to `_parse_raw()` for structural conversion

This is what the CLI `validate` command and the MCP server call to get a model into memory.

---

### `save_model(model: ArchitectureModel, path: str | Path) -> None`

The inverse of `load_model`. Serializes an `ArchitectureModel` back to YAML and writes it to disk.

Internally:
1. Calls `dump_model()` to get a plain dict
2. Creates parent directories if needed (`mkdir -p` equivalent)
3. Writes YAML with `default_flow_style=False, sort_keys=False`

Used after model modifications (e.g., after `architecture-model init` generates a new model).

---

### `dump_model(model: ArchitectureModel) -> dict[str, Any]`

Serialization without I/O. Converts the typed dataclass tree back into a plain Python dict with the structure `{meta, entities, relationships}`.

This is the "model -> dict" direction. The dict is JSON/YAML-serializable. Used by:
- `save_model()` before writing
- The MCP server when it needs to pass model data as JSON
- Tests that need to inspect model structure

Key behavior: Only includes optional fields if they have non-default values (e.g., `description` only if non-empty, `kind` only if not `SERVICE`). This keeps output YAML clean.

---

### `validate_model_data(data: dict[str, Any]) -> list[str]`

Schema-level validation. Takes a raw dict (before parsing into dataclasses) and checks it against the JSON Schema (`spec/schema.json`, Draft 2020-12).

Returns a list of error strings. Empty list = schema-valid.

This is a different concern from `validate_model()`:
- `validate_model_data` = "does the YAML structure match the schema?" (syntactic)
- `validate_model` = "is the model internally consistent?" (semantic)

Falls back gracefully if `jsonschema` isn't installed (returns a single message saying so).

---

### `_parse_raw(raw: dict) -> ArchitectureModel`

The core transformation engine. Takes a raw dict (from `yaml.safe_load` or from an LLM's JSON output) and builds the full typed dataclass tree:

```
raw dict -> ModelMeta + Entities(actors, capabilities, behaviors,
           interfaces, constraints, layers, components, systems) + Relationships
```

Each entity type has its own parser (`_parse_actor`, `_parse_component`, etc.) that:
- Extracts fields with sensible defaults
- Converts string enums to typed enums (`Status`, `Priority`, `ComponentKind`, etc.)
- Handles nested structures (e.g., `Component.fields -> [DataField]`, `Component.signatures -> [FunctionSignature]`, `Behavior.states -> [StateTransition]`)

Prefixed with `_` but used by the MCP server (`opencode-arch`) as a public API for parsing dict data that didn't come from a file.

---

## IF-VALIDATE-API — `architecture_model.core.validator`

### `validate_model(model: ArchitectureModel, strict: bool = False) -> ValidationResult`

The semantic correctness checker. Runs 8 checks in fixed order on a parsed model:

| # | Check | Severity | What it catches |
|---|-------|----------|-----------------|
| 1 | **ID Uniqueness** | ERROR | Same ID used in two entity types (e.g., a component and a capability both called "FOO") |
| 2 | **Referential Integrity** | WARNING | A relationship references an entity ID that doesn't exist in the model |
| 3 | **Orphan Detection** | INFO | Active behaviors/components with zero relationships (dead entities) |
| 4 | **Status Consistency** | WARNING | An ACTIVE entity `depends_on` or `consumes` a PLANNED entity (unstable dependency) |
| 5 | **Capability Realization** | WARNING | An ACTIVE capability has no `realizes` relationship pointing to it (unimplemented capability) |
| 6 | **Meta Completeness** | ERROR/WARNING | Missing `project` or `schema_version` (ERROR), missing `source_artifacts` (WARNING) |
| 7 | **v1.1 Semantics** | INFO/WARNING | Data-model components without fields; state-machine behaviors with unreachable states |
| 8 | **Regen Readiness** | ERROR/WARNING | Components with test_contracts but insufficient constants (<30% = ERROR, <70% = WARNING) or signatures (<50% = WARNING) to support code regeneration |

### `strict` mode

Promotes all WARNINGs to ERRORs, making the bar higher.

### `ValidationResult`

| Field | Type | Description |
|-------|------|-------------|
| `issues` | `list[ValidationIssue]` | Each with `severity`, `code`, `message`, `entity_id`, `context` |
| `is_valid` | `bool` | `True` iff 0 errors |
| `score` | `int` | `100 - (10 * errors) - (2 * warnings)`, floored at 0 |
| `summary()` | `str` | One-line human-readable output |

### Scoring formula

The scoring formula means: 10 errors = score 0, 5 warnings = score 90, etc. This is the "0-100 score" that the whole system reports.
