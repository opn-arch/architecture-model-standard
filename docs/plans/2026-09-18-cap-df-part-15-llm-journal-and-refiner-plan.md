# CAP-DF Part 15 — LLMCallRecord journal + prompt refiner

**Date:** 2026-09-18
**Author:** JIT plan derived from master design `docs/plans/2026-09-18-cap-df-ceremony-and-llm-coverage-design.md` (`ca8b3c0`).
**Status:** draft — execute after Part 14 (OCA `f0d263a` / AMS `8cd21b2`).

## Goal

Close the CAP-DF loop by:

1. Adding an append-only journal at `.architecture/llm_calls.jsonl` that ingests `LLMCallRecord` events from every LLM call site.
2. Adding a `prompt_refiner` meta-walk that analyzes the journal and emits Cards per prompt template: `stable`, `high-failure`, `high-cost`, `unused`.
3. Wiring `LLMCallRecord` emission into OCA's four provider adapters (`mock`, `frontier`, `mcp`, `relay_ext`) so real LLM traffic feeds the journal.

**Coverage impact:** 13 → **14 covered** (adds `CAP-WK.prompt-refinement`). Terminal CAP-DF state.

## Scope

**Split AMS/OCA work.** AMS owns the journal writer + refiner walk + tests. OCA owns provider-adapter wiring + writer callback plumbing.

## Design decisions (locked)

1. **Journal format:** append-only JSONL at `<repo>/.architecture/llm_calls.jsonl`. One `LLMCallRecord` per line. Reuses the existing AMS dataclass (`pipeline/protocol.py:269`) — no new schema. Fields: `stage, purpose, timestamp, files_sent, slices_sent, prompt_template, prompt_tokens, context_tokens, completion_tokens, total_tokens, model, duration_ms, cached, output_used, confidence, items_produced, notes, resolution_id`.

2. **Append semantics:** identical pattern to `feedback/gates.py` — `O_APPEND | O_CREAT | O_WRONLY` + `fsync`. Concurrent writers safe on POSIX. Fail-soft: journal write errors never crash the caller (best-effort logging only).

3. **Additive fields:** the existing `LLMCallRecord` lacks `endpoint_id` (Part 13 concept) and `task_class` (Part 14 concept). Rather than mutate the dataclass, the journal `append()` accepts optional `endpoint_id: str = ""` and `task_class: str = ""` params, folded into the emitted JSON line alongside the dataclass fields. Backward-compat preserved for existing `LLMCallRecord` consumers.

4. **Refiner heuristics (first cut, deterministic):**
   - `high-failure` — prompt_template with `output_used=False` rate ≥ 30% AND ≥ 3 calls total.
   - `high-cost` — prompt_template whose median `total_tokens` is ≥ 4× the median across all templates AND ≥ 3 calls total.
   - `unused` — declared endpoint (from `.architecture/llm/endpoints.yaml`) with 0 journal entries.
   - `stable` — declared + present + doesn't trip high-failure or high-cost.

   Thresholds are constants at module top for easy tuning; not configurable in Part 15.

5. **Card schema:** dataclass `PromptTemplateCard(template_id: str, verdict: str, details: dict)`. `details` carries `{sample_size, failure_rate, median_tokens, endpoint_id?}`. Verdicts are the 4 above.

6. **Refiner input:**
   - Journal path: `<repo>/.architecture/llm_calls.jsonl` (missing → treated as empty).
   - Declared endpoints: `<repo>/.architecture/llm/endpoints.yaml` (missing → skip `unused` detection).

7. **Provider-adapter wiring (OCA):** each provider gains an optional `journal_appender: Callable[[LLMCallRecord], None] | None = None` constructor param. When set, each `complete/structured/stream` call constructs an `LLMCallRecord` with fields it knows (stage="external", purpose from prompt template hint, model, tokens, duration) and invokes `journal_appender(record)`. When `None` (default), providers are silent — Part 15's opt-in wiring keeps existing tests untouched.

8. **Testing strategy:**
   - AMS: unit tests for journal `append()` (atomicity + fail-soft), refiner (each verdict path with synthetic JSONL fixtures + endpoints.yaml).
   - OCA: unit test for one provider adapter (mock) with a stub journal_appender to prove the wiring; other 3 adapters get the constructor param but tests remain provider-focused.

## Deferred (out of scope for Part 15)

