# Session Results — 2026-08-30

## What Was Done

### Fixes Committed (`c3215a3`)

1. **Capability deduplication** — `apply_additions_infer` now checks name similarity (>0.6 threshold via `SequenceMatcher`) against existing capabilities before adding LLM-suggested ones. Prevents duplicates like "MCP Server" + "Mcp Server Management".

2. **Mega-capability bypass** — When heuristic produces ≤3 capabilities and LLM produces ≥5, all LLM capabilities are added directly (bypassing the diff/rename step). Solves the problem where package-level grouping creates one useless mega-capability that all components realize.

3. **Relate logging format** — Added `RefinementLog.summary()` method and `total_changes` property. Relate-stage additions now format as `"from→to (type)"` instead of showing `?`.

4. **Quality score debug logging** — Replaced bare `except: pass` in observe stage with `logging.debug` output showing the exception and path info. Helps diagnose why `analyze_source()` returns 0 on external repos.

5. **Layer precision** — Removed `"api"` from `_LAYER_KEYWORDS["web"]` (was causing false "web" layer on internal files like `api_wrapper.py`). Added `"controller"` and `"server"` as more precise web indicators.

### Docs Saved
- `.opencode/plans/extract-call-chain.md` — Full internal call chain for all 9 pipeline stages + LLM refinement system

### Test Results
- 1583 passed (+10 new), 7 pre-existing failures, 98 skipped

## Remaining Known Issues (None Critical)

All 5 identified issues from the LLM refinement work have been addressed. Potential future improvements:
- Run E2E on opencode-arch again to verify the fixes improve output quality
- The quality score debug logging may reveal the actual root cause on external repos (need to check logs)
- Consider adding "api" back as a web keyword but only when it's a standalone directory name (not filename substring)

## E2E Results Reference (from prior session)

### opencode-arch (with LLM refinement)
- Capabilities: 0 → 58, Components: 15, Layers: 5, Interfaces: 13, Relationships: 119

### colorama (with LLM refinement)
- Capabilities: 4 → 16, Layer corrections: 3, Component renames: 2

### Key Discoveries
- `ObserveStage.run()` returns `StageResult[Inventory]` — `result.output` is an `Inventory` object
- `AllocationResult` has `components: list[ComponentAllocation]` (not `allocations`)
- `DerivedRelationship` has `from_id`/`to_id` (not `source`/`target`), field `rel_type` (not `type`)
- LLM entities lack IDs — name-similarity matching needed (0.3 threshold + substring boost)
- `TestContract` field is `target_component` (not `component_id`)
