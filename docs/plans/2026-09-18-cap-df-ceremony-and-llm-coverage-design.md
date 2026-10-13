# CAP-DF Parts 10–15 — Ceremony + LLM Coverage + Bundling + Self-Improvement

**Status:** Design (approved 2026-09-18)
**Author:** OpenCode session (superpowers:brainstorming skill)
**Follow-on:** JIT implementation plans per part (`2026-09-18-cap-df-part-10-note-plan.md`, etc.)

---

## Goal

Close the 3 uncovered CAP-DF sub-caps (`CAP-WK.note`, `.save`, `.author`) AND extend the ceremony to cover the entire 29-endpoint LLM surface of the two-repo system (`architecture-model-standard` + `opencode-arch`), enabling:

1. **Coverage** — every LLM call-site is declared, discoverable, and audited by a walk.
2. **Self-improvement evolution** — every LLM call is journaled; a refiner meta-walk feeds signal back into the ceremony (closing the L13 loop over the substrate itself).
3. **Call bundling by task complexity** — task-class taxonomy + tier-aware `BundleScheduler` groups semantically-similar LLM invocations into single provider round-trips.

Terminal state: 14/0/2 walk coverage, 29 endpoints declared, 8 task classes routed via `policy.yaml`, self-improving prompt refinement loop live.

---

## LLM endpoint inventory

The audit that motivated this design surfaced **29 LLM integration points across both repos** (13 AMS + 16 OCA). Only ~3 are touched by the original 3-walk ceremony scope; the remaining 26 have no coverage today.

### AMS-side (13 endpoints)

| # | Endpoint | Location | Kind | Router |
|---|---|---|---|---|
| A1 | `PipelineContext.llm_enrich` (universal stage entry) | `pipeline/protocol.py:219` | Completion | `provider.complete()` |
| A2 | Coordinator `infer` naming | `pipeline/coordinator.py:630` | Enrichment | via A1 |
| A3 | Coordinator `allocate` naming | `pipeline/coordinator.py:674` | Enrichment | via A1 |
| A4 | Coordinator semantic review | `pipeline/coordinator.py:500` | Enrichment | via A1 |
| A5 | `llm_refine` refinement | `pipeline/llm_refine.py:413` | Enrichment | via A1 |
| A6 | Emit-stage review | `pipeline/emit.py:554` | Review | Legacy `llm_callback` |
| A7 | Gap-analysis stage diff | `pipeline/gap_analysis.py:479` | Diff | Legacy `llm_callback` |
| A8 | Provider stamp | `pipeline/emit.py:32` | Provenance | Passive read |
| A9 | Docs component-spec author | `docs/components/author.py:249` | Authoring | Legacy `llm_callback` |
| A10 | Quality code_improver | `quality/code_improver.py:200` | Authoring | Legacy `llm_callback` |
| A11 | Quality orchestrator loop | `quality/orchestrator.py:28` | Orchestration | Wraps A10 |
| A12 | 7 write-back `.llm` variants (Family1/2/3/4/6/7/8) | `lifecycle/projectors/write_back_variants.py` | Structured author | `provider.structured()` |
| A13 | CLI `create_llm_callback` bootstrap | `cli/main.py:829,895,958` | DI factory | Constructs A1's provider |

### OCA-side (16 endpoints)

| # | Endpoint | Location | Kind |
|---|---|---|---|
| B1 | `Policy.pick(TaskClass)` router | `llm/policy.py:120` | Routing (no config yet) |
| B2 | `_FallbackProvider.complete` cascade | `llm/policy.py:70` | Transient fallback |
| B3 | 4 provider adapters (frontier/mcp/mock/relay_ext) | `llm/providers/*.py` | Transport |
| B4 | 3 prompt templates (audit/matching/requirements) | `llm/prompts/*.py` | Prompt catalog |
| B5 | `architect_propose` MCP tool | `mcp/tools/ai/propose.py` | Structured author invoke |
| B6 | `architect_work_issue` orchestrator | `mcp/tools/work_issue.py:272` | Full comment→apply loop |
| B7 | `architect_author` (forward-authoring from requirements) | `mcp/tools/author.py` | Requirement→model |
| B8 | `architect_gate` | `mcp/tools/gate.py` | Gate check |
| B9 | `architect_pipeline` LLM enrichment path | `mcp/tools/pipeline.py` | Pipeline invocation |
| B10 | `architect_llm_audit` (2-stage decomposition) | `mcp/tools/llm_audit.py` | Meta-audit |
| B11 | Requirements LLM extractor + matcher | `requirements/{llm_extractor,matcher}.py` | Requirement authoring |
| B12 | Learning classifier / patterns / lessons | `learning/{classifier,patterns,lessons}.py` | Self-improvement |
| B13 | Regen loop | `cli/regen_loop.py` | Iterative code gen |
| B14 | Calibrate / generate / docs / extract / gap_analyzer CLIs | `cli/{...}.py` | Batch invokes |
| B15 | Job worker | `lifecycle_exec/worker.py` | Job runner (calls A12 via B5) |
| B16 | Package-merge LLM assist | `lifecycle_exec/merge.py`, `mcp/tools/lifecycle/package_merge.py` | 3-way merge |

