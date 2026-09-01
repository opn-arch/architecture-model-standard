# Universal Entity Semantics Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make universal intent and decision semantics available, schema-valid, round-trippable, and visible for all 17 architecture entity types without changing typed component interfaces.

**Architecture:** Define the universal fields once on `BaseEntity`, using `interface_refs` for semantic references while retaining `Component.interfaces: list[ComponentInterface]`. Parse and dump the universal fields only through shared base helpers, retain type-specific nested parsing, and drive viewer pages/navigation from all `Entities` collections with shared semantic property rendering.

**Tech Stack:** Python dataclasses, PyYAML, JSON Schema Draft 2020-12, pytest, generated HTML/JavaScript viewer.

---

### Task 1: Add exhaustive red model and schema tests

**Files:**
- Create: `tests/test_universal_entity_semantics.py`
- Modify: `tests/test_viewer_comments.py`

**Step 1: Write the failing tests**

Parameterize over `Actor`, `Capability`, `Behavior`, `Interface`, `Constraint`, `Layer`, `Component`, `System`, `Data`, `Event`, `Resource`, `Environment`, `QualityAttribute`, `Decision`, `Lifecycle`, `Requirement`, and `ExternalSystem`. Construct each with non-empty `intent`, `goals`, `requirements`, `rationale`, `moes`, `value_function`, `failure_modes`, `trade_offs`, `interface_refs`, nested `DecisionEntry`, and `monitored`; for `Component`, also include a nested `ComponentInterface`.

Assert constructor support, `dump_model`/`_parse_raw`, `ArchitectureModel.to_dict`/YAML, JSON Schema validation, nested typed restoration, and preservation through generic model operations. Add parameterized viewer tests asserting every entity gets a property page and generated HTML contains navigable entity data and a comment textarea.

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_universal_entity_semantics.py tests/test_viewer_comments.py -v`

Expected: FAIL because most classes reject universal constructor fields, schema definitions reject them, and viewer properties omit eight entity collections.

### Task 2: Implement universal dataclass and round-trip support

**Files:**
- Modify: `src/architecture_model/core/types.py`
- Modify: `src/architecture_model/core/parser.py`

**Step 1: Move fields to `BaseEntity`**

Add documented defaults for `goals`, `requirements`, `rationale`, `moes`, `value_function`, `failure_modes`, `trade_offs`, `interface_refs`, and `monitored`. Keep `intent` and typed `decisions`; remove exact duplicate subclass declarations while retaining `Component.interfaces` unchanged.

**Step 2: Centralize parser support**

Have `_parse_base` consume every universal field and `_dump_base` emit every populated universal field. Remove duplicate keyword arguments and duplicate dump blocks from type-specific helpers. Mirror the same base serialization in `ArchitectureModel._dump_base` so both public serialization paths agree.

**Step 3: Run focused model tests**

Run: `pytest tests/test_universal_entity_semantics.py tests/test_types_se_fields.py tests/test_parser_decisions.py tests/test_types_decisions.py tests/test_schema_v2.py -v`

Expected: Model round trips pass; schema assertions remain red until Task 3.

### Task 3: Extend JSON Schema universally

**Files:**
- Modify: `src/architecture_model/spec/schema.json`
- Modify: `tests/test_universal_entity_semantics.py`

**Step 1: Define universal field schemas**

Add all universal fields to `$defs.base_entity`, document that `requirements` accepts IDs or statements and `interface_refs` accepts interface IDs or contract names, and expose inherited property names in every entity definition that uses `additionalProperties: false`. Preserve schema/model version conventions rather than bumping the model version.

**Step 2: Run schema tests**

Run: `pytest tests/test_universal_entity_semantics.py tests/test_schema_sync.py tests/test_schema_reconciliation.py tests/test_schema_extensions.py tests/test_profiles/test_profile_schema.py -v`

Expected: PASS with populated universal values valid for all 17 definitions.

### Task 4: Complete viewer entity coverage

**Files:**
- Modify: `src/architecture_model/core/visualize.py`
- Modify: `tests/test_universal_entity_semantics.py`
- Modify: `tests/test_viewer_comments.py`

**Step 1: Build universal properties once**

Add every populated universal semantic field to every property page with readable labels. Serialize nested `DecisionEntry` and typed `ComponentInterface` values through the existing JSON-safe converter; show semantic `interface_refs` as `Interfaces` and typed component contracts under a distinct readable label.

**Step 2: Include all entity collections**

Build property cards and sidebar/search/navigation entries for all 17 collections while preserving existing type-specific fields and behavior diagrams. Leave module detail comment rendering intact.

**Step 3: Run focused viewer tests**

Run: `pytest tests/test_universal_entity_semantics.py tests/test_viewer_v3.py tests/test_viewer_comments.py tests/test_html_viewer.py tests/test_viewer_pipeline_diagrams.py -v`

Expected: PASS for property pages, sidebar/search data, nested rendering, and comment controls across all entity types.

### Task 5: Verify model operations and full suite

**Files:**
- Modify only if a red test demonstrates field loss in `src/architecture_model/core/merger.py`, `src/architecture_model/core/differ.py`, or `src/architecture_model/core/slicer.py`.

**Step 1: Run focused operation tests**

Run: `pytest tests/test_universal_entity_semantics.py tests/test_merger.py tests/test_differ.py tests/test_slicer.py -v`

Expected: PASS because dataclass-preserving operations retain inherited fields; make the smallest demonstrated fix if not.

**Step 2: Run the prescribed suite**

Run: `pytest tests/ -v --ignore=tests/test_config_loader.py`

Expected baseline: 9 known failures, approximately 1964 passing and 109 skipped; no new failures attributable to this change.

**Step 3: Run architecture checks**

Run architecture representativeness and completion gates, recording any pre-existing model limitations separately from feature verification.

### Task 6: Commit the complete change

**Files:**
- Stage only feature, test, plan, and architecture requirement/log files created or modified for this work.

**Step 1: Inspect final diff and status**

Run: `git status --short`, `git diff --check`, and `git diff --stat`.

**Step 2: Commit**

Run: `git commit -m "feat: add universal entity semantics"`

**Step 3: Verify commit**

Run: `git status --short` and `git rev-parse HEAD`.
