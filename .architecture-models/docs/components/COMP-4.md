# Component: Export (COMP-4)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/export/flatfiles.py` | — | — |
| `src/architecture_model/export/reference.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

None

### Dependents (incoming)

None

## Behaviors Realized

None

## Public API

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `derive_prefix` | `repo_name: str` | `str` | Derive a short prefix from repo name.

Rules:
- 'architecture-model-standard' -> 'model-std'
- 'opencode-arch' -> 'opencode'
- anything else: use as-is, lowercased, replacing _ with - |
| `build_flat_export` | `repo_path: Path, prefix: str | None, include_manifests: bool, include_module_specs: bool` | `ExportResult` | Build all flat files for a repo.

Scans for existing artifacts and only includes files that are present.
Each output file is named {prefix}--{category}.{ext} |
| `concat_submodels` | `repo_path: Path` | `str | None` | Concatenate F-block and named sub-model YAMLs. |
| `concat_behavior_submodels` | `repo_path: Path` | `str | None` | Concatenate behavior sub-model YAMLs. |
| `concat_component_models` | `repo_path: Path` | `str | None` | Concatenate COMP-* sub-model YAMLs. |
| `concat_behavior_specs` | `repo_path: Path` | `str | None` | Concatenate behavior spec markdowns. |
| `concat_docs` | `repo_path: Path` | `str | None` | Concatenate generated architecture docs (excluding behaviors subdir). |
| `concat_module_specs` | `repo_path: Path` | `str | None` | Concatenate per-component module YAML specs. |
| `concat_diagrams` | `repo_path: Path` | `str | None` | Concatenate Mermaid diagram files. |
| `concat_skills` | `repo_path: Path` | `str | None` | Concatenate skill markdown files. |
| `manifests_to_markdown` | `manifest_dir: Path` | `str | None` | Convert JSON manifests to readable markdown summaries. |
| `generate_readme` | `` | `str` |  |
| `generate_schema_reference` | `` | `str` |  |
| `generate_api_reference` | `` | `str` |  |
| `generate_custom_instructions` | `repo_name: str, stats: dict` | `str` |  |

## Patterns

- data-class

## Confidence

87%