- **Feedback loop back into ceremony** — master design says `high-failure` prompt → auto-file `promise_note` on the endpoint's `CAP-WK.<id>` sub-cap. That's Part 16 (CAP-DF self-healing). Part 15 emits Cards but doesn't auto-file notes.
- **Cross-repo journal aggregation.** AMS journal is per-repo. Reading OCA's `.architecture/llm_calls.jsonl` from AMS is a follow-up.
- **Automatic ingestion into `endpoints.yaml`.** Discovered stale/undeclared endpoints don't rewrite the YAML; Part 13's walk still gates that.

## Task list

1. **AMS: create `src/architecture_model/feedback/llm_calls.py`** — `LLMCallEvent` (wraps `LLMCallRecord` + optional endpoint_id/task_class), `append(repo, record, endpoint_id="", task_class="")`, `read(repo) -> list[dict]`. Mirrors `feedback/gates.py` pattern.
2. **AMS: create `src/architecture_model/walks/meta/prompt_refiner.py`** — `refine_prompts(repo_path) -> RefinerReport`. Docstring includes `Realizes ``CAP-WK.prompt-refinement``` marker.
3. **AMS: write `tests/feedback/test_llm_calls_journal.py`** — 6 tests: append happy path, missing dir auto-created, round-trip read, fail-soft on unwritable path, endpoint_id/task_class fields present in JSON, concurrent-safe (skip on non-POSIX).
4. **AMS: write `tests/walks/meta/test_prompt_refiner.py`** — 8 tests: each verdict, missing journal, missing endpoints.yaml, mixed real signal.
5. **AMS: wire `CAP-WK.prompt-refinement` sub-cap** in `.architecture/model/capabilities.v3.yaml` after `CAP-WK.llm-endpoint-inventory`; flip `PR-CAP-WK-prompt-refinement-intent` to `verified` with 3 `verified_by` entries.
6. **AMS: update `CONTEXT.md`** — Part 15 additions block after Part 14 block. Coverage bump to 14.
7. **AMS: verification gate** — full pytest (~4334 → ~4348), meta-coverage audit shows 14 covered / 0 uncovered.
8. **AMS: commit** — `feat(model): Part 15 — CAP-WK.prompt-refinement (LLM journal + prompt refiner)`.
9. **OCA: edit `src/opencode_arch/llm/providers/mock.py`** — add optional `journal_appender` param; emit `LLMCallRecord` post-call.
10. **OCA: edit `frontier.py`, `mcp.py`, `relay_ext.py`** — same additive param (real providers already track tokens; just wire the callback).
11. **OCA: write `tests/llm/test_provider_journal_wiring.py`** — 3 tests using MockProvider with stub appender.
12. **OCA: verification gate** — full pytest (~1105 → ~1108).
13. **OCA: commit** — `feat(mcp): Part 15 — LLMCallRecord emission in provider adapters (CAP-DF)`.

## Files created / modified

**AMS new:**
- `src/architecture_model/feedback/llm_calls.py`
- `src/architecture_model/walks/meta/prompt_refiner.py`
- `tests/feedback/test_llm_calls_journal.py`
- `tests/walks/meta/test_prompt_refiner.py`

**AMS modified:**
- `.architecture/model/capabilities.v3.yaml` (add sub-cap + flip promise)
- `CONTEXT.md` (Part 15 additions block)

**OCA new:**
- `tests/llm/test_provider_journal_wiring.py`

**OCA modified:**
- `src/opencode_arch/llm/providers/{mock,frontier,mcp,relay_ext}.py` (add `journal_appender` param)

## Success criteria

- All AMS tests pass (~4334 + 14 new = ~4348).
- All OCA tests pass (1105 + 3 new = 1108).
- Meta-coverage audit reports **14 covered / 2 duplicate-walk / 0 uncovered**.
- Refiner correctly classifies synthetic fixtures into all 4 verdicts.
- Journal survives directory-missing / concurrent-write scenarios (fail-soft verified).
- Provider adapter wiring is opt-in — `journal_appender=None` default preserves all existing test behavior.

## Guardrails

- Two commits (AMS + OCA). Explicit `git add` paths.
- `python` (anaconda), not `python3`.
- No live LLM. Provider tests use canned mock.
- Additive over rewrites: `LLMCallRecord` schema untouched; provider constructors gain optional param only.
- Journal fail-soft: journal errors NEVER propagate to caller (matches Phase 2 gates/drift pattern).
