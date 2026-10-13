# Flow Modeling Substrate (Parts 16a–17b)

**Date:** 2026-09-20
**Status:** In progress — Part 16a executing
**Owner:** CAP-PB (extract) + CAP-DF (evolve)

## Diagnosis

The current AMS model expresses **static topology well** (components, capabilities,
constraints, interfaces, containment/realization edges) but **dynamic flow weakly**:

- No first-class "pipeline" entity — pipelines exist implicitly as chains of
  `triggers` edges between behaviors.
- `triggers` edges are **unordered** — nothing distinguishes stage 1 of a
  7-stage pipeline from stage 7.
- The slicer is topology-scoped (`slice_by_fblock`, `slice_by_layer`,
  `slice_by_entity`) — there is no `slice_by_behavior(BEH-x)` that walks a
  behavior's `triggers` chain to return the sub-model participating in that
  flow.
- Call chains (which components call which within a behavior) are not
  captured on `traces-to` edges even though `manifest/call_graph.py` already
  derives them at AST scan time.

Concrete example: the 7-stage extract pipeline
`BEH-scan → BEH-derive-promises → BEH-infer-flow → BEH-emit-fragments →
BEH-compare → BEH-produce-snapshot → BEH-publish` lives in
`capabilities.v3.yaml:1807-1812` as six triggers edges. A reader cannot
answer "what is stage 3?" without eyeballing declaration order.

## Design Decision (locked)

Reuse **`Behavior`** as the flow entity. No new `Flow` / `Scenario` /
`Pipeline` entity kind. A behavior is **composite** if any of its outgoing
`triggers` edges carries a `sequence:` field — detection is implicit,
requires no new field on `Behavior` itself.

Rationale:
- Fully additive to the schema (2.2 → 2.2, no version bump).
- Existing 7-stage pipeline chain works today; retrofitting is just
  adding `sequence: 1..7` to six existing edges (Part 16c).
- Composite/sub-behavior distinction remains a modeling convention, not
  a schema partition — behaviors nest recursively via `contains` +
  `triggers`.

## Multi-Part Sequence

Each part is additive and independently committable / revertable.

### Part 16a — `sequence:` field on relationships (this commit)

**Scope:** schema + parser + serializer + tests. No model changes.

Files touched:
- `src/architecture_model/spec/schema.json` — add optional
  `sequence: {type: integer, minimum: 1}` to `$defs.relationship.properties`.
- `src/architecture_model/core/types.py` — add
  `sequence: int | None = None` to `Relationship` dataclass; emit in
  `_dump_relationship` only when set (digest stability for existing
  fixtures).
- `src/architecture_model/core/parser.py` — `_parse_relationship` reads
  optional `sequence`; emits `UserWarning` if set on a non-`triggers`
  edge (soft — parses succeed).
- `tests/core/test_relationship_sequence.py` (NEW) — 7 tests covering
  roundtrip, absence-preservation, negative/zero/string rejection at
  schema level, non-triggers warning, existing-fixture regression.
- `tests/spec/test_schema_2_1_defs.py` (extend) — 2 tests for schema
  presence + validity of the new field.

**Verification gate:** `python -m pytest tests/
--ignore=tests/test_config_loader.py -q` → 4351 baseline → expect ~4360
passed, 0 regressions.

**NOT touched in 16a:** `promise-graph.schema.json` (v3 relationships
are loaded via `core.v3_loader.load_v3_model` which doesn't schema-
validate individual relationship dicts; the same `_parse_relationship`
path is reused so the new field flows through automatically).

### Part 16b — `slice_by_behavior` slicer

Add `architecture_model.core.slicer.slice_by_behavior(model, behavior_id, *,
include_components=True)` that:

1. Walks outgoing `triggers` edges from `behavior_id` (BFS, respect
   `sequence:` order when present).
2. Collects behaviors reached + their `traces-to` components.
3. Returns a reduced `ArchitectureModel` containing only the flow
   participants + their 1-hop `contains` ancestors.

### Part 16c — Retrofit existing pipeline + add 2 composite behaviors

- Add `sequence: 1..7` to the six existing `BEH-scan → … → BEH-publish`
  triggers in `capabilities.v3.yaml`.
- Add `BEH-mcp-dev-loop` composite (comment-driven authoring loop,
  ordered sub-behaviors).
- Add `BEH-artifact-rebuild` composite (materialize → project → render).

### Part 17a — Call-chain enrichment on composite `traces-to`

Wire `manifest/call_graph.py` output into pipeline emit so that
`traces-to` edges from a **composite** behavior to its component carry
the specific call path (e.g. `pipeline.coordinator.run_stage →
pipeline.observe.scan_ast → ...`). Scoped to composites only to bound
model size.

### Part 17b — `CAP-WK.flow-audit` meta-walk

Declarative walk that audits every composite behavior for:
- Contiguous `sequence:` values (1..N, no gaps).
- Every sub-behavior reachable from the composite root.
- Every `triggers` step landing on an existing behavior id.

Verdicts: `contiguous` | `gap` | `orphan-step` | `dangling-target`.

## Backward-Compat Guarantee

- No schema version bump.
- Empty / missing `sequence:` field roundtrips identically to today.
- Existing fixtures parse byte-identically (digest-stable).
- Composite detection is inferred from data, not declared — no
  Behavior schema change.