### Key findings

1. **Two competing entry-point patterns coexist:** legacy `llm_callback` (A6/A7/A9/A10) vs. new `LLMProvider` Protocol (A1/A12). No walk audits which endpoints migrated.
2. **`Policy` routing is code-ready but unused:** no `.architecture/llm/policy.yaml` exists in either repo. `TaskClass` enum is unpopulated. Bundling infra is scaffolded but inert.
3. **Every LLM call already emits `LLMCallRecord`** (`pipeline/protocol.py:230`). Self-improvement telemetry sink exists; nothing consumes it.
4. **7 write-back variants are family-scoped**, not promise-scoped. A `PromisePatchLLM` (Part 12) is the 8th variant.
5. **Prompt templates live in 3 files** with no de-duplication signal.

---

## Layered architecture

```
┌── Layer 3: Self-improvement + bundling (Parts 14–15) ─────────────────┐
│                                                                        │
│    LLMCallRecord journal  ──feeds──►  policy tuner + prompt refiner    │
│    Bundle scheduler       ──groups──►  (task_class, provider, template)│
│                                          │                             │
│  ┌── Layer 2: Endpoint coverage + task-class taxonomy (Part 13) ─────┐│
│  │                                                                   ││
│  │  WALK-llm-endpoint-inventory (audit)                              ││
│  │    ├─ discovers 29 endpoints via AST scan                         ││
│  │    ├─ cross-refs against .architecture/llm/endpoints.yaml         ││
│  │    └─ emits Cards: covered / migrated / legacy / undeclared       ││
│  │                                                                   ││
│  │  TaskClass registry: 8 initial classes                            ││
│  │  Complexity tiers: T1 (local) / T2 (cheap <1k tok) / T3 (>1k tok) ││
│  │                                                                   ││
│  │  ┌── Layer 1: Promise-level ceremony (Parts 10–12) ──────────────┐││
│  │  │                                                               │││
│  │  │  architect_promise_note   (Tier 1, comment store only)        │││
│  │  │  architect_promise_save   (Tier 2, batched)                   │││
│  │  │  architect_promise_author (Tier 3, via PromisePatchLLM+policy)│││
│  │  │                                                               │││
│  │  │  Closes CAP-WK.note / .save / .author                         │││
│  │  └───────────────────────────────────────────────────────────────┘││
│  └───────────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────────────┘
```

**Data flow (L13 loop, promise-scoped, cross-repo):**

```
USER/AGENT                                                                    
   │ inspects open promise (e.g. PR-CAP-DF3-goals)                             
   ├── note ──► architect_promise_note (OCA MCP)                              
   │              └──► WALK-note (AMS meta-walk)                              
   │                     └──► comments/store.append(target={promise ref})      
   │                                                                          
   ├── save ──► architect_promise_save (OCA MCP)                              
   │              └──► WALK-save (AMS meta-walk)                              
   │                     └──► ai/proposals.WorkOrder.submit                    
   │                            {intent: fill_promise, entity, attribute}      
   │                                                                          
   └── author ──► architect_promise_author (OCA MCP, requires WO_id)          
                    └──► WALK-author (AMS meta-walk)                          
                           └──► PromisePatchLLM (new .llm variant)             
                                  ├── Policy.pick(TaskClass("authoring"))     
                                  ├── provider.structured(schema)              
                                  └── emit ModelPatch proposal                 
                                        │                                     
                                        └──► proposal_apply → model update    
```

