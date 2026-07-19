# Sub-Models & Recursive Manifests: Post-Fix Assessment

Generated 2026-07-18 after fixing derive_interfaces() and capability filtering.

## 1. What Was Fixed

### Fix 1: derive_interfaces() now uses imports_detailed

**Before:** derive_interfaces() only matched against mod.imports (bare names
like `pathlib`, `types`). These never matched project modules because
module_to_file had dotted paths like `src.architecture_model.core.types`.
Result: **0 interfaces** across all manifests and sub-models.

**After:** Added a second pass that iterates imports_detailed, resolving:

- Relative imports: `from .types import X` --> same-dir resolution,
  `from ..core.parser import X` --> parent-dir resolution
- Absolute imports: `architecture_model.core.parser` --> tries with `src/` prefix
- Package imports: `architecture_model.core` --> resolves to `core/__init__.py`

Result: **83 interface edges** from full project scan.

### Fix 2: Capability filtering

**Before:** Every function became a Capability, including `_parse_raw`,
`_build_id_map`, etc. F5 (Manifest) had 16 capabilities.

**After:** Two-stage filter:

1. Skip functions starting with `_` (private helpers)
2. If block's `__init__.py` has exports, only promote exported functions
3. Fall back to all non-underscore functions if no exports found

Result: F5 went from 16 to **8 capabilities** (the actual public API).

## 2. Sub-Models: Before vs After

| Block | Caps Before | Caps After | Ifaces Before | Ifaces After |
|-------|:----------:|:---------:|:------------:|:-----------:|
| F1 (Cli) | 1 | 1 | 0 | 0 |
| F2 (Config) | 4 | 3 | 0 | 3 |
| F3 (Core) | 20 | 20 | 0 | 7 |
| F4 (Extract) | 1 | 1 | 0 | 0 |
| F5 (Manifest) | 16 | 8 | 0 | 22 |
| F6 (Profiles) | 1 | 1 | 0 | 0 |
| F7 (Spec) | 0 | 0 | 0 | 0 |
| F8 (Utils) | 4 | 4 | 0 | 0 |

## 3. Detailed Sub-Model Contents

### F1: Cli

- **Refines:** `COMP-CLI`
- **Components:** 1
- **Capabilities (1):** main
- **Interfaces:** 0
- **Relationships:** 0

### F2: Config

- **Refines:** `COMP-CONFIG`
- **Components:** 1
- **Capabilities (3):** load_config | discover_config | get_config
- **Interfaces (3):**
  - __init__ -> schema
  - __init__ -> loader
  - loader -> schema
- **Relationships:** 0

### F3: Core

- **Refines:** `COMP-CORE`
- **Components:** 7
- **Capabilities (20):** coverage_report | compute_complexity | identify_systems | auto_assign_f_blocks | decompose_model | test_affinity_decompose | diff_models | merge_manifest | enrich_from_manifest | compact_for_generation | compose_enriched_model | load_model | validate_model_data | dump_model | save_model | slice_by_fblock | slice_by_layer | slice_by_status | slice_for_artifact | validate_model
- **Interfaces (7):**
  - coverage -> types
  - decomposer -> types
  - differ -> types
  - merger -> types
  - parser -> types
  - slicer -> types
  - validator -> types
- **Relationships:** 13

### F4: Extract

- **Refines:** `COMP-EXTRACT`
- **Components:** 1
- **Capabilities (1):** extract_from_code
- **Interfaces:** 0
- **Relationships:** 0

### F5: Manifest

- **Refines:** `COMP-MANIFEST`
- **Components:** 8
- **Capabilities (8):** process_block | print_summary | generate_manifest | load_or_generate_manifest | derive_interfaces | compute_metrics | scan_file | get_manifest_slice
- **Interfaces (22):**
  - __init__ -> blocks
  - __init__ -> display
  - __init__ -> generator
  - __init__ -> interfaces
  - __init__ -> metrics
  - __init__ -> scanner
  - __init__ -> slicers
  - __init__ -> types
  - ... and 14 more
- **Relationships:** 18

### F6: Profiles

- **Refines:** `COMP-PROFILES`
- **Components:** 1
- **Capabilities (1):** load_profile
- **Interfaces:** 0
- **Relationships:** 0

### F7: Spec

- **Refines:** `COMP-SPEC`
- **Components:** 1
- **Capabilities:** 0
- **Interfaces:** 0
- **Relationships:** 0

### F8: Utils

- **Refines:** `COMP-UTILS`
- **Components:** 1
- **Capabilities (4):** is_excluded_dir | collect_py_files | discover_source_files | discover_test_files
- **Interfaces:** 0
- **Relationships:** 0

## 4. Cross-Block Dependency Graph

| Block | Depends On |
|-------|-----------|
| F1 (Cli) | F2, F3, F5 |
| F2 (Config) | F8 |
| F3 (Core) | F2, F5, F6, F8 |
| F4 (Extract) | F2, F3, F5 |
| F5 (Manifest) | F2, F3, F8 |
| F6 (Profiles) | (none) |
| F7 (Spec) | (none) |
| F8 (Utils) | (none) |

## 5. Remaining Gaps

- **F1 (Cli) has 0 interfaces.** The CLI uses lazy imports inside function
  bodies (`from ..core.parser import load_model` inside `_cmd_validate()`).
  These are not captured by the AST scanner as module-level imports.
  Low priority -- the CLI is a thin dispatch layer.
- **F3 (Core) capabilities not filtered by exports.** Core's `__init__.py`
  is empty, so the fallback includes all 20 non-underscore functions.
  Would need `__all__` added to core/__init__.py to filter further.
- **F7 (Spec) has 0 everything** except 1 component. It contains only
  schema.json (no Python functions). This is correct.