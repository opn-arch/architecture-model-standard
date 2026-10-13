# CAP-DF Part 14 — Bundle scheduler + policy activation

**Date:** 2026-09-18
**Author:** JIT plan derived from master design `docs/plans/2026-09-18-cap-df-ceremony-and-llm-coverage-design.md` (`ca8b3c0`).
**Status:** draft — execute after Part 13 (AMS `087785d`).

## Goal

Activate the (currently code-ready but inert) OCA `Policy` router by:

1. Adding `BundleScheduler` — groups `WorkOrder`s by `(task_class, provider, model, prompt_template_id)` and enforces tier-aware batching windows (T1 = never, T2 ≤ 10, T3 ≤ 3).
2. Declaring the 8-task-class routing table in `.architecture/llm/policy.yaml` (OCA-side).
3. Extending `architect_promise_author` to accept a **list** of `job_id`s and dispatch them through the scheduler in a single provider round-trip per bundle.

**Coverage impact:** none (no walk added). Substrate hardening for existing walks.

## Scope

**OCA-only work.** No AMS changes. AMS's Part 13 endpoints.yaml already declares `task_class` and `tier` for all 29 endpoints; Part 14 consumes those declarations from the routing table.

## Design decisions (locked)

1. **Bundle grouping key:** `(task_class, provider_name, model, prompt_template_id)`. `prompt_template_id` comes from the WorkOrder's `intent` field (`fill_promise` maps to template `fill_promise`). WOs with no template default to their `task_class` name — coarse but deterministic.

2. **Tier lookup:** From the routing rule's optional `tier: T1|T2|T3` field (added to `policy.yaml` schema). Absent → T2 default. T1 → dispatch individually (no LLM at all — used for local-only tasks like `provenance`). T2 → batch up to **10**. T3 → batch up to **3**.

3. **Batched prompt shape (T2/T3):** A single prompt with numbered items:
   ```
   You have N tasks. For each numbered item, produce the response.
   Return a JSON object with keys "1", "2", ..., "N".

   ITEM 1:
   <sub-prompt 1>

   ITEM 2:
   <sub-prompt 2>
   ...
   ```
   Response demux by string index. Malformed / missing indices → per-item degrade to individual retry via `_FallbackProvider` on next scheduler pass.

4. **Cost cap enforcement:** `sum(cost_estimate) <= rule.max_cost_usd_per_call * bundle_size`. Cost estimate = `provider.tokenize(prompt) * unit_cost`. If a candidate item would exceed the cap, close the current bundle and open a new one. `unit_cost` defaults to `0.0` when unset (real cost tracking is Part 15).

5. **Policy YAML schema extension:** existing schema already has `rules: {task_class: {provider, model, max_cost_usd_per_call, fallback}}`. Part 14 adds optional `tier: T1|T2|T3` per rule. Backward-compatible — `load_policy` treats missing tier as `T2`.

6. **Task-class inventory (matches master design § "TaskClass taxonomy"):**
   | TaskClass | Tier | Provider (default) | Model |
   |---|---|---|---|
   | `naming` | T2 | mock | mock-haiku |
   | `enrichment` | T2 | mock | mock-haiku |
   | `review` | T2 | mock | mock-haiku |
   | `authoring` | T3 | mock | mock-sonnet |
   | `diff` | T2 | mock | mock-haiku |
   | `gate` | T2 | mock | mock-haiku |
   | `decomposition` | T3 | mock | mock-sonnet |
   | `merge` | T3 | mock | mock-opus |

   All 8 default to the `mock` provider — real-provider activation is opt-in per site (edit `policy.yaml` post-install). `global_budget_usd: 10.0`, `retry_backoff: [1.0, 2.0, 4.0]`.

7. **Tool signature evolution:** `architect_promise_author` gains a **new optional parameter** `job_ids: list[str] | None = None` alongside the existing single `job_id: str`. If `job_ids` is present, it takes precedence and `job_id` is ignored. Backward-compat preserved: existing single-job callers work unchanged. Response for batched call: `{ok: True, results: [{job_id, proposal_id, work_order_id}, ...]}`. Single-job response shape unchanged.