Enforcement: `architect_promise_author` REQUIRES a valid `work_order_id` whose `provenance.entity_id` + `provenance.attribute` pin the target promise. Standalone invocation returns `PRECONDITION_FAILED`. L13 loop is contractually strict.

---

## Per-part deliverable detail

### Part 10 — `CAP-WK.note` (~200 LOC, 1 commit)

**AMS:**
- `src/architecture_model/walks/meta/promise_note.py` (new, ~80 LOC). Python meta-walk. Docstring: ``Realizes ``CAP-WK.note``.``
  - `note_promise(model, entity_id, attribute, text) -> Comment` — validates entity+attr, appends via `comments/store.py`, returns comment with `target = {kind: "promise", entity_id, attribute}`.
- `src/architecture_model/comments/models.py` (edit, ~20 LOC): extend `Comment` with optional `target: PromiseTarget | None`.
- `tests/walks/meta/test_promise_note.py` (new, ~120 LOC): 8 tests (append, target-validation, unknown-entity, unknown-attribute, idempotency, multi-note-per-promise, target roundtrip, docstring parses for meta-coverage).

**OCA:**
- `mcp/tools/promise_note.py` (new, ~60 LOC): `architect_promise_note(repo_path, entity_id, attribute, text) -> {ok, comment_id}`.
- Wire in `mcp/server.py` tool registry.
- `tests/mcp/test_promise_note_tool.py` (new, ~80 LOC): 5 tests.

**Model wire:** `.architecture/model/capabilities.v3.yaml` — mark `PR-CAP-WK-note-intent` `status: verified`, add `verified_by` entries.

**Coverage bump:** 9 → 10 covered.

### Part 11 — `CAP-WK.save` (~250 LOC, 1 commit)

**AMS:**
- `src/architecture_model/walks/meta/promise_save.py` (new, ~100 LOC): `save_promise(model, comment_id) -> WorkOrder`. Reads comment, validates it has a promise target, constructs `WorkOrder.intent = {kind: "fill_promise", entity_id, attribute, source_comment_id}`, submits via existing `ai/proposals.py`.
- `tests/walks/meta/test_promise_save.py` (new, ~150 LOC): 8 tests including idempotency (re-save same comment → same WorkOrder).

**OCA:**
- `mcp/tools/promise_save.py` (new, ~80 LOC): `architect_promise_save(repo_path, comment_id) -> {ok, work_order_id}`. Delegates to existing `mcp/tools/ai/workorder_submit.py` for wire submission; adds promise-scope validation on top.
- `tests/mcp/test_promise_save_tool.py` (new, ~80 LOC).

**Coverage bump:** 10 → 11 covered.

### Part 12 — `CAP-WK.author` (~350 LOC, 1 commit)

**AMS:**
- `src/architecture_model/lifecycle/projectors/write_back_variants.py` (edit, ~80 LOC): add `PromisePatchLLM` class (8th variant, promise-scoped).
  - `base_projector_name = "family1.entity_page"` (reuses entity page as base)
  - `build_prompt(base_view, fragment, config)` — reads `config["entity_id"]` + `config["attribute"]`, builds a prompt asking for that specific attribute's content in canonical shape (list of strings, matching v3 promise `content` field).
  - `expected_proposal_schema()` — JSON schema for a single-attribute fill.
  - `pack_proposal(raw, fragment, config)` — emits a `ModelPatch` targeting `entities.<kind>[?id==entity_id].promises[?attribute==attribute].content`.
- `src/architecture_model/walks/meta/promise_author.py` (new, ~120 LOC): `author_promise(model, work_order_id, provider) -> Proposal` — enforces WorkOrder existence + provenance match, dispatches `PromisePatchLLM` variant, returns proposal.
- `tests/walks/meta/test_promise_author.py` (new, ~180 LOC): 10 tests using `MockProvider` (from OCA); covers WorkOrder-missing → PRECONDITION_FAILED, provenance mismatch, LLM returns malformed JSON → SCHEMA_VIOLATION, happy path emits well-formed patch.

**OCA:**
- `mcp/tools/promise_author.py` (new, ~120 LOC): `architect_promise_author(repo_path, work_order_id, task_class="authoring") -> {ok, proposal_id}`. Resolves provider via existing `Policy.pick(TaskClass("authoring"))`. Falls back to `MockProvider` when no `policy.yaml` exists (activated in Part 14).
- `tests/mcp/test_promise_author_tool.py` (new, ~100 LOC).

