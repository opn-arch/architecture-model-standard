---
artifact_id: api-reference
generated_at: 2026-07-11T16:08:33.604175+00:00
generator: opencode-arch-docs
---
# API Reference

## Overview

This document describes the internal interfaces of the Architecture Model Standard package. All interfaces are internal Python APIs consumed programmatically or via the CLI entry point `architecture-model`.

---

## IF-CLI: CLI Interface

| Property | Value |
|----------|-------|
| **Name** | CLI Interface |
| **Type** | Internal |
| **Protocol** | CLI (Click) |
| **Provider** | `architecture_model.cli.main` |
| **Consumer** | End users, CI pipelines, MCP server |
| **Data Format** | YAML input, text/JSON output |

### Endpoints

| Command | Arguments | Description |
|---------|-----------|-------------|
| `init [path]` | `--force` | Auto-generate `.architecture-model.yaml` from directory structure |
| `validate <model>` | `--strict` | Validate model against invariants |
| `slice <model>` | `--fblock`, `--layer`, `--artifact`, `--status`, `-o` | Extract a model subset |
| `diff <old> <new>` | — | Compare two model versions |
| `stats <model>` | — | Display model statistics |
| `impact <model> <entity_id>` | `--depth` | Trace impact through relationships |
| `manifest [path]` | `-o` | Generate reality-manifest.json via AST scanning |

---

## IF-PARSE-API: Parser API

| Property | Value |
|----------|-------|
| **Name** | Parser API |
| **Type** | Internal |
| **Protocol** | Python function call |
| **Provider** | `architecture_model.core.parser` |
| **Consumer** | CLI, Validator, Slicer, MCP server |
| **Data Format** | YAML ↔ `ArchitectureModel` dataclass |

### Endpoints

| Function | Signature | Returns |
|----------|-----------|---------|
| `load_model` | `(path: str \| Path)` | `ArchitectureModel` |
| `save_model` | `(model: ArchitectureModel, path: str \| Path)` | `None` |
| `dump_model` | `(model: ArchitectureModel)` | `dict[str, Any]` |
| `validate_model_data` | `(data: dict[str, Any])` | `list[str]` |
| `_parse_raw` | `(raw: dict)` | `ArchitectureModel` |

### Data Contract

Input/output YAML structure validated against JSON Schema (Draft 2020-12) at `spec/schema.json`:

```yaml
meta:
  project: <string>
  schema_version: '<string>'
entities:
  components: [...]
  capabilities: [...]
  behaviors: [...]
  interfaces: [...]
  constraints: [...]
  layers: [...]
  actors: [...]
relationships:
  - {from: <id>, to: <id>, type: <relationship_type>}
```

---

## IF-VALIDATE-API: Validator API

| Property | Value |
|----------|-------|
| **Name** | Validator API |
| **Type** | Internal |
| **Protocol** | Python function call |
| **Provider** | `architecture_model.core.validator` |
| **Consumer** | CLI, MCP server |
| **Data Format** | `ArchitectureModel` → `ValidationResult` |

### Endpoints

| Function | Signature | Returns |
|----------|-----------|---------|
| `validate_model` | `(model: ArchitectureModel, strict: bool = False)` | `ValidationResult` |

### Data Contract

**`ValidationResult`** dataclass:

| Field | Type | Description |
|-------|------|-------------|
| `issues` | `list[ValidationIssue]` | Each has `severity`, `code`, `message`, `entity_id`, `context` |
| `is_valid` | `bool` | `True` if zero errors |
| `score` | `int` | 0–100 (deduct 10/error, 2/warning) |

**Severity levels:** `ERROR`, `WARNING`, `INFO`

**Checks performed:** ID uniqueness, referential integrity, orphan detection, status consistency, capability realization, meta completeness, regen readiness.

---

## IF-MANIFEST-API: Manifest API

| Property | Value |
|----------|-------|
| **Name** | Manifest API |
| **Type** | Internal |
| **Protocol** | Python function call |
| **Provider** | `architecture_model.manifest.generator` |
| **Consumer** | CLI, MCP server |
| **Data Format** | `Path` → `dict` (JSON-serializable) |

### Endpoints

| Function | Signature | Returns |
|----------|-----------|---------|
| `generate_manifest` | `(project_root: Path, config: Optional[Any] = None)` | `dict[str, Any]` |
| `load_or_generate_manifest` | `(project_root: Path, output_dir: Path \| None = None)` | `dict[str, Any]` |

### Data Contract

Output dictionary keys:

| Key | Type | Description |
|-----|------|-------------|
| `project_root` | `str` | Absolute path to scanned project |
| `modules` | `list[dict]` | Discovered Python modules with AST metadata |
| `metrics` | `dict` | Aggregate code metrics |
| `functional_blocks` | `list[dict]` | Grouped source packages as F-blocks |

---

## IF-SLICER-API: Slicer API

| Property | Value |
|----------|-------|
| **Name** | Slicer API |
| **Type** | Internal |
| **Protocol** | Python function call |
| **Provider** | `architecture_model.core.slicer` |
| **Consumer** | CLI, MCP server, LLM context formatter |
| **Data Format** | `ArchitectureModel` → `ArchitectureModel` (subset) |

### Endpoints

| Function | Signature | Returns |
|----------|-----------|---------|
| `slice_by_fblock` | `(model: ArchitectureModel, f_block: str, include_relationships: bool = True)` | `ArchitectureModel` |
| `slice_by_layer` | `(model: ArchitectureModel, layer_id: str)` | `ArchitectureModel` |
| `slice_by_status` | `(model: ArchitectureModel, status: Status)` | `ArchitectureModel` |
| `slice_for_artifact` | `(model: ArchitectureModel, artifact_name: str)` | `ArchitectureModel` |

### Data Contract

All slicers return a deep-copied `ArchitectureModel` containing only the entities and relationships relevant to the slice criteria. The output conforms to the same YAML schema as the full model.

**Supported artifact names for `slice_for_artifact`:** `functional-architecture`, `logical-architecture`, `use-cases`, `icd`, `requirements-analysis`, `operations-manual`, `conops`, `testing`, `deployment-guide`, `data-dictionary`, `readme`.

---

## Common Data Types

### ArchitectureModel

The universal data type across all interfaces. Defined in `architecture_model.core.types`. Serialized as YAML with the structure `{meta, entities, relationships}`.

### Relationship Types

`realizes`, `uses`, `constrains`, `contains`, `triggers`, `depends_on`, `implements`, `exposes`

### Entity Statuses

`ACTIVE`, `DEPRECATED`, `PLANNED`