8. **Testing strategy:** Unit tests with a stub `MockProvider` returning canned structured output keyed by prompt-hash. Bundling correctness (group membership, tier caps), cost cap enforcement, tier=T1 individual dispatch, degrade-on-malformed-response, mixed-tier scheduling. All hermetic — `tmp_path` repos with fixture policy.yaml + WOs. Target <2s total.

## Deferred (out of scope for Part 14)

- **Real cost tracking.** `LLMCallRecord` journaling lands in Part 15; Part 14 uses `tokenize()` for pre-flight estimation only, no post-call spend tracking beyond `Policy.spend()` already exists.
- **Adaptive tier promotion.** No feedback loop from failure rates to tier reassignment (Part 15's refiner does that).
- **Live-LLM smoke tests.** Env-gated tests deferred.
- **AMS-side endpoint invocation retrofit.** The 13 AMS endpoints in Part 13 inventory continue calling `provider.complete/structured` directly — routing them through OCA's `Policy` is a follow-up (candidate lesson: cross-repo routing bridge).

## Task list

1. **Write `src/opencode_arch/llm/bundle.py`** — `Bundle` dataclass + `BundleScheduler.schedule(work_orders, policy) -> list[Bundle]` + `BundleScheduler.dispatch(bundle, provider) -> list[dict]` for demux.
2. **Create `.architecture/llm/policy.yaml`** (OCA repo) — declare 8 task classes with the tier field. Format matches `load_policy` schema.
3. **Edit `src/opencode_arch/llm/policy.py`** — add optional `tier` field to `RoutingRule` (default `"T2"`), extend `load_policy` to parse it. Additive; existing tests pass unchanged.
4. **Edit `src/opencode_arch/mcp/tools/promise_author.py`** — add `job_ids: list[str] | None = None` parameter; when set, iterate through bundles produced by `BundleScheduler.schedule`; return `{ok, results: [...]}` shape. Keep single-job path unchanged for backward compat.
5. **Write `tests/llm/test_bundle_scheduler.py`** — 10+ tests covering: group-by key, T1 individual dispatch, T2 max-10, T3 max-3, cost cap splits bundle, prompt shape (numbered items), demux happy path, malformed response degrade, mixed-tier batch, empty input.
6. **Write `tests/mcp/test_promise_author_batch.py`** — 3–4 tests covering batched invocation happy path, mixed success/failure per bundle, single-job backward compat.
7. **Verification gate** — full OCA pytest (`pytest tests/ -q --ignore=tests/logs_db/test_client.py`) passes; existing 1081 passed count unchanged + new tests.
8. **Commit (OCA)** — `feat(mcp): Part 14 — BundleScheduler + policy activation (CAP-DF)`.

## Files created / modified

**OCA new:**
- `src/opencode_arch/llm/bundle.py`
- `.architecture/llm/policy.yaml`
- `tests/llm/test_bundle_scheduler.py`
- `tests/mcp/test_promise_author_batch.py`

**OCA modified:**
- `src/opencode_arch/llm/policy.py` (add `tier` field, additive)
- `src/opencode_arch/mcp/tools/promise_author.py` (add `job_ids` param)

**AMS modified:**
- `CONTEXT.md` — Part 14 additions block (OCA-side highlights, referenced from AMS CONTEXT for coherence).

## Success criteria

- All OCA tests pass (baseline 1081 + new bundle + batch tests).
- `BundleScheduler.schedule` on hand-crafted WO lists produces deterministic groupings matching the design's key.
- T3 authoring bundle with 5 WOs produces 2 bundles (3 + 2), not 1.
- Cost cap: bundle with 4 WOs whose estimated cost exceeds `max_cost_usd_per_call * 4` gets split at the boundary.
- `architect_promise_author(job_ids=[a, b, c])` with 3 queued authoring jobs on 3 different promise notes completes all 3 in one bundled provider round-trip (verified by call-count assert on mock provider).
- Single-job call `architect_promise_author(job_id=x)` returns unchanged response shape (guarded by an unchanged Part 12 test).
- Meta-coverage audit unchanged: 13 covered / 2 duplicate-walk / 0 uncovered.

## Guardrails

- One commit (OCA). Explicit `git add` paths.
- `python` (anaconda), not `python3`.
- No live LLM. All tests use canned mock provider.
- Additive over rewrites: `policy.py` schema extension is optional-field only; `promise_author.py` new param is optional.
- Verify OCA pytest baseline before commit.