**Model wire:** `CAP-WK.author` verified.

**Coverage bump:** 11 → 12 covered. **All 3 Part-4 sub-caps closed.**

### Part 13 — `CAP-WK.llm-endpoint-inventory` (~400 LOC, 1 commit)

**AMS:**
- `src/architecture_model/walks/meta/llm_endpoint_inventory.py` (new, ~180 LOC): AST-scans BOTH repos (import path via `sys.path` inspection).
  - Detects call sites matching: `provider.complete`, `provider.structured`, `provider.stream`, `ctx.llm_enrich`, `llm_callback(`, `run_via_policy`.
  - Cross-references against `.architecture/llm/endpoints.yaml` (declared inventory).
  - Emits Cards per endpoint: `covered` (declared + AST-visible), `undeclared` (AST-visible, not in inventory), `stale` (declared, no AST match), `legacy` (uses `llm_callback` instead of Protocol).
  - Discovers task_class + tier from `endpoints.yaml`.
- `.architecture/llm/endpoints.yaml` (new, ~250 lines): declares all 29 endpoints with `{id, location, kind, task_class, tier, migration_status, prompt_template?}`.
- `tests/walks/meta/test_llm_endpoint_inventory.py` (new, ~150 LOC).

**OCA:** none (audit walk stays AMS-side; OCA endpoints scanned via cross-repo AST).

**Model wire:** add `CAP-WK.llm-endpoint-inventory` sub-cap, mark `verified`.

**Coverage bump:** 12 → 13 covered.

### Part 14 — Bundle scheduler + policy activation (~300 LOC, 1 commit)

**AMS:** no changes (routing lives OCA-side).

**OCA:**
- `llm/bundle.py` (new, ~150 LOC): `BundleScheduler.schedule(work_orders: list[WorkOrder]) -> list[Bundle]`. Groups by `(task_class, provider, prompt_template)`. Enforces `max_cost_usd_per_call` per bundle. Emits `Bundle{work_order_ids, prompt (batched), provider, model}`.
- `.architecture/llm/policy.yaml` (new, ~60 lines): 8 task classes with routing rules — `naming` → cheap Haiku, `authoring` → Sonnet, `merge` → Opus, etc.
- `mcp/tools/promise_author.py` (edit): accept `work_order_ids: list[str]`, dispatch via `BundleScheduler`.
- `tests/llm/test_bundle_scheduler.py` (new, ~120 LOC): 10 tests covering bundling correctness, cost cap, fallback on transient error.

**Coverage:** no CAP-WK bump; substrate hardening for existing walks.

### Part 15 — LLMCallRecord journal + prompt refiner (~250 LOC, 1 commit)

**AMS:**
- `src/architecture_model/feedback/llm_calls.py` (new, ~120 LOC): append-only JSONL at `.architecture/llm_calls.jsonl`. Ingests `LLMCallRecord` from `PipelineContext.llm_calls`. Schema: `{stage, endpoint_id, task_class, tokens_in, tokens_out, duration_ms, provider, model, prompt_digest, response_digest, timestamp}`.
- `src/architecture_model/walks/meta/prompt_refiner.py` (new, ~100 LOC): analyzes journal, detects prompts with high failure rate / high retry count / high cost variance. Emits Cards per prompt template: `stable`, `high-failure`, `high-cost`, `unused`.
- `tests/feedback/test_llm_calls_journal.py` + `tests/walks/meta/test_prompt_refiner.py` (new).

**OCA:** wire `LLMCallRecord` emission into every provider adapter's `complete`/`structured`/`stream` path (~50 LOC edit across 4 provider files).

**Model wire:** add `CAP-WK.prompt-refinement` sub-cap, mark verified.

**Coverage bump:** 13 → 14 covered.

---

## TaskClass taxonomy (Part 13 declares, Part 14 activates)

| TaskClass | Endpoints | Tier | Routing default |
|---|---|---|---|
| `naming` | A2, A3 | T2 | Haiku/mini |
| `enrichment` | A1, A4, A5 | T2 | Haiku/mini |
| `review` | A6 | T2 | Haiku |
| `authoring` | A9, A10, A12 (7 variants), Part 12 `PromisePatchLLM` | T3 | Sonnet |
| `diff` | A7 | T2 | Haiku |
| `gate` | B8 | T2 | Haiku |
| `decomposition` | B10 | T3 | Sonnet/Opus |
| `merge` | B16 | T3 | Opus |

