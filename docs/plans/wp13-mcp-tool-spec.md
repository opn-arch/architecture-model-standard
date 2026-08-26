# WP-13: MCP Tool Update Spec for opencode-arch

## Summary

This document specifies the API changes needed in the `opencode-arch` MCP server to expose the new capabilities added in schema v2.1.

## Changes Required

### 1. `architect_slice` — New Parameters

- **`max_tokens: int | None`** — When set, applies `reduce_to_budget()` after structural slicing. Uses progressive reduction (drop body_hints → test_contracts → truncate signatures → truncate descriptions → drop constants).
- **`detail: str`** — Now surfaces `intent`, `goals`, `moes`, and `detail_level` (L0-L4) in the output when `detail="full"`.

### 2. New Tool: `architect_review`

Wraps `architecture_model.core.review.prepare_review_prompt()` and `apply_review()`.

```
architect_review(repo_path, entity_id, review_data=None)
```

- If `review_data` is None: returns a review prompt for the entity (listing missing SE fields)
- If `review_data` is provided: applies the review and writes the updated model

### 3. `architect_validate` — Semantic Completeness

The validation result now includes INFO-level `SEMANTIC_MISSING_*` issues for ACTIVE entities missing:
- `intent` (components and capabilities)
- `responsibilities` (components)
- `goals` (components)
- `moes` (capabilities)

These do not affect the validation score but are surfaced in the issues list.

### 4. `architect_docs` — PDF Output

The `docs` CLI command now accepts `--pdf` to generate PDF output via pandoc. The MCP `architect_docs` tool should accept a `pdf: bool` parameter.

### 5. New Context Fields in Slice Output

When `detail="full"`, the slicer output now includes per-entity:
- `intent` — purpose statement
- `goals` / `moes` — measurable objectives
- `trade_offs` / `failure_modes` — design rationale (components only)
- `detail_level` — L0 (Skeleton) through L4 (Reviewed)

## Implementation Notes

- All changes are backward-compatible — new fields default to empty/None
- The `reduce_to_budget()` function is pure and stateless — safe to call from MCP
- Cross-repo consistency (`check_consistency()`) and changelog (`generate_changelog()`) are available but not yet exposed as MCP tools — consider adding in a future update