Tiers control bundling window: T1 = never bundle (no LLM); T2 = bundle up to 10 same-class calls per window; T3 = bundle up to 3 (larger context).

---

## Bundling algorithm (Part 14)

```
INPUT:  list[WorkOrder]  (each carries entity_id, attribute, task_class)

Group by (task_class, provider, model, prompt_template_id)
  For each group:
    If tier == T1: dispatch individually (no LLM anyway)
    If tier == T2: batch up to 10 into one call, one prompt with numbered items
    If tier == T3: batch up to 3 with structured schema union
  Enforce: sum(cost_estimate) <= rule.max_cost_usd_per_call * bundle_size

OUTPUT: list[Bundle]  (each = one provider round-trip → many results)
```

Bundle results are demultiplexed via item-index in prompt. Failed items in a bundle degrade to individual retry via `_FallbackProvider`.

---

## Self-improvement journal (Part 15)

`LLMCallRecord` is already emitted at every call site (proven at `pipeline/protocol.py:230`). Part 15 adds:

- **Sink** — `.architecture/llm_calls.jsonl` (append-only)
- **Consumer** — `prompt_refiner.py` meta-walk

Refiner outputs feed CAP-DF ceremony:
- `high-failure` prompt → auto-file a `promise_note` on the endpoint's `CAP-WK.<id>` sub-cap (closes L13 loop back to itself).
- `unused` prompt → mark endpoint stale in `endpoints.yaml`.
- `high-cost` prompt → escalate to promotion review.

The ceremony **audits itself** through this loop — L13 pattern applied to the LLM substrate.

---

## Testing strategy

| Layer | Strategy | Speed |
|---|---|---|
| Meta-walks (Parts 10/11/12/13/15) | Unit tests with synthetic model fixtures; no LLM | <1s each |
| `PromisePatchLLM` (Part 12) | Unit tests with `MockProvider` returning canned structured output | <1s |
| `BundleScheduler` (Part 14) | Unit tests with `MockProvider` + cost calculator | <1s |
| MCP tools (all parts) | Unit tests directly invoking tool functions; no MCP server | <1s each |
| Cross-repo integration | One smoke test per part: full ceremony round-trip on tmp repo, mock provider | ~5s each |
| Real-LLM smoke (opt-in) | Env-gated (`AMS_ENABLE_LIVE_LLM=1`); one test per task_class hitting real provider via policy.yaml; NOT in CI | ~30s each |

**No live LLM calls in CI.**

---

## Coverage impact summary

| After part | Covered | Uncovered | Duplicate-walk | Notes |
|---|---|---|---|---|
| Part 9 (shipped) | 9 | 3 | 2 | note/save/author still open |
| Part 10 | 10 | 2 | 2 | note closed |
| Part 11 | 11 | 1 | 2 | save closed |
| Part 12 | 12 | 0 | 2 | **All Part-4 sub-caps closed** |
| Part 13 | 13 | 0 | 2 | + LLM endpoint inventory |
| Part 14 | 13 | 0 | 2 | Bundling substrate (no walk added) |
| Part 15 | 14 | 0 | 2 | + prompt refiner |

Additionally by Part 15: 29 LLM endpoints declared in `endpoints.yaml`; 8 task classes routed via `policy.yaml`; every LLM call journaled and refined; ceremony closes L13 loop over its own substrate.

---

## Guardrails

- **One commit per part**, explicit `git add` paths (no `git add -A`).
- `python` (anaconda), not `python3`.
- **No live LLM calls in CI** — env-gated smoke tests only.
- **Verification-before-claims:** `pytest tests/walks/ -q` + `pytest tests/ -q --ignore=tests/test_config_loader.py` must pass before each part's commit.
- **Additive over rewrites** — existing `promotion.v3.yaml`, `.llm` variants, `work_issue.py` untouched.
- **JIT implementation plans** — only Part 10 plan written now; Parts 11–15 get their own plans just-in-time when each is ready to ship.

---

## Next step

Invoke `writing-plans` skill to produce `docs/plans/2026-09-18-cap-df-part-10-note-plan.md` (Part 10 only).
